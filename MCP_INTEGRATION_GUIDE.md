# Guide d'Intégration du Serveur MCP - Modèles 3D de Maisons

## ✅ Le serveur MCP est opérationnel !

Le test vient de confirmer que **tous les 5 outils MCP fonctionnent parfaitement** :
- ✅ initialize_model
- ✅ add_volume
- ✅ list_materials
- ✅ export_to_json
- ✅ get_model_info

## 🔌 Options d'intégration

### Option 1 : Claude Desktop (macOS/Windows uniquement)

⚠️ **Pas disponible sur Linux pour le moment**

Pour macOS/Windows, ajoutez cette configuration :

**Fichier de configuration :**
- macOS : `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows : `%APPDATA%\Claude\claude_desktop_config.json`

**Contenu :**
```json
{
  "mcpServers": {
    "house-3d-model": {
      "command": "python3",
      "args": [
        "/home/user/HeatSimulation/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/user/HeatSimulation"
      }
    }
  }
}
```

### Option 2 : Cline (VS Code Extension)

[Cline](https://github.com/cline/cline) est une extension VS Code qui supporte MCP.

**Installation :**
1. Installer Cline depuis VS Code Marketplace
2. Ouvrir les paramètres Cline (JSON)
3. Ajouter la configuration :

```json
{
  "mcpServers": {
    "house-3d-model": {
      "command": "python3",
      "args": [
        "/home/user/HeatSimulation/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/user/HeatSimulation"
      }
    }
  }
}
```

### Option 3 : Continue.dev (VS Code Extension)

[Continue](https://continue.dev) supporte également MCP.

**Configuration :** `~/.continue/config.json`

```json
{
  "mcpServers": [
    {
      "name": "house-3d-model",
      "command": "python3",
      "args": ["/home/user/HeatSimulation/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/home/user/HeatSimulation"
      }
    }
  ]
}
```

### Option 4 : Client MCP Personnalisé (Python)

Si vous développez votre propre client MCP :

```python
import subprocess
import json

# Démarrer le serveur
process = subprocess.Popen(
    ["python3", "/home/user/HeatSimulation/mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Envoyer une requête
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "initialize_model",
        "arguments": {
            "length_x": 10.0,
            "length_y": 8.0,
            "length_z": 3.0,
            "resolution": 0.1
        }
    }
}

process.stdin.write(json.dumps(request) + "\n")
process.stdin.flush()

# Lire la réponse
response = json.loads(process.stdout.readline())
print(response)
```

### Option 5 : MCP Inspector (pour développement/debug)

Pour tester le serveur avec une interface web :

**Avec Node.js 18+ :**
```bash
npx @modelcontextprotocol/inspector python3 /home/user/HeatSimulation/mcp_server.py
```

**OU avec le client Python (sans Node.js) :**
```bash
python3 /home/user/HeatSimulation/test_mcp_client.py
```

### Option 6 : Via API Claude (Anthropic)

Si vous utilisez l'API Claude directement :

```python
import anthropic

client = anthropic.Anthropic(api_key="votre_clé")

# Le serveur MCP peut être référencé dans les messages
# (nécessite une configuration spécifique côté Anthropic)
```

## 🧪 Tester le serveur MCP

### Test rapide (sans Node.js) :
```bash
cd /home/user/HeatSimulation
python3 test_mcp_client.py
```

Cela teste automatiquement tous les outils MCP.

### Test avec MCP Inspector (nécessite Node.js 18+) :
```bash
# Installer NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# Installer Node.js 18
nvm install 18
nvm use 18

