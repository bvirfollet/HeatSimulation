#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fichier: simulation.py
# Généré par le dispatcher de simulation_objet.py

from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import numpy as np
import time

# --- Début des Blocs de Code ---

class Simulation:
    """
    Contrôleur principal de la simulation.
    Gère la boucle de temps et orchestre le modèle et le stockage.
    """

    def __init__(self, modele, stockage, params):
        self.modele = modele
        self.stockage = stockage
        self.params = params
        self.logger = LoggerSimulation(niveau="INFO")

        # Coefficient de stabilité (calculé une fois)
        # On ignore les zones d'air (alpha < 0) pour ce calcul
        alpha_solides = self.modele.Alpha[self.modele.Alpha >= 0]
        if len(alpha_solides) > 0:
            alpha_max = np.max(alpha_solides)
        else:
            alpha_max = 0.0

        self.facteur_stabilite = (alpha_max * self.params.dt) / (self.params.ds ** 2)
        self.logger.info(f"Alpha max (solides): {alpha_max:.2e}")
        self.logger.info(f"Facteur de stabilité (CFL): {self.facteur_stabilite:.4f}")

        if self.facteur_stabilite > 1 / 6:
            self.logger.error(f"SIMULATION INSTABLE ! Facteur CFL > 1/6.")
            self.logger.error("Réduisez le pas de temps (dt) ou augmentez la taille des cellules (ds).")
            # raise ValueError("Simulation instable (CFL > 1/6)")

        self.logger.info("Simulation initialisée.")

    def lancer_simulation(self, duree_s, intervalle_stockage_s):
        """
        Exécute la boucle de simulation principale.
        """
        # --- NOUVEAU (Étape 1) ---
        # Préparer le modèle (détecter les surfaces, etc.)
        self.modele.preparer_simulation()

        self.logger.info(f"Lancement de la simulation pour {duree_s}s...")

        temps_simule_s = 0.0
        temps_dernier_stockage = -np.inf
        dt = self.params.dt

        # Fait une copie de la matrice T pour le calcul (T à t+dt)
        T_suivante = np.copy(self.modele.T)

        try:
            while temps_simule_s <= duree_s:

                # 1. Stocker l'étape actuelle (si nécessaire)
                if (temps_simule_s - temps_dernier_stockage) >= intervalle_stockage_s:
                    pertes = self._calculer_pertes_W()
                    self.stockage.stocker_etape(temps_simule_s, self.modele.T, pertes)
                    temps_dernier_stockage = temps_simule_s

                # 2. Calculer l'étape de Conduction (pour les SOLIDES)
                self._etape_conduction(self.modele.T, T_suivante)

                # 3. Calculer l'étape de Convection (pour les ZONES D'AIR)
                # (Sera implémenté à l'Étape 2)
                # self._etape_convection(self.modele.T, T_suivante)

                # 4. Échanger les matrices (t devient t+dt)
                self.modele.T, T_suivante = T_suivante, self.modele.T

                # 5. Avancer le temps
                temps_simule_s += dt

            # Stocker la toute dernière étape
            pertes = self._calculer_pertes_W()
            self.stockage.stocker_etape(temps_simule_s, self.modele.T, pertes)

            self.logger.info("Simulation terminée.")

        except KeyboardInterrupt:
            self.logger.warning("Simulation interrompue par l'utilisateur.")
            # Sauvegarder l'état actuel
            pertes = self._calculer_pertes_W()
            self.stockage.stocker_etape(temps_simule_s, self.modele.T, pertes)

    def _etape_conduction(self, T_actuelle, T_suivante):
        """
        Calcule la conduction pour UN pas de temps sur toutes les
        cellules 'SOLIDES' (alpha > 0).
        Version vectorisée NumPy.
        """

        # Crée un masque 3D des cellules à calculer (Solides, pas FIXE)
        masque_solide = (self.modele.Alpha > 0)

        # Extrait les sous-matrices nécessaires (performant)
        T = T_actuelle
        A = self.modele.Alpha
        ds_carre = self.params.ds ** 2
        dt = self.params.dt

        # Calcul du Laplacien 3D (vectorisé)
        # On ne calcule que là où le masque est Vrai
        laplacien_T = np.zeros_like(T)

        # --- ATTENTION ---
        # Ce calcul du Laplacien n'est correct que pour les cellules
        # [1:-1, 1:-1, 1:-1]. Il faudrait une gestion plus fine
        # des masques pour les bords. Pour l'instant, on suppose que
        # les cellules solides ne sont pas collées aux bords de la
        # simulation totale (ce qui est le cas avec notre 'EXTERIEUR_FIXE')

        # On ne calcule le Laplacien que sur les points intérieurs
        # pour éviter les erreurs d'index
        masque_interieur = np.zeros_like(T, dtype=bool)
        masque_interieur[1:-1, 1:-1, 1:-1] = True

        # Masque final = Solide ET Intérieur
        masque_calcul = masque_solide & masque_interieur

        # Slicing plus sûr
        T_centre = T[1:-1, 1:-1, 1:-1]

        laplacien_slice = (
                                  T[2:, 1:-1, 1:-1] - 2 * T_centre + T[:-2, 1:-1, 1:-1] +
                                  T[1:-1, 2:, 1:-1] - 2 * T_centre + T[1:-1, :-2, 1:-1] +
                                  T[1:-1, 1:-1, 2:] - 2 * T_centre + T[1:-1, 1:-1, :-2]
                          ) / ds_carre

        # Appliquer le Laplacien calculé
        laplacien_T[1:-1, 1:-1, 1:-1] = laplacien_slice

        # Mise à jour de la température
        # T(t+dt) = T(t) + alpha * dt * Laplacien
        T_suivante[masque_calcul] = T[masque_calcul] + A[masque_calcul] * dt * laplacien_T[masque_calcul]

        # S'assure que les zones non calculées (FIXE, AIR, et bords) gardent leur valeur
        T_suivante[~masque_calcul] = T[~masque_calcul]

    # (L'implémentation de _etape_convection viendra à l'Étape 2)
    # def _etape_convection(self, T_actuelle, T_suivante): ...

    def _calculer_pertes_W(self):
        """
        Calcule les pertes thermiques totales (en Watts)
        à travers les surfaces 'FIXE' (ex: extérieur).
        """
        # (Version simplifiée: on ne calcule que les pertes vers
        # les cellules 'FIXE' (alpha=0))

        masque_fixe = (self.modele.Alpha == 0)
        masque_non_fixe = (self.modele.Alpha != 0)

        pertes_W = 0.0
        T = self.modele.T
        L = self.modele.Lambda
        ds = self.params.ds
        surface_cellule = ds * ds

        # Flux en X (i+1 est fixe, i est non-fixe)
        flux_x1 = (L[:-1, :, :] * (T[:-1, :, :] - T[1:, :, :]) / ds) * (
                    masque_non_fixe[:-1, :, :] & masque_fixe[1:, :, :])
        # Flux en X (i-1 est fixe, i est non-fixe)
        flux_x2 = (L[1:, :, :] * (T[1:, :, :] - T[:-1, :, :]) / ds) * (
                    masque_non_fixe[1:, :, :] & masque_fixe[:-1, :, :])

        # Flux en Y (j+1 est fixe, j est non-fixe)
        flux_y1 = (L[:, :-1, :] * (T[:, :-1, :] - T[:, 1:, :]) / ds) * (
                    masque_non_fixe[:, :-1, :] & masque_fixe[:, 1:, :])
        # Flux en Y (j-1 est fixe, j est non-fixe)
        flux_y2 = (L[:, 1:, :] * (T[:, 1:, :] - T[:, :-1, :]) / ds) * (
                    masque_non_fixe[:, 1:, :] & masque_fixe[:, :-1, :])

        # Flux en Z (k+1 est fixe, k est non-fixe)
        flux_z1 = (L[:, :, :-1] * (T[:, :, :-1] - T[:, :, 1:]) / ds) * (
                    masque_non_fixe[:, :, :-1] & masque_fixe[:, :, 1:])
        # Flux en Z (k-1 est fixe, k est non-fixe)
        flux_z2 = (L[:, :, 1:] * (T[:, :, 1:] - T[:, :, :-1]) / ds) * (
                    masque_non_fixe[:, :, 1:] & masque_fixe[:, :, :-1])

        # Somme de tous les flux (en W/m^2) * surface_cellule (m^2) = W
        pertes_W = np.sum(flux_x1 + flux_x2 + flux_y1 + flux_y2 + flux_z1 + flux_z2) * surface_cellule

        return pertes_W


# --- CLASSE 7: Visualisation ---

