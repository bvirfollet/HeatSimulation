from logger import LoggerSimulation


class ParametresSimulation:
    """Conteneur pour tous les paramètres de la simulation."""

    def __init__(self, N_x, N_y, N_z, ds, dt,
                 T_interieur_init=20.0, T_exterieur_init=0.0):
        self.logger = LoggerSimulation(niveau="DEBUG")

        # Dimensions de la grille (en nombre de cellules)
        self.N_x = N_x
        self.N_y = N_y
        self.N_z = N_z

        # Discrétisation spatiale et temporelle
        self.ds = ds  # Taille d'une cellule (m)
        self.dt = dt  # Pas de temps (s)

        # Températures initiales
        self.T_interieur_init = T_interieur_init
        self.T_exterieur_init = T_exterieur_init

        # Propriétés de l'air (pour la convection)
        self.h_convection = 3.0  # Coefficient de convection W/(m^2.K) (air calme)

        self.logger.info(f"Paramètres créés. Grille: {N_x}x{N_y}x{N_z} ({N_x * N_y * N_z} cellules)")
        self.logger.debug(
            f"Dimensions: {self.get_dim_metres()[0]:.1f}m x {self.get_dim_metres()[1]:.1f}m x {self.get_dim_metres()[2]:.1f}m")
        self.logger.debug(f"Discrétisation: ds={ds}m, dt={dt}s")

    def get_dim_metres(self):
        """Retourne les dimensions physiques de la boîte (en mètres)."""
        # (N-1) * ds car N points définissent N-1 cellules
        return (
            (self.N_x - 1) * self.ds,
            (self.N_y - 1) * self.ds,
            (self.N_z - 1) * self.ds
        )


# --- CLASSE 3: Données du Modèle ---
# (Classes pour stocker les états du modèle)


