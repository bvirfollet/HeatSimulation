
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
    '''Fonction principale de test (modifiée pour le sol et les plans 2D).'''

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
    # NOUVELLE GRILLE: 1m x 1m x 1.5m (pour inclure le sol)
    # N_x=11, N_y=11, N_z=16 (avec ds=0.1)
    params = ParametresSimulation(
        logger=logger,
        dims_m=(1.0, 1.0, 1.5),
        ds=0.1,  # Cellules de 10cm
        dt=20.0, # Pas de temps de 20s
        T_interieur_init=20.0,
        T_exterieur_init=0.0,
        T_sol_init=10.0 # NOUVEAU: Sol à 10°C
    )

    # 3. Construire le modèle de la maison par plans 2D
    modele = ModeleMaison(params)

    # Définition des plans (dimensions (N_y, N_x))
    # Ici: (11, 11)
    dims_plan = (params.N_y, params.N_x)

    # 0 = AIR
    # 1 = PARPAING
    # 2 = CIMENT
    # 3 = XPS (Isolant sol)
    # 4 = PARQUET
    # 5 = TERRE
    # 6 = LAINE_VERRE (Isolant plafond)

    plan_sol = np.full(dims_plan, 5, dtype=int) # Tout en Terre

    plan_dalle = np.full(dims_plan, 2, dtype=int) # Tout en Ciment
    plan_dalle[1:-1, 1:-1] = 3 # Isolant XPS au centre

    plan_parquet = np.full(dims_plan, 4, dtype=int) # Tout en Parquet

    plan_rdc = np.full(dims_plan, 0, dtype=int) # Tout en Air
    plan_rdc[0, :] = 1  # Murs en Parpaing
    plan_rdc[-1, :] = 1
    plan_rdc[:, 0] = 1
    plan_rdc[:, -1] = 1

    plan_plafond = np.full(dims_plan, 6, dtype=int) # Tout en Laine de Verre

    # Mappage des ID de plan vers les noms de MATERIAUX
    mappage = {
        0: "AIR",
        1: "PARPAING",
        2: "CIMENT",
        3: "XPS",
        4: "PARQUET_COMPOSITE",
        5: "TERRE",
        6: "LAINE_VERRE"
    }

    # Définition des hauteurs (Z) pour chaque plan
    plans_etages = {
        # z_min (m), z_max (m) : plan
        (0.1, 0.5): plan_sol,           # 40cm de Terre (k=1 à k=4)
        (0.5, 0.7): plan_dalle,         # 20cm de Dalle Ciment+XPS (k=5 à k=6)
        (0.7, 0.8): plan_parquet,       # 10cm de Parquet (k=7)
        (0.8, 1.3): plan_rdc,           # 50cm de Air+Murs (k=8 à k=12)
        (1.3, 1.4): plan_plafond,       # 10cm de Laine de verre (k=13)
    }

    # Application des plans 2D pour construire les solides
    modele.construire_depuis_plans(plans_etages, mappage)

    # Application des conditions aux limites (T° fixes)
    # Sol profond (k=0) à 10°C
    modele.construire_volume_metres(
        (0.0, 0.0, 0.0), (1.0, 1.0, 0.1), 
        "LIMITE_FIXE", T_override_K=params.T_sol_init
    )
    # 4 Murs extérieurs (sur les côtés) à 0°C
    modele.construire_volume_metres((0.0, 0.0, 0.1), (0.1, 1.0, 1.4), "LIMITE_FIXE")
    modele.construire_volume_metres((0.9, 0.0, 0.1), (1.0, 1.0, 1.4), "LIMITE_FIXE")
    modele.construire_volume_metres((0.1, 0.0, 0.1), (0.9, 0.1, 1.4), "LIMITE_FIXE")
    modele.construire_volume_metres((0.1, 0.9, 0.1), (0.9, 1.0, 1.4), "LIMITE_FIXE")
    # Toit (k=14) à 0°C
    modele.construire_volume_metres(
        (0.0, 0.0, 1.4), (1.0, 1.0, 1.5), 
        "LIMITE_FIXE", T_override_K=params.T_exterieur_init
    )

    # Ajout du radiateur (50W)
    if -1 in modele.zones_air:
        modele.zones_air[-1].set_apport_puissance(0.0)

    # Préparer le modèle (détecter les surfaces, etc.)
    modele.preparer_simulation()

    # 4. Créer et lancer la simulation
    sim = Simulation(modele, params, chemin_sortie=chemin_resultats)

    temps_debut_calcul = time.time()

    sim.lancer_simulation(
        duree_s=7200,                # 2 heures
        intervalle_stockage_s=300    # Log/Stockage toutes les 5 min
    )

    temps_fin_calcul = time.time()
    logger.info(f"Temps de calcul: {(temps_fin_calcul - temps_debut_calcul):.2f} secondes.")

    temps_air_final = {nom: zone.T for nom, zone in modele.zones_air.items()}
    logger.info(f"--- Température Finale de l'Air: {temps_air_final} ---")

    # 5. Visualiser les résultats
    visualiseur = Visualisation(sim)

    logger.info("--- Validation: Visualisation de la Structure 3D ---")
    visualiseur.visualiser_structure(downsample_factor=1)

    # Visualisation t=0
    logger.info("--- Visualisation Résultat (t=0s) ---")
    visualiseur.visualiser_resultat(
        etape_index=0, 
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    # Visualisation t=3600s (milieu)
    # 3600s / 300s/étape = index 12
    logger.info("--- Visualisation Résultat (t=3600s) ---")
    visualiseur.visualiser_resultat(
        etape_index=12, 
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    # Visualisation finale (t=7200s)
    logger.info("--- Visualisation Résultat (t=7200s) ---")
    visualiseur.visualiser_resultat(
        etape_index=-1, 
        downsample_factor=1,
        temp_min=0.0,
        temp_max=25.0
    )

    logger.info("--- Fin de la simulation de test ---")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger_global = LoggerSimulation("ERROR")
        logger_global.error(f"Une erreur fatale est survenue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
