#!/usr/bin/env python3
"""Démonstration automatique de l'interface."""
import sys
sys.path.insert(0, '/home/user/HeatSimulation')
from mcp_server import HouseModelBuilder

print("\n" + "="*60)
print("  DÉMONSTRATION - Création automatique d'une maison")
print("="*60 + "\n")

builder = HouseModelBuilder()

print("1️⃣  Initialisation d'un modèle 8x6x3m...")
builder.initialize_model(8.0, 6.0, 3.0, 0.1)

print("\n2️⃣  Ajout de l'air intérieur...")
builder.add_volume(0.2, 0.2, 0.2, 7.8, 5.8, 2.8, "AIR")

print("\n3️⃣  Construction des murs en PARPAING...")
builder.add_volume(0.0, 0.0, 0.0, 0.2, 6.0, 3.0, "PARPAING")
builder.add_volume(7.8, 0.0, 0.0, 8.0, 6.0, 3.0, "PARPAING")
builder.add_volume(0.0, 0.0, 0.0, 8.0, 0.2, 3.0, "PARPAING")
builder.add_volume(0.0, 5.8, 0.0, 8.0, 6.0, 3.0, "PARPAING")

print("\n4️⃣  Ajout du sol en BETON...")
builder.add_volume(0.0, 0.0, 0.0, 8.0, 6.0, 0.2, "BETON")

print("\n5️⃣  Ajout du plafond en PLACO...")
builder.add_volume(0.0, 0.0, 2.8, 8.0, 6.0, 3.0, "PLACO")

print("\n6️⃣  Export du modèle...")
result = builder.export_to_json("demo_maison.json")

print("\n" + "="*60)
print("✅ MAISON CRÉÉE AVEC SUCCÈS!")
print("="*60)
print(f"\n📊 Statistiques:")
print(f"   - Fichier: demo_maison.json")
print(f"   - Total voxels: {result['model']['statistics']['total_voxels']:,}")
print(f"   - Voxels matériaux: {result['model']['statistics']['non_air_voxels']:,}")
print(f"   - Dimensions: 8m x 6m x 3m")
print(f"   - Résolution: 0.1m (10cm)\n")

# Info du modèle
info = builder.get_model_info()
print(f"📦 Composition:")
for mat_type, count in info['voxel_counts_by_type'].items():
    pct = (count / info['total_voxels']) * 100
    print(f"   - {mat_type}: {count:,} voxels ({pct:.1f}%)")

print("\n" + "="*60 + "\n")
