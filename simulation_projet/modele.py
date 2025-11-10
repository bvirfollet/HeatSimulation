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
        self.surfaces_convection_idx = {}

        self.logger.info("Modèle 3D (matrices NumPy) initialisé.")

    def _coord_m_vers_idx(self, coord_m):
        """Convertit une coordonnée physique (m) en index de grille."""
        return int(round(coord_m / self.params.ds))

    def _set_material_at_idx(self, i, j, k, nom_materiau):
        """Fonction helper pour appliquer un matériau à un seul voxel (i,j,k)."""

        if nom_materiau not in MATERIAUX:
            self.logger.warn(f"Matériau '{nom_materiau}' inconnu. Ignoré à ({i},{j},{k}).")
            return

        props = MATERIAUX[nom_materiau]

        if props["type"] == "AIR":
            id_zone = -1 * (len(self.zones_air) + 1)
            if id_zone not in self.zones_air:
                self.zones_air[id_zone] = ZoneAir(
                    f"{id_zone}", self.logger, self.params.T_interieur_init
                )

            volume_voxel_m3 = self.params.ds ** 3
            self.zones_air[id_zone].volume_m3 += volume_voxel_m3

            self.Alpha[i, j, k] = id_zone
            self.Lambda[i, j, k] = 0.0
            self.RhoCp[i, j, k] = 0.0
            self.T[i, j, k] = self.params.T_interieur_init  # Assure la T° init

        elif props["type"] == "LIMITE_FIXE":
            self.Alpha[i, j, k] = 0.0
            self.Lambda[i, j, k] = 0.0
            self.RhoCp[i, j, k] = 0.0
            # Note: La T° est assignée par construire_volume_metres

        elif props["type"] == "SOLIDE":
            self.Alpha[i, j, k] = props["alpha"]
            self.Lambda[i, j, k] = props["lambda"]
            self.RhoCp[i, j, k] = props["rho"] * props["cp"]
            self.T[i, j, k] = self.params.T_interieur_init  # Assure la T° init

    def construire_volume_metres(self, p1_m, p2_m, nom_materiau, T_override_K=None):
        """
        Remplit un volume de la grille (défini en mètres) avec un matériau.

        p1_m: (x1, y1, z1) en mètres
        p2_m: (x2, y2, z2) en mètres
        T_override_K: (Optionnel) Force la température pour ce volume.
        """

        # 1. Conversion des mètres en index de grille
        x1 = self._coord_m_vers_idx(min(p1_m[0], p2_m[0]))
        y1 = self._coord_m_vers_idx(min(p1_m[1], p2_m[1]))
        z1 = self._coord_m_vers_idx(min(p1_m[2], p2_m[2]))

        x2 = self._coord_m_vers_idx(max(p1_m[0], p2_m[0])) + 1
        y2 = self._coord_m_vers_idx(max(p1_m[1], p2_m[1])) + 1
        z2 = self._coord_m_vers_idx(max(p1_m[2], p2_m[2])) + 1

        x1 = max(0, x1);
        x2 = min(self.params.N_x, x2)
        y1 = max(0, y1);
        y2 = min(self.params.N_y, y2)
        z1 = max(0, z1);
        z2 = min(self.params.N_z, z2)

        s = (slice(x1, x2), slice(y1, y2), slice(z1, z2))
        self.logger.info(f"Volume {s} rempli avec '{nom_materiau}'.")

        if nom_materiau not in MATERIAUX:
            self.logger.error(f"Matériau '{nom_materiau}' inconnu. Ignoré.")
            return

        props = MATERIAUX[nom_materiau]

        # 3. Remplir les matrices (logique optimisée pour NumPy)

        if props["type"] == "AIR":
            id_zone = -1 * (len(self.zones_air) + 1)
            if id_zone not in self.zones_air:
                self.zones_air[id_zone] = ZoneAir(
                    f"{id_zone}", self.logger, self.params.T_interieur_init
                )

            volume_bloc_m3 = (x2 - x1) * (y2 - y1) * (z2 - z1) * (self.params.ds ** 3)
            self.zones_air[id_zone].volume_m3 += volume_bloc_m3

            self.Alpha[s] = id_zone
            self.Lambda[s] = 0.0
            self.RhoCp[s] = 0.0
            self.T[s] = self.params.T_interieur_init

        elif props["type"] == "LIMITE_FIXE":
            self.Alpha[s] = 0.0
            self.Lambda[s] = 0.0
            self.RhoCp[s] = 0.0

            # --- MODIFIÉ: Utilise T_override_K ou T_exterieur_init ---
            if T_override_K is not None:
                self.T[s] = T_override_K
            else:
                self.T[s] = self.params.T_exterieur_init

        elif props["type"] == "SOLIDE":
            self.Alpha[s] = props["alpha"]
            self.Lambda[s] = props["lambda"]
            self.RhoCp[s] = props["rho"] * props["cp"]

            # --- MODIFIÉ: Utilise T_override_K ou T_interieur_init ---
            if T_override_K is not None:
                self.T[s] = T_override_K
            else:
                self.T[s] = self.params.T_interieur_init

    # --- NOUVELLE FONCTION: Construire depuis des plans 2D ---
    def construire_depuis_plans(self, plans_etages, mappage):
        """
        Construit le modèle 3D en "extrudant" des plans 2D (tableaux NumPy)
        sur des hauteurs (z) définies.

        plans_etages: { (z_min_m, z_max_m): plan_numpy, ... }
        mappage:      { id_plan (int): nom_materiau (str), ... }
        """
        self.logger.info("Construction du modèle à partir de plans 2D...")

        # Vérifier que les plans ont la bonne taille (Nx, Ny)
        dims_plan_attendues = (self.params.N_y, self.params.N_x)

        for (z_min_m, z_max_m), plan in plans_etages.items():
            if plan.shape != dims_plan_attendues:
                self.logger.error(f"Plan pour z=[{z_min_m}, {z_max_m}] a la mauvaise taille. "
                                  f"Attendu: {dims_plan_attendues}, Reçu: {plan.shape}. Ignoré.")
                continue

            # 1. Convertir les hauteurs Z en indices de grille
            k1 = self._coord_m_vers_idx(z_min_m)
            # +1 car le slice est exclusif
            k2 = self._coord_m_vers_idx(z_max_m)

            # S'assurer qu'on reste dans les limites Z
            k1 = max(0, k1);
            k2 = min(self.params.N_z, k2)

            if k1 >= k2:  # Si l'épaisseur est nulle (ex: < ds/2)
                continue

            slice_z = slice(k1, k2)
            self.logger.debug(
                f"Application du plan {plan.shape} de z={z_min_m}m à {z_max_m}m (indices k={k1} à {k2 - 1})")

            # 2. Itérer sur les matériaux du mappage (0, 1, 2...)
            for mat_id, nom_materiau in mappage.items():

                # Trouver où ce matériau se trouve dans le plan 2D
                # (plan == mat_id) donne un masque booléen 2D (ex: 11x11)
                # np.where(...) nous donne les indices (y, x)
                indices_y, indices_x = np.where(plan == mat_id)

                if indices_x.size == 0:  # Si ce matériau n'est pas dans ce plan
                    continue

                # 3. Appliquer les propriétés du matériau aux voxels 3D
                if nom_materiau not in MATERIAUX:
                    self.logger.warn(f"Matériau ID {mat_id} ('{nom_materiau}') inconnu. Ignoré.")
                    continue

                props = MATERIAUX[nom_materiau]

                # On utilise les indices x, y et le slice z
                s = (indices_x, indices_y, slice_z)

                if props["type"] == "AIR":
                    id_zone = -1
                    if id_zone not in self.zones_air:
                        self.zones_air[id_zone] = ZoneAir(
                            f"{id_zone}", self.logger, self.params.T_interieur_init
                        )

                    # Calcule le volume ajouté (Nb de voxels * V_voxel)
                    volume_bloc_m3 = indices_x.size * (k2 - k1) * (self.params.ds ** 3)
                    self.zones_air[id_zone].volume_m3 += volume_bloc_m3

                    self.Alpha[s] = id_zone
                    self.Lambda[s] = 0.0
                    self.RhoCp[s] = 0.0
                    self.T[s] = self.params.T_interieur_init

                elif props["type"] == "LIMITE_FIXE":
                    self.Alpha[s] = 0.0
                    self.Lambda[s] = 0.0
                    self.RhoCp[s] = 0.0
                    # La T° est assignée par T_exterieur_init (par défaut)
                    # ou doit être gérée par un appel 'construire_volume_metres'
                    self.T[s] = self.params.T_exterieur_init

                elif props["type"] == "SOLIDE":
                    self.Alpha[s] = props["alpha"]
                    self.Lambda[s] = props["lambda"]
                    self.RhoCp[s] = props["rho"] * props["cp"]
                    self.T[s] = self.params.T_interieur_init

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

        for id_zone, zone in self.zones_air.items():
            masque_air = (self.Alpha == id_zone)
            masque_solide = (self.Alpha > 0)  # SOLIDES (pas LIMITE_FIXE)

            surfaces = np.zeros_like(self.Alpha, dtype=bool)

            surfaces[1:, :, :] |= (masque_solide[1:, :, :] & masque_air[:-1, :, :])
            surfaces[:-1, :, :] |= (masque_solide[:-1, :, :] & masque_air[1:, :, :])
            surfaces[:, 1:, :] |= (masque_solide[:, 1:, :] & masque_air[:, :-1, :])
            surfaces[:, :-1, :] |= (masque_solide[:, :-1, :] & masque_air[:, 1:, :])
            surfaces[:, :, 1:] |= (masque_solide[:, :, 1:] & masque_air[:, :, :-1])
            surfaces[:, :, :-1] |= (masque_solide[:, :, :-1] & masque_air[:, :, 1:])

            indices_tuple = np.where(surfaces)
            self.surfaces_convection_idx[id_zone] = indices_tuple

            nb_surfaces = len(indices_tuple[0])
            self.logger.info(f"Détection terminée: {nb_surfaces} cellules de surface trouvées pour Zone {zone.nom}.")


# --- CLASSE 6: Moteur de Simulation ---
# (Contient la boucle de calcul principale)


