#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fichier: stockage.py
# Généré par le dispatcher de simulation_objet.py

from logger import LoggerSimulation
import os
import pickle

# --- Début des Blocs de Code ---

class StockageResultats:
    """
    Gère le stockage des résultats de simulation sur le disque dur
    pour éviter de saturer la RAM.
    """

    def __init__(self, chemin_sortie):
        self.chemin_sortie = chemin_sortie
        self.logger = LoggerSimulation(nom="Stockage")

        # S'assure que le dossier de sortie existe
        if not os.path.exists(self.chemin_sortie):
            os.makedirs(self.chemin_sortie)

        # Index léger gardé en mémoire
        # Format: [(temps_s, "nom_fichier.pkl"), ...]
        self.index_historique = []

        self.logger.info(f"Stockage configuré pour écrire dans: {self.chemin_sortie}")

    def stocker_etape(self, temps_s, matrice_T, pertes_W):
        """
        Sauvegarde une étape de simulation (matrice T complète)
        sur le disque dur via 'pickle'.
        """
        nom_fichier = f"etape_t_{temps_s:.0f}.pkl"
        chemin_complet = os.path.join(self.chemin_sortie, nom_fichier)

        try:
            with open(chemin_complet, 'wb') as f:
                pickle.dump(matrice_T, f)

            # Ajoute à l'index si la sauvegarde réussit
            self.index_historique.append((temps_s, nom_fichier, pertes_W))
            self.logger.debug(f"Étape t={temps_s}s sauvegardée dans {nom_fichier}")

        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de l'étape {temps_s}s: {e}")

    def charger_etape(self, etape_index=-1):
        """
        Charge une matrice de température depuis le disque.
        Par défaut, charge la dernière étape.
        """
        if not self.index_historique:
            self.logger.error("Aucune étape à charger, l'historique est vide.")
            return None, 0, 0

        try:
            temps_s, nom_fichier, pertes_W = self.index_historique[etape_index]
            chemin_complet = os.path.join(self.chemin_sortie, nom_fichier)

            with open(chemin_complet, 'rb') as f:
                matrice_T = pickle.load(f)

            self.logger.debug(f"Étape t={temps_s}s chargée depuis {nom_fichier}")
            return matrice_T, temps_s, pertes_W

        except Exception as e:
            self.logger.error(f"Échec du chargement de l'étape (index {etape_index}): {e}")
            return None, 0, 0

    def get_index(self):
        return self.index_historique


# --- CLASSE 5: Modèle ---

