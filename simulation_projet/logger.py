import time


class LoggerSimulation:
    """Classe simple pour gérer les logs avec niveaux (INFO, DEBUG)."""

    NIVEAUX = {
        "DEBUG": 1,
        "INFO": 2,
        "WARN": 3,
        "ERROR": 4
    }

    def __init__(self, niveau="INFO"):
        self.niveau_seuil = self.NIVEAUX.get(niveau.upper(), 2)

    def _log(self, niveau, message):
        """Fonction de log interne."""
        if self.NIVEAUX.get(niveau, 0) >= self.niveau_seuil:
            timestamp = time.strftime("[%H:%M:%S]", time.localtime())
            print(f"{timestamp} [{niveau}] {message}")

    def debug(self, message):
        self._log("DEBUG", message)

    def info(self, message):
        self._log("INFO", message)

    def warn(self, message):
        self._log("WARN", message)

    def error(self, message):
        self._log("ERROR", message)


# --- CLASSE 2: Paramètres ---
# (Conteneur pour les paramètres globaux de la simulation)


