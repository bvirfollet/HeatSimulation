# --- Imports ---
from logger import LoggerSimulation


class ParametresSimulation:
    """Conteneur pour tous les paramètres de la simulation."""

    def __init__(self, dim_m, ds_m, dt_s, t_ext, t_int_init, logger=None):
        self.logger = logger if logger else LoggerSimulation(niveau="DEBUG")

        # --- Dimensions Physiques ---
        self.Lx, self.Ly, self.Lz = dim_m # (m)

        # --- Discrétisation Spatiale ---
        self.ds = ds_m # Taille d'un voxel (m)

        # Calcul du nombre de points de grille (N = L/ds + 1)
        # +1 car on modélise les N points, qui définissent N-1 cellules.
        self.N_x = int(self.Lx / self.ds) + 1
        self.N_y = int(self.Ly / self.ds) + 1
        self.N_z = int(self.Lz / self.ds) + 1

        # --- Discrétisation Temporelle ---
        self.dt = dt_s # Pas de temps (s)

        # --- Conditions Thermiques ---
        self.T_EXTERIEUR_INIT = t_ext # Température des bornes (ex: 0°C)
        self.T_INTERIEUR_INIT = t_int_init # Température initiale des solides (ex: 20°C)

        self.h_convection = 8.0 # Coeff. de convection (W/m².K), typique pour air intérieur

        self_str = f"Paramètres créés. Grille: {self.N_x}x{self.N_y}x{self.N_z} ({self.N_x*self.N_y*self.N_z} cellules)"
        self.logger.info(self_str)
        self.logger.debug(f"Dimensions: {self.Lx}m x {self.Ly}m x {self.Lz}m")
        self.logger.debug(f"Discrétisation: ds={self.ds}m, dt={self.dt}s")


# --- Constantes de MATERIAUX (Base de données) ---
# Dictionnaire des propriétés des matériaux.
# Structure: "NOM": [lambda (W/mK), rho (kg/m³), c_p (J/kg.K)]
# L'Alpha (diffusivité) est calculé à la volée.
# Note: "AIR" (ou tout ID < 0) est un marqueur pour une Zone d'Air (convection).
MATERIAUX = {
    # --- Marqueurs Spéciaux ---
    # ID -1: Zone d'air (sera gérée par la convection)
    # Les valeurs L/R/C ne sont pas utilisées pour la conduction
    "AIR": [-1.0, 1.2, 1005],

    # ID 0: Condition limite (température fixe)
    # Les valeurs L/R/C ne sont pas utilisées pour la conduction
    "LIMITE_FIXE": [0.0, 0.0, 0.0],

    # --- Solides (calculés par conduction) ---
    "PARPAING": [1.1, 2000, 880],
    "VERRE": [1.0, 2500, 750],
    "PLACO": [0.25, 900, 840],
    "LAINE_VERRE": [0.040, 15, 840],
    "LAINE_BOIS": [0.040, 140, 2100],
    "BETON": [1.7, 2400, 880]
}

