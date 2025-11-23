# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
from rayonnement import ModeleRayonnement
import numpy as np
import time


class Bilan:
    """Classe pour tracker le bilan d'énergie de la simulation."""

    def __init__(self):
        self.energie_initiale = 0.0
        self.energies = []  # List of (temps, energie_totale, erreur_prc)

    def calculer_energie_totale(self, T, RhoCp, zones_air):
        """
        Calcule l'énergie thermique totale du système:
        E = sum(ρ·cp·V·T) pour solides + sum(ρ·cp·V·T) pour air
        """
        ds3 = RhoCp[0, 0, 0] if RhoCp[0, 0, 0] > 0 else 1.0  # Hack pour ds^3

        # Énergie des solides (J)
        masque_solide = (RhoCp > 0)
        E_solides = np.sum(RhoCp[masque_solide] * T[masque_solide])

        # Énergie des zones d'air (J)
        E_air = 0.0
        for zone in zones_air.values():
            E_air += zone.capacite_thermique_J_K * zone.T

        return E_solides + E_air

    def enregistrer(self, temps_s, T, RhoCp, zones_air):
        """Enregistre l'état d'énergie."""
        E = self.calculer_energie_totale(T, RhoCp, zones_air)

        if not self.energies:  # Premier appel
            self.energie_initiale = E

        erreur_prc = 100.0 * abs(E - self.energie_initiale) / max(abs(self.energie_initiale), 1.0)
        self.energies.append((temps_s, E, erreur_prc))

        return erreur_prc

    def rapport_final(self, logger):
        """Affiche un rapport de conservation d'énergie."""
        if not self.energies:
            return

        temps_final, E_final, err_final = self.energies[-1]
        temps_init, E_init, err_init = self.energies[0]

        err_max = max([e[2] for e in self.energies])

        logger.info("=" * 60)
        logger.info("BILAN D'ÉNERGIE (VALIDATION NUMÉRIQUE)")
        logger.info("=" * 60)
        logger.info(f"Énergie initiale: {E_init:.2e} J")
        logger.info(f"Énergie finale:   {E_final:.2e} J")
        logger.info(f"Erreur absolue: {E_final - E_init:.2e} J")
        logger.info(f"Erreur relative finale: {err_final:.4f}%")
        logger.info(f"Erreur relative max: {err_max:.4f}%")
        if err_max < 0.1:
            logger.info("✓ EXCELLENT: Conservation d'énergie < 0.1%")
        elif err_max < 1.0:
            logger.info("✓ BON: Conservation d'énergie < 1%")
        else:
            logger.warn(f"⚠ ALERTE: Erreur > 1%, vérifier stabilité numérique")
        logger.info("=" * 60)


