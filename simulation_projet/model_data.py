from logger import LoggerSimulation


# --- Constantes de MATERIAUX ---
# (Basées sur le fichier coefficients_alpha.md)
# Dictionnaire des propriétés des matériaux.
# 'alpha' (m^2/s): Diffusivité thermique (vitesse de la chaleur)
# 'lambda' (W/(m.K)): Conductivité thermique (isolation)
# 'rho' (kg/m^3): Masse volumique (poids)
# 'cp' (J/(kg.K)): Capacité thermique (stockage d'énergie)
# 'type' (str): FIXE (T imposée), SOLIDE (calculé), ZONE (nœud d'air)

MATERIAUX = {
    "LIMITE_FIXE": {  # Ex: Mur extérieur à T fixe
        "alpha": 0.0,
        "lambda": 0.0,
        "rho": 0.0,
        "cp": 0.0,
        "type": "FIXE"
    },
    "AIR": {  # Nœud d'air intérieur
        "alpha": -1,  # Marqueur spécial pour 'ZONE'
        "lambda": 0.025,  # Utilisé pour la convection (avec h)
        "rho": 1.2,
        "cp": 1005.0,
        "type": "ZONE"
    },
    "PARPAING": {
        "alpha": 6.25e-7,
        "lambda": 1.1,
        "rho": 2000.0,
        "cp": 880.0,
        "type": "SOLIDE"
    },
    "VERRE": {
        "alpha": 5.33e-7,
        "lambda": 1.0,
        "rho": 2500.0,
        "cp": 750.0,
        "type": "SOLIDE"
    },
    "PLACO": {
        "alpha": 3.30e-7,
        "lambda": 0.25,
        "rho": 900.0,
        "cp": 840.0,
        "type": "SOLIDE"
    },
    "LAINE_VERRE": {
        "alpha": 3.17e-6,
        "lambda": 0.040,
        "rho": 15.0,
        "cp": 840.0,
        "type": "SOLIDE"
    },
    "LAINE_BOIS": {
        "alpha": 1.36e-7,
        "lambda": 0.040,
        "rho": 140.0,
        "cp": 2100.0,
        "type": "SOLIDE"
    }
}





# (Classes pour stocker les états du modèle)

class ZoneAir:
    """Représente un nœud thermique unique pour une zone d'air."""

    def __init__(self, zone_id, T_init, logger):
        self.id = zone_id
        self.T = T_init  # Température actuelle de la zone
        self.volume_m3 = 0.0
        self.capacite_thermique_J_K = 0.0  # Capacité thermique totale (C = m * cp)
        self.logger = logger

        # Propriétés de l'air
        self.rho = MATERIAUX["AIR"]["rho"]
        self.cp = MATERIAUX["AIR"]["cp"]

        self.logger.info(f"Zone '{self.id}' créée, T_init={T_init}°C")

    def ajouter_volume(self, volume_cellule_m3):
        """Ajoute le volume d'une cellule à la zone."""
        self.volume_m3 += volume_cellule_m3

    def finaliser_setup(self):
        """Calcule la capacité thermique totale de la zone."""
        masse_air_kg = self.volume_m3 * self.rho
        self.capacite_thermique_J_K = masse_air_kg * self.cp
        self.logger.info(f"Volume total: {self.volume_m3:.2f} m³")
        self.logger.info(f"Capacité thermique totale: {self.capacite_thermique_J_K:.2f} J/K")

    def calculer_evolution_T(self, puissance_W, dt):
        """
        Calcule la nouvelle température de la zone en fonction
        de la puissance reçue (ou perdue) pendant dt.

        Formule: Q = C * delta_T  =>  delta_T = Q / C
        Q = Energie (Joules) = puissance_W * dt
        C = Capacité thermique (J/K)

        puissance_W > 0 : la zone reçoit de l'énergie (chauffage)
        puissance_W < 0 : la zone perd de l'énergie (refroidissement)
        """
        if self.capacite_thermique_J_K == 0:
            self.logger.warn("Capacité thermique de la zone est nulle. T ne peut pas évoluer.")
            return

        energie_J = puissance_W * dt
        delta_T = energie_J / self.capacite_thermique_J_K
        self.T += delta_T
        self.logger.debug(f"Zone {self.id}: P={puissance_W:.2f}W, dt={dt}s, Q={energie_J:.2f}J, C={self.capacite_thermique_J_K:.2f} J/K, deltaT={delta_T:.3f}°C -> T_new={self.T:.3f}°C")




