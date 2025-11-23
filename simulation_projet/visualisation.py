# Fichier généré automatiquement par dispatcher_le_projet.py

from logger import LoggerSimulation
from model_data import MATERIAUX
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
        grid = pv.ImageData()
        grid.dimensions = (self.params.N_x, self.params.N_y, self.params.N_z)
        grid.spacing = (self.params.ds, self.params.ds, self.params.ds)
        grid.origin = (0.0, 0.0, 0.0)
        return grid

    # --- SUPPRESSION (Matplotlib) ---
    # La fonction visualiser_structure_en_coupes_2d() a été supprimée.

    # --- NOUVELLE VISUALISATION (Proposition B) ---
    def visualiser_structure_slicer_3d(self):
        """
        Affiche la structure 3D avec un "slicer" (plan de coupe)
        interactif pour voir à l'intérieur.
        """
        self.logger.info("Visualisation de la structure avec Slicer 3D (PyVista)...")

        grid = self._creer_grille_pyvista()
        # On utilise Alpha, car il définit les matériaux
        grid.point_data["alpha"] = self.modele.Alpha.ravel(order='F')

        plotter = pv.Plotter(window_size=[800, 600])

        # Ajoute un "widget" de plan de coupe (slicer)
        plotter.add_mesh_slice_orthogonal(
            grid,
            scalars="alpha",
            cmap="viridis"  # Colormap pour les matériaux
        )

        plotter.add_axes_at_origin()

        self.logger.info("Affichage de la fenêtre PyVista (Slicer)...")
        plotter.show()

    def visualiser_surfaces_convection(self):
        """(Outil de Validation) Affiche les solides et les surfaces de convection."""
        self.logger.info("Visualisation des surfaces de convection...")

        # 1. Grille des murs (solides)
        grid = self._creer_grille_pyvista()
        grid.point_data["alpha"] = self.modele.Alpha.ravel(order='F')
        solides = grid.threshold(0.0, scalars="alpha")

        # 2. Points de surface
        points_surface_vis = pv.PolyData()
        tous_points = np.array([], dtype=np.int64).reshape(0, 3)
        ds = self.params.ds

        for id_zone, indices_tuple in self.modele.surfaces_convection_idx.items():
            if indices_tuple[0].size > 0:
                i, j, k = indices_tuple
                points_m = np.vstack((i * ds, j * ds, k * ds)).T
                tous_points = np.vstack((tous_points, points_m))

        # 3. Afficher
        plotter = pv.Plotter(window_size=[800, 600])
        plotter.add_mesh(solides, cmap="bone", opacity=0.1)

        if tous_points.shape[0] > 0:
            points_surface_vis.points = tous_points
            plotter.add_mesh(points_surface_vis, color='red',
                             point_size=10, render_points_as_spheres=True)
        else:
            self.logger.warn("Aucun point de surface à visualiser.")

        plotter.add_axes_at_origin()

        self.logger.info("Affichage (Validation): Murs (gris) et Surfaces de Convection (rouge)...")
        plotter.show()

    # --- MODIFICATION: Visualisation de la Heatmap ---
    def visualiser_resultat(self, etape_index=-1, downsample_factor=1,
                            temp_min=0.0, temp_max=20.0):
        """
        Affiche une "heatmap" 3D en utilisant le même "slicer" 3D
        que la visualisation de la structure.
        """

        etat = self.stockage.charger_etape(etape_index)
        if etat is None:
            return

        temps_s = etat["temps_s"]
        matrice_T = etat["matrice_T"]
        temps_air = etat["temps_air"]

        self.logger.info(f"Visualisation du résultat t={temps_s:.1f}s (downsample x{downsample_factor})...")
        self.logger.info(f"  Températures de l'air: {temps_air}")

        grid = self._creer_grille_pyvista()

        # Injecter les T° de l'air dans la matrice T
        for id_zone, T_air in temps_air.items():
            masque_air_zone = (self.modele.Alpha == id_zone)
            matrice_T[masque_air_zone] = T_air

        grid.point_data["temp"] = matrice_T.ravel(order='F')

        if downsample_factor > 1:
            voi = (0, self.params.N_x - 1, 0, self.params.N_y - 1, 0, self.params.N_z - 1)
            rate = (downsample_factor, downsample_factor, downsample_factor)
            grid = grid.extract_subset(voi, rate=rate)

        plotter = pv.Plotter(window_size=[800, 600])
        cmap = "coolwarm"  # Bleu (froid) vers Rouge (chaud)

        # --- MODIFICATION: Remplacer add_volume par add_mesh_slice_orthogonal ---
        plotter.add_mesh_slice_orthogonal(
            grid,
            scalars="temp",
            cmap=cmap,
            clim=[temp_min, temp_max],  # Applique la plage de température
            scalar_bar_args={'title': 'Température (°C)'}
        )

        plotter.add_axes_at_origin()

        self.logger.info("Lancement de la visualisation PyVista (Heatmap Slicer)...")
        plotter.show()



