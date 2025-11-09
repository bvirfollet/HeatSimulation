# --- Imports ---
from logger import LoggerSimulation
from model_data import MATERIAUX
from model_data import ZoneAir
from parametres import ParametresSimulation
import numpy as np


class ModeleMaison:
    """
    Contient la représentation 3D (matrices NumPy) de la maison.
    Gère la construction géométrique (murs, cloisons) et les
    propriétés de chaque cellule.
    """

    def __init__(self, params, logger=None):
        self.logger = logger if logger else LoggerSimulation(niveau="INFO")
        self.params = params

        # Dimensions de la grille
        N_x, N_y, N_z = params.N_x, params.N_y, params.N_z

        # Matrice 3D des Températures (float)
        self.T = np.full((N_x, N_y, N_z), params.T_INTERIEUR_INIT, dtype=float)

        # Matrice 3D des Propriétés (float)
        # On stocke Lambda (conductivité)
        self.Lambda = np.full((N_x, N_y, N_z), 0.0, dtype=float)

        # On stocke Alpha (diffusivité)
        # Note: Alpha >= 0 pour les solides (conduction)
        #       Alpha = 0.0 pour les limites fixes (pas de calcul)
        #       Alpha < 0 pour les zones d'air (ex: -1, -2, ...) (convection)
        self.Alpha = np.full((N_x, N_y, N_z), 0.0, dtype=float)

        # Gestion des zones d'air (pour la convection)
        self.zones_air = {} # Dictionnaire {id: ZoneAir}

        # Liste des surfaces de convection
        # (index, id_zone, [ix, iy, iz])
        self.surfaces_convection = []
        # Version NumPy pour calcul rapide: [ (ix1, iy1, iz1), (ix2, iy2, iz2), ... ]
        self.surfaces_convection_idx = {} # Dico: {id_zone: np.array}

        self.logger.info("Modèle 3D (matrices NumPy) initialisé.")

    def _calculer_alpha(self, nom_materiau):
        """Calcule la diffusivité (alpha) à partir des données MATERIAUX."""
        if nom_materiau not in MATERIAUX:
            self.logger.warning(f"Matériau '{nom_materiau}' inconnu. Utilise LIMITE_FIXE.")
            nom_materiau = "LIMITE_FIXE"

        L, R, C = MATERIAUX[nom_materiau]

        if L < 0: # C'est un marqueur de zone d'air (ex: -1)
            return L
        if L == 0 or (R * C) == 0: # C'est une limite fixe
            return 0.0

        # alpha = lambda / (rho * cp)
        return L / (R * C)

    def construire_volume_metres(self, pos_depart_m, pos_fin_m, nom_materiau):
        """
        Remplit un volume de la grille avec un matériau donné,
        en utilisant des coordonnées en mètres.

        pos_depart_m: tuple (x0, y0, z0) en mètres
        pos_fin_m: tuple (x1, y1, z1) en mètres
        nom_materiau: "PARPAING", "AIR", "LIMITE_FIXE", ...
        """

        # Conversion des mètres en indices de grille
        # On utilise np.round pour trouver l'indice le plus proche
        ds = self.params.ds
        i_min = max(0, int(np.round(pos_depart_m[0] / ds)))
        i_max = min(self.params.N_x, int(np.round(pos_fin_m[0] / ds)) + 1)
        j_min = max(0, int(np.round(pos_depart_m[1] / ds)))
        j_max = min(self.params.N_y, int(np.round(pos_fin_m[1] / ds)) + 1)
        k_min = max(0, int(np.round(pos_depart_m[2] / ds)))
        k_max = min(self.params.N_z, int(np.round(pos_fin_m[2] / ds)) + 1)

        # Récupérer les propriétés
        if nom_materiau not in MATERIAUX:
            self.logger.warning(f"Matériau '{nom_materiau}' inconnu. N'a rien fait.")
            return

        val_lambda, _, _ = MATERIAUX[nom_materiau]
        val_alpha = self._calculer_alpha(nom_materiau)

        # Remplissage des matrices
        # C'est une "slice" NumPy, très rapide
        self.Alpha[i_min:i_max, j_min:j_max, k_min:k_max] = val_alpha
        self.Lambda[i_min:i_max, j_min:j_max, k_min:k_max] = val_lambda

        # Cas spécial: Gérer les zones d'air (pour la convection)
        if val_alpha < 0:
            id_zone = int(val_alpha) # ex: -1

            # Créer la zone si elle n'existe pas
            if id_zone not in self.zones_air:
                self.zones_air[id_zone] = ZoneAir(
                    f"Zone {id_zone}",
                    self.params,
                    self.logger,
                    self.params.T_INTERIEUR_INIT
                )

            # Mettre à jour le volume de la zone
            volume_cellule = self.params.ds ** 3
            nb_cellules = (i_max - i_min) * (j_max - j_min) * (k_max - k_min)
            self.zones_air[id_zone].volume_m3 += (nb_cellules * volume_cellule)

        # Gérer les conditions limites (température fixe)
        if nom_materiau == "LIMITE_FIXE":
            self.T[i_min:i_max, j_min:j_max, k_min:k_max] = self.params.T_EXTERIEUR_INIT

        self.logger.info(f"Volume [{i_min}:{i_max-1}, {j_min}:{j_max-1}, {k_min}:{k_max-1}] rempli avec '{nom_materiau}'.")

    def preparer_simulation(self):
        """
        Appelée avant de lancer la simulation pour finaliser
        le modèle (détection des surfaces, etc.)
        """
        self.logger.info("Préparation de la simulation...")
        # Finaliser les calculs de volume/capacité pour les zones d'air
        for zone in self.zones_air.values():
            zone.finaliser_volume()

        # Détecter les surfaces de convection
        self._detecter_surfaces_convection()

    def _detecter_surfaces_convection(self):
        """
        (Validation Étape 1)
        Scan a (NumPy) la matrice Alpha pour trouver tous les points SOLIDES
        (Alpha >= 0) qui sont adjacents à un point AIR (Alpha < 0).
        """
        self.logger.info("Détection des surfaces de convection (NumPy)...")

        # 1. Identifier les solides (True où Alpha >= 0)
        solides = (self.Alpha >= 0)
        # 2. Identifier l'air (True où Alpha < 0)
        air = (self.Alpha < 0)

        # 3. Trouver les surfaces en X
        # Solide à [i] et Air à [i+1] -> Solide est une surface
        surf_x1 = solides[:-1, :, :] & air[1:, :, :]
        # Air à [i] et Solide à [i+1] -> Solide est une surface
        surf_x2 = air[:-1, :, :] & solides[1:, :, :]

        # 4. Trouver les surfaces en Y
        surf_y1 = solides[:, :-1, :] & air[:, 1:, :]
        surf_y2 = air[:, :-1, :] & solides[:, 1:, :]

        # 5. Trouver les surfaces en Z
        surf_z1 = solides[:, :, :-1] & air[:, :, 1:]
        surf_z2 = air[:, :, :-1] & solides[:, :, 1:]

        # 6. Combiner tous les masques de surface
        # On crée des masques 3D complets (taille N_x, N_y, N_z)
        # en complétant avec 'False' sur le bord manquant.
        pad_x = ((0, 1), (0, 0), (0, 0)) # Pad à la fin de l'axe X
        pad_y = ((0, 0), (0, 1), (0, 0))
        pad_z = ((0, 0), (0, 0), (0, 1))

        # Le masque final 'surface_totale' est True à (i,j,k)
        # si la cellule (i,j,k) est un SOLIDE touchant de l'AIR.
        surface_totale = (
            np.pad(surf_x1, pad_x, constant_values=False) |
            np.pad(surf_x2, ((1, 0), (0, 0), (0, 0)), constant_values=False) |
            np.pad(surf_y1, pad_y, constant_values=False) |
            np.pad(surf_y2, ((0, 0), (1, 0), (0, 0)), constant_values=False) |
            np.pad(surf_z1, pad_z, constant_values=False) |
            np.pad(surf_z2, ((0, 0), (0, 0), (1, 0)), constant_values=False)
        )

        # 7. Trouver les ID de zone d'air adjacents
        # On ne le fait que pour les zones d'air (ex: -1)
        for id_zone in self.zones_air.keys():
            # Masque de l'air pour CETTE zone
            air_zone_specifique = (self.Alpha == id_zone)

            # Recalculer les surfaces juste pour cette zone
            surf_x1_z = solides[:-1, :, :] & air_zone_specifique[1:, :, :]
            surf_x2_z = air_zone_specifique[:-1, :, :] & solides[1:, :, :]
            surf_y1_z = solides[:, :-1, :] & air_zone_specifique[:, 1:, :]
            surf_y2_z = air_zone_specifique[:, :-1, :] & solides[:, 1:, :]
            surf_z1_z = solides[:, :, :-1] & air_zone_specifique[:, :, 1:]
            surf_z2_z = air_zone_specifique[:, :, :-1] & solides[:, :, 1:]

            surface_zone = (
                np.pad(surf_x1_z, pad_x, constant_values=False) |
                np.pad(surf_x2_z, ((1, 0), (0, 0), (0, 0)), constant_values=False) |
                np.pad(surf_y1_z, pad_y, constant_values=False) |
                np.pad(surf_y2_z, ((0, 0), (1, 0), (0, 0)), constant_values=False) |
                np.pad(surf_z1_z, pad_z, constant_values=False) |
                np.pad(surf_z2_z, ((0, 0), (0, 0), (1, 0)), constant_values=False)
            )

            # 8. Extraire les coordonnées (indices) des points de surface
            # np.where(surface_zone) renvoie 3 arrays: (array_i, array_j, array_k)
            # np.vstack(...).T les transforme en une liste de triplets [(i,j,k), ...]
            indices_surface = np.vstack(np.where(surface_zone)).T
            self.surfaces_convection_idx[id_zone] = indices_surface

            self.logger.info(f"Détection terminée: {len(indices_surface)} cellules de surface trouvées pour Zone {id_zone}.")

