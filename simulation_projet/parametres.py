# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation


class ParametresSimulation:
    """Stocke les paramètres de la simulation (grille, temps)."""

    def __init__(self, logger,
                 dims_m=(1.0, 1.0, 1.0),
                 ds=0.1, dt=20.0,
                 T_interieur_init=20.0,
                 T_exterieur_init=0.0,
                 h_convection=8.0):
        self.logger = logger

        # Dimensions physiques (mètres)
        self.L_x, self.L_y, self.L_z = dims_m

        # Discrétisation (mètres et secondes)
        self.ds = ds  # Taille d'une cellule (dx, dy, dz)
        self.dt = dt  # Pas de temps

        # Nombre de points de grille (N = L/ds + 1)
        # +2 pour inclure les bords (0 et N-1)
        self.N_x = int(round(self.L_x / self.ds)) + 1
        self.N_y = int(round(self.L_y / self.ds)) + 1
        self.N_z = int(round(self.L_z / self.ds)) + 1

        # Températures initiales
        self.T_interieur_init = T_interieur_init
        self.T_exterieur_init = T_exterieur_init

        # Coefficient de convection (W/m^2.K)
        # 8.0 est une valeur typique pour une surface verticale intérieure
        self.h_convection = h_convection

        self.logger.info(
            f"Paramètres créés. Grille: {self.N_x}x{self.N_y}x{self.N_z} ({self.N_x * self.N_y * self.N_z} cellules)")
        self.logger.debug(f"Dimensions: {self.L_x}m x {self.L_y}m x {self.L_z}m")
        self.logger.debug(f"Discrétisation: ds={self.ds}m, dt={self.dt}s")


# --- CLASSE 3: Données du Modèle ---
# (Classes pour stocker les données physiques : ZoneAir)


