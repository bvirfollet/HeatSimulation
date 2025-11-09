# --- Imports ---
from logger import LoggerSimulation
import os
import pickle
import shutil


class StockageResultats:
    """
    Gère la sauvegarde des résultats de simulation (matrices 3D)
    sur le disque pour éviter la saturation de la RAM.
    """

    def __init__(self, chemin_sortie, logger=None):
        self.logger = logger if logger else LoggerSimulation(niveau="INFO")
        self.chemin_sortie = chemin_sortie
        self.index_temps = [] # Liste de (index, temps_s, pertes_W)
        self.index_fichier = 0

        # Nettoyer l'ancien dossier de résultats s'il existe
        try:
            if os.path.exists(self.chemin_sortie):
                shutil.rmtree(self.chemin_sortie)
                self.logger.info(f"Ancien dossier de résultats '{self.chemin_sortie}' supprimé.")
            os.makedirs(self.chemin_sortie)
        except Exception as e:
            self.logger.error(f"Impossible de nettoyer le dossier de sortie: {e}")

        self.logger.info(f"Stockage configuré pour écrire dans: {self.chemin_sortie}")

    def stocker_etape(self, temps_s, matrice_T, pertes_W):
        """Sauvegarde une matrice 3D complète sur le disque via pickle."""

        nom_fichier = f"etape_{self.index_fichier:05d}.pkl"
        chemin_complet = os.path.join(self.chemin_sortie, nom_fichier)

        try:
            with open(chemin_complet, 'wb') as f:
                pickle.dump(matrice_T, f)

            # Stocker uniquement les métadonnées légères en RAM
            self.index_temps.append((self.index_fichier, temps_s, pertes_W))
            self.index_fichier += 1

        except Exception as e:
            self.logger.warning(f"Échec de la sauvegarde de l'étape {self.index_fichier}: {e}")

    def charger_etape(self, index=-1):
        """Charge une étape spécifique depuis le disque (par défaut, la dernière)."""

        if not self.index_temps:
            self.logger.error("Aucune étape n'a été stockée. Impossible de charger.")
            return None, 0, 0

        if index == -1:
            index_a_charger, temps_s, pertes_W = self.index_temps[-1]
        else:
            try:
                index_a_charger, temps_s, pertes_W = self.index_temps[index]
            except IndexError:
                self.logger.error(f"Index d'étape {index} invalide.")
                return None, 0, 0

        nom_fichier = f"etape_{index_a_charger:05d}.pkl"
        chemin_complet = os.path.join(self.chemin_sortie, nom_fichier)

        try:
            with open(chemin_complet, 'rb') as f:
                matrice_T = pickle.load(f)
            return matrice_T, temps_s, pertes_W
        except Exception as e:
            self.logger.error(f"Impossible de charger l'étape {index_a_charger}: {e}")
            return None, 0, 0

