# --- Imports ---
import time


class LoggerSimulation:
    """Classe simple pour gérer le logging avec niveaux et timestamps."""

    NIVEAUX = {
        "DEBUG": 1,
        "INFO": 2,
        "WARNING": 3,
        "ERROR": 4
    }

    def __init__(self, niveau="INFO"):
        self.niveau_seuil = self.NIVEAUX.get(niveau.upper(), 2)

    def _log(self, message, niveau_msg, niveau_str):
        if self.NIVEAUX.get(niveau_str, 0) >= self.niveau_seuil:
            timestamp = time.strftime('%H:%M:%S', time.localtime())
            print(f"[{timestamp}] [{niveau_str}] {message}")

    def debug(self, message):
        self._log(message, 1, "DEBUG")

    def info(self, message):
        self._log(message, 2, "INFO")

    def warning(self, message):
        self._log(message, 3, "WARNING")

    def error(self, message):
        self._log(message, 4, "ERROR")

