"""Independent manufactured solution for the two ``core_mms_v1`` controls.

All time arguments use seconds and xi is the material radius r / R(t).
``exact`` returns columns [C (kg/kg), T (degC)]. ``source`` returns
[f_C (1/s), f_T (W/m^3)]; the thermal source has NOT been divided by b(C).

The three-argument source API follows the two controls in the report:
Q23 uses R = 0.02 m, and Q4 uses the manufactured moving radius.  The
boundary helper takes the geometry explicitly.  No production solver or
discrete right-hand side is imported. NumPy supports the analytic reference,
SciPy supports piecewise-polynomial reconstruction errors, and SymPy is used
only by the executable, independent formula check.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


TAU0_S = 3600.0
END_TIME_S = 14400.0
EVENT_TIME_S = TAU0_S * np.log(25.0)
R0_M = 0.02
H_W_M2_K = 25.0
HM_M_S = 8e-7


def _coordinates(t, xi):
    """Broadcast scalar time or paired times against a one-dimensional xi set."""
    times, points = np.broadcast_arrays(
        np.asarray(t, dtype=float), np.atleast_1d(np.asarray(xi, dtype=float))
    )
    if points.ndim != 1:
        raise ValueError("t and xi must broadcast to one dimension.")
    if not np.isfinite(times).all() or np.any(times < 0):
        raise ValueError("Manufactured time must be finite and nonnegative.")
    if not np.isfinite(points).all() or np.any((points < 0) | (points > 1)):
        raise ValueError("xi must be finite and lie in [0, 1].")
    return times, points


def radius(t, moving):
    """Return the fixed or manufactured radius in metres; preserve time shape."""
    times = np.asarray(t, dtype=float)
    if not np.isfinite(times).all() or np.any(times < 0):
        raise ValueError("Manufactured time must be finite and nonnegative.")
    if not isinstance(moving, (bool, np.bool_)):
        raise TypeError("moving must be a boolean.")
    value = R0_M * (0.7 + 0.3 * np.exp(-times / TAU0_S)) if moving else np.full_like(times, R0_M)
    return float(value) if value.ndim == 0 else value


def _profiles(t, xi):
    """Fields and analytic xi/time derivatives, including regular radial Laplacians."""
    times, points = _coordinates(t, xi)
    decay = np.exp(-times / TAU0_S)
    x = points * points
    pc = 1.0 - 0.3 * x + 0.1 * x * x
    pt = 1.0 + 0.2 * x + 0.05 * x * x
    c = 0.05 + 2.5 * decay * pc
    temperature = 28.0 + 12.0 * (1.0 - decay) * pt
    c_t = -2.5 * decay * pc / TAU0_S
    t_t = 12.0 * decay * pt / TAU0_S
    c_xi = 2.5 * decay * points * (-0.6 + 0.4 * x)
    t_xi = 12.0 * (1.0 - decay) * points * (0.4 + 0.2 * x)
    # C_xixi + C_xi/xi and T_xixi + T_xi/xi, already extended to xi = 0.
    radial_c = 2.5 * decay * (-1.2 + 1.6 * x)
    radial_t = 12.0 * (1.0 - decay) * (0.8 + 0.8 * x)
    return times, c, temperature, c_t, t_t, c_xi, t_xi, radial_c, radial_t


def exact(t, xi):
    """Return exact [C, T] rows, shape (n, 2); scalar xi produces one row."""
    _, c, temperature, *_ = _profiles(t, xi)
    return np.column_stack((c, temperature))


def _properties(c, temperature, material):
    if material == "Q23":
        a_prefactor, a_c = 2.4e-3, 0.45
        k0, k_delta = 0.21, 0.38
        rho0, rho_delta, cp0, cp_delta = 650.0, 128.0, 1450.0, 2736.0
    elif material == "Q4":
        a_prefactor, a_c = 4.2e-4, 0.30
        k0, k_delta = 0.12, 0.20
        rho0, rho_delta, cp0, cp_delta = 760.0, 90.0, 1850.0, 2150.0
    else:
        raise ValueError("material must be 'Q23' or 'Q4'.")
    kelvin = temperature + 273.15
    diffusion = a_prefactor * np.exp(-a_c / c - 3850.0 / kelvin)
    conductivity = k0 + k_delta * c / (1.0 + c)
    capacity = (rho0 + rho_delta * c) * (cp0 + cp_delta * c / (1.0 + c))
    d_dc = diffusion * a_c / (c * c)
    d_dt = diffusion * 3850.0 / (kelvin * kelvin)
    k_dc = k_delta / ((1.0 + c) ** 2)
    return diffusion, conductivity, capacity, d_dc, d_dt, k_dc


def source(t, xi, material):
    """Return continuous [f_C, f_T], shape (n, 2), at fixed material xi.

    Q23 is the fixed-radius control; Q4 is the moving-radius control.
    The returned f_T belongs to b(C) T_t = div(k grad T) + f_T.
    """
    times, c, temperature, c_t, t_t, c_xi, t_xi, radial_c, radial_t = _profiles(t, xi)
    diffusion, conductivity, capacity, d_dc, d_dt, k_dc = _properties(c, temperature, material)
    r = radius(times, moving=material == "Q4")
    diffusion_xi = d_dc * c_xi + d_dt * t_xi
    l_c = (diffusion * radial_c + diffusion_xi * c_xi) / (r * r)
    l_t = (conductivity * radial_t + k_dc * c_xi * t_xi) / (r * r)
    return np.column_stack((c_t - l_c, capacity * t_t - l_t))


def boundary(t, material, moving):
    """Return manufactured (T_air in degC, C_eq in kg/kg) for scalar time."""
    if np.asarray(t).ndim != 0:
        raise ValueError("boundary expects a scalar time.")
    _, c, temperature, _, _, c_xi, t_xi, _, _ = _profiles(t, [1.0])
    diffusion, conductivity, *_ = _properties(c, temperature, material)
    r = radius(t, moving)
    tair = temperature[0] + conductivity[0] * t_xi[0] / (H_W_M2_K * r)
    ceq = c[0] + diffusion[0] * c_xi[0] / (HM_M_S * r)
    return float(tair), float(ceq)


def _reconstruction_error(t, xi, native):
    """PPoly for PCHIP(native) minus the exact quartic, in local xi powers."""
    from scipy.interpolate import PchipInterpolator, PPoly

    if np.asarray(t).ndim != 0:
        raise ValueError("Reconstruction errors require one scalar time.")
    _, points = _coordinates(t, xi)
    values = np.asarray(native, dtype=float)
    if len(points) < 2 or points[0] != 0.0 or points[-1] != 1.0 or np.any(np.diff(points) <= 0):
        raise ValueError("The strictly increasing reconstruction grid must span xi = 0 to 1.")
    if values.shape != (len(points), 2) or not np.isfinite(values).all():
        raise ValueError("native must be a finite (len(xi), 2) array of [C, T] values.")
    interpolant = PchipInterpolator(points, values, axis=0, extrapolate=False)
    decay = np.exp(-float(t) / TAU0_S)
    quadratic = np.array([-0.75 * decay, 2.4 * (1.0 - decay)])
    quartic = np.array([0.25 * decay, 0.6 * (1.0 - decay)])
    left = points[:-1, None]
    coefficients = np.zeros((5, len(points) - 1, 2))
    coefficients[1:] = interpolant.c
    coefficients[0] -= quartic
    coefficients[1] -= 4.0 * left * quartic
    coefficients[2] -= quadratic + 6.0 * left**2 * quartic
    coefficients[3] -= 2.0 * left * quadratic + 4.0 * left**3 * quartic
    coefficients[4] -= exact(t, points[:-1])
    return PPoly(coefficients, points, extrapolate=False)


def error_maximum(t, xi, native):
    """Return (maximum absolute [C,T] errors, their xi locations) on [0,1].

    Every segment is a known quartic error polynomial. Its derivative roots
    and all grid endpoints are evaluated. Root calculations use each cell's
    unit coordinate for conditioning on strongly graded grids. This is a
    floating-point algebraic extremum search, not an interval certificate.
    It does not alter a separately frozen finite-point scoring grid.
    """
    from scipy.interpolate import PPoly

    error = _reconstruction_error(t, xi, native)
    widths = np.diff(error.x)
    # Reparameterize every piece by u = (xi-left)/width on [0,1].
    unit_coefficients = error.c * widths[None, :, None] ** np.arange(4, -1, -1)[:, None, None]
    node_error = np.abs(np.asarray(native) - exact(t, error.x))
    indices = np.argmax(node_error, axis=0)
    maxima = node_error[indices, np.arange(2)].copy()
    locations = error.x[indices].copy()
    interval_count = len(widths)
    for column in range(2):
        unit_poly = PPoly(unit_coefficients[:, :, column], np.arange(interval_count + 1, dtype=float),
                          extrapolate=False)
        roots = unit_poly.derivative().roots(discontinuity=False, extrapolate=False)
        roots = roots[np.isfinite(roots) & (roots >= 0.0) & (roots <= interval_count)]
        if not len(roots):
            continue
        values = np.abs(unit_poly(roots))
        index = int(np.argmax(values))
        if values[index] > maxima[column]:
            interval = min(int(np.floor(roots[index])), interval_count - 1)
            maxima[column] = values[index]
            locations[column] = error.x[interval] + widths[interval] * (roots[index] - interval)
    return maxima, locations


def integrated_L2(t, xi, native):
    """Return sqrt(2 integral_0^1 xi * error(xi)^2 dxi) for [C, T].

    The square of each quartic reconstruction error is integrated exactly
    as a polynomial, independently of the production nodal volume weights.
    Units remain kg/kg and K; no physical-radius or time averaging is used.
    """
    error = _reconstruction_error(t, xi, native)
    widths = np.diff(error.x).astype(np.longdouble)
    left = error.x[:-1].astype(np.longdouble)
    ascending = error.c[::-1].astype(np.longdouble)
    ascending *= widths[None, :, None] ** np.arange(5)[:, None, None]
    squared = np.zeros((9, len(widths), 2), dtype=np.longdouble)
    for i in range(5):
        for j in range(5):
            squared[i + j] += ascending[i] * ascending[j]
    powers = np.arange(9, dtype=np.longdouble)[:, None, None]
    moments = 2.0 * widths[None, :, None] * (
        left[None, :, None] / (powers + 1.0) + widths[None, :, None] / (powers + 2.0)
    )
    terms = squared * moments
    integral = np.sum(terms, axis=(0, 1), dtype=np.longdouble)
    cancellation_scale = np.sum(np.abs(terms), axis=(0, 1), dtype=np.longdouble)
    tolerance = 512.0 * np.finfo(np.longdouble).eps * cancellation_scale
    if np.any(integral < -tolerance):
        raise ArithmeticError("Polynomial square integration lost nonnegativity beyond roundoff.")
    return np.sqrt(np.asarray(np.maximum(integral, 0.0), dtype=float))


def reference_check():
    """Check analytic xi formulas against an independent SymPy x = xi^2 oracle.

    This is formula verification only: no PDE integration or NN training.
    The oracle differentiates the complete conservative flux products and
    uses the original mixture form of cp, independently of _properties.
    """
    import scipy
    import sympy as sp

    st, sx = sp.symbols("t x", nonnegative=True)
    q = sp.exp(-st / 3600)
    c = sp.Rational(1, 20) + sp.Rational(5, 2) * q * (1 - sp.Rational(3, 10) * sx + sx**2 / 10)
    temp = 28 + 12 * (1 - q) * (1 + sx / 5 + sx**2 / 20)
    fixed_r = sp.Rational(1, 50)
    moving_r = fixed_r * (sp.Rational(7, 10) + sp.Rational(3, 10) * q)
    # Independently stated material data; cp is kept as (cp_d + cp_w C)/(1+C).
    materials = {
        "Q23": (sp.Rational(24, 10000), sp.Rational(45, 100), sp.Rational(21, 100),
                sp.Rational(38, 100), 650, 128, 1450, 4186, False),
        "Q4": (sp.Rational(42, 100000), sp.Rational(3, 10), sp.Rational(12, 100),
               sp.Rational(1, 5), 760, 90, 1850, 4000, True),
    }
    times = np.array([0.0, 1.0, 60.0, 3600.0, EVENT_TIME_S - 60.0,
                      EVENT_TIME_S, EVENT_TIME_S + 60.0, END_TIME_S])
    points = np.unique(np.r_[np.linspace(0.0, 1.0, 41), 1e-12, 1e-8, 1.0 - 1e-9])
    tolerance = 512.0 * np.finfo(float).eps
    checks = []

    def record(name, observed, expected, scale, **details):
        observed, expected = np.broadcast_arrays(np.asarray(observed), np.asarray(expected))
        difference = np.abs(observed - expected)
        denominator = np.maximum(np.abs(expected), np.asarray(scale))
        finite = bool(np.isfinite(observed).all() and np.isfinite(expected).all())
        scaled_error = float(np.max(difference / denominator)) if finite else None
        passed = finite and scaled_error <= tolerance
        if isinstance(details.get("units"), list):
            axes = tuple(range(difference.ndim - 1))
            absolute = {"max_absolute_difference_by_column": np.max(difference, axis=axes).tolist() if finite else None}
        else:
            absolute = {"max_absolute_difference": float(np.max(difference)) if finite else None}
        checks.append({"name": name, "status": "PASS" if passed else "FAIL",
                       **absolute, "max_scaled_difference": scaled_error,
                       "scaled_tolerance": tolerance, **details})

    exact_oracle = sp.lambdify((st, sx), (c, temp), "numpy")
    derivative_oracle = sp.lambdify((st, sx), (sp.diff(c, st), sp.diff(temp, st),
                                                sp.diff(c, sx), sp.diff(temp, sx)), "numpy")
    summary = []
    for material, (prefactor, exponent, k0, kd, rho0, rhod, cpd, cpw, moving) in materials.items():
        r = moving_r if moving else fixed_r
        d = prefactor * sp.exp(-exponent / c - 3850 / (temp + sp.Rational(27315, 100)))
        k = k0 + kd * c / (1 + c)
        b = (rho0 + rhod * c) * (cpd + cpw * c) / (1 + c)
        fc = sp.diff(c, st) - 4 * sp.diff(sx * d * sp.diff(c, sx), sx) / r**2
        ft = b * sp.diff(temp, st) - 4 * sp.diff(sx * k * sp.diff(temp, sx), sx) / r**2
        source_oracle = sp.lambdify((st, sx), (fc, ft), "numpy")
        property_oracle = sp.lambdify((st, sx), (d, k, b), "numpy")
        radius_oracle = sp.lambdify(st, r, "numpy")
        capacity_scale = float((rho0 + rhod * 2.55) * (cpd + cpw * 2.55) / 3.55)
        source_scale = np.array([2.55 / TAU0_S, capacity_scale * 12.0 / TAU0_S])
        actual_sources, oracle_sources = [], []
        axis_actual, axis_expected = [], []
        robin_residuals = []
        values_at_key_times = []
        for time in times:
            expected_exact = np.column_stack(exact_oracle(time, points**2))
            record(f"{material}:exact:t={time:.12g}", exact(time, points), expected_exact,
                   [2.55, 43.0], units=["kg/kg", "degC"])
            actual_sources.append(source(time, points, material))
            oracle_sources.append(np.column_stack(source_oracle(time, points**2)))
            record(f"{material}:radius:t={time:.12g}", radius(time, moving), radius_oracle(time),
                   R0_M, units="m")
            # At the axis, 4 D C_x/R^2 = 2 D C_xixi/R^2; no C_x = 0 condition.
            ct, tt, cx, tx = derivative_oracle(time, 0.0)
            da, ka, ba = property_oracle(time, 0.0)
            ra = float(radius_oracle(time))
            axis_expected.append([ct - 4 * da * cx / ra**2, ba * tt - 4 * ka * tx / ra**2])
            axis_actual.append(source(time, [0.0], material)[0])
            ds, ks, _ = property_oracle(time, 1.0)
            cs, ts = exact_oracle(time, 1.0)
            _, _, cx_s, tx_s = derivative_oracle(time, 1.0)
            tair, ceq = boundary(time, material, moving)
            robin_residuals.append([-2 * ds * cx_s / ra - HM_M_S * (cs - ceq),
                                    -2 * ks * tx_s / ra - H_W_M2_K * (ts - tair)])
            if time in (0.0, EVENT_TIME_S, END_TIME_S):
                values_at_key_times.append({"time_s": float(time), "radius_m": ra,
                                           "center_C_T": exact(time, [0.0])[0].tolist(),
                                           "surface_C_T": exact(time, [1.0])[0].tolist(),
                                           "boundary_Tair_Ceq": [tair, ceq],
                                           "source_axis_fC_fT": source(time, [0.0], material)[0].tolist()})
        record(f"{material}:continuous_sources_vs_sympy_x_flux", np.vstack(actual_sources),
               np.vstack(oracle_sources), source_scale, units=["1/s", "W/m^3"])
        record(f"{material}:axis_limit", axis_actual, axis_expected, source_scale,
               units=["1/s", "W/m^3"])
        record(f"{material}:Robin_balance", robin_residuals, np.zeros((len(times), 2)),
               [HM_M_S * 2.55, H_W_M2_K * 12.0], units=["m/s", "W/m^2"])
        paired = source(times, np.linspace(0.0, 1.0, len(times)), material)
        serial = np.vstack([source(ti, [xi], material) for ti, xi in zip(times, np.linspace(0.0, 1.0, len(times)))])
        record(f"{material}:paired_time_broadcast", paired, serial, source_scale,
               units=["1/s", "W/m^3"])
        summary.append({"material": material, "moving": moving,
                        "key_times": values_at_key_times})

    record("event:center_threshold", exact(EVENT_TIME_S, [0.0])[0, 0], 0.15, 2.55,
           units="kg/kg")
    event_slope = float(derivative_oracle(EVENT_TIME_S, 0.0)[0])
    record("event:analytic_slope", event_slope, -0.1 / TAU0_S, 2.55 / TAU0_S, units="1/s")
    # dC/dxi = 2.5 exp(-t/tau0) xi (-0.6 + 0.4 xi^2) < 0 for 0 < xi <= 1.
    monotone = bool(np.all(-0.6 + 0.4 * points[1:] ** 2 < 0))
    checks.append({"name": "event:maximum_at_axis", "status": "PASS" if monotone else "FAIL",
                   "analytic_reason": "xi>0 and -0.6+0.4*xi^2<=-0.2 on (0,1]."})
    after_event = bool(exact(END_TIME_S, [0.0])[0, 0] < 0.15 and EVENT_TIME_S < END_TIME_S)
    checks.append({"name": "window:exact_field_after_event", "status": "PASS" if after_event else "FAIL",
                   "event_time_s": float(EVENT_TIME_S), "end_time_s": END_TIME_S,
                   "post_event_duration_s": float(END_TIME_S - EVENT_TIME_S),
                   "pde_integration_performed": False})
    reconstruction_diagnostics = _check_reconstruction(record, checks, tolerance)
    return {"status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
            "check_scope": "Independent exact-field, source, axis, Robin, reconstruction-extremum and polynomial-integral checks only",
            "pde_integration_performed": False, "neural_network_training_performed": False,
            "core_mms_v1_integration_acceptance": "NOT_RUN",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "dependencies": {"numpy": np.__version__, "scipy": scipy.__version__, "sympy": sp.__version__},
            "source_columns": [{"name": "f_C", "unit": "1/s"},
                               {"name": "f_T", "unit": "W/m^3", "divided_by_capacity": False}],
            "geometries": {"Q23": "fixed R=0.02 m", "Q4": "manufactured moving R_m(t)"},
            "time_samples_s": times.tolist(), "xi_samples": points.tolist(),
            "roundoff_policy": "512 * float64 epsilon after component-wise physical scaling",
            "checks": checks, "controls": summary,
            "reconstruction_diagnostics": reconstruction_diagnostics}


def _check_reconstruction(record, checks, tolerance):
    """Independent known-polynomial, dense-scan and Gauss-moment checks."""
    from scipy.interpolate import PchipInterpolator

    scale = np.array([2.55, 43.0])
    time = TAU0_S
    points = np.linspace(0.0, 1.0, 18)
    constant = np.tile(exact(time, [0.0])[0], (len(points), 1))
    decay = np.exp(-time / TAU0_S)
    expected_maximum = np.array([0.5 * decay, 3.0 * (1.0 - decay)])
    expected_l2 = np.array([np.sqrt(17.0 / 160.0) * decay,
                            np.sqrt(339.0 / 125.0) * (1.0 - decay)])
    maximum, locations = error_maximum(time, points, constant)
    record("reconstruction:constant_interpolant_exact_maximum", maximum, expected_maximum,
           scale, units=["kg/kg", "K"])
    record("reconstruction:constant_interpolant_exact_L2", integrated_L2(time, points, constant),
           expected_l2, scale, units=["kg/kg", "K"])
    record("reconstruction:constant_interpolant_maximum_location", locations, [1.0, 1.0],
           [1.0, 1.0], units=["xi_C", "xi_T"])

    diagnostics = []
    scenarios = [("exact_nodes_axis_layer", TAU0_S, 640, False),
                 ("perturbed_nodes", EVENT_TIME_S, 73, True),
                 ("exact_nodes_final_time", END_TIME_S, 320, False),
                 ("constant_temperature_at_initial_time", 0.0, 80, False)]
    gauss, weights = np.polynomial.legendre.leggauss(5)
    for name, time, cells, perturb in scenarios:
        points = 1.0 - (1.0 - np.linspace(0.0, 1.0, cells + 1)) ** 1.5
        native = exact(time, points)
        if perturb:
            native += np.column_stack((0.003 * np.cos(3 * np.pi * points),
                                       0.05 * np.sin(4 * np.pi * points)))
        interpolant = PchipInterpolator(points, native, axis=0, extrapolate=False)
        maximum, locations = error_maximum(time, points, native)
        dense_xi = np.unique(np.r_[np.linspace(0.0, 1.0, 200001), points])
        dense_error = np.abs(interpolant(dense_xi) - exact(time, dense_xi))
        dense_maximum = np.max(dense_error, axis=0)
        # A second-derivative bound controls how much a uniform dense scan
        # can miss an interior stationary maximum: M * step^2 / 8.
        error = _reconstruction_error(time, points, native)
        widths = np.diff(points)
        curvature_bound = np.max(2 * np.abs(error.c[2]) + 6 * widths[:, None] * np.abs(error.c[1])
                                 + 12 * widths[:, None] ** 2 * np.abs(error.c[0]), axis=0)
        roundoff = tolerance * scale
        scan_allowance = curvature_bound * (1.0 / 200000.0) ** 2 / 8.0 + roundoff
        covered = bool(np.all(dense_maximum <= maximum + roundoff)
                       and np.all(maximum - dense_maximum <= scan_allowance))
        checks.append({"name": f"reconstruction:{name}:dense_maximum", "status": "PASS" if covered else "FAIL",
                       "polynomial_maximum_C_T": maximum.tolist(), "dense_maximum_C_T": dense_maximum.tolist(),
                       "allowable_scan_gap_C_T": scan_allowance.tolist(), "dense_points": len(dense_xi)})
        # Quartic error squared, times xi, has degree nine: five-point
        # Gauss integration is independently exact for each polynomial piece.
        quadrature_xi = (points[:-1, None] + points[1:, None]) / 2.0 + widths[:, None] * gauss / 2.0
        quadrature_error = interpolant(quadrature_xi) - exact(time, quadrature_xi.ravel()).reshape(cells, 5, 2)
        gauss_l2 = np.sqrt(np.sum(widths[:, None, None] * weights[None, :, None]
                                 * quadrature_xi[:, :, None] * quadrature_error**2, axis=(0, 1)))
        analytic_l2 = integrated_L2(time, points, native)
        record(f"reconstruction:{name}:L2_vs_Gauss5", analytic_l2, gauss_l2, scale,
               units=["kg/kg", "K"])
        diagnostics.append({"name": name, "time_s": float(time), "cells": cells,
                            "maximum_error_C_T": maximum.tolist(), "maximum_xi_C_T": locations.tolist(),
                            "integrated_area_L2_C_T": analytic_l2.tolist()})
        if name == "exact_nodes_axis_layer":
            frozen_xi = np.unique(np.r_[np.linspace(0.0, 1.0, 401), np.sqrt(np.arange(201) / 200)])
            sampled_maximum = np.max(np.abs(interpolant(frozen_xi) - exact(time, frozen_xi)), axis=0)
            axis_peak_found = bool(0.0 < locations[1] < points[1]
                                   and maximum[1] > sampled_maximum[1] + roundoff[1])
            checks.append({"name": "reconstruction:first_cell_peak_outside_fixed_points",
                           "status": "PASS" if axis_peak_found else "FAIL",
                           "first_cell_right_xi": float(points[1]), "peak_temperature_xi": float(locations[1]),
                           "full_maximum_temperature_K": float(maximum[1]),
                           "fixed_point_maximum_temperature_K": float(sampled_maximum[1]),
                           "fixed_scoring_grid_unchanged": True})
        if time == 0.0:
            record("reconstruction:initial_constant_temperature_zero", [maximum[1], analytic_l2[1]],
                   [0.0, 0.0], [43.0, 43.0], units=["K_Linf", "K_L2"])
    return diagnostics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-output", type=Path, required=True,
                        help="Write formula-check JSON to this explicit path.")
    arguments = parser.parse_args()
    result = reference_check()
    arguments.check_output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": len(result["checks"]),
                      "output": str(arguments.check_output), "pde_integration_performed": False}))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
