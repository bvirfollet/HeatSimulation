
# ==================================
# Script Principal (main.py)
# ==================================
# Ce script est généré par le dispatcher.
# Exécutez-le pour lancer une simulation de test.

import os
import shutil
from logger import LoggerSimulation
from parametres import ParametresSimulation
from model_data import MATERIAUX, ZoneAir
from modele import ModeleMaison
from stockage import StockageResultats
from simulation import Simulation
from visualisation import Visualisation

def main():
    logger = LoggerSimulation(nom="Main", niveau="INFO")
    logger.info("--- Démarrage de la Simulation de Test ---")

    # 1. Nettoyer les anciens résultats
    chemin_resultats = "resultats_sim"
    if os.path.exists(chemin_resultats):
        shutil.rmtree(chemin_resultats)
        logger.info(f"Ancien dossier de résultats '{chemin_resultats}' supprimé.")

    # 2. Définir les paramètres
    # (Petite grille pour un test rapide)
    params = ParametresSimulation(
        dim_m=(1.0, 1.0, 1.0),   # Maison de 1m x 1m x 1m
        ds_m=0.1,              # Cellules de 10cm
        dt_s=20.0,             # Pas de temps de 20s
        temp_ext=0.0,
        temp_int_init=20.0
    )

    # 3. Construire le modèle
    modele = ModeleMaison(params)

    # Construction:
    # On laisse une bordure d'1 cellule (ds) pour l'EXTERIEUR_FIXE
    ds = params.ds
    Lx, Ly, Lz = params.L_x_m, params.L_y_m, params.L_z_m

    # Créer la "boîte" intérieure d'AIR (Zone -1)
    modele.construire_volume_metres(
        (ds, ds, ds), 
        (Lx-ds, Ly-ds, Lz-ds), 
        "AIR", 
        temp_init=params.temp_interieure_initiale
    )

    # Créer un mur en Parpaing (le mur du fond, en Y=Lz-ds)
    modele.construire_volume_metres(
        (ds, Ly-ds, ds), 
        (Lx-ds, Ly-ds, Lz-ds), 
        "PARPAING",
        temp_init=10.0 # Mur initialement plus froid
    )

    # 4. Initialiser les modules
    stockage = StockageResultats(chemin_resultats)
    sim = Simulation(modele, stockage, params)

    # 5. Lancer la simulation (2h)
    sim.lancer_simulation(duree_s=7200, intervalle_stockage_s=600)

    # 6. Visualiser les résultats
    visualiseur = Visualisation(sim)

    # --- ÉTAPE 1: VALIDATION ---
    logger.info("--- Validation Étape 1: Visualisation des Surfaces de Convection ---")
    visualiseur.visualiser_surfaces_convection()

    # --- Visualisation des Résultats (Heatmap) ---
    logger.info("--- Visualisation des Résultats (Heatmap) ---")
    visualiseur.visualiser_resultat(
        etape_index=-1, # Dernière étape
        downsample_factor=1,
        temp_min_visu=0.0,
        temp_max_visu=20.0
    )

if __name__ == "__main__":
    main()
