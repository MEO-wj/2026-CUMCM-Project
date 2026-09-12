"""Read-only conditional working-error budgets for the frozen drying model.

Public API: analyze_case(case_id, low_json, middle_json, tight_json, cap_json,
                         extra_time_json=None).
No PDE is integrated. Missing evidence remains not_established; these working
estimates are neither rigorous pointwise envelopes nor probability intervals.
"""
from pathlib import Path
import json
import math

import numpy as np
from scipy.interpolate import PchipInterpolator, PPoly


POLICY = {
    'version': 'working-budget-20260912-v5-extra-time-evidence',
    'space_safety': 1.25,
    'time_safety': 2.0,
    'reconstruction_safety': 2.0,
    'floating_epsilon_multiplier': 64.0,
    'space_noise_separation': 10.0,
    'compatible_spatial_order_min': 1.0,
    'compatible_spatial_order_max': 3.0,
    'time_cap_change_growth_max': 4.0,
    'norm_error_shape_alignment_max': 0.25,
    'event_probe_offsets_s': [-60., -30., 0., 30., 60.],
    'event_slope_margin_fraction': 0.5,
    'peak_endpoint_tolerance': 1e-10,
    'component_scales_C_T': [2.55, 22.0],
    'ranking_budget_scope': 'one conservative radial sup work estimate per frozen time/component, broadcast to all five xi',
    'decomposition': 'P-true=(P-L)+(L-true); spatial and time terms use the same local cubic L, reconstruction uses 2*norm(P-L)',
    'event_quantity': 'complete-radial-maximum functional, after verified max/extrapolation commutation; not entire-field error',
    'grid_refinement_ratio': 2,
    'extra_time_step_ratio': 0.5,
    'extra_time_difference_growth_max': 1.0,
    'extra_time_rule': 'Keep original d_tol and d_cap. With a further half-cap run require d_extra<=max(d_cap,original floating_floor); Utime=2*max(d_tol,d_cap,d_extra). A new growing difference invalidates qualification even when the original pair was qualified.',
}
RANK_XI = np.array([0., .25, .5, .75, 1.])
RANK_TIMES = {'Q1': np.array([100., 300., 600., 900., 1200., 1500., 1800.]),
              'Q23': np.arange(1800., 10801., 1800.)}
ESTABLISHED = 'conditional_work_estimate'
UNKNOWN = 'not_established'


def _safe(value):
    if isinstance(value, np.ndarray):
        return _safe(value.tolist())
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _floor(values, scale):
    return POLICY['floating_epsilon_multiplier']*np.finfo(float).eps*np.maximum(np.abs(values), scale)


def _load(case_id, path):
    if path is None or not Path(path).is_file():
        raise FileNotFoundError(str(path))
    path = Path(path)
    metadata = json.loads(path.read_text())
    actual = metadata.get('case', {}).get('case_id')
    if actual != case_id:
        raise ValueError(f'CASE_ID_MISMATCH: requested {case_id!r}, {path} contains {actual!r}')
    if metadata.get('status') != 'complete':
        raise LookupError(f'INPUT_NOT_COMPLETE: {path}: {metadata.get("status")}')
    if metadata.get('fields_order') != ['C', 'T']:
        raise ValueError('UNEXPECTED_FIELD_COMPONENT_ORDER: '+str(path))
    arrays_path = path.with_suffix('.npz')
    declared = metadata.get('arrays_file')
    if declared and Path(declared).name != arrays_path.name:
        raise ValueError(f'ARRAY_FILE_BINDING_MISMATCH: {path}: {declared}')
    with np.load(arrays_path, allow_pickle=False) as source:
        arrays = {key: source[key].copy() for key in source.files}
    for prefix, grid in zip(('coarse', 'fine'), metadata.get('grids', [])):
        xi = arrays[prefix+'_xi']
        if len(xi) != grid['cells']+1 or xi[0] != 0. or xi[-1] != 1. or np.any(np.diff(xi) <= 0):
            raise ValueError('INVALID_NATIVE_GRID: '+str(path))
    return {'path': str(path), 'arrays_path': str(arrays_path), 'meta': metadata, 'a': arrays}


def _grid_cells(bundles):
    return {'coarse': int(bundles[0]['meta']['grids'][0]['cells']),
            'medium': int(bundles[1]['meta']['grids'][0]['cells']),
            'fine': int(bundles[1]['meta']['grids'][1]['cells'])}


def _validate(bundles):
    low, middle, tight, cap = bundles
    first_pair = tuple(g['cells'] for g in low['meta']['grids'])
    if len(first_pair) != 2 or int(first_pair[0]) != first_pair[0] or first_pair[0] < 3:
        raise ValueError('INVALID_COARSE_GRID_PAIR')
    n = int(first_pair[0])
    expected_cells = [(n, 2*n), (2*n, 4*n), (2*n, 4*n), (2*n, 4*n)]
    for bundle, cells in zip(bundles, expected_cells):
        if tuple(g['cells'] for g in bundle['meta']['grids']) != cells:
            raise ValueError('UNEXPECTED_GRID_PAIR: '+bundle['path'])
    expected_accuracy = [dict(rtol=2e-12, atol_C=1e-14, atol_T=1e-13, max_step=60.),
                         dict(rtol=2e-12, atol_C=1e-14, atol_T=1e-13, max_step=60.),
                         dict(rtol=2e-13, atol_C=1e-15, atol_T=1e-14, max_step=60.),
                         dict(rtol=2e-13, atol_C=1e-15, atol_T=1e-14, max_step=30.)]
    for bundle, expected in zip(bundles, expected_accuracy):
        actual = bundle['meta'].get('accuracy', {})
        if any(actual.get(k) != v for k, v in expected.items()):
            raise ValueError('UNEXPECTED_ACCURACY: '+bundle['path'])
        if bundle['meta'].get('parameters') != middle['meta'].get('parameters'):
            raise ValueError('PARAMETER_OR_INPUT_RULE_MISMATCH: '+bundle['path'])
        if bundle['meta'].get('environment_tail') != middle['meta'].get('environment_tail'):
            raise ValueError('TAIL_MISMATCH: '+bundle['path'])
        for key in ('version', 'numpy', 'scipy'):
            if bundle['meta'].get(key) != middle['meta'].get(key):
                raise ValueError(f'{key.upper()}_MISMATCH: '+bundle['path'])
    if not np.array_equal(low['a']['fine_xi'], middle['a']['coarse_xi']):
        raise ValueError('SHARED_MIDDLE_GRID_MISMATCH')
    for bundle in (tight, cap):
        for prefix in ('coarse', 'fine'):
            if not np.array_equal(bundle['a'][prefix+'_xi'], middle['a'][prefix+'_xi']):
                raise ValueError('TIME_CONTROL_GRID_CHANGED')


def _validate_extra_time(bundles, extra):
    reference = bundles[3]
    if tuple(g['cells'] for g in extra['meta']['grids']) != tuple(g['cells'] for g in reference['meta']['grids']):
        raise ValueError('EXTRA_TIME_GRID_PAIR_MISMATCH')
    expected = dict(reference['meta']['accuracy'])
    expected['max_step'] *= POLICY['extra_time_step_ratio']
    if extra['meta'].get('accuracy') != expected:
        raise ValueError('EXTRA_TIME_ACCURACY_MISMATCH: expected '+str(expected))
    for key in ('parameters', 'environment_tail', 'version', 'numpy', 'scipy'):
        if extra['meta'].get(key) != reference['meta'].get(key):
            raise ValueError('EXTRA_TIME_'+key.upper()+'_MISMATCH')
    for prefix, grid in zip(('coarse', 'fine'), extra['meta']['grids']):
        if not np.array_equal(extra['a'][prefix+'_xi'], reference['a'][prefix+'_xi']):
            raise ValueError('EXTRA_TIME_NATIVE_GRID_CHANGED')
        for key in ('rtol', 'atol_C', 'atol_T'):
            if grid.get(key) != expected[key]:
                raise ValueError('EXTRA_TIME_GRID_TOLERANCE_MISMATCH')
        if grid.get('max_step_config_s') != expected['max_step']:
            raise ValueError('EXTRA_TIME_GRID_MAX_STEP_MISMATCH')


