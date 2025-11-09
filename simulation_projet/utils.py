import numpy as np


class UtilsMath:
    """Classe pour les utilitaires mathématiques (ex: interpolation)."""

    @staticmethod
    def _creer_matrice_3d(N_x, N_y, N_z, valeur_initiale=0.0, use_numpy=False):
        """Crée une matrice 3D (liste de listes ou NumPy array)."""
        if use_numpy:
            return np.full((N_x, N_y, N_z), valeur_initiale, dtype=np.float64)
        else:
            return [[[valeur_initiale for _ in range(N_z)]
                     for _ in range(N_y)]
                    for _ in range(N_x)]

    @staticmethod
    def interpoler_trilineaire(point, T_points, V_points):
        """
        Effectue une interpolation trilinéaire.
        (Implémentation à compléter, dépend de la structure des données d'entrée)
        point: tuple (x,y,z) où l'on veut la température
        T_points: points de température connus
        V_points: valeurs à ces points
        """
        # Placeholder - une vraie implémentation est complexe
        print("Interpolation trilinéaire non implémentée.")
        if V_points:
            return V_points[0]  # Retourne une valeur par défaut
        return 0.0