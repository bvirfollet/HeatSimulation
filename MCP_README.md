# Serveur MCP pour Modèles 3D de Maisons

Ce serveur MCP (Model Context Protocol) permet à une IA de construire des modèles volumétriques 3D de maisons et de les exporter en JSON.

## Fonctionnalités

Le serveur expose 5 outils principaux :

### 1. `initialize_model`
Initialise un nouveau modèle 3D de maison avec des dimensions spécifiées.

**Paramètres :**
- `length_x` (nombre) : Longueur en mètres (axe X)
- `length_y` (nombre) : Largeur en mètres (axe Y)
- `length_z` (nombre) : Hauteur en mètres (axe Z)
- `resolution` (nombre, optionnel) : Résolution de la grille en mètres (défaut: 0.1m)

**Exemple :**
```json
{
  "length_x": 10.0,
  "length_y": 8.0,
  "length_z": 3.0,
  "resolution": 0.1
}
```

### 2. `add_volume`
Ajoute un volume rectangulaire avec un matériau spécifique au modèle.

**Paramètres :**
- `x1`, `y1`, `z1` : Coordonnées du premier coin (mètres)
- `x2`, `y2`, `z2` : Coordonnées du second coin (mètres)
- `material` : Nom du matériau

**Exemple :**
```json
{
  "x1": 0.0, "y1": 0.0, "z1": 0.0,
  "x2": 10.0, "y2": 8.0, "z2": 3.0,
  "material": "AIR"
}
```

### 3. `list_materials`
Liste tous les matériaux disponibles avec leurs propriétés thermiques.

**Matériaux disponibles :**
- **AIR** : Zone d'air intérieur
- **LIMITE_FIXE** : Condition aux limites (température fixe)
- **PARPAING** : Blocs de béton (λ=1.1 W/mK)
- **PLACO** : Plaque de plâtre BA13 (λ=0.25 W/mK)
- **LAINE_VERRE** : Laine de verre (λ=0.04 W/mK)
- **LAINE_BOIS** : Laine de bois (λ=0.04 W/mK)
- **TERRE** : Terre/sol (λ=1.5 W/mK)
- **BETON** : Dalle béton (λ=1.7 W/mK)
- **POLYSTYRENE** : Polystyrène expansé/extrudé (λ=0.035 W/mK)
- **PARQUET_COMPOSITE** : Parquet composite (λ=0.15 W/mK)
- **CARRELAGE** : Carrelage (λ=1.0 W/mK)
- **PVC** : Revêtement PVC (λ=0.17 W/mK)
- **MUR_COMPOSITE_EXT** : Mur composite extérieur isolé (λ=0.124 W/mK)

### 4. `export_to_json`
Exporte le modèle complet en JSON avec la géométrie (vertex3D) et les voxels matériaux.

**Paramètres :**
- `filepath` (chaîne, optionnel) : Chemin du fichier de sortie

**Format de sortie JSON :**
```json
{
  "metadata": {
    "version": "1.0",
    "description": "Modèle volumétrique 3D de maison",
    "created_by": "HeatSimulation MCP Server"
  },
  "geometry": {
    "dimensions": {
      "length_x_m": 10.0,
      "length_y_m": 8.0,
      "length_z_m": 3.0
    },
    "resolution_m": 0.1,
    "grid_size": {
      "N_x": 100,
      "N_y": 80,
      "N_z": 30
    },
    "vertices_3d": [
      {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
      {"id": 1, "x": 10.0, "y": 0.0, "z": 0.0},
      ...
    ],
    "bounding_box": {
      "min": {"x": 0.0, "y": 0.0, "z": 0.0},
      "max": {"x": 10.0, "y": 8.0, "z": 3.0}
    }
  },
  "voxels": [
    {
      "index": {"i": 0, "j": 0, "k": 0},
      "center": {"x": 0.05, "y": 0.05, "z": 0.05},
      "material": "PARPAING",
      "properties": {
        "temperature_K": 293.15,
        "diffusivite_m2_s": 6.25e-07,
        "conductivite_W_mK": 1.1,
        "capacite_thermique_volumique_J_m3K": 1760000.0
      }
    },
    ...
  ],
  "materials": {
    "PARPAING": {
      "type": "SOLIDE",
      "conductivite_thermique_W_mK": 1.1,
      "masse_volumique_kg_m3": 2000.0,
      "capacite_thermique_J_kgK": 880.0,
      "diffusivite_m2_s": 6.25e-07
    },
    ...
  },
  "statistics": {
    "total_voxels": 240000,
    "non_air_voxels": 15000
  }
}
```

