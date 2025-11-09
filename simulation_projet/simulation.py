# --- Imports ---
from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import numpy as np
import time


class Simulation:
    """
    Gère le moteur de simulation (boucle temporelle, calculs).
    """

    def __init__(self, modele, stockage, params, logger=None):
        self.logger = logger if logger else LoggerSimulation(niveau="INFO")
        self.modele = modele
        self.stockage = stockage
        self.params = params

        # Créer une copie de T pour le calcul (T à t+dt)
        self.T_suivant = np.copy(self.modele.T)

        # --- Pré-calculs de Stabilité et Masques ---

        # 1. Stabilité (CFL)
        # On ne prend que les 'solides' (Alpha >= 0)
        alpha_solides = self.modele.Alpha[self.modele.Alpha >= 0]
        if len(alpha_solides) > 0:
            self.alpha_max = np.max(alpha_solides)
            self.logger.info(f"Alpha max (solides): {self.alpha_max:0.2e}")

            facteur_cfl = (self.alpha_max * self.params.dt) / (self.params.ds ** 2)
            self.logger.info(f"Facteur de stabilité (CFL): {facteur_cfl:.4f}")
            if facteur_cfl > 1/6:
                self.logger.warning("Facteur CFL > 1/6. Risque d'instabilité !")

        else:
            self.alpha_max = 0
            self.logger.info("Aucun solide détecté, calcul de conduction désactivé.")

        # 2. Masques NumPy (pour calculs vectorisés)
        # On ne calcule que les points qui sont :
        # 1) Pas une limite fixe (Alpha != 0)
        # 2) Pas de l'air (Alpha >= 0)
        # 3) Pas sur les bords (car on utilise les voisins)

        # Masque des "solides" (alpha > 0)
        masque_solides = (self.modele.Alpha > 0)

        # Masque "intérieur" (pas sur les 6 faces de la boîte)
        masque_interieur = np.zeros_like(self.modele.Alpha, dtype=bool)
        masque_interieur[1:-1, 1:-1, 1:-1] = True

        # Le masque final des points à calculer par CONDUCTION
        self.masque_conduction = (masque_solides & masque_interieur)

        self.logger.info("Simulation initialisée.")


    def lancer_simulation(self, duree_s, intervalle_stockage_s):
        """Boucle de simulation principale."""

        temps_simule_s = 0.0
        prochain_stockage_s = 0.0
        dt = self.params.dt

        self.logger.info(f"Lancement de la simulation pour {duree_s}s...")

        while temps_simule_s <= duree_s:

            # 1. Étape de Conduction (dans les solides)
            self._etape_conduction()

            # 2. Étape de Convection (Air <-> Surfaces)
            # (Sera implémentée à l'étape 2)
            # self._etape_convection()

            # 3. Mise à jour de la matrice principale
            # T(t) devient T(t+dt)
            np.copyto(self.modele.T, self.T_suivant)

            # 4. Calcul des pertes (optionnel, coûteux)
            pertes = self._calculer_pertes_W()

            # 5. Stockage des résultats
            if temps_simule_s >= prochain_stockage_s:
                self.stockage.stocker_etape(temps_simule_s, self.modele.T, pertes)
                prochain_stockage_s += intervalle_stockage_s

            temps_simule_s += dt

        self.logger.info("Simulation terminée.")

    def _etape_conduction(self):
        """
        Calcule la conduction (vectorisée avec NumPy) sur tous
        les points définis par 'self.masque_conduction'.
        """

        T = self.modele.T # T à l'instant t
        A = self.modele.Alpha
        m = self.masque_conduction # Masque des points à calculer
        dt = self.params.dt
        ds_carre = self.params.ds ** 2

        # Calcul du Laplacien 3D (vectorisé)
        # T[m] -> ne prend que les points du masque
        laplacien = (
            T[1:-1, 1:-1, 2:]  [m[1:-1, 1:-1, 1:-1]] + # (i, j, k+1)
            T[1:-1, 1:-1, :-2] [m[1:-1, 1:-1, 1:-1]] + # (i, j, k-1)
            T[1:-1, 2:, 1:-1]  [m[1:-1, 1:-1, 1:-1]] + # (i, j+1, k)
            T[1:-1, :-2, 1:-1] [m[1:-1, 1:-1, 1:-1]] + # (i, j-1, k)
            T[2:, 1:-1, 1:-1]  [m[1:-1, 1:-1, 1:-1]] + # (i+1, j, k)
            T[:-2, 1:-1, 1:-1] [m[1:-1, 1:-1, 1:-1]] - # (i-1, j, k)
            6 * T[m]
        ) / ds_carre

        # Appliquer la formule T(t+dt) = T(t) + alpha * dt * Laplacien
        # A[m] -> ne prend que les alpha des points du masque
        self.T_suivant[m] = T[m] + A[m] * dt * laplacien

    def _calculer_pertes_W(self):
        """
        Calcule les pertes totales (en Watts) vers les cellules
        à température "FIXE" (ex: extérieur).
        Utilise la Loi de Fourier: Flux = lambda * (T_int - T_ext) / ds
        """

        T = self.modele.T
        L = self.modele.Lambda
        ds = self.params.ds
        surface_cellule = ds**2

        # Masque des points 'FIXES' (Alpha == 0)
        masque_fixe = (self.modele.Alpha == 0)
        # Masque des points 'NON-FIXES' (Alpha != 0)
        masque_non_fixe = (self.modele.Alpha != 0)

        # Pertes en X
        flux_x1 = (L[1:,:,:] * (T[1:,:,:] - T[:-1,:,:]) / ds) * (masque_non_fixe[1:,:,:] & masque_fixe[:-1,:,:])
        flux_x2 = (L[:-1,:,:] * (T[:-1,:,:] - T[1:,:,:]) / ds) * (masque_non_fixe[:-1,:,:] & masque_fixe[1:,:,:])

        # Pertes en Y
        flux_y1 = (L[:,1:,:] * (T[:,1:,:] - T[:,:-1,:]) / ds) * (masque_non_fixe[:,1:,:] & masque_fixe[:,:-1,:])
        flux_y2 = (L[:,:-1,:] * (T[:,:-1,:] - T[:,1:,:]) / ds) * (masque_non_fixe[:,:-1,:] & masque_fixe[:,1:,:])

        # Pertes en Z
        flux_z1 = (L[:,:,1:] * (T[:,:,1:] - T[:,:,:-1]) / ds) * (masque_non_fixe[:,:,1:] & masque_fixe[:,:,:-1])
        flux_z2 = (L[:,:,:-1] * (T[:,:,:-1] - T[:,:,1:]) / ds) * (masque_non_fixe[:,:,:-1] & masque_fixe[:,:,1:])

        # Somme de tous les flux (en W/m^2) * surface_cellule (m^2) = W
        # --- CORRECTION (ValueError) ---
        # On ne peut pas additionner des matrices de formes différentes.
        # On doit d'abord sommer chaque flux, PUIS les additionner.
        somme_flux_x = np.sum(flux_x1) + np.sum(flux_x2)
        somme_flux_y = np.sum(flux_y1) + np.sum(flux_y2)
        somme_flux_z = np.sum(flux_z1) + np.sum(flux_z2)

        pertes_W = (somme_flux_x + somme_flux_y + somme_flux_z) * surface_cellule

        return pertes_W