def _local_cubic(x, y):
    """Four-node local Lagrange polynomial per interval, without PCHIP slopes."""
    starts = np.clip(np.arange(len(x)-1)-1, 0, len(x)-4)
    ids = starts[:, None]+np.arange(4)
    nodes, values = x[ids], y[ids]
    scale = nodes[:, -1]-nodes[:, 0]
    z = (nodes-x[:-1, None])/scale[:, None]
    d1 = np.diff(values, axis=1)/np.diff(z, axis=1)
    d2 = np.diff(d1, axis=1)/(z[:, 2:]-z[:, :-2])
    d3 = (d2[:, 1]-d2[:, 0])/(z[:, 3]-z[:, 0])
    z0, z1, z2 = z[:, 0], z[:, 1], z[:, 2]
    c3 = d3
    c2 = d2[:, 0]-d3*(z0+z1+z2)
    c1 = d1[:, 0]-d2[:, 0]*(z0+z1)+d3*(z0*z1+z0*z2+z1*z2)
    c0 = values[:, 0]-d1[:, 0]*z0+d2[:, 0]*z0*z1-d3*z0*z1*z2
    return PPoly(np.vstack((c3/scale**3, c2/scale**2, c1/scale, c0)), x, extrapolate=False)


def _combine(terms):
    """Exact cubic PPoly linear combination after translating to common knots."""
    knots = np.unique(np.concatenate([poly.x for _, poly in terms]))
    left = knots[:-1]
    coefficients = np.zeros((4, len(left)))
    for weight, poly in terms:
        if poly.c.shape[0] != 4:
            raise ValueError('Cubic spatial polynomials required.')
        index = np.clip(np.searchsorted(poly.x, left, side='right')-1, 0, len(poly.x)-2)
        shift = left-poly.x[index]
        a, b, c, d = poly.c[:, index]
        coefficients += weight*np.array([a, 3*a*shift+b, 3*a*shift**2+2*b*shift+c,
                                         ((a*shift+b)*shift+c)*shift+d])
    return PPoly(coefficients, knots, extrapolate=False)


def _extrema(poly):
    """All interval endpoints and derivative roots; roots use unit intervals."""
    degree = poly.c.shape[0]-1
    width = np.diff(poly.x)
    unit = poly.c*width[None, :]**np.arange(degree, -1, -1)[:, None]
    values = np.r_[unit[-1], np.sum(unit, axis=0)]
    positions = np.r_[poly.x[:-1], poly.x[1:]]
    if degree == 3:
        a, b, c = 3*unit[0], 2*unit[1], unit[2]
        scale = np.maximum.reduce([np.abs(a), np.abs(b), np.abs(c)])
        is_quadratic = np.abs(a) > 64*np.finfo(float).eps*scale
        curved = is_quadratic.copy()
        disc = b*b-4*a*c
        curved &= disc >= 0.
        candidates = []
        for sign in (-1., 1.):
            r = np.full_like(a, np.nan)
            r[curved] = (-b[curved]+sign*np.sqrt(disc[curved]))/(2*a[curved])
            candidates.append(r)
        r = np.full_like(a, np.nan)
        linear = ~is_quadratic & (np.abs(b) > 64*np.finfo(float).eps*scale)
        r[linear] = -c[linear]/b[linear]
        candidates.append(r)
        for r in candidates:
            keep = (r > 0.) & (r < 1.)
            if keep.any():
                z = r[keep]; a0, b0, c0, d0 = unit[:, keep]
                values = np.r_[values, ((a0*z+b0)*z+c0)*z+d0]
                positions = np.r_[positions, poly.x[:-1][keep]+width[keep]*z]
    elif degree > 0:
        for i in range(len(width)):
            derivative = np.polyder(unit[:, i])
            roots = np.roots(np.trim_zeros(derivative, 'f')) if np.any(derivative) else []
            roots = [float(r.real) for r in roots if abs(r.imag) < 1e-9 and 0. < r.real < 1.]
            if roots:
                values = np.r_[values, np.polyval(unit[:, i], roots)]
                positions = np.r_[positions, poly.x[i]+width[i]*np.asarray(roots)]
    if not np.isfinite(values).all():
        raise ValueError('NONFINITE_POLYNOMIAL_EXTREMA')
    minimum, maximum = int(np.argmin(values)), int(np.argmax(values))
    return {'minimum': float(values[minimum]), 'maximum': float(values[maximum]),
            'minimum_x': float(positions[minimum]), 'maximum_x': float(positions[maximum])}


def _norm(poly):
    e = _extrema(poly)
    if abs(e['minimum']) > abs(e['maximum']):
        return abs(e['minimum']), e['minimum_x'], e['minimum']
    return abs(e['maximum']), e['maximum_x'], e['maximum']


def _time_from_differences(dt, ds, floor, d_extra=None):
    dt, ds, floor = np.asarray(dt), np.asarray(ds), np.asarray(floor)
    original_stable = ds <= POLICY['time_cap_change_growth_max']*np.maximum(dt, floor)
    maximum = np.maximum(dt, ds)
    stable = original_stable
    extra_non_growing = None
    if d_extra is not None:
        d_extra = np.asarray(d_extra)
        maximum = np.maximum(maximum, d_extra)
        extra_non_growing = d_extra <= POLICY['extra_time_difference_growth_max']*np.maximum(ds, floor)
        stable = extra_non_growing
    resolved = maximum > floor
    eligible = resolved & stable
    return {'d_tol': dt, 'd_cap': ds, 'floating_floor': floor,
            'd_extra': d_extra, 'maximum_observed_difference': maximum,
            'd_cross_status': 'not_supplied_not_included',
            'original_cap_drift': ~original_stable,
            'extra_time_control_used': d_extra is not None,
            'extra_difference_non_growing': extra_non_growing,
            'extra_difference_below_floating_resolution': None if d_extra is None else d_extra <= floor,
            'original_cap_drift_resolved_by_extra': (~original_stable & stable & resolved) if d_extra is not None else False,
            'eligible': eligible, 'U': np.where(eligible, POLICY['time_safety']*maximum, np.nan),
            'below_time_resolution': ~resolved, 'cap_drift_requires_more_evidence': ~stable,
            'conditional_interpretation': 'A further observed step-halving difference no longer grows; this is not a proof of BDF convergence order.' if d_extra is not None else None}


def _time_control(base, tight, cap, scale, extra=None):
    dt, ds = np.abs(base-tight), np.abs(tight-cap)
    floor = _floor(np.maximum.reduce([np.abs(base), np.abs(tight), np.abs(cap)]), scale)
    d_extra = None if extra is None else np.abs(cap-extra)
    return _time_from_differences(dt, ds, floor, d_extra)


