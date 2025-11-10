# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import numpy as np
import pyvista as pv


class Visualisation:
    """Gère la visualisation 3D des résultats avec PyVista."""

    def __init__(self, simulation):
        """Initialise le visualiseur en liant la simulation."""
        self.simulation = simulation
        self.modele = simulation.modele
        self.stockage = simulation.stockage
        self.params = simulation.params
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
        Affiche la structure 3D des *matériaux* (basée sur Alpha).
        Ne montre que les solides (alpha >= 0).
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
            voi = (0, self.params.N_x - 1,
                   0, self.params.N_y - 1,
                   0, self.params.N_z - 1)
            rate = (downsample_factor, downsample_factor, downsample_factor)
            grid = grid.extract_subset(voi, rate=rate)

        # Filtre : ne garde que les cellules solides (alpha >= 0)
        # Le 'threshold' fonctionnera sur les 'point_data'
        solides = grid.threshold(0.0, scalars="alpha")

        # Configuration du Plotter
        plotter = pv.Plotter(window_size=[800, 600])
        plotter.add_mesh(solides, cmap="bone", opacity=0.5)
        plotter.add_axes_at_origin()

        # --- CORRECTION (AttributeError) ---
        # La bonne méthode est 'enable_zoom_style', mais le
        # comportement par défaut (trackball) est meilleur.
        # On supprime la ligne.
        # plotter.enable_zoom_scaling()

        self.logger.info("Affichage de la fenêtre PyVista (structure)...")
        plotter.show()

    def visualiser_surfaces_convection(self):
        """
        (Outil de Validation) Affiche les solides en gris et les
        surfaces de convection détectées en points rouges.
        """
        self.logger.info("Visualisation des surfaces de convection...")

        # 1. Créer la grille de base pour les murs (solides)
        grid = self._creer_grille_pyvista()
        # --- CORRECTION (ValueError) ---
        # Mettre les données sur les 'points', comme ci-dessus
        grid.point_data["alpha"] = self.modele.Alpha.ravel(order='F')
        solides = grid.threshold(0.0, scalars="alpha")

        # 2. Créer un objet PyVista pour les points de surface
        points_surface_vis = pv.PolyData()
        tous_points = np.array([], dtype=np.int64).reshape(0, 3)

        ds = self.params.ds

        for id_zone, indices_tuple in self.modele.surfaces_convection_idx.items():
            if indices_tuple[0].size > 0:
                # Convertit les indices (i,j,k) en coordonnées (x,y,z)
                i, j, k = indices_tuple
                points_m = np.vstack((i * ds, j * ds, k * ds)).T
                tous_points = np.vstack((tous_points, points_m))

        if tous_points.shape[0] == 0:
            self.logger.warn("Aucun point de surface à visualiser.")
            # Ne pas s'arrêter, afficher quand même les murs
            # return

        # 3. Afficher les deux
        plotter = pv.Plotter(window_size=[800, 600])
        # Les murs en gris transparent
        plotter.add_mesh(solides, cmap="bone", opacity=0.1)

        # Les points de surface en rouge vif (seulement s'il y en a)
        if tous_points.shape[0] > 0:
            points_surface_vis.points = tous_points
            plotter.add_mesh(points_surface_vis, color='red',
                             point_size=10, render_points_as_spheres=True)

        plotter.add_axes_at_origin()
        # --- CORRECTION (AttributeError) ---
        # On supprime la ligne.
        # plotter.enable_zoom_scaling()

        self.logger.info("Affichage (Validation): Murs (gris) et Surfaces de Convection (rouge)...")
        plotter.show()

    def visualiser_resultat(self, etape_index=-1, downsample_factor=1,
                            temp_min=0.0, temp_max=20.0):
        """
        Affiche une "heatmap" 3D (rendu volumétrique) pour une étape
        de la simulation.

        Rend les températures moyennes (autour de (min+max)/2) transparentes.
        """

        # 1. Charger les données de l'étape
        etat = self.stockage.charger_etape(etape_index)
        if etat is None:
            return

        temps_s = etat["temps_s"]
        matrice_T = etat["matrice_T"]
        temps_air = etat["temps_air"]

        self.logger.info(f"Visualisation du résultat t={temps_s:.1f}s (downsample x{downsample_factor})...")
        self.logger.info(f"  Températures de l'air: {temps_air}")

        # 2. Créer la grille PyVista
        grid = self._creer_grille_pyvista()

        # Remplacer les T° des zones d'air (qui sont à 0 dans la matrice T)
        # par leur vraie température (stockée dans temps_air)
        for id_zone, T_air in temps_air.items():
            masque_air_zone = (self.modele.Alpha == id_zone)
            matrice_T[masque_air_zone] = T_air

        # Attacher les données de température aux points
        grid.point_data["temp"] = matrice_T.ravel(order='F')

        # 3. Downsample (si demandé)
        if downsample_factor > 1:
            # 'sample' est la mauvaise fonction. La bonne est 'extract_subset'.
            # On définit le 'Volume Of Interest' (le volume complet)
            voi = (0, self.params.N_x - 1,
                   0, self.params.N_y - 1,
                   0, self.params.N_z - 1)

            # On définit le taux d'échantillonnage (ex: (2, 2, 2))
            # --- CORRECTION (TypeError) ---
            # L'argument est 'rate', pas 'sample_rate'
            rate = (downsample_factor, downsample_factor, downsample_factor)

            grid = grid.extract_subset(voi, rate=rate)

        # 4. Lancer la visualisation
        plotter = pv.Plotter(window_size=[800, 600])

        # Créer la colormap (Bleu -> Blanc -> Rouge)
        cmap = "coolwarm"

        # Créer la carte d'opacité
        # On veut: Min=Opaque, Milieu=Transparent, Max=Opaque
        milieu = (temp_min + temp_max) / 2.0
        # --- CORRECTION (AttributeError) ---
        # pv.OpacityMap n'existe pas, on crée la liste manuellement
        opacity_map = [0.8, 0.0, 0.8]

        # Ajouter le volume
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
        # --- CORRECTION (AttributeError) ---
        # On supprime la ligne.
        # plotter.enable_zoom_scaling()

        self.logger.info("Lancement de la visualisation PyVista (heatmap)...")
        plotter.show()



