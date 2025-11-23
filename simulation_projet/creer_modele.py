# Fichier généré automatiquement par dispatcher_le_projet.py
# Contient l'éditeur TUI pour 'modele.pkl'

from logger import LoggerSimulation
from model_data import MATERIAUX
from modele import ModeleMaison
from parametres import ParametresSimulation
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.reactive import var
from textual.widgets import Header, Footer, Label, Static
import numpy as np
import sys


class PlanWidget(Static):
    """Widget Textual affichant une seule couche Z du plan."""

    def render(self) -> str:
        # Accéder directement à l'app parent pour les données
        app = self.app
        if not isinstance(app, ModelEditorTUI):
            return "Erreur: app invalide"

        # Récupérer les données du modèle
        plan_2d = app.modele.Alpha[:, :, app.current_z]
        plan_2d_T = plan_2d.T

        H, W = plan_2d_T.shape
        cursor_x = app.cursor_x
        cursor_y = app.cursor_y
        palette_map = app.palette_map

        lignes_str = []
        for y in range(H):
            ligne = ""
            for x in range(W):
                val = plan_2d_T[y, x]
                # Chercher la clé dans la palette avec tolerance pour les floats
                char = None
                if val in palette_map:
                    char = palette_map[val]
                else:
                    # Chercher une clé similaire (pour les erreurs de précision float)
                    for key in palette_map.keys():
                        if isinstance(key, (int, float)) and isinstance(val, (int, float)):
                            if abs(key - val) < 1e-10:
                                char = palette_map[key]
                                break

                if char is None:
                    char = '?'
                    plan_2d_T[y, x] = ''

                if x == cursor_x and y == cursor_y:
                    # Appliquer un style inversé pour le curseur
                    ligne += f"[reverse]{char}[/reverse]"
                else:
                    ligne += char
            lignes_str.append(ligne)

        output = "\n".join(lignes_str)
        return output


