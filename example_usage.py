#!/usr/bin/env python3
"""
Script d'exemple montrant comment utiliser le serveur MCP 3D House Model Builder.
"""

import sys
from pathlib import Path

# Ajouter le répertoire au path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import HouseModelBuilder
import json


def exemple_maison_simple():
    """Exemple 1 : Maison simple avec murs, sol et air intérieur."""
    print("=" * 60)
    print("EXEMPLE 1 : Maison Simple")
    print("=" * 60)

    builder = HouseModelBuilder()

    # 1. Initialiser le modèle (10m x 8m x 3m)
    print("\n1. Initialisation du modèle...")
    result = builder.initialize_model(
        length_x=10.0,
        length_y=8.0,
        length_z=3.0,
        resolution=0.1  # 10cm par voxel
    )
    print(json.dumps(result, indent=2))

    # 2. Créer le volume d'air intérieur
    print("\n2. Ajout du volume d'air intérieur...")
    result = builder.add_volume(
        x1=0.2, y1=0.2, z1=0.2,
        x2=9.8, y2=7.8, z2=2.8,
        material="AIR"
    )
    print(json.dumps(result, indent=2))

    # 3. Créer les murs
    print("\n3. Ajout des murs en parpaing...")

    # Mur gauche
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.0,
        x2=0.2, y2=8.0, z2=3.0,
        material="PARPAING"
    )

    # Mur droit
    builder.add_volume(
        x1=9.8, y1=0.0, z1=0.0,
        x2=10.0, y2=8.0, z2=3.0,
        material="PARPAING"
    )

    # Mur avant
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.0,
        x2=10.0, y2=0.2, z2=3.0,
        material="PARPAING"
    )

    # Mur arrière
    builder.add_volume(
        x1=0.0, y1=7.8, z1=0.0,
        x2=10.0, y2=8.0, z2=3.0,
        material="PARPAING"
    )

    # Plafond
    builder.add_volume(
        x1=0.0, y1=0.0, z1=2.8,
        x2=10.0, y2=8.0, z2=3.0,
        material="PLACO"
    )

    # Sol
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.0,
        x2=10.0, y2=8.0, z2=0.2,
        material="BETON"
    )

    print("Murs, plafond et sol ajoutés.")

    # 4. Afficher les infos du modèle
    print("\n4. Informations sur le modèle...")
    info = builder.get_model_info()
    print(json.dumps(info, indent=2))

    # 5. Exporter en JSON
    print("\n5. Export du modèle en JSON...")
    result = builder.export_to_json("maison_simple.json")
    if result["status"] == "success":
        print(f"✓ Modèle exporté vers : maison_simple.json")
        print(f"  - Total voxels : {result['model']['statistics']['total_voxels']}")
        print(f"  - Voxels non-air : {result['model']['statistics']['non_air_voxels']}")
    else:
        print(f"✗ Erreur : {result['message']}")


