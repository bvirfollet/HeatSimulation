# Fichier généré automatiquement par dispatcher_le_projet.py

import time


class LoggerSimulation:
    """Classe simple pour gérer les niveaux de log (INFO, DEBUG, WARN)."""

    NIVEAUX = {
        "DEBUG": 1,
        "INFO": 2,
        "WARN": 3,
        "ERROR": 4
    }

    def __init__(self, niveau="INFO"):
        self.niveau_log = self.NIVEAUX.get(niveau.upper(), 2)

    def _log(self, message, niveau):
        if self.NIVEAUX.get(niveau, 0) >= self.niveau_log:
            heure = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{heure}] [{niveau}] {message}")

    def debug(self, message):
        self._log(message, "DEBUG")

    def info(self, message):
        self._log(message, "INFO")

    def warn(self, message):
        self._log(message, "WARN")

    def error(self, message):
        self._log(message, "ERROR")


# --- CLASSE 2: Paramètres ---
# (Stocke tous les paramètres fixes de la simulation)


