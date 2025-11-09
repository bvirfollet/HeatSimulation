from logger import LoggerSimulation
from model_data import MATERIAUX
from model_data import ZoneAir
from parametres import ParametresSimulation
import numpy as np


class ModeleMaison:
    """
    Contient les matrices 3D (T, Alpha, Lambda) et les méthodes
    pour construire la géométrie de la maison.
    """

    def __init__(self, params):
        self.params = params
        self.logger = LoggerSimulation(niveau="DEBUG")

        # Dimensions de la grille
        N_x, N_y, N_z = params.N_x, params.N_y, params.N_z

        # Matrice 3D des Températures (initialisée à T_interieur)
        self.T = np.full((N_x, N_y, N_z), params.T_interieur_init, dtype=np.float64)

        # Matrices 3D des propriétés (initialisées à 0)
        self.Alpha = np.zeros((N_x, N_y, N_z), dtype=np.float64)
        self.Lambda = np.zeros((N_x, N_y, N_z), dtype=np.float64)
        self.RhoCp = np.zeros((N_x, N_y, N_z), dtype=np.float64)  # Capacité thermique volumique

        # Gestion des zones d'air (nœuds thermiques)
        self.zones_air = {}  # Dictionnaire {id: ZoneAir}

        # Gestion des surfaces de convection (calculées par _detecter_surfaces)
        # Format: {zone_id: [(i, j, k), (i, j, k), ...]}
        self.surfaces_convection_idx = {}
        # Format: {zone_id: np.array([[i,j,k], [i,j,k], ...])}
        self.surfaces_convection_np = {}

        self.logger.info("Modèle 3D (matrices NumPy) initialisé.")

    def _get_coords_indices(self, pos_m, dim_m):
        """Convertit des coordonnées [m] en indices de grille [i, j, k]."""
        ds = self.params.ds

        # Début (arrondi à l'indice le plus proche)
        i_min = max(0, int(round(pos_m[0] / ds)))
        j_min = max(0, int(round(pos_m[1] / ds)))
        k_min = max(0, int(round(pos_m[2] / ds)))

        # Fin (calculée depuis la position + dimension)
        i_max = min(self.params.N_x - 1, int(round((pos_m[0] + dim_m[0]) / ds)))
        j_max = min(self.params.N_y - 1, int(round((pos_m[1] + dim_m[1]) / ds)))
        k_max = min(self.params.N_z - 1, int(round((pos_m[2] + dim_m[2]) / ds)))

        # Retourne des slices (ex: slice(1, 10))
        return slice(i_min, i_max + 1), slice(j_min, j_max + 1), slice(k_min, k_max + 1)

    def construire_volume_metres(self, pos_m, dim_m, nom_materiau,
                                 zone_id=None, T_imposee=None):
        """
        Remplit un volume de la grille basé sur des coordonnées en mètres.

        pos_m (tuple): (x, y, z) de départ en mètres.
        dim_m (tuple): (largeur_x, largeur_y, largeur_z) en mètres.
        nom_materiau (str): Nom du matériau (ex: "PARPAING").
        zone_id (int): ID de la zone d'air (si matériau="AIR").
        T_imposee (float): Température fixe (si matériau="LIMITE_FIXE").
        """

        try:
            materiau = MATERIAUX[nom_materiau]
        except KeyError:
            self.logger.error(f"Matériau '{nom_materiau}' inconnu. Construction annulée.")
            return

        # 1. Convertir les mètres en indices
        idx = self._get_coords_indices(pos_m, dim_m)
        self.logger.info(f"Volume {idx} rempli avec '{nom_materiau}'.")

        # 2. Remplir les matrices de propriétés
        self.Alpha[idx] = materiau["alpha"]
        self.Lambda[idx] = materiau["lambda"]
        self.RhoCp[idx] = materiau["rho"] * materiau["cp"]

        # 3. Gérer les cas spéciaux (FIXE, ZONE)

        if materiau["type"] == "FIXE":
            # Si T_imposee n'est pas fournie, utiliser T_exterieur par défaut
            temp = T_imposee if T_imposee is not None else self.params.T_exterieur_init
            self.T[idx] = temp

        elif materiau["type"] == "ZONE":
            if zone_id is None:
                self.logger.error("Matériau 'AIR' requiert un 'zone_id'. Construction annulée.")
                return

            # Créer la zone si elle n'existe pas
            if zone_id not in self.zones_air:
                self.zones_air[zone_id] = ZoneAir(zone_id, self.params.T_interieur_init, self.logger)

            # Marquer la grille avec l'ID de la zone
            self.Alpha[idx] = zone_id  # On utilise Alpha pour stocker l'ID de zone

            # Calculer le volume réel rempli
            volume_cellule_m3 = self.params.ds ** 3
            # np.count_nonzero(self.Alpha == zone_id) pourrait être lent,
            # on approxime ou on calcule via les slices
            indices = (idx[0].start, idx[0].stop,
                       idx[1].start, idx[1].stop,
                       idx[2].start, idx[2].stop)

            nb_cellules = (indices[1] - indices[0]) * \
                          (indices[3] - indices[2]) * \
                          (indices[5] - indices[4])

            volume_ajoute = nb_cellules * volume_cellule_m3
            self.zones_air[zone_id].ajouter_volume(volume_ajoute)

    def preparer_simulation(self):
        """Finalise le modèle avant de lancer la simulation."""
        self.logger.info("Préparation de la simulation...")

        # Finaliser les zones d'air (calculer capacité thermique)
        for zone in self.zones_air.values():
            zone.finaliser_setup()

        # Détecter les surfaces de convection
        self._detecter_surfaces_convection()

        # TODO: Pré-calculer d'autres éléments (ex: facteurs de forme)

    def _detecter_surfaces_convection(self):
        """
        Utilise NumPy pour détecter toutes les interfaces SOLIDE <-> ZONE_AIR.
        Remplit 'self.surfaces_convection_idx' et 'self.surfaces_convection_np'.
        """
        self.logger.info("Détection des surfaces de convection (NumPy)...")

        # 1. Créer des masques
        # Masque des zones d'air (alpha < 0)
        masque_air = self.Alpha < 0
        # Masque des solides (alpha >= 0 ET type != FIXE)
        masque_solide = (self.Alpha >= 0) & (self.Lambda > 0)  # Lambda > 0 exclut les 'FIXE'

        # 2. Itérer sur les 6 directions (voisins)
        directions = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

        # Utilise un set pour éviter les doublons (une cellule peut toucher l'air de 2 côtés)
        surfaces_par_zone = {}  # {zone_id: set((i,j,k))}

        for d in directions:
            # Décaler le masque 'air'
            masque_air_decale = np.roll(masque_air, shift=d, axis=(0, 1, 2))

            # L'interface est là où un 'solide' touche un 'air' décalé
            interface = masque_solide & masque_air_decale

            # Récupérer les indices (i,j,k) des solides sur l'interface
            indices_interface = np.argwhere(interface)

            # Récupérer les IDs des zones d'air qu'ils touchent
            # (en regardant le masque alpha décalé dans l'autre sens)
            indices_air_touches = (
                (indices_interface[:, 0] - d[0]) % self.params.N_x,
                (indices_interface[:, 1] - d[1]) % self.params.N_y,
                (indices_interface[:, 2] - d[2]) % self.params.N_z
            )

            zone_ids_touches = self.Alpha[indices_air_touches]

            # Ajouter les indices des solides au bon set
            for i in range(len(indices_interface)):
                idx_tuple = tuple(indices_interface[i])
                zone_id = zone_ids_touches[i]

                if zone_id not in surfaces_par_zone:
                    surfaces_par_zone[zone_id] = set()
                surfaces_par_zone[zone_id].add(idx_tuple)

        # 3. Convertir les sets en listes/arrays NumPy
        for zone_id, idx_set in surfaces_par_zone.items():
            self.surfaces_convection_idx[zone_id] = list(idx_set)
            self.surfaces_convection_np[zone_id] = np.array(list(idx_set))
            self.logger.info(f"Détection terminée: {len(idx_set)} cellules de surface trouvées pour Zone {zone_id}.")


# --- CLASSE 6: Simulation ---
# (Contient le moteur de calcul principal)


