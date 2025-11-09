from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import copy
import numpy as np
import pyvista as pv


class Visualisation:
    """Gère la visualisation 3D des résultats avec PyVista."""

    def __init__(self, simulation):
        self.simulation = simulation
        self.modele = simulation.modele
        self.params = simulation.params
        self.stockage = simulation.stockage
        self.logger = LoggerSimulation(niveau="DEBUG")

        self.logger.info("Visualiseur PyVista initialisé.")

    def _creer_grille_pyvista(self):
        """Crée l'objet grille (ImageData) PyVista."""
        # Crée une grille uniforme (plus approprié pour nos données)
        # pv.ImageData est un alias pour pv.UniformGrid
        grid = pv.ImageData()

        # Définit les dimensions (nombre de points)
        grid.dimensions = (self.params.N_x, self.params.N_y, self.params.N_z)

        # Définit l'espacement physique (important pour les proportions)
        grid.spacing = (self.params.ds, self.params.ds, self.params.ds)

        # On peut aussi définir l'origine (par défaut (0,0,0) ce qui est ok)
        grid.origin = (0.0, 0.0, 0.0)
        return grid

    def visualiser_structure(self, downsample_factor=1):
        """
        Affiche la structure 3D (matériaux) du modèle.
        Affiche les solides (alpha >= 0) et cache l'air (alpha < 0).
        """
        self.logger.info(f"Visualisation de la structure (downsample x{downsample_factor})...")

        grid = self._creer_grille_pyvista()

        # Attache les données de 'Alpha' aux points
        # .ravel('F') est crucial pour l'ordre des données (Fortran vs C)
        # --- CORRECTION (ValueError) ---
        # Nos données (11x11x11) sont aux 'points' (noeuds),
        # pas aux 'cellules' (10x10x10).
        grid.point_data["alpha"] = self.modele.Alpha.ravel(order='F')

        # Downsample si nécessaire
        if downsample_factor > 1:
            voi = (0, self.params.N_x - 1, 0, self.params.N_y - 1, 0, self.params.N_z - 1)
            rate = (downsample_factor, downsample_factor, downsample_factor)
            grid = grid.extract_subset(voi, rate=rate)

        # Filtre : ne garde que les cellules solides (alpha >= 0)
        # Le 'threshold' fonctionnera sur les 'point_data'
        solides = grid.threshold(0.0, scalars="alpha")

        # Configuration du Plotter
        plotter = pv.Plotter(window_size=[800, 600])
        plotter.add_mesh(
            solides,
            scalars="alpha",
            cmap="viridis",  # Colormap pour les matériaux
            opacity="linear",  # Opacité basée sur la valeur alpha
            scalar_bar_args={'title': 'Diffusivité Alpha'}
        )
        plotter.add_axes_at_origin()

        self.logger.info("Affichage de la fenêtre PyVista (structure)...")
        plotter.show()

    def visualiser_surfaces_convection(self):
        """
        [VALIDATION] Affiche les murs (gris) et les surfaces
        de convection détectées (points rouges).
        """
        self.logger.info("Visualisation des surfaces de convection...")

        # 1. Créer la grille de base pour les murs (solides)
        grid = self._creer_grille_pyvista()
        # --- CORRECTION (ValueError) ---
        # Mettre les données sur les 'points', comme ci-dessus
        grid.point_data["alpha"] = self.modele.Alpha.ravel(order='F')
        solides = grid.threshold(0.0, scalars="alpha")

        # 2. Créer un objet PyVista pour les points de surface
        points_surface_m = []
        ds = self.params.ds
        for zone_id, indices_np in self.modele.surfaces_convection_np.items():
            # Convertir les indices (i,j,k) en coordonnées (x,y,z)
            coords_m = indices_np * ds
            points_surface_m.extend(coords_m)

        if not points_surface_m:
            self.logger.warn("Aucun point de surface à visualiser.")
            return

        nuage_points = pv.PolyData(np.array(points_surface_m))

        # 3. Affichage
        plotter = pv.Plotter(window_size=[800, 600])
        # Afficher les murs en gris transparent
        plotter.add_mesh(solides, color='gray', opacity=0.1)
        # Afficher les points de surface en rouge vif
        plotter.add_mesh(nuage_points, color='red', point_size=10, render_points_as_spheres=True)

        plotter.add_axes_at_origin()
        self.logger.info("Affichage (Validation): Murs (gris) et Surfaces de Convection (rouge)...")
        plotter.show()

    def visualiser_resultat(self, etape_index=-1, downsample_factor=1,
                            temp_min=0.0, temp_max=20.0):
        """
        Affiche la "heatmap" 3D (rendu volumétrique) pour une étape donnée.

        etape_index (int): Index de l'étape à charger (-1 pour la dernière).
        temp_min/max (float): Plage de T° pour la colormap.
        """

        # 1. Charger les données depuis le disque
        etat = self.stockage.charger_etape(etape_index)
        if etat is None:
            self.logger.error("Impossible de charger l'étape pour la visualisation.")
            return

        temps_s = etat["temps_s"]
        matrice_T = etat["matrice_T"]
        T_zones = etat["T_zones"]
        self.logger.info(f"Visualisation du résultat t={temps_s:.1f}s (downsample x{downsample_factor})...")
        self.logger.info(f"  Températures de l'air: {T_zones}")

        # 2. Préparer la grille PyVista
        grid = self._creer_grille_pyvista()

        # Remplacer la T° des zones d'air (qui est T=0 dans la matrice T)
        # par la T° réelle de la zone (nœud)
        for zone_id, T_zone in T_zones.items():
            matrice_T[self.modele.Alpha == zone_id] = T_zone

        # Attache les données de Température aux points
        grid.point_data["temp"] = matrice_T.ravel(order='F')

        # 3. Downsample (si demandé)
        if downsample_factor > 1:
            # On définit le 'Volume Of Interest' (le volume complet)
            voi = (0, self.params.N_x - 1,
                   0, self.params.N_y - 1,
                   0, self.params.N_z - 1)

            # On définit le taux d'échantillonnage (ex: (2, 2, 2))
            rate = (downsample_factor, downsample_factor, downsample_factor)

            # --- CORRECTION (TypeError) ---
            # L'argument est 'rate', pas 'sample_rate'
            grid = grid.extract_subset(voi, rate=rate)

        # 4. Lancer la visualisation
        plotter = pv.Plotter(window_size=[800, 600])

        # Définir la colormap (Bleu -> Blanc -> Rouge)
        cmap = "coolwarm"

        # Définir la carte d'opacité (transparence)
        milieu = (temp_min + temp_max) / 2
        # Opacité: 0.8 (froid), 0.0 (milieu), 0.8 (chaud)
        # --- CORRECTION (AttributeError) ---
        # pv.OpacityMap n'existe pas, on utilise la liste directement
        opacity_map = [0.8, 0.0, 0.8]

        # Ajouter le volume (heatmap 3D)
        plotter.add_volume(
            grid,
            scalars="temp",
            cmap=cmap,
            opacity=opacity_map,
            scalar_bar_args={'title': 'Température (°C)'},
            # --- CORRECTION (AttributeError) ---
            # Spécifie la plage de température (color limits) ici
            clim=[temp_min, temp_max]
        )

        plotter.add_axes_at_origin()

        self.logger.info(f"Lancement de la visualisation PyVista (heatmap)...")
        plotter.show()




