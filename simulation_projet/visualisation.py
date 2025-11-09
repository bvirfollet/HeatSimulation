# --- Imports ---
from logger import LoggerSimulation
from modele import ModeleMaison
from parametres import ParametresSimulation
from stockage import StockageResultats
import numpy as np
import pyvista as pv


class Visualisation:
    """
    Gère la visualisation 3D des résultats avec PyVista.
    """

    def __init__(self, simulation):
        self.logger = LoggerSimulation(niveau="DEBUG")
        self.modele = simulation.modele
        self.stockage = simulation.stockage
        self.params = simulation.params

        self.logger.info("Visualiseur PyVista initialisé.")

    def _creer_grille_pyvista(self):
        """Crée l'objet grille (ImageData) PyVista."""
        # Crée une grille uniforme
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
        Visualise la géométrie (les matériaux) du modèle.
        Affiche les solides (Alpha >= 0) et cache l'air (Alpha < 0).
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
        plotter.add_mesh(solides, scalars="alpha", cmap="viridis_r",
                         opacity=0.5, scalar_bar_args={'title': 'Diffusivité (alpha)'})
        plotter.add_axes_at_origin()
        plotter.camera_position = 'iso'

        self.logger.info("Affichage de la fenêtre PyVista (structure)...")
        plotter.show()

    def visualiser_surfaces_convection(self):
        """
        (Validation Étape 1)
        Affiche les murs (solides) en gris transparent et
        les points de surface de convection détectés en ROUGE vif.
        """
        self.logger.info("Visualisation des surfaces de convection...")

        # 1. Créer la grille de base pour les murs (solides)
        grid = self._creer_grille_pyvista()
        # --- CORRECTION (ValueError) ---
        # Mettre les données sur les 'points', comme ci-dessus
        grid.point_data["alpha"] = self.modele.Alpha.ravel(order='F')
        solides = grid.threshold(0.0, scalars="alpha")

        # 2. Créer un objet PyVista pour les points de surface
        # On rassemble tous les indices de toutes les zones
        tous_les_indices = []
        for id_zone in self.modele.surfaces_convection_idx:
            tous_les_indices.append(self.modele.surfaces_convection_idx[id_zone])

        if not tous_les_indices:
            self.logger.warning("Aucune surface de convection à visualiser.")
            return

        indices_np = np.vstack(tous_les_indices)

        # Convertir les indices (i,j,k) en coordonnées (x,y,z)
        coordonnees = indices_np * self.params.ds

        # Créer un nuage de points (PolyData)
        points_surface = pv.PolyData(coordonnees)

        # 3. Afficher les deux
        plotter = pv.Plotter(window_size=[800, 600])
        # Afficher les solides (murs) en gris transparent
        plotter.add_mesh(solides, color='gray', opacity=0.1)
        # Afficher les points de surface en ROUGE
        plotter.add_points(points_surface, color='red', point_size=10,
                           render_points_as_spheres=True)

        plotter.add_axes_at_origin()
        plotter.camera_position = 'iso'

        self.logger.info("Affichage (Validation): Murs (gris) et Surfaces de Convection (rouge)...")
        plotter.show()

    def visualiser_resultat(self, etape_index=-1, downsample_factor=1,
                            temp_min=0.0, temp_max=20.0):
        """
        Visualise la "heatmap" 3D (rendu volumétrique)
        d'une étape de simulation.
        """

        # 1. Charger les données depuis le disque
        matrice_T, temps_s, pertes = self.stockage.charger_etape(etape_index)
        if matrice_T is None:
            self.logger.error("Impossible de visualiser, les données n'ont pas pu être chargées.")
            return

        self.logger.info(f"Visualisation du résultat t={temps_s}s (downsample x{downsample_factor})...")

        # 2. Préparer la grille PyVista
        grid = self._creer_grille_pyvista()

        # Attache les données de Température aux points
        # .ravel('F') est crucial (ordre Fortran)
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

        # 5. Définir la fonction de transfert (Couleur + Opacité)

        # Colormap (Bleu -> Blanc -> Rouge)
        cmap = "coolwarm"

        # Opacity map (pour cacher l'air intérieur)
        # On veut voir le froid (min) et le chaud (max),
        # mais cacher le milieu (température de la pièce)
        milieu = (temp_min + temp_max) / 2.0

        # --- CORRECTION (AttributeError) ---
        # pv.OpacityMap n'existe pas dans certaines versions.
        # On le remplace par la liste manuelle qu'il générait.
        opacity_map = [0.8, 0.0, 0.8] # [Opaque, Transparent, Opaque]

        # Ancien code:
        # opacity_map = pv.OpacityMap([temp_min, milieu, temp_max],
        #                             [0.8, 0.0, 0.8])

        self.logger.info("Lancement de la visualisation PyVista (heatmap)...")

        # Ajoute le rendu volumétrique
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
        plotter.camera_position = 'iso'

        # Afficher la fenêtre
        plotter.show()

