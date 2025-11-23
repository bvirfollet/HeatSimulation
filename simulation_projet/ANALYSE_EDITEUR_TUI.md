# Analyse Détaillée: Éditeur TUI (creer_modele.py)

## Vue d'ensemble

L'éditeur TUI est une application de **Terminal User Interface** basée sur le framework **Textual** (Python), permettant la création et modification interactive de modèles 3D de maisons.

**Statistiques:**
- 332 lignes de code
- 2 classes principales (PlanWidget, ModelEditorTUI)
- Intégration modele.py complète
- Contrôles clavier intuitifs (AZERTY)

**État:** Fonctionnel mais à améliorer pour production

---

## 1. Architecture

### Composants Principaux

```
ModelEditorTUI (App Textual)
├── Header()                   ← Barre titre
├── Horizontal
│   ├── Left Panel (30%)
│   │   ├── Info (dimensions, coordonnées)
│   │   └── Palette (7 matériaux)
│   └── Main View (70%)
│       └── PlanWidget
│           └── Affiche couche Z actuelle en ASCII
├── Status Bar                 ← Messages utilisateur
└── Footer()                   ← Aide clavier
```

### PlanWidget: Affichage 2D

**Rôle:** Rendre une seule couche Z du modèle en ASCII art

**Données:**
- `plan_data` : Array NumPy 2D (couche X,Y)
- `palette` : Dict {alpha → caractère}
- `cursor_pos` : Position curseur (X, Y)

**Rendu:**
```python
for y in range(H):
    for x in range(W):
        char = palette.get(alpha[y,x], '?')
        if cursor: char = [reverse]char[/reverse]
```

**Caractéristiques:**
- ✅ Réactif (mise à jour auto quand données changent)
- ✅ Léger, O(N×M) acceptable
- ⚠️ Pas de couleurs, seulement ASCII + reverse
- ⚠️ Grille 96×151 → peut dépasser largeur terminal

---

## 2. Interactions Clavier

### Navigation
| Touche | Action | Mode |
|--------|--------|------|
| **Q** | Curseur ← Gauche | Continu |
| **D** | Curseur → Droite | Continu |
| **Z** | Curseur ↑ Haut | Continu |
| **S** | Curseur ↓ Bas | Continu |
| **A** | Étage + (Z augmente) | Continu |
| **E** | Étage - (Z diminue) | Continu |

### Sélection Matériau (Palette)
| Touche | Matériau |
|--------|----------|
| **P** | PARPAING |
| **C** | BETON |
| **W** | LAINE_BOIS |
| **T** | TERRE |
| **I** | LAINE_VERRE |
| **#** | LIMITE_FIXE |
| **Espace** | AIR |

### Opérations
| Touche | Action |
|--------|--------|
| **Entrée** | Peindre matériau sélectionné au curseur |
| **Ctrl+S** | Sauvegarder modèle |
| **Ctrl+Q** | Quitter éditeur |

**Clavier:** AZERTY (design français)
- Q=Gauche, D=Droite (pas WASD)
- Labels français
- Adapté pour utilisateurs francophones

---

## 3. Flux de Données

### Initialisation

**Si modele.pkl existe:**
```python
modele = ModeleMaison.charger("modele.pkl", logger)
```

**Si modele.pkl n'existe pas:**
```python
modele = creer_modele_initial(logger, params)
    ↓
modele.construire_volume_metres((0,0,0), (Lx,Ly,Lz), "LIMITE_FIXE")
modele.construire_volume_metres((0,0,0), (Lx,Ly,0.1), "LIMITE_FIXE", T_sol)
modele.preparer_simulation()  # Init zones air
```

### Édition

**Flux: Clavier → Action → Modèle → Affichage**

```python
# 1. Utilisateur appuie Enter
action_paint_material():
    x, y, z = self.cursor_x, self.cursor_y, self.current_z
    nom_mat = self.selected_material_name

    # 2. Appel modèle
    self.modele.set_material_at(x, y, z, nom_mat)

    # 3. Mise à jour affichage
    self.update_plan_view()
        → plan_widget.plan_data = modele.Alpha[:, :, z].T
        → PlanWidget.render() (réactif)
```

### Sauvegarde

```python
action_save_model():
    try:
        modele.preparer_simulation()          # Finalize air zones
        modele.sauvegarder("modele.pkl")      # Pickle binary
        status_message = "Sauvegardé!"
    except Exception as e:
        status_message = f"ERREUR: {e}"
```

