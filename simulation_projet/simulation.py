from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import numpy as np
import copy
import time


class Simulation:
    """
    Moteur principal de la simulation.
    Gère la boucle temporelle et appelle les étapes de calcul.
    """

    def __init__(self, modele, params, stockage):
        self.modele = modele
        self.params = params
        self.stockage = stockage
        self.logger = LoggerSimulation(niveau="DEBUG")

        # Copie locale des matrices pour le calcul
        self.T = np.copy(self.modele.T)
        self.T_suivant = np.copy(self.modele.T)  # Matrice pour t+dt

        self.Alpha = self.modele.Alpha
        self.Lambda = self.modele.Lambda
        self.RhoCp = self.modele.RhoCp

        # Copie locale du dict des zones (pour T°)
        self.zones_air = copy.deepcopy(self.modele.zones_air)

        # Pré-calcul des masques (pour accélérer les calculs NumPy)
        self.masque_solide = (self.Alpha > 0)  # Cellules SOLIDES (calcul conduction)
        self.masque_fixe = (self.Alpha == 0)  # Cellules FIXES (T imposée)
        self.masque_non_fixe = (self.Alpha != 0)  # Cellules non-FIXES

        # Vérification de stabilité
        try:
            alpha_max = np.max(self.Alpha[self.masque_solide])
            ds = self.params.ds
            dt = self.params.dt
            facteur_cfl = (alpha_max * dt) / (ds ** 2)

            self.logger.info(f"Alpha max (solides): {alpha_max:.2e}")
            self.logger.info(f"Facteur de stabilité (CFL): {facteur_cfl:.4f}")

            if facteur_cfl > 1 / 6:
                self.logger.warn(f"Stabilité (CFL) > 1/6 ({facteur_cfl:.4f}). Risque d'instabilité.")

        except ValueError:
            self.logger.warn("Aucun matériau solide trouvé. Impossible de vérifier la stabilité.")

        self.logger.info("Simulation initialisée.")

    def lancer_simulation(self, duree_s, intervalle_stockage_s):
        """Boucle principale de la simulation."""

        self.logger.info(f"Lancement de la simulation pour {duree_s}s...")

        temps_s = 0.0
        prochain_stockage_s = 0.0
        dt = self.params.dt

        while temps_s <= duree_s:

            # 1. Stockage (si temps atteint)
            if temps_s >= prochain_stockage_s:
                pertes = self._calculer_pertes_W()

                # Créer le dict des T° de zones pour le log/stockage
                T_zones_log = {zid: zone.T for zid, zone in self.zones_air.items()}

                self.stockage.stocker_etape(temps_s, self.T, pertes, T_zones_log)
                self.logger.debug(f"t={temps_s:.0f}s, T_air={T_zones_log.get(-1, 0):.2f}°C, Pertes={pertes:.2f}W")
                prochain_stockage_s += intervalle_stockage_s

            # 2. Étape de Conduction (Solides)
            self._etape_conduction()

            # 3. Étape de Convection (Air <-> Solides)
            self._etape_convection()

            # 4. TODO: Étape de Radiation (Soleil, Murs)
            # ...

            # 5. TODO: Étape des Apports Internes (Radiateurs, Occupants)
            # ...

            # 6. Mettre à jour la matrice T pour le prochain pas
            self.T = np.copy(self.T_suivant)

            # 7. Avancer le temps
            temps_s += dt

        self.logger.info("Simulation terminée.")

    def _etape_conduction(self):
        """
        Calcule la conduction pour UN pas de temps (dt) sur les solides.
        Utilise NumPy pour la vectorisation.
        """

        T = self.T
        T_suivant = self.T_suivant
        A = self.Alpha
        M = self.masque_solide  # Masque des cellules à calculer
        ds_carre = self.params.ds ** 2
        dt = self.params.dt

        # Calcul du Laplacien 3D vectorisé
        # On utilise np.roll pour "décaler" la matrice T dans les 6 directions
        laplacien_T = (
                              np.roll(T, -1, axis=0) + np.roll(T, 1, axis=0) +
                              np.roll(T, -1, axis=1) + np.roll(T, 1, axis=1) +
                              np.roll(T, -1, axis=2) + np.roll(T, 1, axis=2) -
                              6 * T
                      ) / ds_carre

        # Formule: T(t+dt) = T(t) + alpha * dt * Laplacien(T)
        # On n'applique ce calcul QUE sur les cellules 'SOLIDES' (M=True)
        delta_T_conduction = A * dt * laplacien_T

        # Mise à jour de T_suivant
        # np.where(M, A, B) -> Si M est Vrai, prend A, sinon B
        T_suivant = np.where(
            M,  # Condition (masque solide)
            T + delta_T_conduction,  # Si Vrai (c'est un solide, on calcule)
            T_suivant  # Si Faux (c'est FIXE ou AIR, on garde la valeur précédente)
        )

        self.T_suivant = T_suivant

    def _etape_convection(self):
        """
        Calcule l'échange thermique par convection entre les Zones d'Air
        et les Surfaces solides pour UN pas de temps (dt).

        Cette méthode utilise une "stratégie additive":
        1. Calcule l'énergie échangée (en Joules).
        2. Met à jour la T° de la ZoneAir (via sa capacité thermique).
        3. Met à jour la T° des cellules de surface (via leur capacité thermique).

        Cela s'ajoute au calcul de conduction.
        """

        h = self.params.h_convection
        dt = self.params.dt
        ds = self.params.ds
        surface_cellule = ds ** 2

        T_actuelle = self.T  # T° des solides à t
        T_apres_conduction = self.T_suivant  # T° des solides à t+dt (après conduction)

        for zone_id, zone in self.zones_air.items():

            indices_np = self.modele.surfaces_convection_np.get(zone_id)

            if indices_np is None or len(indices_np) == 0:
                continue  # Pas de surface pour cette zone

            # Tuple d'indices (pour accès NumPy avancé)
            indices_tuple = (indices_np[:, 0], indices_np[:, 1], indices_np[:, 2])

            # 1. Obtenir les T° des solides (après conduction) et de l'air
            T_solides_vec = T_apres_conduction[indices_tuple]
            T_air = zone.T  # T° de l'air à t

            # 2. Calculer le flux (W) pour chaque cellule de surface
            # Flux (W) = h * A * (T_solide - T_air)
            delta_T_vec = T_solides_vec - T_air
            flux_W_vec = h * surface_cellule * delta_T_vec

            # 3. Mettre à jour la ZONE D'AIR
            # La puissance totale reçue par l'air est l'opposé du flux
            # quittant les solides.
            flux_total_W = np.sum(flux_W_vec)

            # --- CORRECTION (Explosion Numérique) ---
            # Si flux_total_W > 0, les murs sont > air, l'air reçoit de l'énergie (flux positif)
            # Si flux_total_W < 0, les murs sont < air, l'air perd de l'énergie (flux négatif)
            # La formule de ZoneAir attend la puissance *reçue* par l'air.
            # L'air reçoit l'opposé de ce que les murs émettent.
            # Donc, l'air reçoit: flux_total_W
            zone.calculer_evolution_T(flux_total_W, dt)

            # 4. Mettre à jour les CELLULES SOLIDES
            # L'énergie (J) perdue par chaque cellule est: flux_W_vec * dt
            energie_J_vec = flux_W_vec * dt

            # Capacité thermique (J/K) de chaque cellule solide
            RhoCp_vec = self.RhoCp[indices_tuple]
            volume_cellule = ds ** 3
            capacite_thermique_J_K_vec = RhoCp_vec * volume_cellule

            # Delta_T (K) = Energie (J) / Capacité (J/K)
            # On utilise np.divide pour éviter la division par zéro (si C=0)
            delta_T_conv_vec = np.divide(
                energie_J_vec,
                capacite_thermique_J_K_vec,
                out=np.zeros_like(energie_J_vec),
                where=capacite_thermique_J_K_vec != 0
            )

            # On soustrait ce delta_T à la matrice T_suivant
            # (les solides perdent cette T° en plus de la conduction)
            self.T_suivant[indices_tuple] -= delta_T_conv_vec

    def _calculer_pertes_W(self):
        """
        Calcule la puissance totale (en Watts) perdue par la maison
        vers les cellules 'LIMITE_FIXE'.
        Utilise NumPy pour la vectorisation.
        """

        T = self.T
        L = self.Lambda
        ds = self.params.ds
        surface_cellule = ds ** 2

        # Masques des frontières
        masque_fixe = self.masque_fixe
        masque_non_fixe = self.masque_non_fixe

        # Flux en X (i=0 et i=N-1)
        # Flux de [1] vers [0]
        flux_x1 = (L[:, 1, :] * (T[:, 1, :] - T[:, 0, :]) / ds) * (masque_non_fixe[:, 1, :] & masque_fixe[:, 0, :])
        # Flux de [N-2] vers [N-1]
        flux_x2 = (L[:, -2, :] * (T[:, -2, :] - T[:, -1, :]) / ds) * (masque_non_fixe[:, -2, :] & masque_fixe[:, -1, :])

        # Flux en Y (j=0 et j=N-1)
        flux_y1 = (L[:, 1, :] * (T[:, 1, :] - T[:, 0, :]) / ds) * (masque_non_fixe[:, 1, :] & masque_fixe[:, 0, :])
        flux_y2 = (L[:, -2, :] * (T[:, -2, :] - T[:, -1, :]) / ds) * (masque_non_fixe[:, -2, :] & masque_fixe[:, -1, :])

        # Flux en Z (k=0 et k=N-1)
        flux_z1 = (L[:, :, 1] * (T[:, :, 1] - T[:, :, 0]) / ds) * (masque_non_fixe[:, :, 1] & masque_fixe[:, :, 0])
        flux_z2 = (L[:, :, -2] * (T[:, :, -2] - T[:, :, -1]) / ds) * (masque_non_fixe[:, :, -2] & masque_fixe[:, :, -1])

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
# (Gère la visualisation 3D avec PyVista)


