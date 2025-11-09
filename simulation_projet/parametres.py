#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fichier: parametres.py
# Généré par le dispatcher de simulation_objet.py

from logger import LoggerSimulation

# --- Début des Blocs de Code ---

class ParametresSimulation:
    """Conteneur pour tous les paramètres de la simulation."""

    def __init__(self, dim_m, ds_m, dt_s, temp_ext, temp_int_init):
        # Dimensions physiques (mètres)
        self.L_x_m = dim_m[0]
        self.L_y_m = dim_m[1]
        self.L_z_m = dim_m[2]

        # Discrétisation (taille cellule et pas de temps)
        self.ds = float(ds_m)  # Taille cellule (m)
        self.dt = float(dt_s)  # Pas de temps (s)

        # Nombre de points de grille (calculé)
        # On ajoute +1 pour avoir N points, N-1 intervalles
        self.N_x = int(self.L_x_m / self.ds) + 1
        self.N_y = int(self.L_y_m / self.ds) + 1
        self.N_z = int(self.L_z_m / self.ds) + 1

        # Conditions initiales
        self.temp_exterieure = float(temp_ext)
        self.temp_interieure_initiale = float(temp_int_init)

        self.logger = LoggerSimulation(niveau="DEBUG")
        self.logger.info(
            f"Paramètres créés. Grille: {self.N_x}x{self.N_y}x{self.N_z} ({self.N_x * self.N_y * self.N_z} cellules)")
        self.logger.debug(f"Dimensions: {self.L_x_m}m x {self.L_y_m}m x {self.L_z_m}m")
        self.logger.debug(f"Discrétisation: ds={self.ds}m, dt={self.dt}s")


# --- CLASSE 3: Matériaux et Zones ---

# --- Constantes de MATERIAUX (Propriétés physiques) ---
# Format:
# "NOM": {
#   "lambda": Conductivité thermique (W/(m.K))
#   "rho": Masse volumique (kg/m^3)
#   "cp": Capacité thermique massique (J/(kg.K))
#   "alpha": Diffusivité thermique (m^2/s) -> calculé: lambda / (rho * cp)
#   "type": 'SOLIDE' (calculé par conduction) ou 'FIXE' (température imposée)
#   "h_convection": Coeff. de convection de surface (W/(m^2.K)) (pour l'air)
# }
MATERIAUX = {
    # --- Modèle Étape 1: ZoneAir ---
    # L'alpha est -1 pour marquer cette zone comme "spéciale" (gérée
    # par la classe ZoneAir) et non par la conduction.
    "AIR": {
        "lambda": 0.025,
        "rho": 1.2,
        "cp": 1005,
        "alpha": -1,  # Marqueur pour 'ZoneAir'
        "type": 'FLUIDE',  # 'FLUIDE' ou 'GAZ'
        "h_convection": 8.0  # Coeff. typique convection naturelle mur vertical
    },

    # --- Matériaux Solides ---
    "PARPAING": {
        "lambda": 1.1,
        "rho": 2000,
        "cp": 880,
        "alpha": 6.25e-7,  # 1.1 / (2000 * 880)
        "type": 'SOLIDE'
    },
    "VERRE": {
        "lambda": 1.0,
        "rho": 2500,
        "cp": 750,
        "alpha": 5.33e-7,  # 1.0 / (2500 * 750)
        "type": 'SOLIDE'
    },
    "PLACO": {
        "lambda": 0.25,
        "rho": 900,
        "cp": 840,
        "alpha": 3.30e-7,  # 0.25 / (900 * 840)
        "type": 'SOLIDE'
    },
    "LAINE_VERRE": {
        "lambda": 0.040,
        "rho": 15,
        "cp": 840,
        "alpha": 3.17e-6,  # 0.040 / (15 * 840)
        "type": 'SOLIDE'
    },
    "LAINE_BOIS": {
        "lambda": 0.040,
        "rho": 140,
        "cp": 2100,
        "alpha": 1.36e-7,  # 0.040 / (140 * 2100)
        "type": 'SOLIDE'
    },

    # --- Conditions aux limites ---
    "EXTERIEUR_FIXE": {
        "lambda": 0,
        "rho": 0,
        "cp": 0,
        "alpha": 0,
        "type": 'FIXE'
    },
    "INTERIEUR_FIXE_LEGACY": {
        "lambda": 0,
        "rho": 0,
        "cp": 0,
        "alpha": 0,
        "type": 'FIXE'
    }
}