**Points clés:**
- ✅ Changements immédiats (visual feedback)
- ✅ Sauvegarde sur commande (Ctrl+S)
- ⚠️ Pas de sauvegarde auto
- ⚠️ Pas de confirmation avant quit

---

## 4. Intégration modele.py

### Méthode Critiques Utilisées

**`set_material_at(x, y, z, nom_materiau)`**
```python
# Gère logique complexe:
# - Échange air ↔ solide
# - Tracking volume zones air
# - Assignment propriétés matériau
```

**`construire_volume_metres(coin1, coin2, materiau, T_override)`**
```python
# Remplit région cubique avec matériau
# Utilisé pour créer extérieur/sol initialement
```

**`preparer_simulation()`**
```python
# Finalise zones d'air
# Détecte surfaces convection
# Doit être appelé avant simulation
```

**`sauvegarder(chemin)` & `charger(chemin, logger)`**
```python
# Sérialisation pickle
# Gère logger (supprimé avant pickling)
```

### Structures de Données Modifiées

| Champ | Type | Modifié par |
|-------|------|------------|
| `modele.Alpha` | 3D array | set_material_at |
| `modele.Lambda` | 3D array | set_material_at |
| `modele.RhoCp` | 3D array | set_material_at |
| `modele.T` | 3D array | (pas modifié éditeur) |
| `modele.zones_air` | Dict | set_material_at + preparer |
| `modele.surfaces_convection_idx` | Dict | preparer_simulation |

---

## 5. Points Forts

### ✅ Architecture
- Séparation UI ↔ Modèle claire
- Utilisation correcte Textual (reactive variables)
- Lifecycle management (`is_mounted` checks)
- Code lisible, ~330 lignes

### ✅ Intégration
- Interface bien définie avec modele.py
- Validation basique (bounds checking, materiau)
- Préparation correcte avant simulation
- Gestion Logger lors sérialisation

### ✅ Interaction
- Clavier intuitif pour utilisateurs AZERTY
- Feedback visuel (curseur inverse, palette highlight)
- Status bar informatif
- Navigation Z simple et claire

### ✅ Robustesse
- Bounds checking (curseur limité grille)
- Prévention ScreenStackError (`is_mounted` check)
- Gestion exception sauvegarde
- Gestion exception application

---

## 6. Problèmes Critiques

### 🔴 Risque Perte de Données

**Problème:**
```python
BINDINGS = [..., ("ctrl+q", "quit", "Quitter")]
```

Utilisateur peut quitter **sans sauvegarder**. Tous édits de la session perdus.

**Impact:** Haute frustration, données perdues
**Sévérité:** CRITIQUE
**Fix:** Ajouter confirmation dialog

```python
def action_quit(self) -> None:
    if self.has_unsaved_changes:
        # Show: "Modèle modifié. Sauvegarder avant quitter?"
        # Options: Save & Quit | Discard | Cancel
```

### 🔴 Grille Dépasse Terminal

**Problème:**
- Grille: 96 × 151 pixels
- Affichage: 151+ caractères largeur
- Terminal: Typiquement 80-120 caractères

**Résultat:** Défilement horizontal nécessaire, navigation confuse

**Sévérité:** HAUTE
**Fix:**
- Ajouter zoom (⊕/- keys, par ex.)
- Ou: Minimap dans coin
- Ou: Requérir terminal large (recommend 160+ chars)

### 🔴 Pas d'Undo/Redo

**Problème:**
```python
action_paint_material():
    self.modele.set_material_at(x, y, z, nom_mat)  # Immédiat, irreversible
```

Utilisateur can't undo mistake (paint wrong matériau dans coin).

**Sévérité:** MOYENNE-HAUTE
**Fix:**
```python
class EditorHistory:
    def __init__(self):
        self.undo_stack = []  # [(x,y,z, old_mat, new_mat), ...]

    def record_change(self, x, y, z, old_mat, new_mat):
        self.undo_stack.append((x, y, z, old_mat, new_mat))

    def undo(self):
        if self.undo_stack:
            x, y, z, old_mat, new_mat = self.undo_stack.pop()
            modele.set_material_at(x, y, z, old_mat)
```

---

## 7. Problèmes Importants

### ⚠️ Clavier AZERTY Unique

**Problème:** Utilisateurs QWERTY ne peuvent pas naviguer naturellement
- Q=Gauche (au lieu WASD)
- Raccourcis non-intuitifs

**Sévérité:** MOYEN (mineur si public français)
**Fix:** Détecter layout clavier ou faire configurable