# Lancer l'inspecteur
npx @modelcontextprotocol/inspector python3 /home/user/HeatSimulation/mcp_server.py
```

## 📋 Les 5 outils MCP disponibles

### 1. initialize_model
Crée un nouveau modèle 3D.

**Paramètres :**
- `length_x` (number) : Longueur en mètres
- `length_y` (number) : Largeur en mètres
- `length_z` (number) : Hauteur en mètres
- `resolution` (number, optionnel) : Résolution en mètres (défaut: 0.1)

**Exemple JSON-RPC :**
```json
{
  "method": "tools/call",
  "params": {
    "name": "initialize_model",
    "arguments": {
      "length_x": 10.0,
      "length_y": 8.0,
      "length_z": 3.0,
      "resolution": 0.1
    }
  }
}
```

### 2. add_volume
Ajoute un volume rectangulaire avec un matériau.

**Paramètres :**
- `x1, y1, z1` (numbers) : Coordonnées du premier coin
- `x2, y2, z2` (numbers) : Coordonnées du second coin
- `material` (string) : Nom du matériau

**Exemple JSON-RPC :**
```json
{
  "method": "tools/call",
  "params": {
    "name": "add_volume",
    "arguments": {
      "x1": 0.0, "y1": 0.0, "z1": 0.0,
      "x2": 10.0, "y2": 8.0, "z2": 0.2,
      "material": "BETON"
    }
  }
}
```

### 3. list_materials
Liste tous les matériaux disponibles.

**Paramètres :** Aucun

**Matériaux disponibles :**
- AIR, LIMITE_FIXE
- PARPAING, PLACO, LAINE_VERRE, LAINE_BOIS
- TERRE, BETON, POLYSTYRENE
- PARQUET_COMPOSITE, CARRELAGE, PVC
- MUR_COMPOSITE_EXT

### 4. export_to_json
Exporte le modèle en JSON.

**Paramètres :**
- `filepath` (string, optionnel) : Chemin du fichier de sortie

**Format JSON exporté :**
```json
{
  "metadata": {...},
  "geometry": {
    "dimensions": {...},
    "vertices_3d": [...],
    "bounding_box": {...}
  },
  "voxels": [
    {
      "index": {"i": 0, "j": 0, "k": 0},
      "center": {"x": 0.05, "y": 0.05, "z": 0.05},
      "material": "BETON",
      "properties": {...}
    }
  ],
  "materials": {...},
  "statistics": {...}
}
```

### 5. get_model_info
Retourne les informations sur le modèle actuel.

**Paramètres :** Aucun

## 🎯 Cas d'usage

### Exemple 1 : Demander à Claude de créer une maison

Avec un client MCP configuré (Cline, Claude Desktop, etc.), vous pouvez dire :

> "Crée un modèle de maison de 12m x 10m x 6m avec une résolution de 0.1m. Ajoute des murs en MUR_COMPOSITE_EXT, un sol en BETON avec isolation POLYSTYRENE, et exporte le résultat en JSON."

Claude utilisera automatiquement les outils MCP :
1. `initialize_model` pour créer le modèle
2. `add_volume` pour ajouter chaque élément
3. `export_to_json` pour générer le fichier

### Exemple 2 : Construire itérativement

> "Initialise un modèle 8x6x3m. Liste les matériaux disponibles. Ajoute un volume d'air intérieur. Montre-moi les infos du modèle."

### Exemple 3 : Modification d'un modèle existant

> "Le modèle actuel manque d'isolation. Ajoute une couche de LAINE_VERRE de 10cm sous le toit."

## 🔍 Debug et surveillance

### Logs du serveur

Les logs apparaissent sur stderr :
```bash
python3 mcp_server.py 2> serveur.log
```

### Test manuel d'un outil

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_materials","arguments":{}}}' | python3 mcp_server.py
```

## 📚 Documentation supplémentaire

- **MCP_README.md** : Documentation complète du serveur
- **UBUNTU_USAGE.md** : Guide d'utilisation Ubuntu
- **example_usage.py** : Exemples Python
- **test_mcp_client.py** : Client de test MCP

## 🆘 Support

Si vous rencontrez des problèmes :

1. **Tester le serveur :**
   ```bash
   python3 test_mcp_client.py
   ```

2. **Vérifier les logs :**
   ```bash
   python3 mcp_server.py 2>&1 | head -20
   ```

3. **Tester un outil directement :**
   ```python
   from mcp_server import HouseModelBuilder
   builder = HouseModelBuilder()
   result = builder.list_materials()
   print(result)
   ```

## 🚀 Prochaines étapes

1. ✅ Serveur MCP opérationnel
2. ⏳ Attendre Claude Desktop pour Linux
3. ⏳ Ou utiliser Cline/Continue.dev dans VS Code
4. ✅ Ou utiliser le client Python directement

Le serveur est prêt pour l'intégration avec n'importe quel client MCP ! 🎉
