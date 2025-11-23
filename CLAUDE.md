# CLAUDE.md - HeatSimulation Project Guide

> **Last Updated**: 2025-11-23
> **Purpose**: Guide for AI assistants working with this 3D thermal simulation codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Core Architecture](#core-architecture)
4. [Development Workflow](#development-workflow)
5. [Key Conventions](#key-conventions)
6. [Common Tasks](#common-tasks)
7. [Important Files Reference](#important-files-reference)
8. [Testing and Validation](#testing-and-validation)
9. [Known Issues and Improvements](#known-issues-and-improvements)

---

## Project Overview

### What is HeatSimulation?

HeatSimulation is a **3D thermal simulation system** for building energy analysis. It uses finite difference methods to simulate:
- **Heat conduction** through building materials (walls, insulation, concrete, etc.)
- **Convection** between air volumes and solid surfaces
- **Thermal radiation** (Stefan-Boltzmann law)
- **Ground coupling** and external boundary conditions

### Scientific Approach

- **Numerical Method**: FTCS (Forward-Time Central-Space) with semi-implicit convection coupling
- **Validation**: Energy conservation tracking (<1% error target)
- **Physical Models**:
  - Conduction: ∂T/∂t = α·∇²T
  - Convection: Q = h·A·(T_surface - T_air)
  - Radiation: Q = ε·σ·A·(T⁴ - T_sky⁴)

### Technology Stack

- **Language**: Python 3.10+
- **Core Libraries**: NumPy (computation), PyVista (3D visualization), Textual (TUI)
- **Environment**: Virtual environment (venv) based
- **Data Format**: Pickle (.pkl) for model serialization

### Project Status

- **Version**: 2.0 (with semi-implicit coupling and radiation)
- **Quality Score**: 8.5/10 (scientific validation)
- **Production Ready**: Functional but TUI editor needs UX improvements

---

## Repository Structure

```
HeatSimulation/
├── simulation_projet/          # Main source code directory
│   ├── main.py                 # Simulation runner (entry point)
│   ├── creer_modele.py         # TUI editor for building models
│   ├── modele.py               # 3D model management
│   ├── simulation.py           # Physics engine (v2: semi-implicit)
│   ├── model_data.py           # Materials database + ZoneAir class
│   ├── parametres.py           # Simulation parameters
│   ├── constantes.py           # Physical constants (legacy)
│   ├── rayonnement.py          # Thermal radiation module
│   ├── stockage.py             # Results storage
│   ├── visualisation.py        # PyVista 3D visualization
│   ├── logger.py               # Simple logging system
│   ├── utils.py                # Utility functions
│   ├── test_analytique.py      # Analytical validation tests
│   │
│   ├── ANALYSE_EDITEUR_TUI.md       # TUI editor analysis (606 lines)
│   ├── AMÉLIORATIONS_V2.md          # v2 improvements documentation
│   └── FIX_EDITEUR_TUI.md           # TUI fixes documentation
│
├── setup.py                    # Package setup (legacy MusePartition ref)
├── setup.sh                    # Installation script (venv + deps)
├── requirements.txt            # numpy, pyvista
├── .gitignore                  # venv, resultats_sim, __pycache__
└── modele.pkl                  # Generated: 3D building model (binary)
```

### Generated Artifacts (Ignored by Git)

- `venv/` - Virtual environment
- `resultats_sim/` - Simulation output data
- `modele.pkl` - Building model (created by TUI editor)

---

## Core Architecture

### Data Flow

```
┌─────────────────┐
│  creer_modele.py│  User creates/edits 3D building model
│  (TUI Editor)   │  → Saves to modele.pkl
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   modele.pkl    │  Serialized 3D model (pickle)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     main.py     │  Loads model → Runs simulation
│                 │  → Generates resultats_sim/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ visualisation.py│  Displays 3D temperature fields
│  (PyVista)      │  → Interactive 3D viewer
└─────────────────┘
```

### Key Classes

#### ModeleMaison (modele.py)
**Purpose**: Manages 3D grid, materials, and geometry

**Key Attributes**:
- `T` (np.ndarray): Temperature field [N_x, N_y, N_z]
- `Alpha` (np.ndarray): Diffusivity field (also used as material ID)
- `Lambda` (np.ndarray): Thermal conductivity field
- `RhoCp` (np.ndarray): Volumetric heat capacity field
- `zones_air` (dict): Air volume zones {id: ZoneAir}
- `surfaces_convection_idx` (dict): Convection surface indices

**Key Methods**:
- `construire_volume_metres(p1, p2, material, T_override)` - Fill 3D region
- `construire_depuis_plans_ascii(plans, mapping)` - Build from ASCII art
- `set_material_at(x, y, z, material)` - Edit single voxel (TUI editor)
- `preparer_simulation()` - Finalize air zones, detect surfaces
- `sauvegarder(path)` / `charger(path, logger)` - Pickle serialization

#### Simulation (simulation.py)
**Purpose**: Physics engine with semi-implicit time stepping

**v2 Improvements**:
- Semi-implicit convection coupling (eliminates time lag)
- Energy balance tracking (Bilan class)
- Thermal radiation support (ModeleRayonnement)

**Key Methods**:
- `lancer_simulation(duree_s, intervalle_stockage_s)` - Main loop
- `_etape_conduction()` - FTCS conduction step
- `_etape_convection_implicite()` - Implicit air-solid coupling
- `_etape_rayonnement()` - Radiation heat transfer

#### ZoneAir (model_data.py)
**Purpose**: Represents air volume with uniform temperature

**Key Attributes**:
- `T` (float): Air temperature [°C]
- `volume_m3` (float): Volume [m³]
- `capacite_thermique_J_K` (float): Thermal capacity [J/K]
- `puissance_apport_W` (float): Heating power [W] (e.g., radiator)

#### ParametresSimulation (parametres.py)
**Purpose**: Stores grid, time, and boundary conditions

**Key Parameters**:
- `dims_m` (tuple): Physical dimensions (Lx, Ly, Lz) [m]
- `ds` (float): Grid spacing [m] (default: 0.1m)
- `dt` (float): Time step [s] (default: 10s)
- `T_interieur_init` (float): Initial indoor temp [°C] (default: 20°C)
- `T_exterieur_init` (float): Initial outdoor temp [°C] (default: 0°C)
- `T_sol_init` (float): Ground temperature [°C] (default: 10°C)
- `h_convection` (float): Convection coefficient [W/m²K] (default: 8.0)

### Materials Database (MATERIAUX in model_data.py)

**Material Types**:
1. `"AIR"` - Air zones (convection)
2. `"LIMITE_FIXE"` - Fixed boundary conditions
3. `"SOLIDE"` - Building materials (conduction)

**Available Materials** (13 total):
- **Structural**: PARPAING, BETON, TERRE
- **Insulation**: LAINE_VERRE, LAINE_BOIS, POLYSTYRENE
- **Finishes**: PLACO, CARRELAGE, PVC, PARQUET_COMPOSITE
- **Composite**: MUR_COMPOSITE_EXT (equivalent multi-layer wall)
- **Special**: AIR, LIMITE_FIXE

**Material Properties**:
```python
{
    "lambda": float,  # Thermal conductivity [W/mK]
    "rho": float,     # Density [kg/m³]
    "cp": float,      # Specific heat [J/kgK]
    "type": str,      # "SOLIDE" | "AIR" | "LIMITE_FIXE"
    "alpha": float    # Diffusivity (auto-calculated for SOLIDE)
}
```

**Adding New Materials**:
```python
MATERIAUX["NEW_MATERIAL"] = {
    "lambda": 0.5,
    "rho": 1500.0,
    "cp": 900.0,
    "type": "SOLIDE"
}
# Alpha is auto-calculated by loop at end of file
```

---

## Development Workflow

### Standard Workflow

```bash
# 1. Setup environment (first time only)
./setup.sh

# 2. Activate virtual environment
source venv/bin/activate

# 3. Create/edit building model (TUI editor)
cd simulation_projet
python creer_modele.py

# 4. Run simulation
python main.py

# 5. View results (opens PyVista interactive window)
# Results are automatically visualized at t=0, t=3600s, t=7200s
```

### TUI Editor Workflow (creer_modele.py)

**Purpose**: Interactively create 3D building models

**Controls** (AZERTY keyboard):
- **Navigation**: Q (left), D (right), Z (up), S (down)
- **Floors**: A (up Z), E (down Z)
- **Paint**: Enter (apply selected material)
- **Material Selection**: P (parpaing), C (béton), B (laine bois), T (terre), I (laine verre), H (limite fixe), Space (air)
- **Save**: Ctrl+S
- **Quit**: Ctrl+Q

**Workflow**:
1. Editor loads existing `modele.pkl` or creates blank model
2. Navigate with QZSD + AE
3. Select material (P, C, B, etc.)
4. Paint with Enter
5. Save with Ctrl+S (IMPORTANT: No auto-save!)
6. Quit with Ctrl+Q

**⚠️ CRITICAL**: Always Ctrl+S before quitting! No confirmation dialog exists.

### Simulation Workflow (main.py)

**Default Parameters** (can be modified in main.py):
```python
sim.lancer_simulation(
    duree_s=7200,              # 2 hours
    intervalle_stockage_s=600  # Save every 10 minutes
)
```

**Output**:
- Console logs with energy balance report
- `resultats_sim/` directory with temperature snapshots
- Interactive PyVista visualizations

---

## Key Conventions

### Coding Style

1. **Language**: French for comments, docstrings, and variable names
   - Exception: Standard English terms (e.g., `alpha`, `lambda`)

2. **File Headers**: All files generated by "dispatcher_le_projet.py" (legacy)
   ```python
   # Fichier généré automatiquement par dispatcher_le_projet.py
   ```

3. **Naming Conventions**:
   - Classes: PascalCase (e.g., `ModeleMaison`, `Simulation`)
   - Functions/Methods: snake_case (e.g., `construire_volume_metres`)
   - Constants: UPPER_CASE (e.g., `MATERIAUX`)

4. **NumPy Indexing**: Always [x, y, z] order (Fortran-style for PyVista)

5. **Temperature Units**: Celsius [°C] for user-facing, Kelvin [K] internally for radiation

### Git Conventions

**Branch**: Currently on `claude/claude-md-mibhny7ty9ii41vr-01HBkFD4cnx81oyA3x8LyG4U`

**Commit Messages** (recent pattern):
- Clear, descriptive English
- Examples: "Fixed TUI and improovement of thermic modelisation", "Step 5 (prise en compte du sol)"

**Ignored Files** (.gitignore):
- `.idea/` (IDE)
- `__pycache__/` (Python bytecode)
- `resultats_sim/` (simulation outputs)
- `venv/` (virtual environment)

### Physics Conventions

1. **Grid Indexing**: (x, y, z) where z is vertical (height)

2. **Material ID Encoding** (in Alpha array):
   - `> 0`: Solid materials (diffusivity value)
   - `= 0`: Fixed boundary conditions (LIMITE_FIXE)
   - `< 0`: Air zones (negative zone ID, e.g., -1)

3. **Stability Criterion** (CFL):
   ```
   CFL = α_max · dt / ds² < 1/6
   ```
   Simulation checks this and throws ValueError if violated.

4. **Energy Conservation Target**: < 1% error (excellent), < 5% acceptable

---

## Common Tasks

### Adding a New Material

**File**: `simulation_projet/model_data.py`

```python
# 1. Add to MATERIAUX dictionary (before the auto-calc loop)
MATERIAUX["MY_MATERIAL"] = {
    "lambda": 0.8,      # W/mK
    "rho": 1200.0,      # kg/m³
    "cp": 1000.0,       # J/kgK
    "type": "SOLIDE"
}

# 2. (Optional) Add to TUI palette in creer_modele.py
# File: creer_modele.py, line ~114
base_palette = {
    # ...
    'MY_MATERIAL': 'M',  # Single character for display
}

# 3. (Optional) Add keybinding in creer_modele.py
# File: creer_modele.py, line ~72
BINDINGS = [
    # ...
    ("m", "select_material('MY_MATERIAL')", "My Material (M)"),
]
```

### Modifying Grid Resolution

**File**: `simulation_projet/creer_modele.py` (line ~285)

```python
params = ParametresSimulation(
    logger=logger,
    dims_m=(9.5, 15.0, 6.6),  # Physical dimensions [m]
    ds=0.1,                    # Grid spacing [m] → 96x151x67 points
    dt=10.0,                   # Time step [s]
    # ...
)
```

**⚠️ Impact**:
- Smaller `ds` → finer resolution → longer computation
- Ensure CFL stability: `dt < ds²/(6·α_max)`
- Large grids (>100³) may exceed terminal width in TUI

### Changing Simulation Duration

**File**: `simulation_projet/main.py` (line ~55)

```python
sim.lancer_simulation(
    duree_s=3600,              # 1 hour (instead of 7200)
    intervalle_stockage_s=300  # Save every 5 min (instead of 600)
)
```

### Enabling/Disabling Radiation

**File**: `simulation_projet/main.py` (modify Simulation creation)

```python
# Enable radiation (default)
sim = Simulation(modele, chemin_sortie=chemin_resultats, enable_rayonnement=True)

# Disable radiation (faster, simpler physics)
sim = Simulation(modele, chemin_sortie=chemin_resultats, enable_rayonnement=False)
```

### Adding Heating Power to Air Zone

**File**: Modify after loading model in `main.py`

```python
modele = ModeleMaison.charger(chemin_modele, logger)

# Add 1000W heating to air zone -1
if -1 in modele.zones_air:
    modele.zones_air[-1].set_apport_puissance(1000.0)  # Watts
```

### Running Analytical Tests

**File**: `simulation_projet/test_analytique.py`

```bash
cd simulation_projet
python test_analytique.py
```

**Expected Output**:
```
============================================================
SUITE DE TESTS ANALYTIQUES - SIMULATION THERMIQUE
============================================================
TEST ANALYTIQUE: Diffusion 1D
...
✓ TOUS LES TESTS SONT PASSÉS
============================================================
```

---

## Important Files Reference

### Entry Points

| File | Purpose | Usage |
|------|---------|-------|
| `creer_modele.py` | TUI editor | `python creer_modele.py` |
| `main.py` | Simulation runner | `python main.py` |
| `test_analytique.py` | Validation tests | `python test_analytique.py` |

### Core Modules

| File | Lines | Key Classes/Functions |
|------|-------|----------------------|
| `modele.py` | 393 | `ModeleMaison` - 3D grid management |
| `simulation.py` | 355 | `Simulation`, `Bilan` - Physics engine |
| `model_data.py` | 188 | `MATERIAUX`, `ZoneAir` |
| `parametres.py` | 45 | `ParametresSimulation` |
| `rayonnement.py` | ~170 | `ModeleRayonnement` |
| `visualisation.py` | ~200 | `Visualisation` (PyVista) |
| `stockage.py` | ~100 | `StockageResultats` |
| `logger.py` | 41 | `LoggerSimulation` |

### Documentation

| File | Lines | Purpose |
|------|-------|---------|
| `ANALYSE_EDITEUR_TUI.md` | 606 | Detailed TUI editor analysis |
| `AMÉLIORATIONS_V2.md` | 330 | v2 improvements (semi-implicit, radiation) |
| `FIX_EDITEUR_TUI.md` | ? | TUI bug fixes |
| `CLAUDE.md` | This file | AI assistant guide |

### Configuration

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies (numpy, pyvista) |
| `setup.sh` | Automated venv setup |
| `setup.py` | Legacy package config (MusePartition reference, ignore) |
| `.gitignore` | Git exclusions |

---

## Testing and Validation

### Energy Conservation Check

**Automatic**: Run at end of every simulation

**Interpretation**:
```
✓ EXCELLENT: < 0.1% error
✓ BON:       < 1.0% error
⚠ ACCEPTABLE: < 5.0% error
✗ INSUFFISANT: > 5.0% error
```

**Debugging High Errors**:
1. Check CFL stability (should be < 0.166)
2. Reduce `dt` or increase `ds`
3. Verify material properties (no zero RhoCp for solids)
4. Check for air zone volume errors

### Stability Check (CFL)

**Automatic**: Checked at Simulation initialization

**Formula**:
```
CFL = α_max · dt / ds²
Required: CFL < 1/6 ≈ 0.166
```

**If CFL > 0.166**:
- Simulation throws `ValueError("Simulation instable (CFL).")`
- **Fix**: Reduce `dt` in `parametres.py`

### Analytical Validation

**File**: `test_analytique.py`

**Tests**:
1. **1D Diffusion**: Compare FTCS vs analytical solution (erf function)
2. **Thermal Equilibrium**: Verify system approaches steady state

**Running**:
```bash
python test_analytique.py
```

---

## Known Issues and Improvements

### TUI Editor Issues (See ANALYSE_EDITEUR_TUI.md)

#### 🔴 CRITICAL
1. **No quit confirmation** - Data loss risk (Ctrl+Q without Ctrl+S)
2. **Grid exceeds terminal width** - 151 characters wide (typical terminal: 80-120)
3. **No Undo/Redo** - Mistakes are permanent

#### ⚠️ IMPORTANT
4. **AZERTY keyboard only** - QWERTY users have poor UX
5. **Limited palette** - Only 7/13 materials accessible
6. **No save progress indicator** - Appears frozen during save

#### 💡 PLANNED IMPROVEMENTS
- Quit confirmation dialog
- Zoom/minimap for navigation
- Undo/Redo stack
- QWERTY/AZERTY auto-detection
- Full material palette with Shift+ keys
- Save progress bar

### Simulation Improvements (See AMÉLIORATIONS_V2.md)

#### ✅ IMPLEMENTED (v2)
- Semi-implicit convection coupling
- Energy balance tracking
- Thermal radiation (Stefan-Boltzmann)
- Reduced time step (20s → 10s)
- Analytical validation tests

#### 🚀 FUTURE (v3)
1. **Solar radiation** - Gain through windows
2. **Humidity and condensation** - Wet zones
3. **Day/night temperature schedule** - Realistic T_ext variations
4. **Adaptive time stepping** - Variable dt based on gradients
5. **Multi-zone air** - Vertical stratification
6. **GPU parallelization** - CUDA for large grids (>100³)

### Setup.py Inconsistency

**Issue**: `setup.py` references "MusePartition" (audio transcription project)

**Impact**: None (not used for installation; setup.sh handles everything)

**Action**: Can be ignored or cleaned up

---

## Quick Reference

### File to Edit for Common Changes

| Task | File | Line(s) |
|------|------|---------|
| Add material | `model_data.py` | ~17-114 |
| Change grid size | `creer_modele.py` | ~285-293 |
| Change time step | `parametres.py` | ~11 |
| Change sim duration | `main.py` | ~55-58 |
| Enable/disable radiation | `main.py` | ~51 |
| Add heating power | `main.py` | ~37-39 (after load) |
| TUI keybindings | `creer_modele.py` | ~72-91 |

### Command Cheatsheet

```bash
# Setup (once)
./setup.sh

# Activate venv (every session)
source venv/bin/activate

# Create model
cd simulation_projet && python creer_modele.py

# Run simulation
python main.py

# Run tests
python test_analytique.py

# Deactivate venv
deactivate
```

### Typical Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `Simulation instable (CFL).` | Time step too large | Reduce `dt` in parametres.py |
| `Fichier modèle 'modele.pkl' introuvable.` | No model created | Run `creer_modele.py` first |
| `Erreur > 1%, vérifier stabilité` | Energy conservation issue | Check CFL, reduce dt |
| `Module textual not found` | Missing dependency | `pip install textual` |
| `ImportError: pyvista` | Missing dependency | `pip install pyvista` |

---

## Notes for AI Assistants

### When Modifying Code

1. **Respect French Conventions**: Keep comments/docs in French unless asked otherwise
2. **NumPy Best Practices**: Use vectorized operations (avoid Python loops)
3. **Logger Usage**: Use `self.logger.info/debug/warn/error` instead of print()
4. **Physical Units**: Always comment units (e.g., `[W/mK]`, `[°C]`, `[J]`)
5. **CFL Safety**: After changing `dt` or `ds`, verify CFL < 0.166

### When Adding Features

1. **Test Energy Conservation**: Run simulation and check error < 1%
2. **Document in French**: Add comments explaining physics/math
3. **Update CLAUDE.md**: Add new materials/features to this guide
4. **Consider TUI**: If adding materials, update `creer_modele.py` palette

### When Debugging

1. **Enable DEBUG logging**: Change `niveau="DEBUG"` in logger initialization
2. **Check CFL first**: Most instabilities come from CFL violation
3. **Verify material properties**: Ensure no zero/negative values
4. **Run analytical tests**: `python test_analytique.py`

### Project Context

- **Owner**: Bertrand Virfollet (bvirfollet)
- **Domain**: Building energy simulation / thermal engineering
- **Maturity**: Research/Educational tool (not commercial production)
- **Quality**: High scientific rigor (v2: 8.5/10), moderate software engineering

---

## Changelog

### 2025-11-23 (v2.0)
- ✅ Semi-implicit convection coupling
- ✅ Energy balance tracking and validation
- ✅ Thermal radiation (Stefan-Boltzmann)
- ✅ Reduced time step (10s) for better stability
- ✅ Analytical validation tests
- ✅ Comprehensive documentation (this file)

### Earlier Steps (Step 2-5)
- Step 5: Ground coupling (TERRE material, T_sol)
- Step 4: TUI editor improvements
- Step 3: Convection implementation
- Step 2: Basic conduction solver

---

**End of CLAUDE.md**

For questions or issues, refer to:
- Technical details: `AMÉLIORATIONS_V2.md`
- TUI editor issues: `ANALYSE_EDITEUR_TUI.md`
- Code comments in individual files
