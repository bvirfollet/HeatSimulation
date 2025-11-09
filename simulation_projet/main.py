# --- main.py ---
# Point d'entrée de la simulation dispatchée.

import os
import shutil
import sys

# --- Imports du Projet ---
# (Généré dynamiquement par le dispatcher, mais on les met ici
# pour que l'IDE puisse les trouver)
try:
    from logger import LoggerSimulation
    from parametres import ParametresSimulation
    from model_data import MATERIAUX, ZoneAir
    from modele import ModeleMaison
    from stockage import StockageResultats
    from simulation import Simulation
    from visualisation import Visualisation
except ImportError as e:
    print(f"ERREUR d'import: {e}", file=sys.stderr)
    print("Veuillez vous assurer d'être dans le dossier 'simulation_projet'", file=sys.stderr)
    sys.exit(1)


def main():
    # --- CORRECTION (SyntaxError) ---
    # On utilise des triples apostrophes pour le docstring interne
    # pour éviter le conflit avec les triples guillemets externes.
    '''Fonction principale de test.'''
    
    logger = LoggerSimulation(niveau="DEBUG")
    logger.info("--- Démarrage de la Simulation de Test ---")

    # --- 1. Paramètres ---
    # On simule une boîte de 1m x 1m x 1m
    params = ParametresSimulation(
        dim_m=(1.0, 1.0, 1.0), # 1m x 1m x 1m
        ds_m=0.1,             # Cellules de 10cm
        dt_s=20.0,            # Pas de temps de 20s
        t_ext=0.0,            # Extérieur à 0°C
        t_int_init=20.0       # Intérieur initial à 20°C
    )
    # Note: La grille sera de 11x11x11 points (0m à 1m par pas de 0.1)

    # --- 2. Construction du Modèle ---
    modele = ModeleMaison(params, logger)
    
    # 2a. Définir l'extérieur (Température fixe)
    # On crée une "coquille" de 10cm à 0°C
    modele.construire_volume_metres((0,0,0), (1.0, 1.0, 1.0), "LIMITE_FIXE")

    # 2b. Creuser l'intérieur (Air)
    # On laisse 10cm de mur (0.1m) sur chaque face
    modele.construire_volume_metres((0.1, 0.1, 0.1), (0.9, 0.9, 0.9), "AIR")
    
    # 2c. Remplacer un des murs par du Parpaing
    # On remplace la "LIMITE_FIXE" en Y=1.0m (indice 10) 
    # par un mur en parpaing à l'indice 9 (de 0.9m à 0.9m)
    modele.construire_volume_metres((0.1, 0.9, 0.1), (0.9, 0.9, 0.9), "PARPAING")
    
    # Préparer le modèle (détection des surfaces, etc.)
    modele.preparer_simulation()


    # --- 3. Stockage ---
    chemin_resultats = "resultats_sim"
    stockage = StockageResultats(chemin_resultats, logger)
    
    # --- 4. Simulation ---
    sim = Simulation(modele, stockage, params, logger)
    
    # Lancer pour 2h (7200s), sauvegarde toutes les 10min (600s)
    sim.lancer_simulation(duree_s=7200, intervalle_stockage_s=600)

    # --- 5. Visualisation ---
    visualiseur = Visualisation(sim)
    
    # 5a. Validation (Étape 1)
    logger.info("--- Validation Étape 1: Visualisation des Surfaces de Convection ---")
    visualiseur.visualiser_surfaces_convection()
    
    # 5b. Résultats (Heatmap)
    logger.info("--- Visualisation des Résultats (Heatmap) ---")
    visualiseur.visualiser_resultat(
        etape_index=-1, # Visualiser la dernière étape
        downsample_factor=1,
        temp_min=0.0,
        temp_max=20.0
    )

if __name__ == "__main__":
    main()