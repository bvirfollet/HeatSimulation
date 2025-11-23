# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation
from model_data import MATERIAUX
from model_data import ZoneAir
from parametres import ParametresSimulation
import numpy as np
import pickle


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

    # --- NOUVEAU: Sauvegarde et Chargement du modèle ---
    def sauvegarder(self, chemin_fichier):
        """Sauvegarde l'objet ModeleMaison complet dans un fichier pickle."""
        self.logger.info(f"Sauvegarde du modèle dans '{chemin_fichier}'...")
        try:
            # On ne veut pas sauvegarder le logger
            logger_temp = self.logger
            self.logger = None
            self.params.logger = None
            for zone in self.zones_air.values():
                zone.logger = None

            with open(chemin_fichier, 'wb') as f:
                pickle.dump(self, f)

            # Restaurer le logger
            self.logger = logger_temp
            self.params.logger = logger_temp
            for zone in self.zones_air.values():
                zone.logger = logger_temp

            self.logger.info("Sauvegarde terminée.")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde du modèle: {e}")
            # Restaurer le logger même en cas d'échec
            self.logger = logger_temp
            self.params.logger = logger_temp
            for zone in self.zones_air.values():
                zone.logger = logger_temp

    @staticmethod
    def charger(chemin_fichier, logger):
        """Charge un objet ModeleMaison depuis un fichier pickle."""
        logger.info(f"Chargement du modèle depuis '{chemin_fichier}'...")
        try:
            with open(chemin_fichier, 'rb') as f:
                modele = pickle.load(f)

            # Attacher un nouveau logger
            modele.logger = logger
            modele.params.logger = logger
            for zone in modele.zones_air.values():
                zone.logger = logger

            logger.info("Modèle chargé avec succès.")
            logger.info(f"Grille: {modele.params.N_x}x{modele.params.N_y}x{modele.params.N_z}")
            return modele
        except FileNotFoundError:
            logger.error(f"Fichier modèle '{chemin_fichier}' introuvable.")
            return None
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {e}")
            return None

    def _coord_m_vers_idx(self, coord_m):
        """Convertit une coordonnée physique (m) en index de grille."""
        return int(round(coord_m / self.params.ds))

    # --- NOUVEAU: Méthode pour l'éditeur TUI ---
    def set_material_at(self, x, y, z, nom_materiau):
        """
        Définit le matériau à UN point (x, y, z) de la grille.
        Gère la mise à jour des volumes d'air.
        """
        if not (0 <= x < self.params.N_x and
                0 <= y < self.params.N_y and
                0 <= z < self.params.N_z):
            return  # En dehors des limites

        if nom_materiau not in MATERIAUX:
            self.logger.warn(f"Matériau '{nom_materiau}' inconnu. Ignoré.")
            return

        props_new = MATERIAUX[nom_materiau]

        # --- Gestion complexe des zones d'air ---
        id_zone_existante = self.Alpha[x, y, z]
        volume_voxel_m3 = self.params.ds ** 3

        # Cas 1: On remplace un matériau par de l'AIR
        if props_new["type"] == "AIR":
            id_zone_a_rejoindre = -1  # On suppose une seule zone d'air

            # Si on remplace un solide, on doit ajouter du volume
            if id_zone_existante >= 0:  # C'était un SOLIDE ou LIMITE
                if id_zone_a_rejoindre not in self.zones_air:
                    self.zones_air[id_zone_a_rejoindre] = ZoneAir(
                        f"{id_zone_a_rejoindre}", self.logger, self.params.T_interieur_init
                    )
                self.zones_air[id_zone_a_rejoindre].volume_m3 += volume_voxel_m3

            # Si on remplace une AUTRE zone d'air (fusion), on ne gère pas
            elif id_zone_existante != id_zone_a_rejoindre and id_zone_existante < 0:
                self.logger.warn("La fusion de zones d'air n'est pas gérée.")
                # (On devrait transférer le volume, etc.)

            self.Alpha[x, y, z] = id_zone_a_rejoindre
            self.Lambda[x, y, z] = 0.0
            self.RhoCp[x, y, z] = 0.0
            self.T[x, y, z] = self.params.T_interieur_init

        # Cas 2: On remplace de l'AIR par un matériau
        elif id_zone_existante < 0:  # C'était de l'AIR
            if id_zone_existante in self.zones_air:
                self.zones_air[id_zone_existante].volume_m3 -= volume_voxel_m3

            # Appliquer les nouvelles propriétés (SOLIDE ou LIMITE)
            self._apply_material_props(x, y, z, nom_materiau, props_new)

        # Cas 3: On remplace un SOLIDE/LIMITE par un autre SOLIDE/LIMITE
        else:
            self._apply_material_props(x, y, z, nom_materiau, props_new)

    def _apply_material_props(self, x, y, z, nom_materiau, props):
        """Helper pour appliquer les propriétés d'un matériau (non-air)."""
        if props["type"] == "LIMITE_FIXE":
            self.Alpha[x, y, z] = 0.0
            self.Lambda[x, y, z] = 0.0
            self.RhoCp[x, y, z] = 0.0
            if nom_materiau == "TERRE":  # Cas spécial
                self.T[x, y, z] = self.params.T_sol_init
            else:
                self.T[x, y, z] = self.params.T_exterieur_init

        elif props["type"] == "SOLIDE":
            self.Alpha[x, y, z] = props["alpha"]
            self.Lambda[x, y, z] = props["lambda"]
            self.RhoCp[x, y, z] = props["rho"] * props["cp"]
            if nom_materiau == "TERRE":
                self.T[x, y, z] = self.params.T_sol_init
            else:
                self.T[x, y, z] = self.params.T_interieur_init

    def construire_volume_metres(self, p1_m, p2_m, nom_materiau, T_override_K=None):
        """Remplit un volume de la grille (défini en mètres) avec un matériau."""

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

        if props["type"] == "AIR":
            id_zone = -1
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

            if T_override_K is not None:
                self.T[s] = T_override_K
            else:
                self.T[s] = self.params.T_exterieur_init

        elif props["type"] == "SOLIDE":
            self.Alpha[s] = props["alpha"]
            self.Lambda[s] = props["lambda"]
            self.RhoCp[s] = props["rho"] * props["cp"]

            if T_override_K is not None:
                self.T[s] = T_override_K
            else:
                self.T[s] = self.params.T_interieur_init

    def construire_depuis_plans_ascii(self, plans_definition_str, mappage_ascii):
        """Construit le modèle 3D en "extrudant" des plans 2D (dessinés en ASCII)."""
        self.logger.info("Construction du modèle à partir de plans ASCII...")
        dims_plan_attendues_yx = (self.params.N_y, self.params.N_x)

        mappage_inv = {v: k for k, v in mappage_ascii.items()}
        id_plan_map = {}
        mat_id_counter = 0

        mappage_num = {}

        for char, nom_materiau in mappage_ascii.items():
            if nom_materiau not in MATERIAUX:
                self.logger.warn(f"ASCII Mappage: Matériau '{nom_materiau}' inconnu. Ignoré.")
                continue
            id_plan_map[char] = mat_id_counter
            mappage_num[mat_id_counter] = nom_materiau
            mat_id_counter += 1

        plans_etages_numpy = {}

        # 1. Convertir tous les plans ASCII en plans NumPy
        for (z_min_m, z_max_m), plan_str in plans_definition_str.items():
            lignes = [ligne.rstrip() for ligne in plan_str.strip().split('\n') if
                      ligne.strip()]  # rstrip pour enlever les espaces de fin

            if not lignes:
                self.logger.warn(f"Plan ASCII pour z=[{z_min_m}, {z_max_m}] est vide. Ignoré.")
                continue

            hauteur = len(lignes)

            # Vérifier que toutes les lignes ont la même longueur (celle de la plus longue)
            largeur = max(len(ligne) for ligne in lignes)

            lignes_paddees = [ligne.ljust(largeur) for ligne in lignes]  # Padder avec des espaces

            dims_plan_recu_yx = (hauteur, largeur)

            if dims_plan_recu_yx != dims_plan_attendues_yx:
                self.logger.error(f"Plan ASCII pour z=[{z_min_m}, {z_max_m}] a la mauvaise taille. "
                                  f"Attendu (Y,X): {dims_plan_attendues_yx}, Reçu: {dims_plan_recu_yx}. Ignoré.")
                continue

            plan_np = np.full(dims_plan_attendues_yx, 0, dtype=int)

            for y, ligne in enumerate(lignes_paddees):
                for x, char in enumerate(ligne):
                    if char not in id_plan_map:
                        self.logger.warn(
                            f"Caractère '{char}' à (y={y}, x={x}) non trouvé dans le mappage_ascii. Utilisation de ' ' (AIR).")
                        char = ' '  # Par défaut, on met de l'air
                    plan_np[y, x] = id_plan_map[char]

            plans_etages_numpy[(z_min_m, z_max_m)] = plan_np

        # 2. Appeler l'ancienne fonction de construction NumPy
        self.construire_depuis_plans(plans_etages_numpy, mappage_num)

    def construire_depuis_plans(self, plans_etages, mappage):
        """Construit le modèle 3D en "extrudant" des plans 2D (tableaux NumPy)."""
        self.logger.info("Construction du modèle à partir de plans 2D (NumPy)...")

        dims_plan_attendues = (self.params.N_y, self.params.N_x)

        for (z_min_m, z_max_m), plan in plans_etages.items():
            if plan.shape != dims_plan_attendues:
                self.logger.error(f"Plan pour z=[{z_min_m}, {z_max_m}] a la mauvaise taille. "
                                  f"Attendu: {dims_plan_attendues}, Reçu: {plan.shape}. Ignoré.")
                continue

            k1 = self._coord_m_vers_idx(z_min_m)
            k2 = self._coord_m_vers_idx(z_max_m)
            k1 = max(0, k1);
            k2 = min(self.params.N_z, k2)

            if k1 >= k2: continue

            slice_z = slice(k1, k2)
            self.logger.debug(
                f"Application du plan {plan.shape} de z={z_min_m}m à {z_max_m}m (indices k={k1} à {k2 - 1})")

            for mat_id, nom_materiau in mappage.items():
                indices_y, indices_x = np.where(plan == mat_id)
                if indices_x.size == 0: continue

                if nom_materiau not in MATERIAUX:
                    self.logger.warn(f"Matériau ID {mat_id} ('{nom_materiau}') inconnu. Ignoré.")
                    continue

                props = MATERIAUX[nom_materiau]
                s = (indices_x, indices_y, slice_z)

                if props["type"] == "AIR":
                    id_zone = -1
                    if id_zone not in self.zones_air:
                        self.zones_air[id_zone] = ZoneAir(
                            f"{id_zone}", self.logger, self.params.T_interieur_init
                        )
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
                    pass

                elif props["type"] == "SOLIDE":
                    self.Alpha[s] = props["alpha"]
                    self.Lambda[s] = props["lambda"]
                    self.RhoCp[s] = props["rho"] * props["cp"]
                    if nom_materiau == "TERRE":
                        self.T[s] = self.params.T_sol_init
                    else:
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
