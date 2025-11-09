# --- Imports ---
from logger import LoggerSimulation


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

class ZoneAir:
    """
    Représente un volume d'air (une "zone") dans la simulation.
    Cette classe suit l'évolution de la température de l'air
    en fonction des apports et des pertes par convection.
    """
    def __init__(self, nom, params, logger, t_init=20.0):
        self.nom = nom
        self.logger = logger
        self.params = params

        self.T_air = t_init # Température actuelle de la zone (flottant)
        self.volume_m3 = 0.0 # Volume total (calculé par ModeleMaison)
        self.capacite_thermique_J_K = 0.0 # Capacité thermique totale (J/K)

        # Données de l'air
        _, self.rho_air, self.cp_air = MATERIAUX["AIR"]

        self.logger.info(f"Zone '{self.nom}' créée, T_init={self.T_air}°C")

    def finaliser_volume(self):
        """Appelée après la construction du modèle pour calculer la capacité."""
        # Capacité (J/K) = Volume (m³) * Densité (kg/m³) * Cp (J/kg.K)
        self.capacite_thermique_J_K = self.volume_m3 * self.rho_air * self.cp_air
        self.logger.info(f"Volume total: {self.volume_m3:.2f} m³")
        self.logger.info(f"Capacité thermique totale: {self.capacite_thermique_J_K:.2f} J/K")

    def calculer_evolution_T(self, flux_convection_W, dt_s):
        """
        Met à jour la température de l'air en fonction du flux net.
        flux_convection_W: Puissance nette reçue par l'air (en Watts).
                           Positif = l'air se réchauffe.
                           Négatif = l'air se refroidit.
        """
        # Variation d'Énergie (Joules) = Puissance (Watts) * Temps (s)
        delta_energie_J = flux_convection_W * dt_s

        # Variation de Température (°K ou °C) = Énergie (J) / Capacité (J/K)
        delta_T = delta_energie_J / self.capacite_thermique_J_K

        # Mettre à jour la température de l'air
        self.T_air += delta_T