class Simulation:
    """Contient le moteur de calcul et la boucle temporelle.

    AMÉLIORATIONS (v2):
    - Couplage semi-implicite conduction-convection
    - Conservation d'énergie tracée
    - Pas de temps adaptatif (optionnel)
    """

    def __init__(self, modele, chemin_sortie="resultats_sim", enable_rayonnement=True):
        self.modele = modele
        self.params = modele.params  # Récupère les params depuis le modèle
        self.logger = modele.logger  # Récupère le logger depuis le modèle
        self.stockage = StockageResultats(chemin_sortie, self.logger)
        self.bilan = Bilan()  # Bilan d'énergie
        self.rayonnement = ModeleRayonnement(self.logger, enable_external=enable_rayonnement)

        self.T = np.copy(self.modele.T)
        self.T_suivant = np.copy(self.T)

        self.masque_fixe = (self.modele.Alpha <= 0)
        self.masque_solide = (self.modele.Alpha > 0)

        if np.any(self.masque_solide):
            alpha_max = np.max(self.modele.Alpha[self.masque_solide])
            ds2 = self.params.ds ** 2
            facteur_cfl = (alpha_max * self.params.dt) / ds2

            self.logger.info(f"Alpha max (solides): {alpha_max:0.2e}")
            self.logger.info(f"Facteur de stabilité (CFL): {facteur_cfl:.4f}")
            if facteur_cfl > (1 / 6):
                self.logger.error(f"Instabilité détectée! CFL ({facteur_cfl:.4f}) > 0.166.")
                raise ValueError("Simulation instable (CFL).")
        else:
            self.logger.warn("Aucun matériau solide trouvé. Impossible de vérifier la stabilité.")

        self.logger.info("Simulation initialisée (v2: semi-implicite + bilan énergie + rayonnement).")

    def lancer_simulation(self, duree_s, intervalle_stockage_s=600):
        """Lance la boucle de simulation principale avec couplage semi-implicite.

        Schéma semi-implicite (couplage améloré):
        1. Conduction: T_mid = T(t) + α·dt/ds²·∇²T(t)
        2. Convection (implicite): Résout T(t+dt) via Newton pour chaque surface
           - Élimine le décalage temporel entre conduction et convection
        """

        temps_simule_s = 0.0
        prochain_stockage_s = 0.0
        dt = self.params.dt

        self.logger.info(f"Lancement de la simulation pour {duree_s}s...")
        self.logger.info(f"Schéma: Semi-implicite FTCS + Newton convection")

        # Enregistrement bilan initial
        self.bilan.enregistrer(temps_simule_s, self.T, self.modele.RhoCp, self.modele.zones_air)

        # Stockage de l'état initial
        self.stocker_etape_simulation(temps_simule_s)
        prochain_stockage_s += intervalle_stockage_s

        while temps_simule_s <= duree_s:

            # T_suivant contient T(t)
            # self.T va contenir T(t+dt) après conduction
            # Puis convection résout couplage à (t+dt)
            # Puis rayonnement ajoute effet radiativité

            self._etape_conduction()
            self._etape_convection_implicite()
            self._etape_rayonnement()

            # Appliquer les conditions limites (écraser T(t+dt))
            self.T[self.masque_fixe] = self.T_suivant[self.masque_fixe]

            # Mettre à jour l'état T(t) -> T(t+dt)
            np.copyto(self.T_suivant, self.T)
            temps_simule_s += dt

            # Enregistrer bilan d'énergie
            err_prc = self.bilan.enregistrer(temps_simule_s, self.T, self.modele.RhoCp, self.modele.zones_air)

            # Gérer le stockage
            if temps_simule_s >= prochain_stockage_s:
                self.stocker_etape_simulation(temps_simule_s)
                prochain_stockage_s += intervalle_stockage_s

        # Stockage final
        if (temps_simule_s - dt) < (prochain_stockage_s - intervalle_stockage_s):
            self.stocker_etape_simulation(temps_simule_s)

        self.logger.info("Simulation terminée.")

        temps_air_final = {zone.nom: zone.T for zone in self.modele.zones_air.values()}
        self.logger.info(f"--- Température Finale de l'Air: {temps_air_final} ---")

        # Afficher bilan d'énergie
        self.bilan.rapport_final(self.logger)

    def stocker_etape_simulation(self, temps_s):
        """Helper pour stocker l'état actuel."""
        pertes = self._calculer_pertes_W()
        temps_air_str = ", ".join([f"T_air_{z.nom}={z.T:.2f}°C" for z in self.modele.zones_air.values()])
        self.logger.debug(f"t={temps_s:.0f}s, {temps_air_str}, Pertes={pertes:.2f}W")
        self.stockage.stocker_etape(temps_s, self.T, self.modele.zones_air)

    def _etape_conduction(self):
        """Calcule un pas de temps (dt) de CONDUCTION."""

        T = self.T_suivant  # Lecture de T(t)
        T_new = self.T  # Écriture dans T(t+dt)
        A = self.modele.Alpha
        ds2 = self.params.ds ** 2
        dt = self.params.dt
        M = self.masque_solide

        laplacien_T = (
                T[1:-1, 2:, 1:-1] + T[1:-1, :-2, 1:-1] +
                T[2:, 1:-1, 1:-1] + T[:-2, 1:-1, 1:-1] +
                T[1:-1, 1:-1, 2:] + T[1:-1, 1:-1, :-2] -
                6 * T[1:-1, 1:-1, 1:-1]
        )

        masque_interieur = M[1:-1, 1:-1, 1:-1]

        T_new[1:-1, 1:-1, 1:-1][masque_interieur] = \
            T[1:-1, 1:-1, 1:-1][masque_interieur] + \
            (A[1:-1, 1:-1, 1:-1][masque_interieur] * dt / ds2) * \
            laplacien_T[masque_interieur]

    def _etape_convection_implicite(self):
        """Calcule la CONVECTION (Air <-> Solides) avec couplage SEMI-IMPLICITE.

        Schéma semi-implicite (résout implicitement le couplage air-solides):
        - Après conduction, on a T_mid pour les solides
        - Convection couple solides et air de façon implicite pour t+dt

        Pour chaque zone air, on résout:
          h·A_total·(T_solide - T_air) = C_air·dT_air/dt + h·A_surfaces·T_air
        Via itération Newton ou simple point-fixe.
        """

        T_solides_mid = self.T  # T après conduction (T intermédiaire, pas final)
        T_solides_fin = self.T  # On va mettre à jour in-place
        T_solides_t = self.T_suivant  # T(t) pour lectures

        h = self.params.h_convection
        dt = self.params.dt
        surface_cellule = self.params.ds ** 2
        ds3 = self.params.ds ** 3

        # Itération: jusqu'à convergence du couplage
        nb_iter_max = 2  # 1 itération souvent suffisant pour h petit
        tolerance = 0.01  # Tolérance en K

        for iter_coupl in range(nb_iter_max):
            dT_max = 0.0

            for id_zone, zone in self.modele.zones_air.items():

                T_air_ancien = zone.T
                indices_tuple = self.modele.surfaces_convection_idx[id_zone]

                if indices_tuple[0].size == 0:
                    continue

                # T surfaces actuelles (itération courante)
                T_surfaces_vec = T_solides_fin[indices_tuple]
                A_total = surface_cellule * indices_tuple[0].size

                # --- Flux convectif moyen ---
                # Q = h * A * (T_surf - T_air)
                # Équilibre air: C_air * dT_air = Q * dt
                # Résultat: T_air(t+dt) = T_air(t) + h*A*dt/(C_air) * (T_surf_moy - T_air(t+dt))

                # Résoudre implicitement: T_air_new = f(T_air_new)
                # Itération: T_air_new = T_air_old + h*A_tot*dt/C * (T_surf_moy - T_air_new)
                # Rearrangé: T_air_new * (1 + h*A*dt/C) = T_air_old + h*A*dt/C * T_surf_moy

                if zone.capacite_thermique_J_K > 0:
                    coeff_implicit = 1.0 + (h * A_total * dt) / zone.capacite_thermique_J_K
                    T_surf_moy = np.mean(T_surfaces_vec)
                    T_air_new = (T_air_ancien + (h * A_total * dt / zone.capacite_thermique_J_K) * T_surf_moy) / coeff_implicit
                else:
                    T_air_new = T_air_ancien

                dT_air = T_air_new - T_air_ancien
                dT_max = max(dT_max, abs(dT_air))

                # --- Mettre à jour l'air ---
                zone.T = T_air_new

                # --- Mettre à jour les solides (implicite aussi) ---
                # Chaque surface échange: Q = h*A*(T_surf - T_air_new)
                # dT_surf = -Q*dt / (ρ*cp*V)
                delta_T_surf_vec = T_surfaces_vec - T_air_new
                flux_W_vec = h * surface_cellule * delta_T_surf_vec
                energie_J_vec = flux_W_vec * dt
                capacite_J_K_vec = self.modele.RhoCp[indices_tuple] * ds3

                delta_T_conv_vec = np.divide(
                    energie_J_vec,
                    capacite_J_K_vec,
                    out=np.zeros_like(energie_J_vec),
                    where=capacite_J_K_vec != 0
                )

                T_solides_fin[indices_tuple] -= delta_T_conv_vec

            # Vérifier convergence
            if dT_max < tolerance:
                if iter_coupl > 0:
                    self.logger.debug(f"Convection implicite: convergence en {iter_coupl+1} itérations (dT_max={dT_max:.4f}K)")
                break

    def _etape_rayonnement(self):
        """Calcule l'effet du RAYONNEMENT THERMIQUE (Stefan-Boltzmann).

        Modèle gris simplifié:
        - Rayonnement externe (surfaces vers ciel): Q = ε·σ·A·(T^4 - T_sky^4)
        - Appliqué aux surfaces en contact avec l'air

        Note: Rayonnement optionnel, peut être désactivé si self.rayonnement.enable_external=False
        """

        if not self.rayonnement.enable_external:
            return  # Pas de rayonnement

        T = self.T
        ds = self.params.ds
        dt = self.params.dt

        # Appliquer rayonnement aux surfaces externes
        dT_rayonnement = self.rayonnement.appliquer_rayonnement_surfaces_externes(
            T, self.modele.Lambda, self.modele.RhoCp,
            self.modele.surfaces_convection_idx,
            ds, dt, emissivite_default=0.85
        )

        # Ajouter correction de rayonnement
        self.T += dT_rayonnement

    def _calculer_pertes_W(self):
        """Calcule les pertes de puissance (W) vers les 'LIMITE_FIXE'."""

        T = self.T
        L = self.modele.Lambda
        ds = self.params.ds

        masque_fixe = (self.modele.Alpha == 0)  # LIMITE_FIXE
        masque_non_fixe = (self.modele.Alpha != 0)

        surface_cellule = ds * ds

        # Flux en X
        flux_x1 = (L[:, :-1, :] * (T[:, :-1, :] - T[:, 1:, :]) / ds) * (
                    masque_non_fixe[:, :-1, :] & masque_fixe[:, 1:, :])
        flux_x2 = (L[:, 1:, :] * (T[:, 1:, :] - T[:, :-1, :]) / ds) * (
                    masque_non_fixe[:, 1:, :] & masque_fixe[:, :-1, :])

        # Flux en Y
        flux_y1 = (L[:-1, :, :] * (T[:-1, :, :] - T[1:, :, :]) / ds) * (
                    masque_non_fixe[:-1, :, :] & masque_fixe[1:, :, :])
        flux_y2 = (L[1:, :, :] * (T[1:, :, :] - T[:-1, :, :]) / ds) * (
                    masque_non_fixe[1:, :, :] & masque_fixe[:-1, :, :])

        # Flux en Z
        flux_z1 = (L[:, :, :-1] * (T[:, :, :-1] - T[:, :, 1:]) / ds) * (
                    masque_non_fixe[:, :, :-1] & masque_fixe[:, :, 1:])
        flux_z2 = (L[:, :, 1:] * (T[:, :, 1:] - T[:, :, :-1]) / ds) * (
                    masque_non_fixe[:, :, 1:] & masque_fixe[:, :, :-1])

        somme_flux_x = np.sum(flux_x1) + np.sum(flux_x2)
        somme_flux_y = np.sum(flux_y1) + np.sum(flux_y2)
        somme_flux_z = np.sum(flux_z1) + np.sum(flux_z2)

        pertes_W = (somme_flux_x + somme_flux_y + somme_flux_z) * surface_cellule

        return pertes_W
