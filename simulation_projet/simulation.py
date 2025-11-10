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

        self.logger.info("Simulation initialisée.")

    def lancer_simulation(self, duree_s, intervalle_stockage_s=600):
        """Lance la boucle de simulation principale."""

        temps_simule_s = 0.0
        prochain_stockage_s = 0.0
        dt = self.params.dt

        self.logger.info(f"Lancement de la simulation pour {duree_s}s...")

        # Stockage de l'état initial
        self.stocker_etape_simulation(temps_simule_s)
        prochain_stockage_s += intervalle_stockage_s

        while temps_simule_s <= duree_s:

            # T_suivant contient T(t)
            # self.T va contenir T(t+dt)

            self._etape_conduction()
            self._etape_convection()

            # Appliquer les conditions limites (écraser T(t+dt))
            self.T[self.masque_fixe] = self.T_suivant[self.masque_fixe]

            # Mettre à jour l'état T(t) -> T(t+dt)
            np.copyto(self.T_suivant, self.T)
            temps_simule_s += dt

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

    def _etape_convection(self):
        """Calcule un pas de temps (dt) de CONVECTION (Air <-> Solides)."""

        T_solides_t = self.T_suivant  # Lecture de T(t)
        T_solides_t_plus_dt = self.T  # Écriture dans T(t+dt)

        h = self.params.h_convection
        dt = self.params.dt
        surface_cellule = self.params.ds ** 2

        for id_zone, zone in self.modele.zones_air.items():

            T_air_t = zone.T
            indices_tuple = self.modele.surfaces_convection_idx[id_zone]

            if indices_tuple[0].size == 0:
                continue

            T_surfaces_t_vec = T_solides_t[indices_tuple]

            # P = h * A * (T_solide - T_air)
            delta_T_vec = T_surfaces_t_vec - T_air_t
            flux_W_vec = h * surface_cellule * delta_T_vec

            # --- Mettre à jour la Zone d'Air ---
            # flux_total_W = Puissance totale *quittant* les solides.
            # Si T_solide < T_air, flux_total_W est NÉGATIF. L'air doit PERDRE de l'énergie.
            flux_total_W = np.sum(flux_W_vec)
            zone.calculer_evolution_T(flux_total_W, dt)

            # --- Mettre à jour les Solides ---
            # E (J) = P (W) * t (s)
            energie_J_vec = flux_W_vec * dt

            # C (J/K) = (rho * cp) * V_voxel
            capacite_J_K_vec = self.modele.RhoCp[indices_tuple] * (self.params.ds ** 3)

            # deltaT = E / C
            delta_T_conv_vec = np.divide(
                energie_J_vec,
                capacite_J_K_vec,
                out=np.zeros_like(energie_J_vec),
                where=capacite_J_K_vec != 0
            )

            # T_solide(t+dt) = T_solide_conduction(t+dt) - delta_T_convection
            T_solides_t_plus_dt[indices_tuple] -= delta_T_conv_vec

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


# --- CLASSE 7: Visualisation ---
# (Gère le rendu 3D avec PyVista)


