#!/usr/bin/env python3
"""
Serveur MCP pour la construction de modèles volumétriques 3D de maisons.
Permet à une IA de créer des modèles et de les exporter en JSON.
"""

import json
import sys
from pathlib import Path

# Ajouter le répertoire simulation_projet au path
sys.path.insert(0, str(Path(__file__).parent / "simulation_projet"))

from logger import LoggerSimulation
from model_data import MATERIAUX
from modele import ModeleMaison
from parametres import ParametresSimulation
import numpy as np

# Importer le SDK MCP
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Erreur: le package 'mcp' n'est pas installé.", file=sys.stderr)
    print("Installez-le avec: pip install mcp", file=sys.stderr)
    sys.exit(1)


class HouseModelBuilder:
    """Gestionnaire de construction de modèles de maisons."""

    def __init__(self):
        self.modele = None
        self.params = None
        self.logger = None
        self.model_initialized = False

    def initialize_model(self, length_x: float, length_y: float, length_z: float,
                         resolution: float = 0.1) -> dict:
        """
        Initialise un nouveau modèle 3D de maison.

        Args:
            length_x: Longueur en mètres (axe X)
            length_y: Largeur en mètres (axe Y)
            length_z: Hauteur en mètres (axe Z)
            resolution: Résolution de la grille en mètres (taille d'un voxel)

        Returns:
            dict: Informations sur le modèle initialisé
        """
        # Créer un logger
        self.logger = LoggerSimulation(niveau="INFO")

        # Créer les paramètres
        self.params = ParametresSimulation(
            logger=self.logger,
            dims_m=(length_x, length_y, length_z),
            ds=resolution
        )

        # Créer le modèle
        self.modele = ModeleMaison(self.params)
        self.model_initialized = True

        return {
            "status": "success",
            "dimensions": {
                "length_x": length_x,
                "length_y": length_y,
                "length_z": length_z
            },
            "grid_size": {
                "N_x": self.params.N_x,
                "N_y": self.params.N_y,
                "N_z": self.params.N_z
            },
            "resolution": resolution,
            "total_voxels": self.params.N_x * self.params.N_y * self.params.N_z
        }

    def add_volume(self, x1: float, y1: float, z1: float,
                   x2: float, y2: float, z2: float,
                   material: str) -> dict:
        """
        Ajoute un volume rectangulaire avec un matériau spécifique.

        Args:
            x1, y1, z1: Coordonnées du premier coin (mètres)
            x2, y2, z2: Coordonnées du second coin (mètres)
            material: Nom du matériau (voir liste des matériaux disponibles)

        Returns:
            dict: Résultat de l'opération
        """
        if not self.model_initialized:
            return {"status": "error", "message": "Le modèle doit d'abord être initialisé"}

        if material not in MATERIAUX:
            return {
                "status": "error",
                "message": f"Matériau '{material}' inconnu",
                "available_materials": list(MATERIAUX.keys())
            }

        try:
            p1 = (x1, y1, z1)
            p2 = (x2, y2, z2)
            self.modele.construire_volume_metres(p1, p2, material)

            return {
                "status": "success",
                "volume": {
                    "corner1": {"x": x1, "y": y1, "z": z1},
                    "corner2": {"x": x2, "y": y2, "z": z2},
                    "material": material
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_materials(self) -> dict:
        """
        Liste tous les matériaux disponibles avec leurs propriétés.

        Returns:
            dict: Dictionnaire des matériaux et leurs propriétés
        """
        materials_info = {}
        for nom, props in MATERIAUX.items():
            materials_info[nom] = {
                "type": props["type"],
                "conductivite_thermique_W_mK": props["lambda"],
                "masse_volumique_kg_m3": props["rho"],
                "capacite_thermique_J_kgK": props["cp"]
            }
            if props["type"] == "SOLIDE":
                materials_info[nom]["diffusivite_m2_s"] = props["alpha"]

        return {"materials": materials_info}

    def export_to_json(self, filepath: str = None) -> dict:
        """
        Exporte le modèle complet en JSON avec la géométrie (vertex3D) et les voxels.

        Args:
            filepath: Chemin du fichier de sortie (optionnel)

        Returns:
            dict: Le modèle exporté en format JSON
        """
        if not self.model_initialized:
            return {"status": "error", "message": "Le modèle doit d'abord être initialisé"}

        # Extraire les vertices uniques et créer la géométrie
        vertices_3d = []
        voxels = []

        # Parcourir tous les voxels de la grille
        for i in range(self.params.N_x):
            for j in range(self.params.N_y):
                for k in range(self.params.N_z):
                    # Coordonnées physiques du centre du voxel
                    x = (i + 0.5) * self.params.ds
                    y = (j + 0.5) * self.params.ds
                    z = (k + 0.5) * self.params.ds

                    # Identifier le matériau
                    alpha_val = self.modele.Alpha[i, j, k]

                    # Déterminer le matériau
                    material_name = "AIR"
                    if alpha_val < 0:
                        material_name = "AIR"
                    else:
                        # Chercher le matériau correspondant
                        lambda_val = self.modele.Lambda[i, j, k]
                        rho_cp_val = self.modele.RhoCp[i, j, k]

                        # Trouver le matériau qui correspond
                        for nom, props in MATERIAUX.items():
                            if props["type"] == "SOLIDE":
                                if abs(props["alpha"] - alpha_val) < 1e-9:
                                    material_name = nom
                                    break
                            elif props["type"] == "LIMITE_FIXE" and alpha_val == 0.0:
                                if lambda_val == 0.0 and rho_cp_val == 0.0:
                                    material_name = "LIMITE_FIXE"
                                    break

                    # Ne stocker que les voxels non-air pour optimiser
                    if material_name != "AIR" or alpha_val != 0.0:
                        voxel_data = {
                            "index": {"i": int(i), "j": int(j), "k": int(k)},
                            "center": {"x": float(x), "y": float(y), "z": float(z)},
                            "material": material_name,
                            "properties": {
                                "temperature_K": float(self.modele.T[i, j, k]),
                                "diffusivite_m2_s": float(alpha_val) if alpha_val > 0 else None,
                                "conductivite_W_mK": float(lambda_val) if lambda_val > 0 else None,
                                "capacite_thermique_volumique_J_m3K": float(rho_cp_val) if rho_cp_val > 0 else None
                            }
                        }
                        voxels.append(voxel_data)

        # Créer les vertices de la boîte englobante
        vertices_3d = [
            {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": 1, "x": float(self.params.L_x), "y": 0.0, "z": 0.0},
            {"id": 2, "x": float(self.params.L_x), "y": float(self.params.L_y), "z": 0.0},
            {"id": 3, "x": 0.0, "y": float(self.params.L_y), "z": 0.0},
            {"id": 4, "x": 0.0, "y": 0.0, "z": float(self.params.L_z)},
            {"id": 5, "x": float(self.params.L_x), "y": 0.0, "z": float(self.params.L_z)},
            {"id": 6, "x": float(self.params.L_x), "y": float(self.params.L_y), "z": float(self.params.L_z)},
            {"id": 7, "x": 0.0, "y": float(self.params.L_y), "z": float(self.params.L_z)}
        ]

        # Créer le modèle JSON complet
        model_json = {
            "metadata": {
                "version": "1.0",
                "description": "Modèle volumétrique 3D de maison",
                "created_by": "HeatSimulation MCP Server"
            },
            "geometry": {
                "dimensions": {
                    "length_x_m": float(self.params.L_x),
                    "length_y_m": float(self.params.L_y),
                    "length_z_m": float(self.params.L_z)
                },
                "resolution_m": float(self.params.ds),
                "grid_size": {
                    "N_x": int(self.params.N_x),
                    "N_y": int(self.params.N_y),
                    "N_z": int(self.params.N_z)
                },
                "vertices_3d": vertices_3d,
                "bounding_box": {
                    "min": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "max": {
                        "x": float(self.params.L_x),
                        "y": float(self.params.L_y),
                        "z": float(self.params.L_z)
                    }
                }
            },
            "voxels": voxels,
            "materials": self.list_materials()["materials"],
            "statistics": {
                "total_voxels": int(self.params.N_x * self.params.N_y * self.params.N_z),
                "non_air_voxels": len(voxels)
            }
        }

        # Sauvegarder dans un fichier si demandé
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(model_json, f, indent=2, ensure_ascii=False)
                return {
                    "status": "success",
                    "message": f"Modèle exporté vers {filepath}",
                    "model": model_json
                }
            except Exception as e:
                return {"status": "error", "message": f"Erreur lors de l'export: {str(e)}"}

        return {"status": "success", "model": model_json}

    def get_model_info(self) -> dict:
        """
        Retourne les informations sur le modèle actuel.

        Returns:
            dict: Informations sur le modèle
        """
        if not self.model_initialized:
            return {"status": "error", "message": "Aucun modèle initialisé"}

        # Compter les voxels par type de matériau
        material_counts = {}
        for i in range(self.params.N_x):
            for j in range(self.params.N_y):
                for k in range(self.params.N_z):
                    alpha_val = self.modele.Alpha[i, j, k]
                    if alpha_val < 0:
                        mat = "AIR"
                    elif alpha_val == 0.0:
                        mat = "LIMITE_FIXE"
                    else:
                        mat = "SOLIDE"
                    material_counts[mat] = material_counts.get(mat, 0) + 1

        return {
            "status": "success",
            "initialized": self.model_initialized,
            "dimensions": {
                "length_x": float(self.params.L_x),
                "length_y": float(self.params.L_y),
                "length_z": float(self.params.L_z)
            },
            "grid_size": {
                "N_x": int(self.params.N_x),
                "N_y": int(self.params.N_y),
                "N_z": int(self.params.N_z)
            },
            "resolution": float(self.params.ds),
            "total_voxels": int(self.params.N_x * self.params.N_y * self.params.N_z),
            "voxel_counts_by_type": material_counts,
            "air_zones": len(self.modele.zones_air)
        }


# Instance globale du builder
builder = HouseModelBuilder()

# Créer le serveur MCP
app = Server("house-3d-model-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Liste tous les outils disponibles."""
    return [
        Tool(
            name="initialize_model",
            description="Initialise un nouveau modèle 3D de maison avec des dimensions spécifiées",
            inputSchema={
                "type": "object",
                "properties": {
                    "length_x": {
                        "type": "number",
                        "description": "Longueur en mètres (axe X)"
                    },
                    "length_y": {
                        "type": "number",
                        "description": "Largeur en mètres (axe Y)"
                    },
                    "length_z": {
                        "type": "number",
                        "description": "Hauteur en mètres (axe Z)"
                    },
                    "resolution": {
                        "type": "number",
                        "description": "Résolution de la grille en mètres (taille d'un voxel, défaut: 0.1)",
                        "default": 0.1
                    }
                },
                "required": ["length_x", "length_y", "length_z"]
            }
        ),
        Tool(
            name="add_volume",
            description="Ajoute un volume rectangulaire avec un matériau spécifique au modèle",
            inputSchema={
                "type": "object",
                "properties": {
                    "x1": {"type": "number", "description": "Coordonnée X du premier coin (mètres)"},
                    "y1": {"type": "number", "description": "Coordonnée Y du premier coin (mètres)"},
                    "z1": {"type": "number", "description": "Coordonnée Z du premier coin (mètres)"},
                    "x2": {"type": "number", "description": "Coordonnée X du second coin (mètres)"},
                    "y2": {"type": "number", "description": "Coordonnée Y du second coin (mètres)"},
                    "z2": {"type": "number", "description": "Coordonnée Z du second coin (mètres)"},
                    "material": {
                        "type": "string",
                        "description": "Nom du matériau (AIR, PARPAING, PLACO, LAINE_VERRE, BETON, TERRE, etc.)"
                    }
                },
                "required": ["x1", "y1", "z1", "x2", "y2", "z2", "material"]
            }
        ),
        Tool(
            name="list_materials",
            description="Liste tous les matériaux disponibles avec leurs propriétés thermiques",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="export_to_json",
            description="Exporte le modèle complet en JSON avec la géométrie (vertex3D) et les voxels matériaux",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Chemin du fichier de sortie (optionnel)"
                    }
                }
            }
        ),
        Tool(
            name="get_model_info",
            description="Retourne les informations sur le modèle actuel (dimensions, nombre de voxels, etc.)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Gère les appels d'outils."""

    try:
        if name == "initialize_model":
            result = builder.initialize_model(
                length_x=arguments["length_x"],
                length_y=arguments["length_y"],
                length_z=arguments["length_z"],
                resolution=arguments.get("resolution", 0.1)
            )
        elif name == "add_volume":
            result = builder.add_volume(
                x1=arguments["x1"], y1=arguments["y1"], z1=arguments["z1"],
                x2=arguments["x2"], y2=arguments["y2"], z2=arguments["z2"],
                material=arguments["material"]
            )
        elif name == "list_materials":
            result = builder.list_materials()
        elif name == "export_to_json":
            result = builder.export_to_json(
                filepath=arguments.get("filepath")
            )
        elif name == "get_model_info":
            result = builder.get_model_info()
        else:
            result = {"status": "error", "message": f"Outil '{name}' inconnu"}

        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    except Exception as e:
        error_result = {"status": "error", "message": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def main():
    """Point d'entrée principal du serveur."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