def _space_control(delta_mc, delta_fm, noise, extra_eligible=True):
    am, af = np.abs(delta_mc), np.abs(delta_fm)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        order = np.log(am/af)/np.log(2.)
        denominator = np.exp2(order)-1.
    sign = delta_mc*delta_fm > 0.
    separated = np.minimum(am, af) > POLICY['space_noise_separation']*noise
    compatible = ((order >= POLICY['compatible_spatial_order_min']) &
                  (order <= POLICY['compatible_spatial_order_max']))
    eligible = sign & separated & compatible & extra_eligible
    with np.errstate(divide='ignore', invalid='ignore'):
        uf = POLICY['space_safety']*af/denominator
        um = POLICY['space_safety']*am/denominator
    return {'delta_medium_minus_coarse': delta_mc, 'delta_fine_minus_medium': delta_fm,
            'observed_order': order, 'same_sign': sign, 'noise_separated': separated,
            'compatible_with_nominal_second_order': compatible, 'eligible': eligible,
            'U_medium': np.where(eligible, um, np.nan), 'U_fine': np.where(eligible, uf, np.nan)}


def _rank_values(bundle, prefix, times):
    arrays = bundle['a']; x = arrays[prefix+'_xi']
    key = prefix+'_native_fields'
    if key not in arrays:
        raise KeyError('MISSING_NATIVE_FIELDS: '+bundle['path'])
    ids = np.searchsorted(arrays['sample_times_s'], times)
    if np.any(ids >= len(arrays['sample_times_s'])) or not np.array_equal(arrays['sample_times_s'][ids], times):
        raise KeyError('MISSING_FROZEN_RANK_TIMES: '+bundle['path'])
    values = np.empty((len(times), 5, 2)); rec = np.full_like(values, np.nan)
    local_values = np.empty_like(values)
    rec_status = np.full(values.shape, UNKNOWN, dtype=object)
    for j, index in enumerate(ids):
        native = arrays[key][index]
        if native.shape != (len(x), 2) or not np.isfinite(native).all():
            raise ValueError('INVALID_NATIVE_SNAPSHOT: '+bundle['path'])
        at_node = np.min(np.abs(x[:, None]-RANK_XI), axis=0) <= 8*np.finfo(float).eps
        for component in range(2):
            p = PchipInterpolator(x, native[:, component]); local = _local_cubic(x, native[:, component])
            value = p(RANK_XI); difference = np.abs(value-local(RANK_XI))
            floor = _floor(value, POLICY['component_scales_C_T'][component])
            structural = at_node | bool(np.all(native[:, component] == native[0, component]))
            established = difference > floor
            values[j, :, component] = value
            local_values[j, :, component] = local(RANK_XI)
            rec[j, :, component] = np.where(structural, 0., np.where(established, POLICY['reconstruction_safety']*difference, np.nan))
            rec_status[j, :, component] = np.where(structural, 'not_applicable_native_or_constant_reconstruction',
                                                    np.where(established, ESTABLISHED, 'not_established_below_reconstruction_resolution'))
    return values, rec, rec_status, local_values


def _field_budget(bundles, family, extra=None):
    if family not in RANK_TIMES:
        return {'status': 'not_applicable', 'reason': 'Q4 primary numerical quantity is its event time.'}
    low, middle, tight, cap = bundles; times = RANK_TIMES[family]; cells = _grid_cells(bundles)
    c, _, _, lc = _rank_values(low, 'coarse', times)
    duplicate, _, _, _ = _rank_values(low, 'fine', times)
    m, rec_m, rec_status_m, lm = _rank_values(middle, 'coarse', times)
    f, rec_f, rec_status_f, lf = _rank_values(middle, 'fine', times)
    _, _, _, mt = _rank_values(tight, 'coarse', times); _, _, _, ft = _rank_values(tight, 'fine', times)
    _, _, _, mc = _rank_values(cap, 'coarse', times); _, _, _, fc = _rank_values(cap, 'fine', times)
    scales = np.asarray(POLICY['component_scales_C_T'])
    me = fe = None
    if extra is not None:
        _, _, _, me = _rank_values(extra, 'coarse', times)
        _, _, _, fe = _rank_values(extra, 'fine', times)
    time_m = _time_control(lm, mt, mc, scales, me); time_f = _time_control(lf, ft, fc, scales, fe)
    noise = np.maximum(time_m['maximum_observed_difference'], time_f['maximum_observed_difference'])
    noise = POLICY['time_safety']*noise+np.maximum(time_m['floating_floor'], time_f['floating_floor'])
    duplicate_ok = np.abs(duplicate-m) <= _floor(m, scales)
    space = _space_control(lm-lc, lf-lm, noise, duplicate_ok)
    um = space['U_medium']+time_m['U']+rec_m
    uf = space['U_fine']+time_f['U']+rec_f
    ur = (4.*uf+um)/3.
    failed = []
    for index in np.argwhere(~np.isfinite(ur)):
        idx = tuple(index); reasons = []
        if not space['eligible'][idx]: reasons.append('space_not_established')
        if not time_m['eligible'][idx] or not time_f['eligible'][idx]: reasons.append('time_not_established')
        if not np.isfinite(rec_m[idx]) or not np.isfinite(rec_f[idx]): reasons.append('reconstruction_not_established')
        if not duplicate_ok[idx]: reasons.append('duplicate_shared_grid_production_values_disagree')
        failed.append({'index_time_xi_component': list(idx), 'time_s': times[idx[0]],
                       'xi': RANK_XI[idx[1]], 'component': ['C', 'T'][idx[2]], 'reasons': reasons})
    norm_records = [[_event_point(bundles, float(t), component, snapshots=True, extra=extra)
                     for component in range(2)] for t in times]
    norm_m = np.array([[r['direct_medium']['U_work_sup'] for r in pair] for pair in norm_records])
    norm_f = np.array([[r['direct_fine']['U_work_sup'] for r in pair] for pair in norm_records])
    norm_r = (4.*norm_f+norm_m)/3.
    broadcast = lambda a: np.repeat(a[:, None, :], len(RANK_XI), axis=1)
    radial = {'scope': 'One conditional radial sup-norm working estimate per time and component, conservatively applied to every frozen xi. Norm convergence is not a claim of pointwise order or a rigorous envelope.',
              'grid_cells': cells,
              'records_by_time_and_component': norm_records,
              'direct_medium': {'cells': cells['medium'], 'value': m, 'U_work': broadcast(norm_m)},
              'direct_fine': {'cells': cells['fine'], 'value': f, 'U_work': broadcast(norm_f)},
              'primary': {'value': (4.*f-m)/3., 'U_work': broadcast(norm_r),
                                        'grid_pair_cells': [cells['medium'], cells['fine']],
                                        'status': np.where(np.isfinite(broadcast(norm_r)), ESTABLISHED, UNKNOWN)},
              'same_conservative_U_for_all_five_xi': True}
    return {'status': ESTABLISHED if np.isfinite(norm_r).all() else 'partial_not_established',
            'times_s': times, 'xi': RANK_XI, 'components': ['C', 'T'], 'units': ['kg/kg', 'K'],
            'grid_cells': cells,
            'preferred_for_ranking': 'radial_sup_budget', 'radial_sup_budget': radial,
            'coordinate': 'fixed material xi, not fixed physical r',
            'space_and_time_basis': 'same independent local cubic L on every grid and time-control trajectory; formal values remain PCHIP',
            'direct_coarse': {'cells': cells['coarse'], 'value': c, 'U_work': np.full_like(c, np.nan), 'status': UNKNOWN,
                           'reason': 'No coarse-grid tight/cap runs were supplied; do not invent its total time budget.'},
            'direct_medium': {'cells': cells['medium'], 'value': m, 'U_space': space['U_medium'], 'time': time_m,
                           'U_reconstruction': rec_m, 'reconstruction_status': rec_status_m, 'U_work': um},
            'direct_fine': {'cells': cells['fine'], 'value': f, 'U_space': space['U_fine'], 'time': time_f,
                            'U_reconstruction': rec_f, 'reconstruction_status': rec_status_f, 'U_work': uf},
            'primary': {'value': (4.*f-m)/3., 'U_work': ur,
                                      'grid_pair_cells': [cells['medium'], cells['fine']],
                                      'status': np.where(np.isfinite(ur), ESTABLISHED, UNKNOWN),
                                      'value_kind': 'linear extrapolated field value'},
            'spatial_diagnostics': space, 'duplicate_shared_grid_difference': duplicate-m,
            'not_established_quantities': failed,
            'spatial_noise_assumption': 'Per-quantity medium/fine time-control differences diagnose temporal contamination of the three-grid sequence. The unmeasured coarse-grid time error is not given a certified bound.',
            'claim_scope': 'Per-frozen-point conditional working estimates; not a strict field envelope.'}


