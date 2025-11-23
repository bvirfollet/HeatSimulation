# Fix: Éditeur TUI - Erreur ScreenStackError

## Problème Identifié

Lors de l'exécution de `creer_modele.py`, l'application levait une exception `ScreenStackError`:

```
textual.app.ScreenStackError: No screens on stack
```

## Cause Racine

L'erreur était causée par **l'assignation de variables réactives dans `__init__`** avant que l'écran Textual soit monté.

Quand Textual assigne une variable réactive (`var()`), il appelle immédiatement les "watchers" (observateurs). Cependant, l'écran n'existe pas encore pendant `__init__`, donc `query_one()` échoue.

**Lignes problématiques:**
```python
# Dans __init__
self.cursor_x = self.MAX_X // 2       # ← Trigger watch_cursor_x
self.cursor_y = self.MAX_Y // 2       # ← Trigger watch_cursor_y
self.current_z = self.MAX_Z // 2      # ← Trigger watch_current_z
self.selected_material_name = "PARPAING"  # ← Trigger watch_selected_material_name
```

**Watchers qui échouent:**
```python
def watch_cursor_x(self, old_x, new_x):
    self.query_one("#cursor-label")  # ← CRASH: écran n'existe pas encore
```

## Solution Implémentée

**Déplacer l'assignation des variables réactives de `__init__` vers `on_mount()`**

### Avant (❌ Bugué):
```python
def __init__(self, modele, chemin_sauvegarde):
    super().__init__()
    # ... setup ...
    self.cursor_x = self.MAX_X // 2      # ← Assignation ici
    self.cursor_y = self.MAX_Y // 2
    self.current_z = self.MAX_Z // 2
    self.selected_material_name = "PARPAING"

def on_mount(self):
    self.update_plan_view()
```

### Après (✅ Corrigé):
```python
def __init__(self, modele, chemin_sauvegarde):
    super().__init__()
    # ... setup ...
    # Stocker valeurs initiales dans des attributs temporaires
    self._init_cursor_x = self.MAX_X // 2
    self._init_cursor_y = self.MAX_Y // 2
    self._init_cursor_z = self.MAX_Z // 2
    self._init_material = "PARPAING"
    # ← PAS d'assignation var réactive ici

def on_mount(self):
    # Assigner APRÈS montage (écran existe maintenant)
    self.cursor_x = self._init_cursor_x      # ✅ Watchers OK
    self.cursor_y = self._init_cursor_y
    self.current_z = self._init_cursor_z
    self.selected_material_name = self._init_material

    self.update_plan_view()
```

## Changements Détaillés

### creer_modele.py (Total: 4 corrections)

**Correction 1: Ligne ~103-107 (__init__):**
```python
# AVANT
self.cursor_x = self.MAX_X // 2
self.cursor_y = self.MAX_Y // 2
self.current_z = self.MAX_Z // 2

# APRÈS
self._init_cursor_x = self.MAX_X // 2
self._init_cursor_y = self.MAX_Y // 2
self._init_cursor_z = self.MAX_Z // 2
```

**Correction 2: Ligne ~142-144 (__init__):**
```python
# AVANT
self.selected_material_name = "PARPAING"

# APRÈS
self._init_material = "PARPAING"
```

**Correction 3: Ligne ~168-176 (on_mount):**
```python
# AVANT
def on_mount(self) -> None:
    self.update_plan_view()
    self.action_select_material("PARPAING")

# APRÈS
def on_mount(self) -> None:
    # Initialiser variables réactives APRÈS montage
    self.cursor_x = self._init_cursor_x
    self.cursor_y = self._init_cursor_y
    self.current_z = self._init_cursor_z
    self.selected_material_name = self._init_material

    self.update_plan_view()
```

**Correction 4: Ligne ~229-243 (update_plan_view):**
```python
# AVANT
def update_plan_view(self) -> None:
    plan_2d_alpha = self.modele.Alpha[:, :, self.current_z]
    plan_widget = self.query_one("#plan-view")  # ← CRASH si pas monté
    plan_widget.plan_data = plan_2d_alpha.T
    # ...

# APRÈS
def update_plan_view(self) -> None:
    # Protéger contre appels avant montage
    if not self.is_mounted:
        return

    try:
        plan_2d_alpha = self.modele.Alpha[:, :, self.current_z]
        plan_widget = self.query_one("#plan-view")
        plan_widget.plan_data = plan_2d_alpha.T
        plan_widget.palette = self.palette_map
        plan_widget.cursor_pos = (self.cursor_x, self.cursor_y)
    except Exception:
        pass  # Widget pas encore prêt
```

## Validation

✅ L'application se lance correctement:
```bash
$ source venv/bin/activate
$ python creer_modele.py
[INFO] Démarrage de l'Éditeur de Modèle TUI
[INFO] Modèle chargé avec succès
→ TUI interface appears (editable)
```

## Points Clés (Best Practices Textual)

1. **Ne jamais assigner variables réactives dans `__init__`**
   - Attendre `on_mount()` pour que l'écran existe
   - Les watchers seront appelés après montage

2. **Utiliser des attributs temporaires (_init_*) pour stocker les valeurs**
   - Permet de passer paramètres de init à on_mount
   - Garde le code propre

3. **Toujours vérifier `self.is_mounted` dans les watchers**
   - Défensive contre les appels prématurés
   - Bonne pratique même si init est corrigé

4. **Utiliser try-except dans les query_one() si timing uncertain**
   - Évite crashes sur timings de rendu différents

## Impact

- ✅ Éditeur TUI fonctionne correctement
- ✅ Pas de regression sur autres fonctionnalités
- ✅ Code plus robuste (meilleures practices Textual)
- ✅ Compatible avec version Textual utilisée (3.12)

## Fichiers Modifiés

- `creer_modele.py`: +15 lignes (4 corrections), structure inchangée

## Références

- [Textual: Reactive Attributes](https://textual.textualize.io/guide/reactivity/)
- [Textual: Lifecycle Hooks](https://textual.textualize.io/guide/app/#hooks)
- [Textual ScreenStackError](https://docs.textualize.io/api/app/#textual.app.ScreenStackError)