class ModelEditorTUI(App):
    """Une application TUI pour éditer les plans du modèle de simulation."""

    CSS_PATH = "creer_modele.tcss"

    # Raccourcis clavier
    BINDINGS = [
        ("q", "move_cursor(-1, 0)", "Gauche"),
        ("d", "move_cursor(1, 0)", "Droite"),
        ("z", "move_cursor(0, -1)", "Haut"),
        ("s", "move_cursor(0, 1)", "Bas"),
        ("a", "change_floor(1)", "Étage Sup (+Z)"),
        ("e", "change_floor(-1)", "Étage Inf (-Z)"),
        ("enter", "paint_material", "Peindre"),
        ("ctrl+s", "save_model", "Sauvegarder"),
        ("ctrl+q", "quit", "Quitter"),

        # --- Palette ---
        ("p", "select_material('PARPAING')", "Parpaing (P)"),
        ("c", "select_material('BETON')", "Béton (C)"),
        ("b", "select_material('LAINE_BOIS')", "Laine Bois (W)"),
        ("t", "select_material('TERRE')", "Terre (T)"),
        ("i", "select_material('LAINE_VERRE')", "Laine Verre (I)"),
        ("h", "select_material('LIMITE_FIXE')", "Limite (#)"),
        ("space", "select_material('AIR')", "Air ( )"),
    ]

    def __init__(self, modele, chemin_sauvegarde):
        super().__init__()
        self.modele = modele
        self.params = modele.params
        self.chemin_sauvegarde = chemin_sauvegarde
        self.logger = modele.logger

        # Limites du curseur
        self.MAX_X = self.params.N_x - 1
        self.MAX_Y = self.params.N_y - 1
        self.MAX_Z = self.params.N_z - 1

        # État interne (PAS de variables réactives ici)
        self.cursor_x = self.MAX_X // 2
        self.cursor_y = self.MAX_Y // 2
        self.current_z = self.MAX_Z // 2
        self.selected_material = "PARPAING"
        self.status_msg = "Appuyez sur Ctrl+Q pour quitter."

        # Création de la palette
        self.palette_map = {}
        base_palette = {
            'PARPAING': 'P',
            'BETON': 'C',
            'LAINE_BOIS': 'W',
            'TERRE': 'T',
            'LAINE_VERRE': 'I',
            'LIMITE_FIXE': '#',
            'AIR': ' '
        }

        for nom, char in base_palette.items():
            if nom in MATERIAUX:
                alpha = MATERIAUX[nom]["alpha"]
                self.palette_map[alpha] = char

        # Gérer les autres matériaux
        for nom, props in MATERIAUX.items():
            if nom not in base_palette:
                alpha = props["alpha"]
                if alpha not in self.palette_map:
                    self.palette_map[alpha] = '?'

        # Gérer les IDs d'air multiples
        for i in range(-1, -10, -1):
            self.palette_map[i] = ' '

    def compose(self) -> ComposeResult:
        """Crée l'interface utilisateur TUI."""
        yield Header()
        with Horizontal():
            with Vertical(id="left-panel"):
                yield Label("Infos", id="info-title")
                yield Label(f"Modèle: {self.params.N_x}x{self.params.N_y}x{self.params.N_z}")
                yield Label(f"Couche Z: {self.current_z} / {self.MAX_Z}", id="z-label")
                yield Label(f"Curseur (X,Y): {self.cursor_x}, {self.cursor_y}", id="cursor-label")
                yield Label("\nPalette:", id="palette-title")
                yield Label(f"[ ] Air (Espace)", id="mat-AIR")
                yield Label(f"[#] Limite (H)", id="mat-LIMITE_FIXE")
                yield Label(f"[P] Parpaing", id="mat-PARPAING")
                yield Label(f"[C] Béton", id="mat-BETON")
                yield Label(f"[B] Laine Bois", id="mat-LAINE_BOIS")
                yield Label(f"[T] Terre", id="mat-TERRE")
                yield Label(f"[L] Laine Verre", id="mat-LAINE_VERRE")
            with ScrollableContainer(id="main-view"):
                yield PlanWidget(id="plan-view")
        yield Label(self.status_msg, id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Appelé lors du démarrage de l'application."""
        self.update_ui()

    def update_ui(self) -> None:
        """Met à jour tous les éléments de l'interface."""
        # Mettre à jour labels d'info
        try:
            self.query_one("#z-label", Label).update(f"Couche Z: {self.current_z} / {self.MAX_Z}")
        except Exception as e:
            self.logger.error(f"Erreur z-label: {e}")

        try:
            self.query_one("#cursor-label", Label).update(f"Curseur (X,Y): {self.cursor_x}, {self.cursor_y}")
        except Exception as e:
            self.logger.error(f"Erreur cursor-label: {e}")

        try:
            self.query_one("#status-bar", Label).update(self.status_msg)
        except Exception as e:
            self.logger.error(f"Erreur status-bar: {e}")

        # Mettre à jour la palette
        for mat_name in ['AIR', 'LIMITE_FIXE', 'PARPAING', 'BETON', 'LAINE_BOIS', 'TERRE', 'LAINE_VERRE']:
            try:
                label = self.query_one(f"#mat-{mat_name}", Label)
                if mat_name == self.selected_material:
                    label.update(f"[reverse]{self.palette_map.get(MATERIAUX[mat_name]['alpha'], '?')} {mat_name}[/reverse]")
                else:
                    label.update(f"[ ] {mat_name}")
            except Exception as e:
                self.logger.debug(f"Erreur mat-{mat_name}: {e}")

        # Mettre à jour le plan
        try:
            if not self.is_mounted:
                return
            plan_widget = self.query_one("#plan-view", PlanWidget)
            # Forcer le refresh du widget pour qu'il relise les données du modèle
            plan_widget.refresh()
        except Exception as e:
            self.logger.error(f"Erreur plan-view refresh: {e}")

    # --- Actions (Raccourcis Clavier) ---

    def action_move_cursor(self, dx: int, dy: int) -> None:
        self.cursor_x = max(0, min(self.MAX_X, self.cursor_x + dx))
        self.cursor_y = max(0, min(self.MAX_Y, self.cursor_y + dy))
        self.update_ui()

    def action_change_floor(self, dz: int) -> None:
        self.current_z = max(0, min(self.MAX_Z, self.current_z + dz))
        self.update_ui()

    def action_select_material(self, nom_materiau: str) -> None:
        if nom_materiau in MATERIAUX:
            self.selected_material = nom_materiau
            self.status_msg = f"Matériau sélectionné: {nom_materiau}"
            self.update_ui()
        else:
            self.status_msg = f"Matériau '{nom_materiau}' non trouvé."
            self.update_ui()

    def action_paint_material(self) -> None:
        x, y, z = self.cursor_x, self.cursor_y, self.current_z
        nom_mat = self.selected_material

        self.modele.set_material_at(x, y, z, nom_mat)

        # Mettre à jour la vue
        self.update_ui()
        self.status_msg = f"'{nom_mat}' appliqué à ({x}, {y}, {z})"
        self.update_ui()

    def action_save_model(self) -> None:
        self.status_msg = "Sauvegarde du modèle..."
        self.update_ui()
        try:
            self.modele.preparer_simulation()
            self.modele.sauvegarder(self.chemin_sauvegarde)
            self.status_msg = f"Modèle sauvegardé dans '{self.chemin_sauvegarde}'! (Ctrl+Q pour quitter)"
            self.update_ui()
        except Exception as e:
            self.status_msg = f"ERREUR de sauvegarde: {e}"
            self.update_ui()


# --- Fonctions Helper ---

def creer_modele_initial(logger, params):
    '''
    Crée un modèle de maison "vide" (rempli de LIMITE_FIXE)
    si aucun fichier modele.pkl n'est trouvé.
    '''
    logger.info("Aucun 'modele.pkl' trouvé. Création d'un modèle vide...")
    modele = ModeleMaison(params)

    # Remplir le volume avec l'extérieur (0°C)
    modele.construire_volume_metres(
        (0.0, 0.0, 0.0), (params.L_x, params.L_y, params.L_z),
        "LIMITE_FIXE", T_override_K=params.T_exterieur_init
    )
    # Remplir le sol (10°C)
    modele.construire_volume_metres(
        (0.0, 0.0, 0.0), (params.L_x, params.L_y, 0.1),
        "LIMITE_FIXE", T_override_K=params.T_sol_init
    )

    # Préparer (calcule les volumes d'air = 0)
    modele.preparer_simulation()
    return modele


def main_editeur():
    '''
    Fonction principale pour créer et sauvegarder le modèle de la maison.
    '''
    logger = LoggerSimulation(niveau="DEBUG")
    logger.info("--- Démarrage de l'Éditeur de Modèle TUI ---")

    chemin_sauvegarde = "modele.pkl"

    # 1. Définir les paramètres (doivent être fixes)
    params = ParametresSimulation(
        logger=logger,
        dims_m=(9.5, 15.0, 6.6), # 96x151x67 points
        ds=0.1,
        dt=10.0,
        T_interieur_init=20.0,
        T_exterieur_init=0.0,
        T_sol_init=10.0
    )

    # 2. Charger le modèle s'il existe, sinon en créer un vide
    modele = ModeleMaison.charger(chemin_sauvegarde, logger)
    if modele is None:
        modele = creer_modele_initial(logger, params)

    # 3. Lancer l'application TUI
    app = ModelEditorTUI(modele, chemin_sauvegarde)
    app.run()

    # (La sauvegarde est gérée dans l'application TUI via Ctrl+S)
    logger.info("--- Éditeur TUI fermé ---")


if __name__ == "__main__":
    try:
        main_editeur()
    except Exception as e:
        print(f"ERREUR FATALE dans l'éditeur TUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
