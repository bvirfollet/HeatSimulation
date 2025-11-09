#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fichier: model_data.py
# Généré par le dispatcher de simulation_objet.py

from logger import LoggerSimulation

# --- Début des Blocs de Code ---

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

class ZoneAir:
    """
    Représente un volume d'air (une pièce) dont la température
    est supposée homogène et évolue par convection avec les
    parois.
    """

    def __init__(self, nom, params, temp_init):
        self.nom = nom
        self.logger = LoggerSimulation(nom=f"ZoneAir[{nom}]")

        self.volume_m3 = 0.0
        self.temperature = temp_init

        # Propriétés de l'air
        self.mat_air = MATERIAUX["AIR"]
        self.rho_cp = self.mat_air["rho"] * self.mat_air["cp"]  # Capacité thermique volumique (J/(m^3.K))
        self.h_convection = self.mat_air["h_convection"]

        self.surface_cellule = params.ds ** 2
        self.logger.info(f"Zone '{nom}' créée, T_init={temp_init}°C")

    def ajouter_volume_cellule(self, volume_cellule):
        """Ajoute le volume d'une cellule à la zone."""
        self.volume_m3 += volume_cellule

    def finaliser_initialisation(self):
        """Calcule la capacité thermique totale de la zone."""
        if self.volume_m3 == 0:
            self.logger.warning("Le volume de la zone est nul.")
            self.capacite_thermique_totale = 0
        else:
            # C_tot = Volume (m^3) * Capacité volumique (J/(m^3.K))
            self.capacite_thermique_totale = self.volume_m3 * self.rho_cp
            self.logger.info(f"Volume total: {self.volume_m3:.2f} m^3")
            self.logger.info(f"Capacité thermique totale: {self.capacite_thermique_totale:.2f} J/K")

    def calculer_evolution_convection(self, dt, T_surface, T_solide_idx, modele):
        """
        Calcule l'énergie échangée par convection avec une liste
        de cellules de surface et met à jour la température de la zone.

        T_surface (np.array): Liste des températures des cellules solides en contact.
        T_solide_idx (list): Liste des indices (i,j,k) de ces cellules.
        modele (ModeleMaison): Le modèle (pour les lambdas).
        """
        # (Cette fonction sera implémentée à l'Étape 2)
        # Pour l'instant, la température de la zone reste fixe
        pass

