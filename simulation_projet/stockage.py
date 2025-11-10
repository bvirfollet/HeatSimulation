# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation
import os
import pickle
import shutil


class StockageResultats:
    """Gère le stockage et le chargement des résultats de simulation."""

    def __init__(self, chemin_sortie, logger):
        self.chemin_sortie = chemin_sortie
        self.logger = logger
        self.index_temps = []  # Liste de (temps, chemin_fichier)

        # Nettoyer l'ancien dossier de résultats
        try:
            if os.path.exists(self.chemin_sortie):
                shutil.rmtree(self.chemin_sortie)
                self.logger.info(f"Ancien dossier de résultats '{self.chemin_sortie}' supprimé.")
            os.makedirs(self.chemin_sortie)
        except Exception as e:
            self.logger.error(f"Impossible de nettoyer le dossier de sortie: {e}")

        self.logger.info(f"Stockage configuré pour écrire dans: {self.chemin_sortie}")

    def stocker_etape(self, temps_s, matrice_T, zones_air):
        """Sauvegarde l'état complet de la simulation à un instant t."""

        nom_fichier = f"etape_{len(self.index_temps):05d}.pkl"
        chemin_complet = os.path.join(self.chemin_sortie, nom_fichier)

        # Stocke les températures de l'air de toutes les zones
        temps_air = {nom: zone.T for nom, zone in zones_air.items()}

        etat = {
            "temps_s": temps_s,
            "matrice_T": matrice_T,
            "temps_air": temps_air
        }

        try:
            with open(chemin_complet, 'wb') as f:
                pickle.dump(etat, f)
            self.index_temps.append((temps_s, chemin_complet))
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de l'étape {nom_fichier}: {e}")

    def charger_etape(self, index=-1):
        """Charge un état de simulation depuis le disque (par défaut, le dernier)."""
        if not self.index_temps:
            self.logger.error("Aucune étape de simulation n'a été sauvegardée.")
            return None

        try:
            temps_s, chemin_complet = self.index_temps[index]
            with open(chemin_complet, 'rb') as f:
                etat = pickle.load(f)
            return etat
        except Exception as e:
            self.logger.error(f"Impossible de charger l'étape {chemin_complet}: {e}")
            return None


# --- CLASSE 5: Modèle de la Maison ---
# (Gère les matrices 3D de la géométrie et des matériaux)