def _dense_coverage(bundle, prefix, left, right):
    a = bundle['a']; starts, ends = a[prefix+'_dense_starts'], a[prefix+'_dense_ends']
    if len(starts) == 0 or np.any(np.diff(ends) < 0.) or np.any(ends <= starts):
        raise ValueError('INVALID_DENSE_SEGMENTS: '+bundle['path'])
    cursor = left
    for start, end in zip(starts, ends):
        if end < cursor: continue
        if start > cursor: return False
        cursor = max(cursor, float(end))
        if cursor >= right: return True
    return False


def _dense_state(bundle, prefix, t):
    from 数值模型 import evaluate_saved_dense
    if not _dense_coverage(bundle, prefix, t, t):
        raise ValueError('NO_ACTUAL_DENSE_COVERAGE: '+bundle['path'])
    state = evaluate_saved_dense(bundle['a'], prefix, float(t))
    if not np.isfinite(state).all():
        raise ValueError('NONFINITE_DENSE_STATE')
    return state


def _event_point(bundles, t, component=0, snapshots=False, space_basis='L', extra=None):
    low, middle, tight, cap = bundles; cells = _grid_cells(bundles)
    def poly(bundle, prefix):
        x = bundle['a'][prefix+'_xi']
        if snapshots:
            times = bundle['a']['sample_times_s']; index = int(np.searchsorted(times, t))
            if index >= len(times) or times[index] != t:
                raise KeyError('MISSING_RANK_SNAPSHOT')
            y = bundle['a'][prefix+'_native_fields'][index, :, component]
        else:
            y = _dense_state(bundle, prefix, t)[:, component]
        return PchipInterpolator(x, y), _local_cubic(x, y), y
    c, lc, _ = poly(low, 'coarse'); duplicate, _, _ = poly(low, 'fine')
    m, lm, ym = poly(middle, 'coarse'); f, lf, yf = poly(middle, 'fine')
    mt, lmt, _ = poly(tight, 'coarse'); ft, lft, _ = poly(tight, 'fine')
    mc, lmc, _ = poly(cap, 'coarse'); fc, lfc, _ = poly(cap, 'fine')
    sc, sm, sf = (lc, lm, lf) if space_basis == 'L' else (c, m, f)
    smt, sft, smc, sfc = (lmt, lft, lmc, lfc) if space_basis == 'L' else (mt, ft, mc, fc)
    sme = sfe = None
    if extra is not None:
        me, lme, _ = poly(extra, 'coarse'); fe, lfe, _ = poly(extra, 'fine')
        sme, sfe = (lme, lfe) if space_basis == 'L' else (me, fe)
    dm = _combine([(1., sm), (-1., sc)]); df = _combine([(1., sf), (-1., sm)])
    nm, _, _ = _norm(dm); nf, peak, sign_f = _norm(df)
    floor = float(_floor(max(_norm(m)[0], _norm(f)[0]), POLICY['component_scales_C_T'][component]))
    tm, tf, time_details = [], [], []
    for base, tightened, reduced, further, target in ((sm, smt, smc, sme, tm), (sf, sft, sfc, sfe, tf)):
        dt = _norm(_combine([(1., base), (-1., tightened)]))[0]
        dc = _norm(_combine([(1., tightened), (-1., reduced)]))[0]
        de = None if further is None else _norm(_combine([(1., reduced), (-1., further)]))[0]
        detail = _time_from_differences(dt, dc, floor, de)
        time_details.append(detail)
        target.extend([dt, dc, float(detail['U'])])
    ratio = nm/nf if nf > 0 else math.nan
    alignment = _norm(_combine([(1., dm), (-ratio, df)]))[0]/nm if nm > 0 and np.isfinite(ratio) else math.inf
    same_shape_sign = float(dm(peak))*sign_f > 0.
    duplicate_difference = _norm(_combine([(1., duplicate), (-1., m)]))[0]
    noise = 2.*max(float(d['maximum_observed_difference']) for d in time_details)+floor
    space = _space_control(nm, nf, noise, same_shape_sign and alignment <= POLICY['norm_error_shape_alignment_max'] and duplicate_difference <= floor)
    rec_m_raw = _norm(_combine([(1., m), (-1., lm)]))[0]
    rec_f_raw = _norm(_combine([(1., f), (-1., lf)]))[0]
    def rec_value(delta, native):
        if np.all(native == native[0]): return 0.
        return 2.*delta if delta > floor else math.nan
    rec_m, rec_f = rec_value(rec_m_raw, ym), rec_value(rec_f_raw, yf)
    um = float(space['U_medium'])+tm[2]+rec_m
    uf = float(space['U_fine'])+tf[2]+rec_f
    extrapolated = _combine([(4./3., f), (-1./3., m)])
    maximum = _extrema(extrapolated)
    reasons = []
    if not bool(space['eligible']): reasons.append('radial_spatial_order_shape_or_noise_qualification_not_established')
    if not np.isfinite(tm[2]): reasons.append('radial_medium_time_control_not_established')
    if not np.isfinite(tf[2]): reasons.append('radial_fine_time_control_not_established')
    if not np.isfinite(rec_m): reasons.append('radial_medium_reconstruction_not_established')
    if not np.isfinite(rec_f): reasons.append('radial_fine_reconstruction_not_established')
    result = {'time_s': t, 'component': ['C', 'T'][component], 'unit': ['kg/kg', 'K'][component],
            'grid_cells': cells,
            'state_source': 'native_fixed_time_snapshots' if snapshots else 'actual_BDF_dense_polynomials',
            'space_and_time_basis': space_basis,
            'status': ESTABLISHED if np.isfinite(um+uf) else UNKNOWN,
            'not_established_reasons': reasons,
            'U_extrapolated_sup_work': (4.*uf+um)/3.,
            'direct_medium': {'cells': cells['medium'], 'U_space_sup': space['U_medium'], 'd_tol_sup': tm[0], 'd_cap_sup': tm[1],
                           'd_extra_sup': time_details[0]['d_extra'], 'time_control': time_details[0],
                           'U_time_sup': tm[2], 'U_rec_sup': rec_m, 'U_work_sup': um},
            'direct_fine': {'cells': cells['fine'], 'U_space_sup': space['U_fine'], 'd_tol_sup': tf[0], 'd_cap_sup': tf[1],
                            'd_extra_sup': time_details[1]['d_extra'], 'time_control': time_details[1],
                            'U_time_sup': tf[2], 'U_rec_sup': rec_f, 'U_work_sup': uf},
            'space': space, 'error_shape_alignment_defect': alignment,
            'same_sign_at_fine_difference_extremum': same_shape_sign,
            'duplicate_shared_grid_sup_difference': duplicate_difference, 'floating_floor': floor,
            'computed_field_max': maximum['maximum'], 'computed_max_xi': maximum['maximum_x'],
            'scope': 'Full radial polynomial difference norms; conditional norm-level work estimate, not a pointwise rigorous envelope.'}
    if component == 0:
        result.update(U_C_extrapolated_sup_work=(4.*uf+um)/3., computed_C_max=maximum['maximum'],
                      computed_residual=maximum['maximum']-.15)
    return result