```python
# Option: Config file
KEYBOARD_LAYOUT = "AZERTY"  # or "QWERTY"

if KEYBOARD_LAYOUT == "QWERTY":
    BINDINGS = [
        ("w", "move_cursor(0, -1)", "Up"),
        ("a", "move_cursor(-1, 0)", "Left"),
        ("s", "move_cursor(0, 1)", "Down"),
        ("d", "move_cursor(1, 0)", "Right"),
        ...
    ]
```

### ⚠️ Pas de Feedback Opérations Longues

**Problème:**
```python
action_save_model():
    self.modele.preparer_simulation()  # Peut prendre 1-2s pour large grille
    self.modele.sauvegarder(chemin)
    # Utilisateur pense = application figée
```

**Sévérité:** MOYEN
**Fix:** Ajouter progress indicator

```python
async def action_save_model(self):
    self.status_message = "Sauvegarde... 0%"
    try:
        self.modele.preparer_simulation()
        self.status_message = "Sauvegarde... 50%"
        self.modele.sauvegarder(chemin)
        self.status_message = "Sauvegarde... 100%"
    except Exception as e:
        self.status_message = f"ERREUR: {e}"
```

### ⚠️ Pas de Persistence Position Curseur Z-Change

**Problème:**
```python
action_change_floor(dz):
    self.current_z = max(0, min(self.MAX_Z, self.current_z + dz))
    # self.cursor_x, self.cursor_y inchangés
    # ✅ En fait, c'est correct!
```

**Status:** Faux alarm - implémenté correctement

### ⚠️ Palette Limitée à 7 Matériaux

**Problème:** database contient 13 matériaux, seulement 7 accessibles

```python
base_palette = {
    'PARPAING': 'P',
    'BETON': 'C',
    'LAINE_BOIS': 'W',
    'TERRE': 'T',
    'LAINE_VERRE': 'I',
    'LIMITE_FIXE': '#',
    'AIR': ' '
    # Manquent: PLACO, POLYSTYRENE, CARRELAGE, PVC, etc.
}
```

**Sévérité:** MOYEN
**Fix:** Ajouter matériaux supplémentaires avec Shift+touche

```python
BINDINGS = [
    # Palette de base
    ("p", "select_material('PARPAING')", "P"),
    ("c", "select_material('BETON')", "C"),
    # Matériaux supplémentaires
    ("shift+p", "select_material('PLACO')", "Placo"),
    ("shift+c", "select_material('CARRELAGE')", "Carrelage"),
    ...
]
```

---

## 8. Problèmes Mineurs

### Détails UI

**Messages status permanent**
```python
status_message = "Modèle sauvegardé!"
# Reste visible indéfiniment
# ✓ Fix: Auto-clear après 2-3s
```

**Pas d'aide système**
- Utilisateur doit mémoriser keybinds
- ✓ Fix: Ajouter F1 ou ? pour afficher aide

**Info matériau manquante**
```python
# Affiche juste nom du matériau sélectionné
# ✓ Mieux: Montrer λ, ρ, cp quand matériau sélectionné
```

**Pas d'affichage coordonnées globales**
```python
# Affiche curseur (0-95) mais pas position mètres
# ✓ Mieux: Afficher x=0.0m, y=0.0m aussi
```

---

## 9. Recommandations Prioritaires

### Niveau 1: CRITIQUE (Faire immédiatement)

| # | Problème | Effort | Impact |
|---|----------|--------|--------|
| 1 | Confirmation quit | 30 min | Très haut (perte données) |
| 2 | Zoom/minimap grille | 4 hrs | Haut (usabilité) |
| 3 | Undo/Redo | 2 hrs | Haut (édition confortable) |

### Niveau 2: IMPORTANT (Prochaine version)

| # | Problème | Effort | Impact |
|---|----------|--------|--------|
| 4 | Palette expanded | 1 hr | Moyen (options matériau) |
| 5 | Layout clavier auto | 1 hr | Moyen (accessibilité) |
| 6 | Progress feedback | 1 hr | Moyen (UX) |
| 7 | Help overlay | 1 hr | Moyen (découverte) |

### Niveau 3: BONUS (Nice-to-have)

| # | Problème | Effort | Impact |
|---|----------|--------|--------|
| 8 | Validation models | 2 hrs | Bas (utilisateurs attentifs) |
| 9 | Multi-layer view | 4 hrs | Bas (contexte) |
| 10 | Export/import | 3 hrs | Bas (flexibilité) |

