#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fichier: modele.py
# Généré par le dispatcher de simulation_objet.py

from logger import LoggerSimulation
from model_data import MATERIAUX
from model_data import ZoneAir
from parametres import ParametresSimulation
import numpy as np

# --- Début des Blocs de Code ---

class ModeleMaison:
    """
    Contient l'état du système : les matrices 3D (Température, Alpha, Lambda)
    et les routines pour construire la géométrie.
    """

    def __init__(self, params):
        self.params = params
        self.logger = LoggerSimulation(nom="ModeleMaison")

        # Dimensions de la grille
        N_x, N_y, N_z = params.N_x, params.N_y, params.N_z

        # Initialise les matrices NumPy
        # Matrice T (Température):
        self.T = np.full((N_x, N_y, N_z), params.temp_exterieure, dtype=np.float64)

        # Matrice Alpha (Diffusivité):
        # 0.0 correspond à 'FIXE' (exterieur)
        self.Alpha = np.full((N_x, N_y, N_z), MATERIAUX["EXTERIEUR_FIXE"]["alpha"], dtype=np.float64)

        # Matrice Lambda (Conductivité):
        self.Lambda = np.full((N_x, N_y, N_z), MATERIAUX["EXTERIEUR_FIXE"]["lambda"], dtype=np.float64)

        # --- NOUVEAU (Étape 1 Convection) ---
        # Dictionnaire des zones d'air. Clé = ID (ex: -1), Valeur = objet ZoneAir
        self.zones_air = {}
        # Liste des indices (i,j,k) des cellules solides en contact avec l'air
        self.surfaces_convection = {}  # Format: {id_zone: [ (i,j,k), ... ]}

        self.logger.info("Modèle 3D (matrices NumPy) initialisé.")

    def _coords_metres_vers_indices(self, coord_m):
        """Convertit un tuple (x, y, z) en mètres en indices (i, j, k)."""
        i = int(round(coord_m[0] / self.params.ds))
        j = int(round(coord_m[1] / self.params.ds))
        k = int(round(coord_m[2] / self.params.ds))
        # S'assure de rester dans les bornes
        i = max(0, min(i, self.params.N_x - 1))
        j = max(0, min(j, self.params.N_y - 1))
        k = max(0, min(k, self.params.N_z - 1))
        return i, j, k

    def construire_volume_metres(self, p1_m, p2_m, nom_materiau, temp_init=None):
        """
        Remplit un volume de la grille (défini par deux coins en mètres)
        avec les propriétés d'un matériau.
        """
        i1, j1, k1 = self._coords_metres_vers_indices(p1_m)
        i2, j2, k2 = self._coords_metres_vers_indices(p2_m)

        # S'assure que p1 est le coin min et p2 le coin max
        i_min, i_max = min(i1, i2), max(i1, i2)
        j_min, j_max = min(j1, j2), max(j1, j2)
        k_min, k_max = min(k1, k2), max(k1, k2)

        if nom_materiau not in MATERIAUX:
            self.logger.error(f"Matériau '{nom_materiau}' inconnu. Construction annulée.")
            return

        mat = MATERIAUX[nom_materiau]
        mat_alpha = mat["alpha"]

        # --- NOUVEAU (Étape 1 Convection) ---
        if mat_alpha < 0:  # C'est une ZoneAir
            # L'ID de la zone est l'alpha négatif (ex: -1, -2)
            id_zone = int(mat_alpha)

            if id_zone not in self.zones_air:
                # Crée la zone si elle n'existe pas
                t_init = temp_init if temp_init is not None else self.params.temp_interieure_initiale
                self.zones_air[id_zone] = ZoneAir(f"Zone {id_zone}", self.params, t_init)

            zone = self.zones_air[id_zone]
            volume_cellule = self.params.ds ** 3

            # Remplit les matrices
            for i in range(i_min, i_max + 1):
                for j in range(j_min, j_max + 1):
                    for k in range(k_min, k_max + 1):
                        self.Alpha[i, j, k] = mat_alpha
                        self.Lambda[i, j, k] = mat["lambda"]
                        if temp_init is not None:
                            self.T[i, j, k] = temp_init
                        else:
                            self.T[i, j, k] = zone.temperature  # Température initiale de la zone

                        # Ajoute le volume à la zone
                        zone.ajouter_volume_cellule(volume_cellule)

        else:  # C'est un matériau SOLIDE ou FIXE
            # Tranches NumPy pour une assignation rapide
            s = (slice(i_min, i_max + 1),
                 slice(j_min, j_max + 1),
                 slice(k_min, k_max + 1))

            self.Alpha[s] = mat_alpha
            self.Lambda[s] = mat["lambda"]

            # Applique la température initiale si spécifiée
            if temp_init is not None:
                self.T[s] = temp_init
            elif mat["type"] == 'FIXE':
                # Cas spécial pour EXTERIEUR_FIXE (température par défaut)
                self.T[s] = self.params.temp_exterieure

        self.logger.info(f"Volume [{i_min}:{i_max}, {j_min}:{j_max}, {k_min}:{k_max}] rempli avec '{nom_materiau}'.")

    def preparer_simulation(self):
        """
        Finalise l'initialisation avant de lancer la simulation.
        - Finalise les zones d'air
        - Détecte les surfaces de convection
        """
        self.logger.info("Préparation de la simulation...")
        # 1. Finaliser les zones d'air
        for zone_id, zone in self.zones_air.items():
            zone.finaliser_initialisation()

        # 2. Détecter les surfaces
        self._detecter_surfaces_convection()

    def _detecter_surfaces_convection(self):
        """
        (Étape 1) Identifie les indices (i,j,k) des cellules SOLIDES
        qui sont adjacentes à une cellule AIR (alpha < 0).

        Cette version utilise NumPy pour la performance.
        """
        self.logger.info("Détection des surfaces de convection (NumPy)...")

        # 1. Identifier les cellules AIR (booléen)
        est_air = (self.Alpha < 0)
        # 2. Identifier les cellules SOLIDES (booléen)
        est_solide = (self.Alpha >= 0)  # Note: inclut FIXE (alpha=0)

        # 3. Trouver les frontières
        # On "décale" la grille d'air dans les 6 directions.
        # Si une cellule "solide" touche une cellule "air décalée",
        # alors c'est une surface.

        frontiere = np.zeros_like(est_solide, dtype=bool)

        # Voisins en X
        frontiere[1:, :, :] |= (est_solide[1:, :, :] & est_air[:-1, :, :])
        frontiere[:-1, :, :] |= (est_solide[:-1, :, :] & est_air[1:, :, :])
        # Voisins en Y
        frontiere[:, 1:, :] |= (est_solide[:, 1:, :] & est_air[:, :-1, :])
        frontiere[:, :-1, :] |= (est_solide[:, :-1, :] & est_air[:, 1:, :])
        # Voisins en Z
        frontiere[:, :, 1:] |= (est_solide[:, :, 1:] & est_air[:, :, :-1])
        frontiere[:, :, :-1] |= (est_solide[:, :, :-1] & est_air[:, :, 1:])

        # 4. Extraire les indices (i,j,k) de ces points de surface
        indices_surface = np.argwhere(frontiere)

        # 5. Classer les indices par zone d'air
        # (Pour l'instant, on suppose une seule zone d'air, id = -1)
        # Une version plus avancée devrait vérifier *quelle* zone d'air
        # est adjacente à quel solide.

        # Pour notre Étape 1, on met tout dans la zone -1 (si elle existe)
        zone_id_par_defaut = -1
        if zone_id_par_defaut in self.zones_air:
            self.surfaces_convection[zone_id_par_defaut] = indices_surface
            self.logger.info(
                f"Détection terminée: {len(indices_surface)} cellules de surface trouvées pour Zone {zone_id_par_defaut}.")
        else:
            self.logger.warning("Aucune ZoneAir (-1) trouvée. Pas de surfaces de convection.")

        # (Debug) On peut assigner une valeur spéciale pour voir les surfaces
        # for i, j, k in indices_surface:
        #    self.Lambda[i,j,k] = 999


# --- CLASSE 6: Simulation ---