def _maximum_functional_point(bundles, t, extra=None):
    """Budget max(C), never a linear combination of direct-grid root times."""
    from 数值模型 import maximum_reconstruction
    low, middle, tight, cap = bundles
    sources = [(low, 'coarse'), (middle, 'coarse'), (middle, 'fine'),
               (tight, 'coarse'), (tight, 'fine'), (cap, 'coarse'), (cap, 'fine')]
    if extra is not None:
        sources.extend([(extra, 'coarse'), (extra, 'fine')])
    maxima, locations, alternatives, native_states = [], [], [], []
    for bundle, prefix in sources:
        x = bundle['a'][prefix+'_xi']; native = _dense_state(bundle, prefix, t)[:, 0]
        p = PchipInterpolator(x, native); local = _local_cubic(x, native)
        pe, le = _extrema(p), _extrema(local)
        maxima.append(pe['maximum']); locations.append(pe['maximum_x']); native_states.append(native)
        alternatives.append({'P_max': pe['maximum'], 'P_max_xi': pe['maximum_x'],
                             'L_max': le['maximum'], 'L_max_xi': le['maximum_x']})
    q = np.asarray(maxima); floor = float(_floor(np.max(np.abs(q)), 2.55))
    tm = _time_control(q[1], q[3], q[5], 2.55, None if extra is None else q[7])
    tf = _time_control(q[2], q[4], q[6], 2.55, None if extra is None else q[8])
    duplicate = _dense_state(low, 'fine', t)[:, 0]
    duplicate_difference = float(np.max(np.abs(duplicate-native_states[1])))
    noise = 2*max(float(tm['maximum_observed_difference']), float(tf['maximum_observed_difference']))+floor
    space = _space_control(q[1]-q[0], q[2]-q[1], noise, duplicate_difference <= floor)
    common_xi = locations[1]
    same_peak = all(abs(x-common_xi) <= POLICY['peak_endpoint_tolerance'] for x in locations)
    rec, rec_status = [], []
    for i in (1, 2):
        x = middle['a'][('coarse' if i == 1 else 'fine')+'_xi']; values = native_states[i]
        at = int(np.argmin(np.abs(x-common_xi))); alt = alternatives[i]
        native_function = (abs(x[at]-common_xi) <= POLICY['peak_endpoint_tolerance'] and
                           abs(alt['L_max_xi']-common_xi) <= POLICY['peak_endpoint_tolerance'] and
                           abs(alt['P_max']-values[at]) <= floor and abs(alt['L_max']-values[at]) <= floor)
        if native_function:
            rec.append(0.); rec_status.append('not_applicable_max_functional_attained_at_same_native_point_under_full_P_and_L_search')
        else:
            difference = abs(alt['P_max']-alt['L_max'])
            allowed = abs(alt['L_max_xi']-common_xi) <= POLICY['peak_endpoint_tolerance'] and difference > floor
            rec.append(2*difference if allowed else math.nan)
            rec_status.append(ESTABLISHED if allowed else 'not_established_reconstruction_changes_peak_or_is_unresolved')
    actual_max, actual_location = maximum_reconstruction(middle['a']['fine_xi'], native_states[2],
                                                         middle['a']['coarse_xi'], native_states[1])
    commuting = float(actual_max-(4*q[2]-q[1])/3.)
    same_peak &= abs(actual_location-common_xi) <= POLICY['peak_endpoint_tolerance']
    commutation_valid = same_peak and abs(commuting) <= floor
    um = float(space['U_medium'])+float(tm['U'])+rec[0]
    uf = float(space['U_fine'])+float(tf['U'])+rec[1]
    eligible = commutation_valid and np.isfinite(um+uf)
    reasons = []
    if not bool(space['eligible']): reasons.append('maximum_functional_space_not_established')
    if not bool(tm['eligible']) or not bool(tf['eligible']): reasons.append('maximum_functional_time_not_established')
    if not all(np.isfinite(rec)): reasons.append('maximum_functional_reconstruction_not_established')
    if not commutation_valid: reasons.append('max_extrapolation_commutation_or_common_peak_not_demonstrated')
    return {'time_s': t, 'status': ESTABLISHED if eligible else UNKNOWN,
            'grid_cells': _grid_cells(bundles),
            'quantity': 'Q(t)=complete_radial_maximum_of_C', 'unit': 'kg/kg',
            'direct_maxima_coarse_medium_fine': q[:3], 'direct_peak_locations_production_tight_cap': locations[:7],
            'extra_time_peak_locations': locations[7:] if extra is not None else None,
            'all_peak_locations_including_extra': locations,
            'P_and_L_maximum_checks': alternatives,
            'space': space, 'time_direct_medium': tm, 'time_direct_fine': tf,
            'direct_medium_U_work': um, 'direct_fine_U_work': uf,
            'reconstruction_U_medium_fine': rec, 'reconstruction_status': rec_status,
            'U_maximum_extrapolated_work': (4*uf+um)/3.+abs(commuting) if eligible else math.nan,
            'U_commutation_roundoff': abs(commuting),
            'computed_C_max': float(actual_max), 'computed_max_xi': float(actual_location),
            'computed_residual': float(actual_max-.15), 'floating_floor': floor,
            'maximum_reconstruction_called': True, 'max_commutation_difference': commuting,
            'max_commutation_established': commutation_valid,
            'duplicate_shared_grid_native_max_difference': duplicate_difference,
            'not_established_reasons': reasons,
            'scope': 'Conditional maximum-functional work estimate only. Reconstruction NA here does not mean entire-field reconstruction error is zero.'}


def _scalar_dense_coefficients(bundle, prefix, left, right, state_index):
    a = bundle['a']; midpoint = (left+right)/2.
    ends = a[prefix+'_dense_ends']; j = min(int(np.searchsorted(ends, midpoint)), len(ends)-1)
    if not a[prefix+'_dense_starts'][j] <= midpoint <= ends[j]:
        raise ValueError('TIME_POLYNOMIAL_WOULD_EXTRAPOLATE')
    order = int(a[prefix+'_dense_orders'][j]); d = a[prefix+'_dense_coefficients'][j]
    result = np.zeros(6); result[0] = d[0, state_index]; basis = np.array([1.])
    for k in range(order):
        shift, denominator = a[prefix+'_dense_shifts'][j, k], a[prefix+'_dense_denominators'][j, k]
        basis = np.polynomial.polynomial.polymul(basis, [(left-shift)/denominator, (right-left)/denominator])
        result[:len(basis)] += d[k+1, state_index]*basis
    return result


