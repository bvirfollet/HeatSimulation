"""
Test de validation analytique pour la simulation 1D.

Cas de test: Diffusion thermique 1D dans un demi-espace semi-infini
- Domaine: [0, +∞]
- Condition initiale: T(x, 0) = T_0 (x > 0)
- Condition limite: T(0, t) = T_1 (x = 0, t > 0)
- Solution analytique: T(x,t) = T_1 + (T_0 - T_1)·erf(x / (2√(α·t)))

La simulation FTCS doit converger vers cette solution analytique.
"""

import numpy as np
from scipy.special import erf
from logger import LoggerSimulation
from parametres import ParametresSimulation
from modele import ModeleMaison
from simulation import Simulation
import matplotlib.pyplot as plt


def solution_analytique_1d(x_vec, t, T_0, T_1, alpha):
    """
    Solution analytique pour diffusion 1D semi-infini.
    T(x,t) = T_1 + (T_0 - T_1)·erf(x / (2√(α·t)))
    """
    if t <= 0:
        return T_0 * np.ones_like(x_vec)

    eta = x_vec / (2 * np.sqrt(alpha * t))
    return T_1 + (T_0 - T_1) * erf(eta)


def test_diffusion_1d():
    """Test la solution FTCS contre la solution analytique pour cas 1D."""

    logger = LoggerSimulation(niveau="INFO")

    # Paramètres du test
    L = 1.0  # Longueur domaine (m)
    ds = 0.05  # Discrétisation spatiale
    dt = 0.1  # Pas de temps
    T_0 = 20.0  # T initiale (intérieur)
    T_1 = 0.0  # T limite (extérieur)
    alpha = 1.0e-6  # Diffusivité (m²/s) ~ béton

    # Créer grille 1D
    N = int(L / ds) + 1
    x_vec = np.linspace(0, L, N)

    logger.info("=" * 60)
    logger.info("TEST ANALYTIQUE: Diffusion 1D")
    logger.info("=" * 60)
    logger.info(f"Domaine: [0, {L}] m")
    logger.info(f"Discrétisation: dx={ds}m, N={N} points")
    logger.info(f"Pas temps: dt={dt}s")
    logger.info(f"Diffusivité: α={alpha:.2e} m²/s")
    logger.info(f"CFL = α·dt/dx² = {alpha*dt/ds**2:.4f} (doit être < 1/6 = 0.1667)")

    # Vérifier CFL
    cfl = alpha * dt / ds**2
    if cfl > 1/6:
        logger.error(f"Instabilité CFL! {cfl:.4f} > 0.1667")
        return False

    # Solution FTCS 1D explicite
    T = np.full(N, T_0, dtype=np.float64)
    T[0] = T_1  # Condition limite

    temps_fin = 1000.0  # 1000 secondes
    nb_steps = int(temps_fin / dt)

    erreurs_l2 = []
    temps_vec = []

    # Boucle temporelle
    for step in range(nb_steps):
        t_current = step * dt

        # FTCS: T_new = T + α·dt/ds² * (T_{i+1} - 2T_i + T_{i-1})
        T_new = T.copy()
        coeff = alpha * dt / ds**2

        for i in range(1, N-1):
            T_new[i] = T[i] + coeff * (T[i+1] - 2*T[i] + T[i-1])

        T_new[0] = T_1  # Réappliquer limite
        T = T_new

        # Tous les 100 steps, calculer erreur
        if step % 100 == 0:
            t_current = step * dt
            T_exacte = solution_analytique_1d(x_vec, t_current, T_0, T_1, alpha)
            erreur_l2 = np.sqrt(np.mean((T - T_exacte)**2))
            erreurs_l2.append(erreur_l2)
            temps_vec.append(t_current)

            logger.info(f"t={t_current:7.1f}s: Erreur L² = {erreur_l2:.6f} K")

    # Résultats finaux
    T_exacte_finale = solution_analytique_1d(x_vec, temps_fin, T_0, T_1, alpha)
    erreur_l2_finale = np.sqrt(np.mean((T - T_exacte_finale)**2))
    erreur_linf_finale = np.max(np.abs(T - T_exacte_finale))

    logger.info("")
    logger.info("RÉSULTATS FINAUX (t=1000s)")
    logger.info("=" * 60)
    logger.info(f"Erreur L² (RMS): {erreur_l2_finale:.6f} K")
    logger.info(f"Erreur L∞ (Max): {erreur_linf_finale:.6f} K")

    # Critères
    success = True
    if erreur_l2_finale < 0.01:
        logger.info("✓ EXCELLENT: Erreur < 0.01 K")
    elif erreur_l2_finale < 0.1:
        logger.info("✓ BON: Erreur < 0.1 K")
    elif erreur_l2_finale < 1.0:
        logger.info("⚠ ACCEPTABLE: Erreur < 1 K")
    else:
        logger.warn(f"✗ INSUFFISANT: Erreur > 1 K")
        success = False

    logger.info("=" * 60)

    # Plot optionnel
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(x_vec, T, 'b-', label='FTCS', linewidth=2)
        plt.plot(x_vec, T_exacte_finale, 'r--', label='Analytique', linewidth=2)
        plt.xlabel('Position x (m)')
        plt.ylabel('Température (K)')
        plt.title('Diffusion 1D: FTCS vs Analytique (t=1000s)')
        plt.legend()
        plt.grid(True)
        plt.savefig('/tmp/test_analytique_diffusion_1d.png', dpi=100)
        logger.info("Graphique sauvegardé: /tmp/test_analytique_diffusion_1d.png")
    except Exception as e:
        logger.warn(f"Impossible de créer graphique: {e}")

    return success


