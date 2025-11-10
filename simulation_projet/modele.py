# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation
from model_data import MATERIAUX
from model_data import ZoneAir
from parametres import ParametresSimulation
import numpy as np


class ModeleMaison:
    """Gère la géométrie 3D, les matériaux et la détection des surfaces."""

    def __init__(self, params):
        self.params = params
        self.logger = params.logger

        # Création des grilles 3D (NumPy)
        dims = (self.params.N_x, self.params.N_y, self.params.N_z)

        # Matrice de Température (initialisée à T_interieur)
        self.T = np.full(dims, self.params.T_interieur_init, dtype=np.float64)

        # Matrice de Diffusivité (alpha)
        self.Alpha = np.full(dims, 0.0, dtype=np.float64)

        # Matrice de Conductivité (lambda)
        self.Lambda = np.full(dims, 0.0, dtype=np.float64)

        # Matrice de Capacité Thermique Volumique (rho * cp)
        self.RhoCp = np.full(dims, 0.0, dtype=np.float64)

        # Dictionnaire des zones d'air
        self.zones_air = {}  # ex: {-1: ZoneAir(...)}

        # Index des surfaces de convection (pré-calculé)
        # Format: {id_zone_air: (tuple_indices_x, tuple_indices_y, tuple_indices_z)}
        self.surfaces_convection_idx = {}

        self.logger.info("Modèle 3D (matrices NumPy) initialisé.")

    def _coord_m_vers_idx(self, coord_m):
        """Convertit une coordonnée physique (m) en index de grille."""
        # round(m / ds)
        return int(round(coord_m / self.params.ds))

    def construire_volume_metres(self, p1_m, p2_m, nom_materiau):
        """
        Remplit un volume de la grille (défini en mètres) avec un matériau.

        p1_m: (x1, y1, z1) en mètres
        p2_m: (x2, y2, z2) en mètres
        """

        # 1. Conversion des mètres en index de grille
        # On s'assure que p1 est min et p2 est max
        x1 = self._coord_m_vers_idx(min(p1_m[0], p2_m[0]))
        y1 = self._coord_m_vers_idx(min(p1_m[1], p2_m[1]))
        z1 = self._coord_m_vers_idx(min(p1_m[2], p2_m[2]))

        # L'index max est N (ex: 10m / 0.1m = 100 -> index 100)
        # On prend +1 car le 'slice' (ex: 0:11) est exclusif à la fin
        x2 = self._coord_m_vers_idx(max(p1_m[0], p2_m[0])) + 1
        y2 = self._coord_m_vers_idx(max(p1_m[1], p2_m[1])) + 1
        z2 = self._coord_m_vers_idx(max(p1_m[2], p2_m[2])) + 1

        # S'assure qu'on reste dans les limites de la grille
        x1 = max(0, x1);
        x2 = min(self.params.N_x, x2)
        y1 = max(0, y1);
        y2 = min(self.params.N_y, y2)
        z1 = max(0, z1);
        z2 = min(self.params.N_z, z2)

        s = (slice(x1, x2), slice(y1, y2), slice(z1, z2))
        self.logger.info(f"Volume {s} rempli avec '{nom_materiau}'.")

        # 2. Récupérer les propriétés du matériau
        if nom_materiau not in MATERIAUX:
            self.logger.error(f"Matériau '{nom_materiau}' inconnu. Ignoré.")
            return

        props = MATERIAUX[nom_materiau]

        # 3. Remplir les matrices

        if props["type"] == "AIR":
            # Cas spécial: Zone d'air (convection)

            # ID de la zone (ex: -1, -2...). On utilise des ID négatifs.
            id_zone = -1 * (len(self.zones_air) + 1)

            if id_zone not in self.zones_air:
                self.zones_air[id_zone] = ZoneAir(
                    f"{id_zone}",  # Nom de la zone
                    self.logger,
                    self.params.T_interieur_init
                )

            # Ajoute le volume de ce bloc à la zone
            volume_bloc_m3 = (x2 - x1) * (y2 - y1) * (z2 - z1) * (self.params.ds ** 3)
            self.zones_air[id_zone].volume_m3 += volume_bloc_m3

            # Marque la grille avec l'ID de la zone
            self.Alpha[s] = id_zone
            self.Lambda[s] = 0.0  # Pas de conduction
            self.RhoCp[s] = 0.0  # Pas de capacité (stocké dans l'objet ZoneAir)
            # Ne pas toucher à T[s], il garde T_interieur_init

        elif props["type"] == "LIMITE_FIXE":
            # Cas spécial: Condition limite (température fixe)
            self.Alpha[s] = 0.0  # Ne diffuse pas
            self.Lambda[s] = 0.0  # Ne conduit pas
            self.RhoCp[s] = 0.0
            # IMPOSER LA TEMPÉRATURE
            self.T[s] = self.params.T_exterieur_init

        elif props["type"] == "SOLIDE":
            # Cas standard: Matériau solide (conduction)
            self.Alpha[s] = props["alpha"]
            self.Lambda[s] = props["lambda"]
            self.RhoCp[s] = props["rho"] * props["cp"]
            # La température T[s] garde sa valeur initiale (T_interieur_init)

    def preparer_simulation(self):
        """Finalise le modèle avant de lancer la simulation."""
        self.logger.info("Préparation de la simulation...")
        # Finaliser la capacité thermique des zones d'air
        for zone in self.zones_air.values():
            zone.finaliser_capacite()

        # Détecter toutes les surfaces de convection
        self._detecter_surfaces_convection()

    def _detecter_surfaces_convection(self):
        """
        Scan (en NumPy) la grille Alpha pour trouver les interfaces
        entre 'AIR' (val < 0) et 'SOLIDE' (val >= 0).
        Stocke les *indices des solides* en contact.
        """
        self.logger.info("Détection des surfaces de convection (NumPy)...")

        # Pour chaque zone d'air (ex: id_zone = -1)
        for id_zone, zone in self.zones_air.items():
            # 1. Créer un masque 'True' là où se trouve la zone d'air
            masque_air = (self.Alpha == id_zone)

            # 2. Créer un masque 'True' là où se trouvent les solides
            # (alpha >= 0, mais on exclut LIMITE_FIXE qui a alpha=0)
            masque_solide = (self.Alpha > 0)

            # 3. Trouver les interfaces
            surfaces = np.zeros_like(self.Alpha, dtype=bool)

            # Vérifie les 6 voisins (X, Y, Z)
            # Un solide est une surface si son voisin est de l'air
            surfaces[1:, :, :] |= (masque_solide[1:, :, :] & masque_air[:-1, :, :])
            surfaces[:-1, :, :] |= (masque_solide[:-1, :, :] & masque_air[1:, :, :])

            surfaces[:, 1:, :] |= (masque_solide[:, 1:, :] & masque_air[:, :-1, :])
            surfaces[:, :-1, :] |= (masque_solide[:, :-1, :] & masque_air[:, 1:, :])

            surfaces[:, :, 1:] |= (masque_solide[:, :, 1:] & masque_air[:, :, :-1])
            surfaces[:, :, :-1] |= (masque_solide[:, :, :-1] & masque_air[:, :, 1:])

            # 4. Stocker les indices (format tuple (i, j, k))
            indices_tuple = np.where(surfaces)
            self.surfaces_convection_idx[id_zone] = indices_tuple

            nb_surfaces = len(indices_tuple[0])
            self.logger.info(f"Détection terminée: {nb_surfaces} cellules de surface trouvées pour Zone {zone.nom}.")


# --- CLASSE 6: Moteur de Simulation ---
# (Contient la boucle de calcul principale)