def _endpoint_time_polynomial(bundle, left, right, endpoint):
    a = bundle['a']; knots = [left, right]
    for prefix in ('coarse', 'fine'):
        for key in ('_dense_starts', '_dense_ends'):
            knots.extend(v for v in a[prefix+key] if left < v < right)
    knots = np.unique(knots); coefficients = np.zeros((6, len(knots)-1))
    state_index = 0 if endpoint == 'axis' else -2
    for i, (begin, end) in enumerate(zip(knots[:-1], knots[1:])):
        medium = _scalar_dense_coefficients(bundle, 'coarse', begin, end, state_index)
        fine = _scalar_dense_coefficients(bundle, 'fine', begin, end, state_index)
        unit = (4.*fine-medium)/3.
        coefficients[:, i] = unit[::-1]/(end-begin)**np.arange(5, -1, -1)
    return PPoly(coefficients, knots, extrapolate=False)


def _event_budget(bundles, family, extra=None):
    if family == 'Q1': return {'status': 'not_applicable', 'reason': 'Q1 has fixed prescribed times, no drying event.'}
    middle = bundles[1]; t0 = middle['meta'].get('critical_time_s')
    if t0 is None: return {'status': UNKNOWN, 'reason': 'No completed middle-grid event.'}
    times = t0+np.asarray(POLICY['event_probe_offsets_s']); left, right = float(times[0]), float(times[-1])
    for bundle in bundles + ([extra] if extra is not None else []):
        for prefix in ('coarse', 'fine'):
            if not _dense_coverage(bundle, prefix, left, right):
                return {'status': UNKNOWN, 'value_kind': 'event_time', 'value_s': t0,
                        'reason': 'Required common physical-time neighborhood is not actually covered.',
                        'missing_coverage_file': bundle['path'], 'grid_prefix': prefix, 'required_window_s': [left, right]}
    probes = [_maximum_functional_point(bundles, float(t), extra) for t in times]
    field_norms = [_event_point(bundles, float(t), extra=extra) for t in times]
    legacy_norms = [_event_point(bundles, float(t), space_basis='P', extra=extra) for t in times]
    result = {'status': UNKNOWN, 'value_kind': 'event_time_of_maximum_of_extrapolated_field',
              'value_s': t0, 'U_work_s': None, 'probes': probes, 'window_s': [left, right],
              'quantity_for_error_propagation': 'radial maximum functional, not entire C field sup error',
              'entire_field_norm_diagnostics_L_decomposed': field_norms,
              'entire_field_norm_legacy_P_diagnostics': [{'time_s': p['time_s'], 'status': p['status'],
                                                        'p': p['space']['observed_order'],
                                                        'alignment': p['error_shape_alignment_defect']} for p in legacy_norms],
              'linear_combination_of_grid_root_times_used': False,
              'scope': 'Conditional maximum-functional/inverse-residual working estimate; no entire-field accuracy or strict interval certificate.'}
    if not all(p['status'] == ESTABLISHED for p in probes):
        result['reason'] = 'At least one maximum-functional budget or commutation check is not established.'
        return result
    tolerance = POLICY['peak_endpoint_tolerance']
    locations = np.array([p['computed_max_xi'] for p in probes])
    endpoint = 'axis' if np.all(locations <= tolerance) else ('surface' if np.all(locations >= 1.-tolerance) else None)
    if endpoint is None:
        result['reason'] = 'Peak moved, changed branch, or is an interior branch without a certified dense time derivative.'
        return result
    branch = _endpoint_time_polynomial(middle, left, right, endpoint)
    check_times = np.unique(np.r_[times, branch.x, (branch.x[:-1]+branch.x[1:])/2.])
    branch_checks = []
    for t in check_times:
        pm = PchipInterpolator(middle['a']['coarse_xi'], _dense_state(middle, 'coarse', float(t))[:, 0])
        pf = PchipInterpolator(middle['a']['fine_xi'], _dense_state(middle, 'fine', float(t))[:, 0])
        peak = _extrema(_combine([(4./3., pf), (-1./3., pm)]))
        position = peak['maximum_x']; branch_checks.append({'t_s': t, 'max_xi': position})
        if (endpoint == 'axis' and position > tolerance) or (endpoint == 'surface' and position < 1.-tolerance):
            result.update(reason='Observed peak branch changed inside the saved neighborhood.', branch_checks=branch_checks)
            return result
    derivative = _extrema(branch.derivative())
    raw_minimum_descent = -derivative['maximum']
    numerical_floor = float(_floor(max(abs(derivative['minimum']), abs(derivative['maximum'])), 0.))
    smin = POLICY['event_slope_margin_fraction']*raw_minimum_descent
    result.update(branch=endpoint, branch_checks=branch_checks, minimum_computed_branch_descent=raw_minimum_descent,
                  working_slope_lower_safety_value=smin, slope_minimum_at_s=derivative['maximum_x'],
                  slope_method='Differentiate actual native-endpoint BDF polynomials after field extrapolation; test all time-polynomial extrema. The 0.5 margin is empirical, not a theorem about the true PDE derivative.')
    if smin <= POLICY['space_noise_separation']*numerical_floor:
        result['reason'] = 'Near-tangency, nondecreasing residual, or unresolved descent.'; return result
    root_u = middle['meta'].get('root_tolerance_s')
    if root_u is None or not np.isfinite(root_u) or root_u <= 0.:
        result['reason'] = 'Root-location interface allowance is missing.'; return result
    root_residual_allowance = max(abs(derivative['minimum']), abs(derivative['maximum']))*root_u + probes[2]['floating_floor']
    if abs(probes[2]['computed_residual']) > root_residual_allowance:
        result.update(reason='Stored root does not match the recomputed extrapolated-field residual within its interface allowance.',
                      residual_at_reported_root=probes[2]['computed_residual'], residual_allowance=root_residual_allowance)
        return result
    field_u = max(p['U_maximum_extrapolated_work'] for p in probes)
    u_time = field_u/smin+root_u
    bracket_supported = probes[0]['computed_residual']-probes[0]['U_maximum_extrapolated_work'] > 0 and probes[-1]['computed_residual']+probes[-1]['U_maximum_extrapolated_work'] < 0
    result.update(U_maximum_functional_window_work=field_u, U_root_s=root_u, candidate_U_work_s=u_time,
                  root_location_source='metadata.root_tolerance_s; stored event-bracketing solver steps are not final brentq uncertainty brackets.',
                  robust_probe_bracket=bracket_supported,
                  assumptions=['The observed stable native-endpoint maximum remains active between branch checks.',
                               'The maximum of the five established maximum-functional work estimates represents this short neighborhood.',
                               'The empirically reduced computed-residual slope is usable for the conditional inverse-residual estimate.'])
    if not bracket_supported or u_time > min(t0-left, right-t0):
        result['reason'] = 'Working event interval is not supported inside the actually evaluated neighborhood.'; return result
    result.update(status=ESTABLISHED, U_work_s=u_time, interval_s=[t0-u_time, t0+u_time])
    return result