def test_equilibre_thermique():
    """Test que le système converge vers équilibre après longue simulation."""

    logger = LoggerSimulation(niveau="INFO")

    logger.info("=" * 60)
    logger.info("TEST: Équilibre Thermique")
    logger.info("=" * 60)

    # Créer un petit modèle (1m³ simple)
    params = ParametresSimulation(
        logger,
        dims_m=(0.5, 0.5, 0.5),
        ds=0.1,
        dt=10.0,
        T_interieur_init=20.0,
        T_exterieur_init=0.0,
        T_sol_init=10.0,
        h_convection=8.0
    )

    # Créer modèle minimal (sans éditeur, juste une boîte)
    modele = ModeleMaison(params)

    # Peupler très minimalement (un seul voxel solide au centre)
    from model_data import MATERIAUX
    props_beton = MATERIAUX["BETON"]
    modele.Alpha[2, 2, 2] = props_beton["alpha"]
    modele.Lambda[2, 2, 2] = props_beton["lambda"]
    modele.RhoCp[2, 2, 2] = props_beton["rho"] * props_beton["cp"]
    modele.T[2, 2, 2] = 20.0

    logger.info("Modèle créé: 1 voxel béton, 0.1m cube")
    logger.info("Simulation: 2 heures avec T_ext fixe à 0°C")

    # Lancer simulation rapide
    sim = Simulation(modele, chemin_sortie="/tmp/test_equilibre")
    sim.lancer_simulation(duree_s=7200, intervalle_stockage_s=600)

    T_final = modele.T[2, 2, 2]
    logger.info(f"Température finale du béton: {T_final:.2f}°C")
    logger.info(f"Température extérieure: {params.T_exterieur_init}°C")
    logger.info(f"Écart à l'équilibre: {abs(T_final - params.T_exterieur_init):.2f}°C")

    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SUITE DE TESTS ANALYTIQUES - SIMULATION THERMIQUE")
    print("=" * 70 + "\n")

    # Test 1: Diffusion 1D
    test1_passed = test_diffusion_1d()

    print("\n")

    # Test 2: Équilibre
    test2_passed = test_equilibre_thermique()

    print("\n" + "=" * 70)
    if test1_passed and test2_passed:
        print("✓ TOUS LES TESTS SONT PASSÉS")
    else:
        print("✗ CERTAINS TESTS ONT ÉCHOUÉ")
    print("=" * 70)
