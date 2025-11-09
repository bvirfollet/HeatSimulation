#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fichier: logger.py
# Généré par le dispatcher de simulation_objet.py

import time

# --- Début des Blocs de Code ---

class LoggerSimulation:
    """Classe simple pour gérer le logging avec niveaux et timestamps."""
    NIVEAUX = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

    def __init__(self, nom="Simulation", niveau="INFO"):
        self.nom = nom
        self.niveau = self.NIVEAUX.get(niveau, 20)

    def _log(self, niveau_msg, message):
        if self.NIVEAUX.get(niveau_msg, 99) >= self.niveau:
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{timestamp}] [{niveau_msg}] {message}")

    def debug(self, message):
        self._log("DEBUG", message)

    def info(self, message):
        self._log("INFO", message)

    def warning(self, message):
        self._log("WARNING", message)

    def error(self, message):
        self._log("ERROR", message)


# --- CLASSE 2: Paramètres ---