def analyze_case(case_id, low_json, middle_json, tight_json, cap_json, extra_time_json=None):
    """Return JSON-safe budgets; invalid identity never silently selects another case."""
    result = {'case_id': case_id, 'policy': dict(POLICY), 'status': UNKNOWN,
              'document_sections': ['8.3', '8.4 numerical-input budget only', '8.5'],
              'PDE_runs_started': 0, 'strict_error_bound_claimed': False}
    paths = dict(low=low_json, middle=middle_json, tight=tight_json, cap=cap_json)
    extra = None
    try:
        bundles = [_load(case_id, p) for p in paths.values()]
        _validate(bundles)
        if extra_time_json is not None:
            extra = _load(case_id, extra_time_json)
            _validate_extra_time(bundles, extra)
    except FileNotFoundError as exc:
        result.update(reason='required_input_not_available', detail=str(exc), supplied_paths={k: str(v) for k, v in paths.items()})
        return _safe(result)
    except LookupError as exc:
        result.update(reason='required_completed_evidence_not_available', detail=str(exc))
        return _safe(result)
    except Exception as exc:
        result.update(status='invalid_input', reason=type(exc).__name__+': '+str(exc))
        return _safe(result)
    result['sources'] = {key: {'metadata_file': b['path'], 'arrays_file': b['arrays_path'],
                               'version': b['meta'].get('version'), 'accuracy': b['meta']['accuracy'],
                               'source_freeze': b['meta'].get('source_freeze'),
                               'case_identity_checked': True} for key, b in zip(paths, bundles)}
    result['parameters'] = bundles[1]['meta'].get('parameters')
    result['grid_cells'] = _grid_cells(bundles)
    result['extra_time_control_used'] = extra is not None
    if extra is not None:
        result['sources']['extra_time'] = {'metadata_file': extra['path'], 'arrays_file': extra['arrays_path'],
                                          'version': extra['meta'].get('version'), 'accuracy': extra['meta']['accuracy'],
                                          'case_identity_checked': True, 'grid_and_half_cap_checked': True}
    family = bundles[1]['meta']['case']['family']; result['family'] = family
    for key, function in (('fields', _field_budget), ('event', _event_budget)):
        try: result[key] = function(bundles, family, extra)
        except Exception as exc: result[key] = {'status': UNKNOWN, 'reason': type(exc).__name__+': '+str(exc)}
    statuses = [result[k]['status'] for k in ('fields', 'event') if result[k]['status'] != 'not_applicable']
    result['status'] = ESTABLISHED if statuses and all(s == ESTABLISHED for s in statuses) else 'partial_or_not_established'
    return _safe(result)


def _combine_quartic(terms):
    knots = np.unique(np.concatenate([p.x for _, p in terms])); left = knots[:-1]
    result = np.zeros((5, len(left)))
    for weight, poly in terms:
        index = np.clip(np.searchsorted(poly.x, left, side='right')-1, 0, len(poly.x)-2)
        z = left-poly.x[index]; a, b, c, d, e = poly.c[:, index]
        result += weight*np.array([a, 4*a*z+b, 6*a*z*z+3*b*z+c,
                                    4*a*z**3+3*b*z*z+2*c*z+d,
                                    (((a*z+b)*z+c)*z+d)*z+e])
    return PPoly(result, knots, extrapolate=False)


def _quartic_norm(poly):
    width = np.diff(poly.x)
    unit = poly.c*width[None, :]**np.arange(4, -1, -1)[:, None]
    local = PPoly(unit, np.arange(len(width)+1, dtype=float), extrapolate=False)
    roots = local.derivative().roots(discontinuity=False, extrapolate=False)
    roots = roots[np.isfinite(roots)]
    return float(np.max(np.abs(np.r_[unit[-1], np.sum(unit, axis=0), local(roots)])))


def validate_mms_decomposition(case_id, low_json, middle_json, tight_json, cap_json):
    """Check the same L decomposition against every saved MMS time, without PDE runs.

    The available MMS packs use 160/320 and 320/640. Initial nodes are an
    explicitly prescribed structural case, not a fabricated zero GCI estimate.
    """
    import mms_reference
    bundles = [_load(case_id, path) for path in (low_json, middle_json, tight_json, cap_json)]
    _validate(bundles)
    cells = _grid_cells(bundles)
    for bundle in bundles:
        if not bundle['meta']['parameters'].get('mms') or bundle['meta']['parameters'] != bundles[1]['meta']['parameters']:
            raise ValueError('MMS_REFERENCE_PARAMETER_MISMATCH')
        for prefix in ('coarse', 'fine'):
            bundle['a'][prefix+'_native_fields'] = bundle['a'][prefix+'_mms_native_fields']
    production = dict(rtol=2e-12, atol_C=1e-14, atol_T=1e-13, max_step=60.)
    expected_acc = [production, production,
                    dict(rtol=2e-13, atol_C=1e-15, atol_T=1e-14, max_step=60.),
                    dict(rtol=2e-13, atol_C=1e-15, atol_T=1e-14, max_step=30.)]
    for bundle, accuracy in zip(bundles, expected_acc):
        if bundle['meta']['accuracy'] != accuracy:
            raise ValueError('MMS_TIME_CONTROL_MISMATCH')
    times = bundles[1]['a']['sample_times_s']
    if not all(np.array_equal(b['a']['sample_times_s'], times) for b in bundles):
        raise ValueError('MMS_SAMPLE_TIMES_MISMATCH')
    duplicate = float(np.max(np.abs(bundles[0]['a']['fine_native_fields']-bundles[1]['a']['coarse_native_fields'])))
    summaries = {label: {'times_checked': 0, 'qualified_times': 0, 'structural_initial_times': 0,
                         'not_established_positive_times': 0, 'underestimated_qualified_bounds': 0,
                         'minimum_U_over_actual': None, 'minimum_ratio_record': None} for label in ('C', 'T')}
    rows = []
    middle = bundles[1]
    for index, t in enumerate(times):
        errors = []
        for prefix in ('coarse', 'fine'):
            errors.append(mms_reference._reconstruction_error(float(t), middle['a'][prefix+'_xi'],
                                                               middle['a'][prefix+'_native_fields'][index]))
        for component, label in enumerate(('C', 'T')):
            budget = _event_point(bundles, float(t), component, snapshots=True)
            em = PPoly(errors[0].c[:, :, component], errors[0].x, extrapolate=False)
            ef = PPoly(errors[1].c[:, :, component], errors[1].x, extrapolate=False)
            actual = [_quartic_norm(em), _quartic_norm(ef),
                      _quartic_norm(_combine_quartic([(4./3., ef), (-1./3., em)]))]
            u = [budget['direct_medium']['U_work_sup'], budget['direct_fine']['U_work_sup'],
                 budget['U_extrapolated_sup_work']]
            summary = summaries[label]; summary['times_checked'] += 1
            row = {'time_s': float(t), 'component': label, 'grid_pair_cells': [cells['medium'], cells['fine']],
                   'quantity_order': ['direct_medium', 'direct_fine', 'primary'],
                   'actual_P_error_medium_fine_primary': actual,
                   'U_work_medium_fine_primary': u, 'budget_status': budget['status'],
                   'observed_order_L': budget['space']['observed_order'],
                   'shape_alignment_L': budget['error_shape_alignment_defect'],
                   'not_established_reasons': budget['not_established_reasons']}
            if t == 0.:
                summary['structural_initial_times'] += 1
                row['initial_condition_scope'] = 'Prescribed analytic nodal initial field; no GCI/time qualification inferred. Actual P reconstruction errors remain explicitly listed.'
            elif budget['status'] == ESTABLISHED:
                summary['qualified_times'] += 1
                for kind, bound, error in zip(('direct_medium', 'direct_fine', 'primary'), u, actual):
                    if bound+budget['floating_floor'] < error:
                        summary['underestimated_qualified_bounds'] += 1
                    if error > budget['floating_floor'] and (summary['minimum_U_over_actual'] is None or bound/error < summary['minimum_U_over_actual']):
                        summary['minimum_U_over_actual'] = bound/error
                        summary['minimum_ratio_record'] = {'time_s': float(t), 'quantity': kind, 'U': bound, 'actual_error': error}
            else:
                summary['not_established_positive_times'] += 1
            rows.append(row)
    return _safe({'case_id': case_id, 'policy': dict(POLICY), 'PDE_runs_started': 0,
                  'sources': [b['path'] for b in bundles], 'reference_source': mms_reference.__file__,
                  'grid_cells': cells, 'duplicate_shared_grid_native_difference': duplicate,
                  'summaries': summaries, 'rows': rows,
                  'scope': 'Empirical non-underestimation check for all qualified saved-time radial sup quantities, including direct and extrapolated P outputs. Not a general proof or full-model acceptance.'})