### 5. `get_model_info`
Retourne les informations sur le modèle actuel (dimensions, nombre de voxels, etc.).

## Installation

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

2. Configuration pour Claude Desktop :

Ajoutez la configuration suivante dans le fichier de configuration de Claude Desktop :

**Sur macOS :** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Sur Windows :** `%APPDATA%\Claude\claude_desktop_config.json`
**Sur Linux :** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "house-3d-model": {
      "command": "python3",
      "args": [
        "/chemin/complet/vers/HeatSimulation/mcp_server.py"
      ],
      "description": "Serveur MCP pour la construction de modèles volumétriques 3D de maisons"
    }
  }
}
```

## Utilisation avec une IA

Une fois le serveur configuré, vous pouvez demander à l'IA de créer des modèles de maisons. Exemples de commandes :

### Exemple 1 : Maison simple
```
Crée un modèle de maison de 10m x 8m x 3m avec :
- Un volume d'air intérieur de 9m x 7m x 2.5m centré
- Des murs en parpaing de 0.2m d'épaisseur
- Un sol en béton de 0.2m d'épaisseur
Puis exporte le résultat en JSON vers "maison_simple.json"
```

### Exemple 2 : Maison avec isolation
```
Initialise un modèle de 12m x 10m x 6m avec une résolution de 0.1m.
Ajoute :
1. Volume d'air intérieur : de (0.3, 0.3, 0.3) à (11.7, 9.7, 5.7)
2. Murs extérieurs en MUR_COMPOSITE_EXT : épaisseur 0.3m
3. Plancher en BETON : de (0, 0, 0) à (12, 10, 0.2)
4. Isolation sous plancher en POLYSTYRENE : de (0, 0, 0.2) à (12, 10, 0.3)
Exporte ensuite le modèle.
```

## Exemple de code Python direct

Si vous voulez utiliser le serveur directement en Python :

```python
from mcp_server import HouseModelBuilder

# Créer un builder
builder = HouseModelBuilder()

# Initialiser un modèle
result = builder.initialize_model(
    length_x=10.0,
    length_y=8.0,
    length_z=3.0,
    resolution=0.1
)
print(result)

# Ajouter un volume d'air
builder.add_volume(
    x1=0.2, y1=0.2, z1=0.2,
    x2=9.8, y2=7.8, z2=2.8,
    material="AIR"
)

# Ajouter des murs
builder.add_volume(
    x1=0.0, y1=0.0, z1=0.0,
    x2=0.2, y2=8.0, z2=3.0,
    material="PARPAING"
)

# Lister les matériaux
materials = builder.list_materials()
print(materials)

# Exporter en JSON
result = builder.export_to_json("mon_modele.json")
print(result)

# Obtenir des infos
info = builder.get_model_info()
print(info)
```

## Structure du JSON exporté

Le JSON exporté contient :

1. **metadata** : Informations sur le fichier
2. **geometry** :
   - **dimensions** : Dimensions physiques (L_x, L_y, L_z)
   - **resolution_m** : Résolution de la grille
   - **grid_size** : Nombre de voxels (N_x, N_y, N_z)
   - **vertices_3d** : Liste des 8 sommets de la boîte englobante
   - **bounding_box** : Coordonnées min/max de la boîte
3. **voxels** : Liste des voxels avec :
   - **index** : Position dans la grille (i, j, k)
   - **center** : Coordonnées 3D du centre du voxel
   - **material** : Nom du matériau
   - **properties** : Propriétés thermiques du voxel
4. **materials** : Dictionnaire de tous les matériaux utilisés
5. **statistics** : Statistiques sur le modèle

## Architecture

Le serveur MCP :
- Utilise le SDK MCP Python officiel
- S'interface avec le système de simulation thermique existant
- Expose des outils via le protocole MCP standard
- Génère des exports JSON structurés

## Dépendances

- `numpy` : Calculs numériques et grilles 3D
- `pyvista` : Visualisation 3D (pour le projet principal)
- `mcp>=1.0.0` : SDK MCP Python

## Développement

Pour modifier le serveur :

1. Le code principal est dans `mcp_server.py`
2. Les matériaux sont définis dans `simulation_projet/model_data.py`
3. La classe `ModeleMaison` est dans `simulation_projet/modele.py`

## Licence

Ce projet fait partie du système HeatSimulation.

## Support

Pour toute question ou problème, créez une issue sur le dépôt GitHub.
