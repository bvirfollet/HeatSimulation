
# Fichier généré: main.py
# C'est votre "Simulateur".
# Il charge le fichier 'modele.pkl' (créé par creer_modele.py)
# et lance la simulation physique.

import os
import shutil
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
    '''
    Fonction principale de simulation.
    Charge un modèle pré-construit et lance les calculs.
    '''

    logger = LoggerSimulation(niveau="DEBUG")
    logger.info("--- Démarrage de la Simulation ---")

    chemin_modele = "modele.pkl"
    chemin_resultats = "resultats_sim"

    # 1. Charger le Modèle
    if not os.path.exists(chemin_modele):
        logger.error(f"Fichier modèle '{chemin_modele}' introuvable.")
        logger.error("Veuillez d'abord exécuter 'python creer_modele.py' pour le générer.")
        sys.exit(1)

    modele = ModeleMaison.charger(chemin_modele, logger)
    if modele is None:
        sys.exit(1)

    # 2. Nettoyer les anciens résultats
    if os.path.exists(chemin_resultats):
        try:
            shutil.rmtree(chemin_resultats)
            logger.info(f"Ancien dossier de résultats '{chemin_resultats}' supprimé.")
        except Exception as e:
            logger.warn(f"Impossible de supprimer l'ancien dossier: {e}")

    # 3. Créer et lancer la simulation
    # (Les paramètres sont déjà dans l'objet 'modele')
    sim = Simulation(modele, chemin_sortie=chemin_resultats)

    temps_debut_calcul = time.time()

    sim.lancer_simulation(
        duree_s=7200,                # 2 heures
        intervalle_stockage_s=600    # Log/Stockage toutes les 10 min
    )

    temps_fin_calcul = time.time()
    logger.info(f"Temps de calcul: {(temps_fin_calcul - temps_debut_calcul):.2f} secondes.")

    temps_air_final = {zone.nom: zone.T for zone in modele.zones_air.values()}
    logger.info(f"--- Température Finale de l'Air: {temps_air_final} ---")

    # 4. Visualiser les résultats
    visualiseur = Visualisation(sim)

    logger.info("--- Validation: Visualisation de la Structure (Slicer 3D) ---")
    visualiseur.visualiser_structure_slicer_3d()

    logger.info("--- Visualisation Résultat (t=0s) ---")
    visualiseur.visualiser_resultat(
        etape_index=0, 
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    logger.info("--- Visualisation Résultat (t=3600s) ---")
    visualiseur.visualiser_resultat(
        etape_index=6, 
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    logger.info("--- Visualisation Résultat (t=7200s) ---")
    visualiseur.visualiser_resultat(
        etape_index=-1, 
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    logger.info("--- Fin de la simulation ---")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            logger_global = LoggerSimulation("ERROR")
            logger_global.error(f"Une erreur fatale est survenue: {e}")
        except Exception:
            print(f"ERREUR FATALE: {e}")

        import traceback
        traceback.print_exc()
        sys.exit(1)