def self_check():
    """Small algebra/qualification checks, without running or altering any PDE."""
    x = np.array([0., .07, .23, .51, .72, 1.]); y = x**3-2*x*x+.4*x+1.
    p = _local_cubic(x, y); q = np.linspace(0., 1., 301)
    assert np.max(np.abs(p(q)-(q**3-2*q*q+.4*q+1.))) < 2e-13
    hill = PPoly(np.array([[0.], [-1.], [1.], [0.]]), [0., 1.])
    e = _extrema(hill); assert abs(e['maximum']-.25) < 1e-14 and abs(e['maximum_x']-.5) < 1e-14
    twice = _combine([(2., PchipInterpolator(x, y)), (-1., PchipInterpolator(x, y))])
    assert np.max(np.abs(twice(q)-PchipInterpolator(x, y)(q))) < 1e-13
    spatial = _space_control(np.array([.04, 0., .04, .04]), np.array([.01, 0., -.01, .01]), np.array([1e-8, 1e-8, 1e-8, .002]))
    assert spatial['eligible'].tolist() == [True, False, False, False]
    zero = _time_control(np.array([1.]), np.array([1.]), np.array([1.]), 1.)
    assert not zero['eligible'][0] and not np.isfinite(zero['U'][0])
    pending = _time_from_differences(1e-6, 5e-6, 1e-12)
    supported = _time_from_differences(1e-6, 5e-6, 1e-12, 2e-6)
    still_growing = _time_from_differences(1e-6, 5e-6, 1e-12, 6e-6)
    new_adverse_evidence = _time_from_differences(2e-6, 1e-6, 1e-12, 3e-6)
    assert not pending['eligible'] and pending['original_cap_drift']
    assert supported['eligible'] and supported['original_cap_drift_resolved_by_extra']
    assert supported['d_tol'] == pending['d_tol'] and supported['d_cap'] == pending['d_cap']
    assert supported['U'] == 2*5e-6 and not still_growing['eligible']
    assert not new_adverse_evidence['original_cap_drift'] and not new_adverse_evidence['eligible']
    alternate_x = np.array([0., .02, .1, .4, .63, .91, 1.])
    pa = PchipInterpolator(x, y)
    pb = PchipInterpolator(alternate_x, alternate_x**3-2*alternate_x**2+.4*alternate_x+1.)
    difference = _combine([(1., pa), (-1., pb)])
    assert np.max(np.abs(difference(q)-(pa(q)-pb(q)))) < 3e-13
    dense_points = np.linspace(0., 1., 20001)
    assert _norm(difference)[0]+1e-13 >= np.max(np.abs(pa(dense_points)-pb(dense_points)))
    rate = 3e-7; arrays = {}
    for prefix in ('coarse', 'fine'):
        d = np.zeros((1, 6, 4)); d[0, 0, 0] = .15-60.*rate; d[0, 1, 0] = -120.*rate
        arrays.update({prefix+'_dense_starts': np.array([0.]), prefix+'_dense_ends': np.array([120.]),
                       prefix+'_dense_orders': np.array([1]), prefix+'_dense_coefficients': d,
                       prefix+'_dense_shifts': np.array([[120., 0., 0., 0., 0.]]),
                       prefix+'_dense_denominators': np.array([[120., 1., 1., 1., 1.]])})
    fake = {'a': arrays, 'path': 'in_memory_exact_linear_dense_control'}
    branch = _endpoint_time_polynomial(fake, 0., 120., 'axis')
    tt = np.linspace(0., 120., 21)
    assert np.max(np.abs(branch(tt)-(.15-rate*(tt-60.)))) < 1e-14
    assert abs(_extrema(branch.derivative())['maximum']+rate) < 1e-18
    assert _dense_coverage(fake, 'coarse', 0., 120.) and not _dense_coverage(fake, 'coarse', -1., 120.)
    quartic = PPoly(np.array([[1.], [-2.], [1.5], [-.5], [.0625]]), [0., 1.])
    assert abs(_quartic_norm(quartic)-.0625) < 1e-13
    for n in (160, 320, 640):
        packs = []
        for stage, pair in enumerate(((n, 2*n), (2*n, 4*n), (2*n, 4*n), (2*n, 4*n))):
            accuracy = dict(rtol=2e-12 if stage < 2 else 2e-13,
                            atol_C=1e-14 if stage < 2 else 1e-15,
                            atol_T=1e-13 if stage < 2 else 1e-14,
                            max_step=30. if stage == 3 else 60.)
            packs.append({'path': 'in_memory_grid_structure_check',
                          'meta': {'grids': [{'cells': k} for k in pair], 'accuracy': accuracy,
                                   'parameters': {'family': 'Q1'}, 'version': 'structure-check',
                                   'numpy': 'structure-check', 'scipy': 'structure-check'},
                          'a': {prefix+'_xi': 1-(1-np.linspace(0., 1., k+1))**1.5
                                for prefix, k in zip(('coarse', 'fine'), pair)}})
        _validate(packs)
        assert _grid_cells(packs) == dict(coarse=n, medium=2*n, fine=4*n)
    json.dumps(_safe({'U': np.array([np.nan, 1.]), 'flag': np.bool_(True)}), allow_nan=False)
    return {'status': 'algebra_and_near_zero_semantics_checked', 'PDE_runs': 0,
            'checks': ['local cubic exactness', 'interior polynomial maximum', 'PPoly alignment',
                       'cross-grid PPoly vs direct evaluation', 'actual dense polynomial field extrapolation and derivative',
                       'out-of-coverage rejection', 'sign/noise/per-quantity qualification',
                       'metadata-driven 160/320/640, 320/640/1280 and 640/1280/2560 grid ladders',
                       'additional time evidence retains old differences and requires non-growth',
                       'new growing evidence invalidates an originally qualified time comparison',
                       'zero time differences stay unknown', 'JSON null handling']}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-id')
    parser.add_argument('--low', type=Path)
    parser.add_argument('--middle', type=Path)
    parser.add_argument('--tight', type=Path)
    parser.add_argument('--cap', type=Path)
    parser.add_argument('--extra-time', type=Path, help='Optional further same-grid/time-tolerance run with half the cap step.')
    parser.add_argument('--mms', action='store_true', help='Validate the complete L decomposition against the saved MMS analytic field.')
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--output', type=Path, help='Optional new JSON file; existing evidence is not overwritten.')
    arguments = parser.parse_args()
    if arguments.self_check or not arguments.case_id:
        if arguments.mms:
            parser.error('--mms requires --case-id and the four input paths.')
        output = self_check()
    else:
        if arguments.mms:
            if arguments.extra_time is not None:
                parser.error('The MMS decomposition check currently uses its four frozen input packs.')
            output = validate_mms_decomposition(arguments.case_id, arguments.low, arguments.middle, arguments.tight, arguments.cap)
        else:
            output = analyze_case(arguments.case_id, arguments.low, arguments.middle, arguments.tight, arguments.cap, arguments.extra_time)
    serialized = json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    if arguments.output:
        if arguments.output.exists():
            parser.error('Existing output is preserved; select a new evidence path.')
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized)
    else:
        print(serialized, end='')
