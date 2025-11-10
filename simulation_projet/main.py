
# Fichier généré automatiquement par dispatcher_le_projet.py
import os
import shutil
import copy
import time
import numpy as np
import sys
from logger import LoggerSimulation
from parametres import ParametresSimulation
from model_data import MATERIAUX, ZoneAir
from modele import ModeleMaison
from simulation import Simulation
from visualisation import Visualisation

def main():
    '''Fonction principale de test.'''

    logger = LoggerSimulation(niveau="DEBUG")
    logger.info("--- Démarrage de la Simulation de Test ---")

    # 1. Nettoyer les anciens résultats
    chemin_resultats = "resultats_sim"
    if os.path.exists(chemin_resultats):
        try:
            shutil.rmtree(chemin_resultats)
            logger.info(f"Ancien dossier de résultats '{chemin_resultats}' supprimé.")
        except Exception as e:
            logger.warn(f"Impossible de supprimer l'ancien dossier: {e}")

    # 2. Créer les paramètres
    # On teste une boîte de 1m x 1m x 1m
    params = ParametresSimulation(
        logger=logger,
        dims_m=(1.0, 1.0, 1.0),
        ds=0.1,  # Cellules de 10cm
        dt=20.0, # Pas de temps de 20s
        T_interieur_init=20.0,
        T_exterieur_init=0.0
    )

    # 3. Construire le modèle de la maison
    modele = ModeleMaison(params)

    # --- CORRECTION (Ordre de Construction) ---
    # On construit de l'extérieur vers l'intérieur pour que
    # l'intérieur (20°C) écrase l'extérieur (0°C).

    # 1. Remplir tout de LIMITE_FIXE (0°C)
    modele.construire_volume_metres(
        (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), "LIMITE_FIXE"
    )

    # 2. "Tailler" le Parpaing (à 20°C)
    # Mur du fond + Mur de droite
    modele.construire_volume_metres(
        (0.1, 0.1, 0.1), (0.9, 0.2, 0.9), "PARPAING"
    )
    modele.construire_volume_metres(
        (0.8, 0.1, 0.1), (0.9, 0.9, 0.9), "PARPAING"
    )


    # 3. "Tailler" l'Air (à 20°C)
    modele.construire_volume_metres(
        (0.1, 0.2, 0.1), (0.8, 0.9, 0.9), "AIR"
    )

    # --- NOUVEAU: Ajout d'une source de chaleur (Radiateur) ---
    # On ajoute 50W à la zone d'air (id = -1)
    if -1 in modele.zones_air:
        modele.zones_air[-1].set_apport_puissance(50.0)

    # Préparer le modèle (détecter les surfaces, etc.)
    modele.preparer_simulation()

    # 4. Créer et lancer la simulation
    sim = Simulation(modele, params, chemin_sortie=chemin_resultats)

    temps_debut_calcul = time.time()

    sim.lancer_simulation(
        duree_s=7200,                # 2 heures
        intervalle_stockage_s=60     # Log/Stockage chaque minute
    )

    temps_fin_calcul = time.time()
    logger.info(f"Temps de calcul: {(temps_fin_calcul - temps_debut_calcul):.2f} secondes.")

    temps_air_final = {nom: zone.T for nom, zone in modele.zones_air.items()}
    logger.info(f"--- Température Finale de l'Air: {temps_air_final} ---")

    # 5. Visualiser les résultats
    visualiseur = Visualisation(sim)

    # Validation Étape 1: Montrer les surfaces de convection détectées
    logger.info("--- Validation Étape 1: Visualisation des Surfaces de Convection ---")
    visualiseur.visualiser_surfaces_convection()

    # --- NOUVEAU: Visualisation multi-étapes ---

    # Visualisation t=0
    logger.info("--- Visualisation Résultat (t=0s) ---")
    visualiseur.visualiser_resultat(
        etape_index=0, # Première étape
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    # Visualisation t=3600s (milieu)
    # L'index 60 = 3600s / 60s/étape
    logger.info("--- Visualisation Résultat (t=3600s) ---")
    visualiseur.visualiser_resultat(
        etape_index=60, 
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    # Visualisation finale (t=7200s)
    logger.info("--- Visualisation Résultat (t=7200s) ---")
    visualiseur.visualiser_resultat(
        etape_index=-1, # Dernière étape
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0 # Augmenté pour voir le chauffage
    )

    logger.info("--- Fin de la simulation de test ---")


# --- CORRECTION: Ceci est le point d'entrée correct pour main.py ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Attrape l'erreur au plus haut niveau pour le log
        logger_global = LoggerSimulation("ERROR")
        logger_global.error(f"Une erreur fatale est survenue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
