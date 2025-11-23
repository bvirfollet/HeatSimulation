# Guide d'utilisation sur Ubuntu 20.04

Claude Desktop n'est pas disponible pour Linux. Voici les alternatives pour utiliser le serveur MCP sur Ubuntu.

## 🚀 Option 1 : Interface Interactive (Recommandé)

La solution la plus simple sans dépendances MCP :

```bash
cd /home/user/HeatSimulation
python3 interactive_builder.py
```

### Fonctionnalités :
- Menu interactif en français
- Création de modèles étape par étape
- 3 exemples prédéfinis
- Export JSON direct

### Exemple d'utilisation :
1. Choisir "1" pour créer un modèle
2. Entrer les dimensions (ou accepter les défauts)
3. Choisir "2" pour ajouter des volumes
4. Choisir "5" pour exporter en JSON

Ou utilisez les exemples prédéfinis (option "6") !

## 🧪 Option 2 : Script Python Direct

Créez votre propre script :

```python
#!/usr/bin/env python3
from mcp_server import HouseModelBuilder

# Créer le builder
builder = HouseModelBuilder()

# Initialiser le modèle
builder.initialize_model(10.0, 8.0, 3.0, resolution=0.1)

# Ajouter des volumes
builder.add_volume(0.0, 0.0, 0.0, 10.0, 8.0, 0.2, "BETON")  # Sol
builder.add_volume(0.2, 0.2, 0.2, 9.8, 7.8, 2.8, "AIR")     # Intérieur

# Exporter
builder.export_to_json("ma_maison.json")
print("✓ Modèle créé!")
```

## 🔍 Option 3 : MCP Inspector (pour développeurs)

Pour tester le serveur MCP avec une interface web :

```bash
# Installer Node.js (si pas déjà installé)
sudo apt update
sudo apt install nodejs npm

# Lancer l'inspecteur MCP
npx @modelcontextprotocol/inspector python3 /home/user/HeatSimulation/mcp_server.py
```

Ouvrez ensuite votre navigateur à l'URL indiquée.

## 📦 Option 4 : Utiliser avec Claude via l'API

Si vous avez une clé API Claude :

```python
import anthropic
from mcp_server import HouseModelBuilder

# Créer un client Claude
client = anthropic.Anthropic(api_key="votre_clé")

# Le serveur MCP peut être appelé programmatiquement
# pour générer des modèles basés sur des prompts
```

## 🎯 Exemples rapides

### Exemple 1 : Maison simple

```bash
cd /home/user/HeatSimulation
python3 example_usage.py
```

Génère automatiquement `maison_simple.json` et `maison_isolee.json`.

### Exemple 2 : Interface interactive

```bash
python3 interactive_builder.py
# Puis choisir l'option 6 -> 1 pour une maison simple
```

### Exemple 3 : Script personnalisé

```bash
cat > ma_construction.py <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/user/HeatSimulation')
from mcp_server import HouseModelBuilder

builder = HouseModelBuilder()
builder.initialize_model(15, 12, 7, 0.1)

# Studio 15m x 12m x 7m (2 étages)
builder.add_volume(0.3, 0.3, 0.3, 14.7, 11.7, 6.7, "AIR")

# Murs
builder.add_volume(0.0, 0.0, 0.0, 0.3, 12.0, 7.0, "MUR_COMPOSITE_EXT")
builder.add_volume(14.7, 0.0, 0.0, 15.0, 12.0, 7.0, "MUR_COMPOSITE_EXT")
builder.add_volume(0.0, 0.0, 0.0, 15.0, 0.3, 7.0, "MUR_COMPOSITE_EXT")
builder.add_volume(0.0, 11.7, 0.0, 15.0, 12.0, 7.0, "MUR_COMPOSITE_EXT")

# Sol et toit
builder.add_volume(0.0, 0.0, 0.0, 15.0, 12.0, 0.3, "BETON")
builder.add_volume(0.0, 0.0, 6.7, 15.0, 12.0, 7.0, "LAINE_VERRE")

builder.export_to_json("mon_studio.json")
print("✓ Studio créé dans mon_studio.json")
EOF

chmod +x ma_construction.py
python3 ma_construction.py
```

## 📊 Visualiser les résultats

Une fois le JSON généré, vous pouvez :

1. **L'inspecter** :
   ```bash
   python3 -m json.tool maison_simple.json | less
   ```

2. **Compter les voxels** :
   ```bash
   jq '.statistics' maison_simple.json
   ```

3. **Lister les matériaux utilisés** :
   ```bash
   jq '.materials | keys' maison_simple.json
   ```

## ⚡ Performances

- Résolution 0.1m : ~1M voxels pour 10x10x3m → ~40MB JSON
- Résolution 0.05m : ~8M voxels → ~320MB JSON
- Pour de grandes maisons, utilisez 0.1m ou 0.2m

## 🐛 Dépannage

### Erreur : Module 'numpy' not found
```bash
pip3 install numpy
```

### Erreur : Module 'mcp' not found
```bash
pip3 install mcp
```

### Fichier JSON trop volumineux
Augmentez la résolution :
```python
builder.initialize_model(10, 8, 3, resolution=0.2)  # 20cm au lieu de 10cm
```

## 📚 Documentation complète

Voir `MCP_README.md` pour la documentation complète du serveur MCP.

## 🔗 Intégration future

Quand Claude Desktop sera disponible sur Linux, suivez `MCP_README.md` pour la configuration.
