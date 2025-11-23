#!/usr/bin/env python3
"""
Interface interactive pour construire des modèles 3D de maisons.
Alternative simple au serveur MCP pour utilisation directe.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import HouseModelBuilder
import json


def menu_principal():
    """Affiche le menu principal."""
    print("\n" + "="*60)
    print("  CONSTRUCTEUR INTERACTIF DE MODÈLES 3D DE MAISONS")
    print("="*60)
    print("\n1. Créer un nouveau modèle")
    print("2. Ajouter un volume")
    print("3. Lister les matériaux disponibles")
    print("4. Voir les informations du modèle")
    print("5. Exporter en JSON")
    print("6. Exemples prédéfinis")
    print("0. Quitter")
    print("\n" + "="*60)


def creer_modele(builder):
    """Interface pour créer un nouveau modèle."""
    print("\n--- Création d'un nouveau modèle ---")
    try:
        length_x = float(input("Longueur X (m) [défaut: 10]: ") or "10")
        length_y = float(input("Largeur Y (m) [défaut: 8]: ") or "8")
        length_z = float(input("Hauteur Z (m) [défaut: 3]: ") or "3")
        resolution = float(input("Résolution (m) [défaut: 0.1]: ") or "0.1")

        result = builder.initialize_model(length_x, length_y, length_z, resolution)
        print("\n✓ Modèle créé avec succès!")
        print(json.dumps(result, indent=2))
        return True
    except Exception as e:
        print(f"\n✗ Erreur: {e}")
        return False


def ajouter_volume(builder):
    """Interface pour ajouter un volume."""
    if not builder.model_initialized:
        print("\n✗ Veuillez d'abord créer un modèle (option 1)")
        return

    print("\n--- Ajout d'un volume ---")
    print("Exemples de matériaux: AIR, PARPAING, PLACO, BETON, LAINE_VERRE")
    print("(Utilisez l'option 3 pour voir tous les matériaux)\n")

    try:
        x1 = float(input("X1 (m): "))
        y1 = float(input("Y1 (m): "))
        z1 = float(input("Z1 (m): "))
        x2 = float(input("X2 (m): "))
        y2 = float(input("Y2 (m): "))
        z2 = float(input("Z2 (m): "))
        material = input("Matériau: ").strip().upper()

        result = builder.add_volume(x1, y1, z1, x2, y2, z2, material)

        if result["status"] == "success":
            print("\n✓ Volume ajouté avec succès!")
        else:
            print(f"\n✗ Erreur: {result['message']}")
            if "available_materials" in result:
                print("\nMatériaux disponibles:")
                for mat in result["available_materials"]:
                    print(f"  - {mat}")
    except Exception as e:
        print(f"\n✗ Erreur: {e}")


def lister_materiaux(builder):
    """Affiche tous les matériaux disponibles."""
    print("\n--- Matériaux disponibles ---\n")
    result = builder.list_materials()

    for nom, props in sorted(result["materials"].items()):
        print(f"• {nom}")
        print(f"  Type: {props['type']}")
        print(f"  Conductivité thermique (λ): {props['conductivite_thermique_W_mK']} W/mK")
        print(f"  Masse volumique (ρ): {props['masse_volumique_kg_m3']} kg/m³")
        print(f"  Capacité thermique (cp): {props['capacite_thermique_J_kgK']} J/kgK")
        if "diffusivite_m2_s" in props:
            print(f"  Diffusivité (α): {props['diffusivite_m2_s']:.2e} m²/s")
        print()


def info_modele(builder):
    """Affiche les informations du modèle."""
    result = builder.get_model_info()
    print("\n--- Informations du modèle ---")
    print(json.dumps(result, indent=2))


def exporter_json(builder):
    """Exporte le modèle en JSON."""
    if not builder.model_initialized:
        print("\n✗ Veuillez d'abord créer un modèle (option 1)")
        return

    print("\n--- Export JSON ---")
    filename = input("Nom du fichier [défaut: modele_3d.json]: ").strip() or "modele_3d.json"

    try:
        result = builder.export_to_json(filename)
        if result["status"] == "success":
            print(f"\n✓ Modèle exporté vers: {filename}")
            stats = result['model']['statistics']
            print(f"  - Total voxels: {stats['total_voxels']}")
            print(f"  - Voxels non-air: {stats['non_air_voxels']}")
        else:
            print(f"\n✗ Erreur: {result['message']}")
    except Exception as e:
        print(f"\n✗ Erreur: {e}")


def exemples_predefinis(builder):
    """Charge un exemple prédéfini."""
    print("\n--- Exemples prédéfinis ---")
    print("1. Maison simple (10x8x3m)")
    print("2. Maison isolée (12x10x6m)")
    print("3. Pièce avec fenêtre")
    print("0. Retour")

    choix = input("\nVotre choix: ").strip()

    if choix == "1":
        print("\nCréation d'une maison simple...")
        builder.initialize_model(10.0, 8.0, 3.0, 0.1)

        # Air intérieur
        builder.add_volume(0.2, 0.2, 0.2, 9.8, 7.8, 2.8, "AIR")

        # Murs
        builder.add_volume(0.0, 0.0, 0.0, 0.2, 8.0, 3.0, "PARPAING")
        builder.add_volume(9.8, 0.0, 0.0, 10.0, 8.0, 3.0, "PARPAING")
        builder.add_volume(0.0, 0.0, 0.0, 10.0, 0.2, 3.0, "PARPAING")
        builder.add_volume(0.0, 7.8, 0.0, 10.0, 8.0, 3.0, "PARPAING")

        # Plafond et sol
        builder.add_volume(0.0, 0.0, 2.8, 10.0, 8.0, 3.0, "PLACO")
        builder.add_volume(0.0, 0.0, 0.0, 10.0, 8.0, 0.2, "BETON")

        print("✓ Maison simple créée!")

    elif choix == "2":
        print("\nCréation d'une maison isolée...")
        builder.initialize_model(12.0, 10.0, 6.0, 0.1)

        # Air
        builder.add_volume(0.3, 0.3, 0.3, 11.7, 9.7, 5.7, "AIR")

        # Murs composites
        builder.add_volume(0.0, 0.0, 0.0, 0.3, 10.0, 6.0, "MUR_COMPOSITE_EXT")
        builder.add_volume(11.7, 0.0, 0.0, 12.0, 10.0, 6.0, "MUR_COMPOSITE_EXT")
        builder.add_volume(0.0, 0.0, 0.0, 12.0, 0.3, 6.0, "MUR_COMPOSITE_EXT")
        builder.add_volume(0.0, 9.7, 0.0, 12.0, 10.0, 6.0, "MUR_COMPOSITE_EXT")

        # Sol multicouche
        builder.add_volume(0.0, 0.0, 0.0, 12.0, 10.0, 0.1, "POLYSTYRENE")
        builder.add_volume(0.0, 0.0, 0.1, 12.0, 10.0, 0.3, "BETON")

        # Plafond
        builder.add_volume(0.0, 0.0, 5.7, 12.0, 10.0, 5.8, "PLACO")
        builder.add_volume(0.0, 0.0, 5.8, 12.0, 10.0, 6.0, "LAINE_VERRE")

        print("✓ Maison isolée créée!")

    elif choix == "3":
        print("\nCréation d'une pièce avec fenêtre...")
        builder.initialize_model(5.0, 4.0, 2.7, 0.1)

        # Air intérieur
        builder.add_volume(0.2, 0.2, 0.2, 4.8, 3.8, 2.5, "AIR")

        # Murs
        builder.add_volume(0.0, 0.0, 0.0, 0.2, 4.0, 2.7, "PARPAING")
        builder.add_volume(4.8, 0.0, 0.0, 5.0, 4.0, 2.7, "PARPAING")

        # Mur avant avec fenêtre
        builder.add_volume(0.0, 0.0, 0.0, 5.0, 0.2, 2.7, "PARPAING")
        # Fenêtre (air extérieur simulé)
        builder.add_volume(1.5, 0.0, 1.0, 3.5, 0.2, 2.0, "LIMITE_FIXE")

        # Mur arrière
        builder.add_volume(0.0, 3.8, 0.0, 5.0, 4.0, 2.7, "PARPAING")

        # Sol et plafond
        builder.add_volume(0.0, 0.0, 0.0, 5.0, 4.0, 0.2, "BETON")
        builder.add_volume(0.0, 0.0, 2.5, 5.0, 4.0, 2.7, "PLACO")

        print("✓ Pièce avec fenêtre créée!")


def main():
    """Fonction principale."""
    builder = HouseModelBuilder()

    while True:
        menu_principal()
        choix = input("Votre choix: ").strip()

        if choix == "1":
            creer_modele(builder)
        elif choix == "2":
            ajouter_volume(builder)
        elif choix == "3":
            lister_materiaux(builder)
        elif choix == "4":
            info_modele(builder)
        elif choix == "5":
            exporter_json(builder)
        elif choix == "6":
            exemples_predefinis(builder)
        elif choix == "0":
            print("\nAu revoir!")
            break
        else:
            print("\n✗ Choix invalide!")

        input("\nAppuyez sur Entrée pour continuer...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterruption par l'utilisateur. Au revoir!")
    except Exception as e:
        print(f"\n✗ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