def exemple_maison_isolee():
    """Exemple 2 : Maison avec isolation thermique."""
    print("\n" + "=" * 60)
    print("EXEMPLE 2 : Maison avec Isolation")
    print("=" * 60)

    builder = HouseModelBuilder()

    # 1. Initialiser le modèle (12m x 10m x 6m - maison à étage)
    print("\n1. Initialisation du modèle...")
    result = builder.initialize_model(
        length_x=12.0,
        length_y=10.0,
        length_z=6.0,
        resolution=0.1
    )
    print(json.dumps(result, indent=2))

    # 2. Volume d'air intérieur
    print("\n2. Ajout du volume d'air intérieur...")
    builder.add_volume(
        x1=0.3, y1=0.3, z1=0.3,
        x2=11.7, y2=9.7, z2=5.7,
        material="AIR"
    )

    # 3. Murs composites extérieurs (déjà isolés)
    print("\n3. Ajout des murs composites isolés...")

    # Mur gauche
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.0,
        x2=0.3, y2=10.0, z2=6.0,
        material="MUR_COMPOSITE_EXT"
    )

    # Mur droit
    builder.add_volume(
        x1=11.7, y1=0.0, z1=0.0,
        x2=12.0, y2=10.0, z2=6.0,
        material="MUR_COMPOSITE_EXT"
    )

    # Mur avant
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.0,
        x2=12.0, y2=0.3, z2=6.0,
        material="MUR_COMPOSITE_EXT"
    )

    # Mur arrière
    builder.add_volume(
        x1=0.0, y1=9.7, z1=0.0,
        x2=12.0, y2=10.0, z2=6.0,
        material="MUR_COMPOSITE_EXT"
    )

    # 4. Sol multicouche
    print("\n4. Ajout du sol multicouche...")

    # Terre sous le sol
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.0,
        x2=12.0, y2=10.0, z2=0.05,
        material="TERRE"
    )

    # Isolation polystyrène
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.05,
        x2=12.0, y2=10.0, z2=0.15,
        material="POLYSTYRENE"
    )

    # Dalle béton
    builder.add_volume(
        x1=0.0, y1=0.0, z1=0.15,
        x2=12.0, y2=10.0, z2=0.3,
        material="BETON"
    )

    # 5. Plafond/toit
    print("\n5. Ajout du plafond isolé...")

    # Placo intérieur
    builder.add_volume(
        x1=0.0, y1=0.0, z1=5.7,
        x2=12.0, y2=10.0, z2=5.75,
        material="PLACO"
    )

    # Isolation laine de verre
    builder.add_volume(
        x1=0.0, y1=0.0, z1=5.75,
        x2=12.0, y2=10.0, z2=5.95,
        material="LAINE_VERRE"
    )

    # Couverture extérieure
    builder.add_volume(
        x1=0.0, y1=0.0, z1=5.95,
        x2=12.0, y2=10.0, z2=6.0,
        material="PLACO"  # Simplifié
    )

    # 6. Afficher les infos
    print("\n6. Informations sur le modèle...")
    info = builder.get_model_info()
    print(json.dumps(info, indent=2))

    # 7. Exporter
    print("\n7. Export du modèle en JSON...")
    result = builder.export_to_json("maison_isolee.json")
    if result["status"] == "success":
        print(f"✓ Modèle exporté vers : maison_isolee.json")
        print(f"  - Total voxels : {result['model']['statistics']['total_voxels']}")
        print(f"  - Voxels non-air : {result['model']['statistics']['non_air_voxels']}")


def exemple_liste_materiaux():
    """Exemple 3 : Lister tous les matériaux disponibles."""
    print("\n" + "=" * 60)
    print("EXEMPLE 3 : Liste des Matériaux")
    print("=" * 60)

    builder = HouseModelBuilder()
    result = builder.list_materials()

    print("\nMatériaux disponibles :\n")
    for nom, props in result["materials"].items():
        print(f"• {nom}")
        print(f"  Type : {props['type']}")
        print(f"  λ (conductivité) : {props['conductivite_thermique_W_mK']} W/mK")
        print(f"  ρ (masse volumique) : {props['masse_volumique_kg_m3']} kg/m³")
        print(f"  cp (capacité thermique) : {props['capacite_thermique_J_kgK']} J/kgK")
        if "diffusivite_m2_s" in props:
            print(f"  α (diffusivité) : {props['diffusivite_m2_s']:.2e} m²/s")
        print()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║  EXEMPLES D'UTILISATION - MCP 3D House Model Builder  ║")
    print("╚" + "=" * 58 + "╝")

    # Exécuter les exemples
    exemple_liste_materiaux()
    exemple_maison_simple()
    exemple_maison_isolee()

    print("\n" + "=" * 60)
    print("✓ Tous les exemples ont été exécutés avec succès !")
    print("=" * 60)
    print("\nFichiers générés :")
    print("  - maison_simple.json")
    print("  - maison_isolee.json")
    print("\nVous pouvez maintenant examiner ces fichiers JSON.")
    print()