---

## 10. Plan Amélioration (Phased)

### Phase 1: Sécurité (1 jour)

```python
# AVANT: Quit sans demander
BINDINGS = [("ctrl+q", "quit", "Quitter")]

# APRÈS: Confirmation
def action_quit(self):
    if self.has_unsaved_changes:
        self._show_quit_confirmation()
    else:
        self.exit()

def _show_quit_confirmation(self):
    # Utiliser Textual Dialog
    self.app.push_screen(QuitConfirmationScreen(self))
```

### Phase 2: Usabilité (2 jours)

```python
# Ajout zoom
BINDINGS = [
    ("plus", "zoom_in", "Zoom +"),
    ("minus", "zoom_out", "Zoom -"),
]

self.zoom_level = 1  # 1x = normal
self.viewport = (0, 0)  # Top-left visible

def action_zoom_in(self):
    self.zoom_level = min(4, self.zoom_level + 1)
    self.update_plan_view()

def action_zoom_out(self):
    self.zoom_level = max(1, self.zoom_level - 1)
    self.update_plan_view()
```

### Phase 3: Edição (2 jours)

```python
# Undo/Redo
class EditorHistory:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []

    def undo(self, modele):
        if self.undo_stack:
            x, y, z, old_mat = self.undo_stack.pop()
            modele.set_material_at(x, y, z, old_mat)
            # Repush redo

# Intégrer history
def action_paint_material(self):
    x, y, z = self.cursor_x, self.cursor_y, self.current_z
    old_mat = self.modele.Alpha[x, y, z]  # Sauvegarder ancien
    new_mat = self.selected_material_name

    self.modele.set_material_at(x, y, z, new_mat)
    self.history.record(x, y, z, old_mat, new_mat)
    self.has_unsaved_changes = True

def action_undo(self):
    self.history.undo(self.modele)
    self.update_plan_view()
```

---

## 11. Code Quality Metrics

| Métrique | Valeur | Grade |
|----------|--------|-------|
| Lignes code | 332 | ✓ Raisonnable |
| Complexité cyclo | ~15 avg | B (acceptable) |
| Duplication | ~10% | B (peu) |
| Type hints | 0% | D (aucuns) |
| Docstrings | 20% | C (minimum) |
| Test coverage | 0% | F (aucun test) |

### Amélioration Code Quality

```python
# AVANT
def __init__(self, modele, chemin_sauvegarde):
    self.modele = modele

# APRÈS
def __init__(self, modele: 'ModeleMaison', chemin_sauvegarde: str) -> None:
    """Initialize editor with model and save path.

    Args:
        modele: ModeleMaison instance to edit
        chemin_sauvegarde: Path to save model.pkl
    """
    self.modele = modele
```

---

## 12. Résumé Exécutif

### État Actuel
- **Fonctionnel:** Oui, édition basique works
- **Production-ready:** Non, risques UX+data loss
- **Code quality:** Bon (B-), mais peu documenté

### Score Composite

```
Architecture:     B+  (séparation claire)
Clavier:          B   (AZERTY OK, QWERTY non)
Intégration:      A-  (modele.py integration good)
Robustesse:       C+  (pas confirmations, undo)
UX:               D   (grille trop large, pas undo)
Code:             B   (lisible, peu type-hints)
────────────────────
MOYEN:            B-  (Fonctionne, à polir)
```

### Actions Immédiates

1. **Ajouter quit confirmation** (30 min, impact TRÈS HAUT)
2. **Tester à terminal small** → Report bugs si grille > width
3. **Documenter keybinds** (pour utilisateurs)

### Vers Production

Avant release grand public:
- ☑ Confirmation quit
- ☑ Undo/Redo (au moins basic)
- ☑ Zoom ou minimap
- ☑ Help system (F1)

---

## 13. Fichiers Concernés

```
creer_modele.py (332 lignes)
├── PlanWidget (52 lignes) - Affichage 2D
└── ModelEditorTUI (280 lignes)
    ├── __init__ (49 lignes)
    ├── compose (19 lignes)
    ├── Observateurs (27 lignes)
    └── Actions (31 lignes)

creer_modele.tcss (39 lignes)
└── Layout/positionnement

modele.py (399 lignes) - Intégration
└── Utilisé par: set_material_at, preparer, sauvegarder
```

---

**Prochaines étapes:** Vérifier si vous voulez implémenter Phase 1 (confirmation quit) ou autres améliorations?
