
import time
import shutil
from logger import LoggerSimulation
from parametres import ParametresSimulation
from model_data import MATERIAUX, ZoneAir
from modele import ModeleMaison
from simulation import Simulation
from stockage import StockageResultats
from visualisation import Visualisation

def main():
    '''Fonction principale de test.'''

    logger = LoggerSimulation(niveau="DEBUG")
    logger.info("--- Démarrage de la Simulation de Test ---")

    # --- 1. Paramètres ---
    # Utiliser un pas de temps plus court pour les logs
    # --- CORRECTION (Intervalle Log) ---
    duree_sim_s = 7200 # 2 heures
    intervalle_log_s = 60 # 1 minute

    chemin_resultats = "resultats_sim"

    # Nettoyer les anciens résultats
    import os
    if os.path.exists(chemin_resultats):
        try:
            shutil.rmtree(chemin_resultats)
            logger.info(f"Ancien dossier de résultats '{chemin_resultats}' supprimé.")
        except Exception as e:
            logger.error(f"Impossible de supprimer '{chemin_resultats}': {e}")

    params = ParametresSimulation(
        N_x=11, N_y=11, N_z=11, # Grille 11x11x11 points
        ds=0.1,  # Cellules de 10cm
        dt=20.0, # Pas de temps de 20s
        T_interieur_init=20.0,
        T_exterieur_init=0.0
    )

    # --- 2. Construction du Modèle ---
    modele = ModeleMaison(params)

    # Dimensions (1m x 1m x 1m)
    dim_ext = (1.0, 1.0, 1.0)
    pos_ext = (0.0, 0.0, 0.0)

    # Intérieur (0.8m x 0.8m x 0.8m)
    dim_int = (0.8, 0.8, 0.8)
    pos_int = (0.1, 0.1, 0.1)

    # Mur en parpaing (0.1m x 0.8m x 0.8m)
    dim_mur = (0.1, 0.8, 0.8)
    pos_mur = (0.8, 0.1, 0.1)

    # --- CORRECTION (Bug de T° Initiale) ---
    # On construit de l'intérieur vers l'extérieur

    # 1. Remplir les limites extérieures (T=0°C)
    modele.construire_volume_metres(pos_ext, dim_ext, "LIMITE_FIXE",
                                     T_imposee=params.T_exterieur_init)

    # 2. Remplir l'air intérieur (T=20°C par défaut)
    modele.construire_volume_metres(pos_int, dim_int, "AIR", zone_id=-1)

    # 3. Remplir le mur en parpaing (T=20°C par défaut)
    modele.construire_volume_metres(pos_mur, dim_mur, "PARPAING")

    # Préparer le modèle (détecter les surfaces, etc.)
    modele.preparer_simulation()

    # --- 3. Initialisation de la Simulation ---
    stockage = StockageResultats(chemin_resultats, logger)
    sim = Simulation(modele, params, stockage)

    # --- 4. Lancement ---
    start_time = time.time()
    sim.lancer_simulation(duree_s=duree_sim_s, intervalle_stockage_s=intervalle_log_s)
    end_time = time.time()

    logger.info(f"Temps de calcul: {end_time - start_time:.2f} secondes.")

    # Log de la T° finale
    T_zones_finales = {zid: zone.T for zid, zone in sim.zones_air.items()}
    logger.info(f"--- Température Finale de l'Air: {T_zones_finales} ---")

    # --- 5. Visualisation ---
    visualiseur = Visualisation(sim)

    # Validation Étape 1: Voir les surfaces de convection
    logger.info("--- Validation Étape 1: Visualisation des Surfaces de Convection ---")
    visualiseur.visualiser_surfaces_convection()

    # Visualisation finale (Heatmap)
    logger.info("--- Visualisation des Résultats (Heatmap) ---")
    visualiseur.visualiser_resultat(
        etape_index=-1, # Dernière étape
        downsample_factor=1,
        temp_min=0.0,
        temp_max=20.0
    )

    logger.info("--- Fin de la simulation de test ---")


if __name__ == "__main__":
    main()
