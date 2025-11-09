from logger import LoggerSimulation
import os
import pickle
import shutil
import copy


class StockageResultats:
    """
    Gère le stockage des résultats de simulation sur le disque.
    N'utilise pas la RAM pour stocker l'historique complet.
    """

    def __init__(self, chemin_sortie, logger):
        self.chemin_sortie = chemin_sortie
        self.logger = logger
        self.index_temps = []  # Liste de (temps_s, nom_fichier)

        # Nettoyer le dossier de résultats précédent
        if os.path.exists(self.chemin_sortie):
            try:
                shutil.rmtree(self.chemin_sortie)
                self.logger.info(f"Ancien dossier de résultats '{self.chemin_sortie}' supprimé.")
            except Exception as e:
                self.logger.error(f"Impossible de supprimer le dossier '{self.chemin_sortie}': {e}")

        # Créer le nouveau dossier
        try:
            os.makedirs(self.chemin_sortie)
            self.logger.info(f"Stockage configuré pour écrire dans: {self.chemin_sortie}")
        except Exception as e:
            self.logger.error(f"Impossible de créer le dossier '{self.chemin_sortie}': {e}")

    def stocker_etape(self, temps_s, matrice_T, pertes_W, T_zones):
        """Sauvegarde l'état actuel (matrice T) sur le disque."""

        nom_fichier = f"etape_{len(self.index_temps):05d}.pkl"
        chemin_complet = os.path.join(self.chemin_sortie, nom_fichier)

        etat = {
            "temps_s": temps_s,
            "matrice_T": matrice_T,
            "pertes_W": pertes_W,
            "T_zones": copy.deepcopy(T_zones)  # Important de copier
        }

        try:
            with open(chemin_complet, 'wb') as f:
                pickle.dump(etat, f)
            self.index_temps.append((temps_s, nom_fichier))
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de l'étape {temps_s}s : {e}")

    def charger_etape(self, index=-1):
        """Charge une étape spécifique depuis le disque (par défaut, la dernière)."""

        if not self.index_temps:
            self.logger.error("Aucune étape n'a été stockée.")
            return None

        try:
            temps_s, nom_fichier = self.index_temps[index]
            chemin_complet = os.path.join(self.chemin_sortie, nom_fichier)

            with open(chemin_complet, 'rb') as f:
                etat = pickle.load(f)
            return etat

        except IndexError:
            self.logger.error(f"Index d'étape {index} hors limites.")
            return None
        except Exception as e:
            self.logger.error(f"Impossible de charger l'étape depuis '{chemin_complet}': {e}")
            return None


# --- CLASSE 5: Modèle ---
# (Contient les matrices 3D (T, Alpha, Lambda) et les méthodes de construction)


