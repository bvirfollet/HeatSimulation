"""
Module RAYONNEMENT THERMIQUE pour simulation thermique.

Modèle gris simplifié:
- Rayonnement longue onde (LW) entre surfaces opaque
- Utilise approximation de rayonnement diffus (isotrope)
- Basé sur loi de Stefan-Boltzmann

Formulation:
  Q_rad = ε·σ·A·(T_surface^4 - T_ambiant^4)

où:
  ε = émissivité (0.8-0.95 pour matériaux de construction)
  σ = constante Stefan-Boltzmann = 5.67e-8 W/m²K⁴
  A = aire de surface
  T_surface, T_ambiant = températures absolues (K)

"""

import numpy as np


class ModeleRayonnement:
    """
    Gère le rayonnement thermique.

    Options:
    1. Rayonnement interne (solides ↔ air) - optionnel
    2. Rayonnement externe (surface ↔ ciel) - importante
    3. Rayonnement sol (surface ↔ sol) - modérée
    """

    SIGMA = 5.67e-8  # Stefan-Boltzmann (W/m²K⁴)

    def __init__(self, logger, enable_external=True, enable_internal=False):
        """
        Args:
            logger: Logger instance
            enable_external: Inclure rayonnement vers l'extérieur (ciel)
            enable_internal: Inclure rayonnement entre surfaces intérieures
        """
        self.logger = logger
        self.enable_external = enable_external
        self.enable_internal = enable_internal

        # Émissivités par défaut des matériaux
        self.emissivites = {
            "PARPAING": 0.85,
            "PLACO": 0.90,
            "LAINE_VERRE": 0.85,
            "LAINE_BOIS": 0.85,
            "BETON": 0.88,
            "TERRE": 0.90,
            "CARRELAGE": 0.95,
            "PVC": 0.80,
            "PARQUET_COMPOSITE": 0.85,
            "MUR_COMPOSITE_EXT": 0.85,
            "POLYSTYRENE": 0.80,
        }

        # Température "effective" du ciel
        # En réalité: T_sky ≈ T_air - 10 à 20°C (selon humidité, nuages)
        self.T_sky_K = 273.15 - 10.0  # -10°C = 263.15 K (ciel dégagé)

        if self.enable_external:
            logger.info("Rayonnement ACTIVÉ: Modèle gris externe (Stefan-Boltzmann)")
            logger.info(f"Température effective du ciel: {self.T_sky_K - 273.15:.1f}°C")
        else:
            logger.info("Rayonnement DÉSACTIVÉ")

    def calculer_flux_rayonnement_externe(self, T_surface_K, emissivite, A_surface):
        """
        Calcule flux radiatif vers l'extérieur (ciel).

        Q_rad = ε·σ·A·(T_surface^4 - T_sky^4)

        Args:
            T_surface_K: Température de surface (K)
            emissivite: Coefficient d'émissivité (0-1)
            A_surface: Aire de surface (m²)

        Returns:
            Flux radiatif (W) > 0 si perte, < 0 si gain
        """
        if not self.enable_external:
            return 0.0

        Q = emissivite * self.SIGMA * A_surface * (
            T_surface_K**4 - self.T_sky_K**4
        )
        return Q

    def calculer_flux_rayonnement_interne(self, T_surf1_K, T_surf2_K, eps1, eps2, A):
        """
        Rayonnement diffus entre deux surfaces (modèle simplifié).

        Flux effectif:
        Q = ε_eff·σ·A·(T1^4 - T2^4)

        avec ε_eff = 1 / (1/ε1 + 1/ε2 - 1) pour deux surfaces parallèles

        Args:
            T_surf1_K, T_surf2_K: Températures surfaces (K)
            eps1, eps2: Émissivités
            A: Aire d'échange (m²)

        Returns:
            Flux de surf1 vers surf2 (W)
        """
        if not self.enable_internal:
            return 0.0

        # Émissivité effective (2 surfaces parallèles)
        eps_eff = 1.0 / (1.0/eps1 + 1.0/eps2 - 1.0)

        Q = eps_eff * self.SIGMA * A * (T_surf1_K**4 - T_surf2_K**4)
        return Q

    def appliquer_rayonnement_surfaces_externes(self, T, Lambda, RhoCp, surfaces_convection_idx,
                                                ds, dt, emissivite_default=0.85):
        """
        Applique correction rayonnement externe aux surfaces en contact air.

        Stratégie:
        1. Identifier surfaces externes (LIMITE_FIXE adjacentes)
        2. Calculer flux radiatif Q_rad = ε·σ·A·(T^4 - T_sky^4)
        3. Modifier température: ΔT = -Q_rad·dt / (ρ·cp·V)

        Args:
            T: Champ température (3D array)
            Lambda: Conductivité thermique (3D array)
            RhoCp: Capacité volumique (3D array)
            surfaces_convection_idx: Dict de surfaces de convection
            ds: Discrétisation spatiale (m)
            dt: Pas de temps (s)
            emissivite_default: Émissivité par défaut si inconnue

        Returns:
            ΔT correction (3D array, zéro sauf surfaces)
        """
        dT_rayonnement = np.zeros_like(T)

        if not self.enable_external:
            return dT_rayonnement

        # Pour chaque zone air (surfaces externes)
        for id_zone, indices_tuple in surfaces_convection_idx.items():
            if indices_tuple[0].size == 0:
                continue

            # Température surfaces
            T_surfaces_K = T[indices_tuple] + 273.15  # Convertir en Kelvin

            # Émissivité (pour l'instant, utiliser default)
            eps = emissivite_default

            # Aire par surface
            A_face = ds * ds

            # Flux radiatif: Q = ε·σ·A·(T^4 - T_sky^4)
            Q_rad_vec = eps * self.SIGMA * A_face * (
                T_surfaces_K**4 - self.T_sky_K**4
            )

            # Variation de température
            V_voxel = ds**3
            C_voxel = RhoCp[indices_tuple] * V_voxel

            dT_rad_vec = np.divide(
                -Q_rad_vec * dt,  # Signe: perte → ΔT négatif
                C_voxel,
                out=np.zeros_like(Q_rad_vec),
                where=C_voxel != 0
            )

            dT_rayonnement[indices_tuple] = dT_rad_vec

        return dT_rayonnement

    def set_temperature_sky(self, T_sky_C):
        """Définir température du ciel (°C)."""
        self.T_sky_K = T_sky_C + 273.15
        self.logger.info(f"Température du ciel: {T_sky_C:.1f}°C ({self.T_sky_K:.2f}K)")

    def set_emissivite(self, materiau, emissivite):
        """Définir l'émissivité pour un matériau."""
        if 0 <= emissivite <= 1:
            self.emissivites[materiau] = emissivite
        else:
            self.logger.warn(f"Émissivité invalide pour {materiau}: {emissivite}")

    def get_emissivite(self, materiau):
        """Récupérer l'émissivité d'un matériau."""
        return self.emissivites.get(materiau, 0.85)
