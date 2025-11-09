#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fichier: visualisation.py
# Généré par le dispatcher de simulation_objet.py

from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import numpy as np
import pyvista as pv

# --- Début des Blocs de Code ---

class Visualisation:
    """
    Gère la création de visualisations 3D interactives
    avec PyVista.
    """

    def __init__(self, simulation):
        self.modele = simulation.modele
        self.stockage = simulation.stockage
        self.params = simulation.params
        self.logger = LoggerSimulation(niveau="DEBUG")

        self.logger.info("Visualiseur PyVista initialisé.")

    def _creer_grille_pyvista(self):
        """Crée l'objet grille (ImageData) PyVista."""
        # pv.ImageData est l'alias de pv.UniformGrid, plus stable
        grid = pv.ImageData()

        # Définit les dimensions (nombre de points)
        grid.dimensions = (self.params.N_x, self.params.N_y, self.params.N_z)

        # Définit l'espacement physique (important pour les proportions)
        grid.spacing = (self.params.ds, self.params.ds, self.params.ds)

        grid.origin = (0.0, 0.0, 0.0)
        return grid

    def visualiser_structure(self, downsample_factor=1):
        """
        Affiche la structure 3D (les matériaux).
        Utilise un 'threshold' pour cacher l'air (alpha < 0).
        """
        self.logger.info(f"Visualisation de la structure (downsample x{downsample_factor})...")

        grid = self._creer_grille_pyvista()

        # Attache les données de 'Alpha' aux cellules
        # .ravel('F') est crucial pour l'ordre des données (Fortran vs C)
        grid.cell_data["alpha"] = self.modele.Alpha.ravel(order='F')

        # Downsample si nécessaire
        if downsample_factor > 1:
            voi = (0, self.params.N_x - 1, 0, self.params.N_y - 1, 0, self.params.N_z - 1)
            rate = (downsample_factor, downsample_factor, downsample_factor)
            grid = grid.extract_subset(voi, rate=rate)

        # Filtre : ne garde que les cellules solides (alpha >= 0)
        solides = grid.threshold(0.0, scalars="alpha")

        # Configuration du Plotter
        plotter = pv.Plotter(window_size=[800, 600])
        plotter.add_mesh(solides, scalars="alpha", cmap="viridis",
                         scalar_bar_args={'title': 'Diffusivité Alpha'})
        plotter.add_axes_at_origin()

        self.logger.info("Affichage de la fenêtre PyVista (structure)...")
        plotter.show()

    def visualiser_surfaces_convection(self):
        """
        (Validation Étape 1) Affiche les surfaces de convection
        détectées en rouge vif.
        """
        self.logger.info("Visualisation des surfaces de convection...")

        # 1. Créer la grille de base pour les murs (solides)
        grid = self._creer_grille_pyvista()
        grid.cell_data["alpha"] = self.modele.Alpha.ravel(order='F')
        solides = grid.threshold(0.0, scalars="alpha")

        # 2. Créer un objet PyVista pour les points de surface
        # On suppose une seule zone (id -1) pour l'instant
        zone_id = -1
        if zone_id not in self.modele.surfaces_convection:
            self.logger.warning("Aucune surface de convection trouvée pour la zone -1.")
            return

        indices = self.modele.surfaces_convection[zone_id]

        if len(indices) == 0:
            self.logger.warning("La liste des surfaces de convection est vide.")
            return

        # Convertit les indices (i,j,k) en coordonnées (x,y,z)
        # Note: PyVista veut les centres des cellules,
        # donc on ajoute 0.5 * ds à l'origine
        ds = self.params.ds
        points_xyz = (indices.astype(np.float64) * ds) + (ds * 0.5)

        # Crée un nuage de points
        surface_points = pv.PolyData(points_xyz)

        # 3. Afficher les deux
        plotter = pv.Plotter(window_size=[800, 600])
        # Les murs en gris transparent
        plotter.add_mesh(solides, style='surface', color='grey', opacity=0.1)
        # Les points de surface en rouge vif
        plotter.add_mesh(surface_points, color='red', point_size=8.0,
                         render_points_as_spheres=True)

        plotter.add_axes_at_origin()
        self.logger.info("Affichage (Validation): Murs (gris) et Surfaces de Convection (rouge)...")
        plotter.show()

    def visualiser_resultat(self, etape_index=-1, downsample_factor=1,
                            temp_min_visu=None, temp_max_visu=None):
        """
        Affiche une "heatmap" 3D volumétrique d'une étape
        de simulation.
        """
        # 1. Charger les données de l'étape
        matrice_T, temps_s, pertes = self.stockage.charger_etape(etape_index)
        if matrice_T is None:
            self.logger.error("Impossible d'afficher le résultat, chargement échoué.")
            return

        self.logger.info(f"Visualisation du résultat t={temps_s:.0f}s (downsample x{downsample_factor})...")

        # 2. Créer la grille PyVista
        grid = self._creer_grille_pyvista()

        # Attache les données de Température aux *points* (noeuds) de la grille
        # Note: PyVista préfère les données aux points pour le volume rendering
        grid.point_data["temp"] = matrice_T.ravel(order='F')

        # 3. Downsample (si demandé)
        if downsample_factor > 1:
            voi = (0, self.params.N_x - 1, 0, self.params.N_y - 1, 0, self.params.N_z - 1)
            rate = (downsample_factor, downsample_factor, downsample_factor)
            grid = grid.extract_subset(voi, rate=rate)

        # 4. Lancer la visualisation
        plotter = pv.Plotter(window_size=[800, 600])

        # Définir la plage de température (clim)
        temp_min = np.min(matrice_T) if temp_min_visu is None else temp_min_visu
        temp_max = np.max(matrice_T) if temp_max_visu is None else temp_max_visu

        # Créer une colormap (bleu -> blanc -> rouge)
        cmap = "coolwarm"

        # Créer une "fonction de transfert d'opacité"
        # 0.0 = transparent, 1.0 = opaque
        # On rend les températures moyennes transparentes
        opacity_map = [0.0, 0.4, 0.0]  # Transparent au milieu
        if temp_max_visu is not None:
            # Si on a une plage définie, on peut faire un V
            milieu = (temp_max + temp_min) / 2
            opacity_map = pv.OpacityMap([temp_min, milieu, temp_max],
                                        [0.8, 0.0, 0.8])

        self.logger.info("Lancement de la visualisation PyVista (heatmap)...")

        # Ajoute le rendu volumétrique
        plotter.add_volume(
            grid,
            scalars="temp",
            cmap=cmap,
            opacity=opacity_map,
            scalar_bar_args={'title': 'Température (°C)'},
            # Spécifie la plage de température (color limits)
            clim=[temp_min, temp_max]
        )

        plotter.add_axes_at_origin()
        plotter.enable_zoom_scaling()  # Permet de zoomer/dézoomer

        self.logger.info("Affichage de la fenêtre PyVista (heatmap)...")
        plotter.show()

