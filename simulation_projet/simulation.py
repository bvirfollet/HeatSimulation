# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import numpy as np
import time


class Simulation:
    """Contient le moteur de calcul et la boucle temporelle."""

    def __init__(self, modele, params, chemin_sortie="resultats_sim"):
        self.modele = modele
        self.params = params
        self.logger = params.logger
        self.stockage = StockageResultats(chemin_sortie, self.logger)

        # Copie locale des matrices (état t)
        self.T = np.copy(self.modele.T)

        # Matrice pour l'état t+dt
        self.T_suivant = np.copy(self.T)

        # --- Pré-calcul des masques (pour accélérer NumPy) ---

        # Masque des points FIXES (LIMITE_FIXE ou AIR)
        # alpha <= 0 signifie que le point n'est PAS calculé par conduction
        self.masque_fixe = (self.modele.Alpha <= 0)

        # Masque des points SOLIDES (calculés par conduction)
        self.masque_solide = (self.modele.Alpha > 0)

        # --- Vérification de la stabilité (CFL) ---
        if np.any(self.masque_solide):
            alpha_max = np.max(self.modele.Alpha[self.masque_solide])
            ds2 = self.params.ds ** 2

            # Facteur de stabilité (doit être < 1/6 pour 3D)
            facteur_cfl = (alpha_max * self.params.dt) / ds2

            self.logger.info(f"Alpha max (solides): {alpha_max:0.2e}")
            self.logger.info(f"Facteur de stabilité (CFL): {facteur_cfl:.4f}")
            if facteur_cfl > (1 / 6):
                self.logger.error(f"Instabilité détectée! CFL ({facteur_cfl:.4f}) > 0.166.")
                self.logger.error("Réduisez 'dt' ou augmentez 'ds'.")
                raise ValueError("Simulation instable (CFL).")
            elif facteur_cfl > (1 / 10):
                self.logger.warn(f"Facteur de stabilité ({facteur_cfl:.4f}) élevé. Proche de la limite (0.166).")
        else:
            self.logger.warn("Aucun matériau solide trouvé. Impossible de vérifier la stabilité.")

        self.logger.info("Simulation initialisée.")

    def lancer_simulation(self, duree_s, intervalle_stockage_s=600):
        """Lance la boucle de simulation principale."""

        temps_simule_s = 0.0
        prochain_stockage_s = 0.0

        dt = self.params.dt

        self.logger.info(f"Lancement de la simulation pour {duree_s}s...")

        while temps_simule_s <= duree_s:

            # 1. Gérer le stockage
            if temps_simule_s >= prochain_stockage_s:
                pertes = self._calculer_pertes_W()
                temps_air_str = ", ".join([f"T_air_{z.nom}={z.T:.2f}°C" for z in self.modele.zones_air.values()])
                self.logger.debug(f"t={temps_simule_s:.0f}s, {temps_air_str}, Pertes={pertes:.2f}W")

                self.stockage.stocker_etape(temps_simule_s, self.T, self.modele.zones_air)
                prochain_stockage_s += intervalle_stockage_s

            # T_suivant contient T(t)
            # self.T va contenir T(t+dt)

            # 3. Calculer la Conduction (Solides)
            # Calcule T(t+dt) basé sur T(t)
            self._etape_conduction()

            # 4. Calculer la Convection (Air <-> Solides)
            # Met à jour T(t+dt) sur les surfaces solides
            # Met à jour T_air(t+dt) dans les ZoneAir
            self._etape_convection()

            # 5. Appliquer les conditions limites
            self.T[self.masque_fixe] = self.T_suivant[self.masque_fixe]

            # 6. Mettre à jour l'état
            # T(t) devient T(t+dt) pour la prochaine itération
            np.copyto(self.T_suivant, self.T)
            temps_simule_s += dt

        # Stockage final
        pertes = self._calculer_pertes_W()
        self.stockage.stocker_etape(temps_simule_s, self.T, self.modele.zones_air)
        self.logger.info("Simulation terminée.")
        temps_air_final = {zone.nom: zone.T for zone in self.modele.zones_air.values()}
        self.logger.info(f"--- Température Finale de l'Air: {temps_air_final} ---")

    def _etape_conduction(self):
        """Calcule un pas de temps (dt) de CONDUCTION."""

        T = self.T_suivant  # Lecture de T(t)
        T_new = self.T  # Écriture dans T(t+dt)

        A = self.modele.Alpha
        ds2 = self.params.ds ** 2
        dt = self.params.dt

        # Masque des points à calculer (Solides)
        M = self.masque_solide

        # Le cœur du calcul (différences finies 3D en NumPy)
        # T_new[M] = T[M] + (A[M] * dt / ds2) * ( ... Laplacien ... )

        laplacien_T = (
                T[1:-1, 2:, 1:-1] + T[1:-1, :-2, 1:-1] +  # Voisins Y
                T[2:, 1:-1, 1:-1] + T[:-2, 1:-1, 1:-1] +  # Voisins X
                T[1:-1, 1:-1, 2:] + T[1:-1, 1:-1, :-2] -  # Voisins Z
                6 * T[1:-1, 1:-1, 1:-1]
        )

        # On applique le calcul SEULEMENT aux points intérieurs (1:-1)
        # ET qui sont des solides (M[1:-1, 1:-1, 1:-1])

        masque_interieur = M[1:-1, 1:-1, 1:-1]

        T_new[1:-1, 1:-1, 1:-1][masque_interieur] = \
            T[1:-1, 1:-1, 1:-1][masque_interieur] + \
            (A[1:-1, 1:-1, 1:-1][masque_interieur] * dt / ds2) * \
            laplacien_T[masque_interieur]

    def _etape_convection(self):
        """Calcule un pas de temps (dt) de CONVECTION (Air <-> Solides)."""

        T_solides_t = self.T_suivant  # Lecture de T(t) des solides
        T_solides_t_plus_dt = self.T  # Écriture dans T(t+dt)

        h = self.params.h_convection
        dt = self.params.dt
        surface_cellule = self.params.ds ** 2

        # Itérer sur chaque zone d'air (ex: Zone -1)
        for id_zone, zone in self.modele.zones_air.items():

            # 1. Récupérer les T° de l'air (t) et des surfaces (t)
            T_air_t = zone.T  # Température unique de la zone (float)

            # Indices (i, j, k) des cellules de surface solides
            indices_tuple = self.modele.surfaces_convection_idx[id_zone]

            # Si aucune surface n'est trouvée, passer
            if indices_tuple[0].size == 0:
                continue

            # Récupérer les T° de toutes ces cellules de surface
            T_surfaces_t_vec = T_solides_t[indices_tuple]

            # 2. Calculer le flux de chaleur (W) pour chaque cellule de surface
            # Loi de Newton: P = h * A * (T_solide - T_air)
            delta_T_vec = T_surfaces_t_vec - T_air_t
            flux_W_vec = h * surface_cellule * delta_T_vec

            # 3. Mettre à jour la Zone d'Air
            # flux_total_W = Puissance totale *quittant* les solides.
            flux_total_W = np.sum(flux_W_vec)

            # L'air reçoit l'opposé : -flux_total_W.
            # (Si les murs sont froids (0C) et l'air chaud (20C),
            # delta_T_vec est négatif, flux_W_vec est négatif.
            # L'air doit PERDRE de l'énergie.
            # L'air reçoit donc -flux_total_W (qui est positif... ERREUR)

            # --- CORRECTION ERREUR DE SIGNE (23/05/2024) ---
            # flux_total_W = puissance quittant les solides.
            # Si T_solide > T_air, flux_total_W est POSITIF. L'air doit GAGNER de l'énergie.
            # Si T_solide < T_air, flux_total_W est NÉGATIF. L'air doit PERDRE de l'énergie.
            # La fonction `calculer_evolution_T` attend la puissance NETTE (positif=gain, negatif=perte).
            # Donc on doit lui passer `flux_total_W` (le flux des solides vers l'air).
            zone.calculer_evolution_T(flux_total_W, dt)

            # 4. Mettre à jour les Solides
            # Les solides perdent l'énergie (flux_W_vec)

            # Énergie perdue (J) = Puissance (W) * temps (s)
            energie_J_vec = flux_W_vec * dt

            # Récupérer la capacité thermique (J/K) de chaque cellule de surface
            # RhoCp = (rho * cp) * Volume_cellule
            capacite_J_K_vec = self.modele.RhoCp[indices_tuple] * (self.params.ds ** 3)

            # Delta T (°C) = Energie (J) / Capacité (J/K)
            # On utilise np.divide pour éviter les divisions par zéro
            delta_T_conv_vec = np.divide(
                energie_J_vec,
                capacite_J_K_vec,
                out=np.zeros_like(energie_J_vec),
                where=capacite_J_K_vec != 0
            )

            # Appliquer cette variation de T° (due à la convection)
            # T_solide(t+dt) = T_solide_conduction(t+dt) - delta_T_convection
            T_solides_t_plus_dt[indices_tuple] -= delta_T_conv_vec

    def _calculer_pertes_W(self):
        """Calcule les pertes de puissance (W) vers les 'LIMITE_FIXE'."""

        T = self.T  # Utilise l'état le plus récent
        L = self.modele.Lambda
        ds = self.params.ds

        # Masque des zones FIXES (T° imposée, ex: extérieur à 0°C)
        masque_fixe = (self.modele.Alpha == 0)  # LIMITE_FIXE

        # Masque des zones NON-FIXES (Solides ou Air)
        masque_non_fixe = (self.modele.Alpha != 0)

        surface_cellule = ds * ds
        pertes_W = 0.0

        # Flux en X (de i vers i+1)
        # T[i] (non-fixe) -> T[i+1] (fixe)
        flux_x1 = (L[:, :-1, :] * (T[:, :-1, :] - T[:, 1:, :]) / ds) * (
                    masque_non_fixe[:, :-1, :] & masque_fixe[:, 1:, :])
        # T[i+1] (non-fixe) -> T[i] (fixe)
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

        # Somme de tous les flux (en W/m^2) * surface_cellule (m^2) = W
        # --- CORRECTION (ValueError) ---
        # On ne peut pas additionner des matrices de formes différentes.
        # On doit d'abord sommer chaque flux, PUIS les additionner.
        somme_flux_x = np.sum(flux_x1) + np.sum(flux_x2)
        somme_flux_y = np.sum(flux_y1) + np.sum(flux_y2)
        somme_flux_z = np.sum(flux_z1) + np.sum(flux_z2)

        pertes_W = (somme_flux_x + somme_flux_y + somme_flux_z) * surface_cellule

        return pertes_W


# --- CLASSE 7: Visualisation ---
# (Gère le rendu 3D avec PyVista)


