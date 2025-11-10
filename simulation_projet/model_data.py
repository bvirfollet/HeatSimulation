# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation


# --- Constantes de MATERIAUX (Dictionnaire) ---
# Chaque matériau est défini par:
# (lambda (W/mK), rho (kg/m^3), cp (J/kgK))
#
# L'alpha (diffusivité) est calculé automatiquement (alpha = lambda / (rho * cp))
#
# Note sur les 'types':
# 'SOLIDE': Matériau standard, calculé par conduction (ex: PARPAING)
# 'LIMITE_FIXE': Température fixe, n'évolue pas (ex: Extérieur)
# 'AIR': Nœud d'air, calculé par convection (ex: 'Zone -1')
#
MATERIAUX = {
    # 1. Air (pour les Zones de Convection)
    "AIR": {
        "lambda": 0.0,
        "rho": 1.204,  # kg/m^3 (à 20°C)
        "cp": 1005.0,  # J/(kg.K)
        "type": "AIR",
        "alpha": -1.0
    },

    # 2. Conditions aux limites
    "LIMITE_FIXE": {
        "lambda": 0.0,
        "rho": 0.0,
        "cp": 0.0,
        "type": "LIMITE_FIXE",
        "alpha": 0.0  # Ne diffuse pas
    },

    # 3. Solides (Murs, Isolants, etc.)
    "PARPAING": {
        "lambda": 1.1,
        "rho": 2000.0,
        "cp": 880.0,
        "type": "SOLIDE"
    },
    "VERRE": {
        "lambda": 1.0,
        "rho": 2500.0,
        "cp": 750.0,
        "type": "SOLIDE"
    },
    "PLACO": {
        "lambda": 0.25,
        "rho": 900.0,
        "cp": 840.0,
        "type": "SOLIDE"
    },
    "LAINE_VERRE": {
        "lambda": 0.040,
        "rho": 15.0,
        "cp": 840.0,
        "type": "SOLIDE"
    },
    "LAINE_BOIS": {
        "lambda": 0.040,
        "rho": 140.0,
        "cp": 2100.0,
        "type": "SOLIDE"
    },

    # --- NOUVEAUX MATÉRIAUX (Sol) ---
    "TERRE": {
        "lambda": 1.5,  # Très variable (sec/humide)
        "rho": 1800.0,  # Masse volumique
        "cp": 800.0,  # Capacité thermique
        "type": "SOLIDE"
    },
    "CIMENT": {  # Dalle béton
        "lambda": 1.7,
        "rho": 2200.0,
        "cp": 880.0,
        "type": "SOLIDE"
    },
    "XPS": {  # Polystyrène expansé/extrudé
        "lambda": 0.035,
        "rho": 30.0,
        "cp": 1450.0,
        "type": "SOLIDE"
    },
    "PARQUET_COMPOSITE": {
        "lambda": 0.15,
        "rho": 700.0,
        "cp": 1700.0,
        "type": "SOLIDE"
    }
}

# --- Calcul automatique de la diffusivité (alpha) pour les SOLIDES ---
# --- CORRECTION (KeyError 'alpha') ---
# Ce bloc doit être copié par le dispatcher dans model_data.py
for nom, props in MATERIAUX.items():
    if props["type"] == "SOLIDE":
        # alpha = lambda / (rho * cp)
        props["alpha"] = props["lambda"] / (props["rho"] * props["cp"])




class ZoneAir:
    """Représente un volume d'air (nœud) à une température unique."""

    def __init__(self, nom, logger, T_init=20.0):
        self.nom = nom
        self.logger = logger
        self.T = T_init  # Température actuelle de la zone
        self.volume_m3 = 0.0

        # --- Apport de puissance (Radiateur) ---
        self.puissance_apport_W = 0.0  # (W)

        # Propriétés de l'air
        props = MATERIAUX["AIR"]
        self.rho = props["rho"]
        self.cp = props["cp"]

        # Capacité thermique totale (J/K) = V * rho * cp
        self.capacite_thermique_J_K = 0.0

        self.logger.info(f"Zone '{self.nom}' créée, T_init={self.T}°C")

    def set_apport_puissance(self, puissance_W):
        """Règle la puissance du "radiateur" pour cette zone."""
        self.puissance_apport_W = puissance_W
        self.logger.info(f"Zone '{self.nom}': Apport de puissance réglé à {puissance_W} W.")

    def finaliser_capacite(self):
        """Doit être appelée après que le volume total est connu."""
        self.capacite_thermique_J_K = self.volume_m3 * self.rho * self.cp
        self.logger.info(f"Volume total: {self.volume_m3:.2f} m³")
        self.logger.info(f"Capacité thermique totale: {self.capacite_thermique_J_K:.2f} J/K")

    def calculer_evolution_T(self, puissance_pertes_W, dt_s):
        """
        Calcule la nouvelle température de la zone.
        puissance_pertes_W: Puissance *perdue* par la zone (ex: -500W).
        """

        # Puissance nette = Apports (positifs) + Pertes (négatives)
        puissance_nette_W = self.puissance_apport_W + puissance_pertes_W

        # Énergie (J) = Puissance (W) * Temps (s)
        energie_J = puissance_nette_W * dt_s

        if self.capacite_thermique_J_K > 0:
            delta_T = energie_J / self.capacite_thermique_J_K
        else:
            self.logger.warn(f"Zone {self.nom}: Capacité thermique nulle. DeltaT non calculé.")
            delta_T = 0.0

        self.logger.debug(
            f"Zone {self.nom}: P_pertes={puissance_pertes_W:+.2f}W, P_apport={self.puissance_apport_W:+.2f}W -> P_net={puissance_nette_W:+.2f}W")
        self.logger.debug(
            f"Zone {self.nom}: Q_net={energie_J:+.2f}J, C={self.capacite_thermique_J_K:.2f} J/K, deltaT={delta_T:+.3f}°C -> T_new={self.T + delta_T:.3f}°C")

        self.T += delta_T




