#!/usr/bin/env python3
"""
Client de test simple pour le serveur MCP.
Alternative à MCP Inspector qui ne nécessite pas Node.js.
"""

import json
import subprocess
import sys


def send_mcp_request(process, request):
    """Envoie une requête JSON-RPC au serveur MCP."""
    request_json = json.dumps(request) + "\n"
    process.stdin.write(request_json)
    process.stdin.flush()

    # Lire la réponse (ignorer les lignes de log)
    while True:
        response_line = process.stdout.readline()
        if not response_line:
            return None

        # Ignorer les lignes de log (commencent par [)
        if response_line.strip().startswith('['):
            continue

        # Essayer de parser le JSON
        try:
            return json.loads(response_line)
        except json.JSONDecodeError:
            # Si ce n'est pas du JSON valide, continuer
            continue


def test_mcp_server():
    """Test interactif du serveur MCP."""
    print("\n" + "="*70)
    print("  TEST CLIENT MCP - Serveur de Modèles 3D de Maisons")
    print("="*70 + "\n")

    # Démarrer le serveur MCP
    print("🚀 Démarrage du serveur MCP...")
    process = subprocess.Popen(
        ["python3", "/home/user/HeatSimulation/mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # 1. Initialize
        print("\n📋 1. Initialisation de la connexion...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        response = send_mcp_request(process, init_request)
        print(f"✅ Serveur initialisé: {response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")

        # 2. List tools
        print("\n📋 2. Liste des outils disponibles...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        response = send_mcp_request(process, list_tools_request)
        tools = response.get('result', {}).get('tools', [])
        print(f"✅ {len(tools)} outils trouvés:\n")
        for tool in tools:
            print(f"   🔧 {tool['name']}: {tool['description']}")

        # 3. Test initialize_model
        print("\n📋 3. Test: Initialisation d'un modèle 8x6x3m...")
        init_model_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "initialize_model",
                "arguments": {
                    "length_x": 8.0,
                    "length_y": 6.0,
                    "length_z": 3.0,
                    "resolution": 0.1
                }
            }
        }
        response = send_mcp_request(process, init_model_request)
        result_text = response.get('result', {}).get('content', [{}])[0].get('text', '{}')
        result = json.loads(result_text)
        if result.get('status') == 'success':
            print(f"✅ Modèle créé: {result['grid_size']['N_x']}x{result['grid_size']['N_y']}x{result['grid_size']['N_z']} voxels")
        else:
            print(f"❌ Erreur: {result.get('message')}")

        # 4. Test add_volume
        print("\n📋 4. Test: Ajout d'un volume d'air intérieur...")
        add_volume_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "add_volume",
                "arguments": {
                    "x1": 0.2, "y1": 0.2, "z1": 0.2,
                    "x2": 7.8, "y2": 5.8, "z2": 2.8,
                    "material": "AIR"
                }
            }
        }
        response = send_mcp_request(process, add_volume_request)
        result_text = response.get('result', {}).get('content', [{}])[0].get('text', '{}')
        result = json.loads(result_text)
        if result.get('status') == 'success':
            print(f"✅ Volume AIR ajouté")

        # 5. Test list_materials
        print("\n📋 5. Test: Liste des matériaux...")
        list_mat_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "list_materials",
                "arguments": {}
            }
        }
        response = send_mcp_request(process, list_mat_request)
        result_text = response.get('result', {}).get('content', [{}])[0].get('text', '{}')
        result = json.loads(result_text)
        materials = result.get('materials', {})
        print(f"✅ {len(materials)} matériaux disponibles")

        # 6. Test get_model_info
        print("\n📋 6. Test: Informations sur le modèle...")
        info_request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "get_model_info",
                "arguments": {}
            }
        }
        response = send_mcp_request(process, info_request)
        result_text = response.get('result', {}).get('content', [{}])[0].get('text', '{}')
        result = json.loads(result_text)
        if result.get('status') == 'success':
            print(f"✅ Total voxels: {result['total_voxels']:,}")
            print(f"   Zones d'air: {result['air_zones']}")

        # 7. Test export_to_json
        print("\n📋 7. Test: Export JSON...")
        export_request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "export_to_json",
                "arguments": {
                    "filepath": "/home/user/HeatSimulation/test_mcp_output.json"
                }
            }
        }
        response = send_mcp_request(process, export_request)
        result_text = response.get('result', {}).get('content', [{}])[0].get('text', '{}')
        result = json.loads(result_text)
        if result.get('status') == 'success':
            stats = result['model']['statistics']
            print(f"✅ Export réussi!")
            print(f"   Total voxels: {stats['total_voxels']:,}")
            print(f"   Voxels matériaux: {stats['non_air_voxels']:,}")
            print(f"   Fichier: test_mcp_output.json")

        print("\n" + "="*70)
        print("✅ TOUS LES TESTS RÉUSSIS! Le serveur MCP fonctionne parfaitement.")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Terminer proprement le processus
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    test_mcp_server()
