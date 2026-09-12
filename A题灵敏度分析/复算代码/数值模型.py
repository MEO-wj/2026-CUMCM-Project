"""Parameterized copy of the verified radial finite-volume/BDF equations.

Analysis outputs are sparse, unrounded snapshots. Production answer files are
never written. Coarse and fine trajectories advance to the same boundaries.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

from dataclasses import dataclass
import time
import numpy as np
import scipy
from scipy.integrate import BDF
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from scipy.sparse import diags

VERSION = 'sensitivity-common-trajectory-20260912-v3'
RANK_XI = np.array([0., .25, .5, .75, 1.])
EARLY = np.array([1., 5., 10., 30., 60., 100.])
RANK_TIMES = {'Q1': np.array([100., 300., 600., 900., 1200., 1500., 1800.]),
              'Q23': np.arange(1800., 10801., 1800.),
              'Q4': np.arange(1800., 21601., 1800.)}
FACTORS = ('A_scale', 'a_scale', 'B_scale', 'h_scale', 'hm_scale',
           'k_scale', 'b_scale', 'C0_scale', 'R0_scale', 'shrink_amplitude_eta')


from 输入读取 import load_observations


def parameters(case):
    family = case['family']
    if family not in ('Q1', 'Q23', 'Q4'):
        raise ValueError(f'Unknown family: {family}')
    factors = dict.fromkeys(FACTORS, 1.)
    overrides = case.get('overrides', {})
    if set(overrides) - set(factors):
        raise ValueError(f'Unknown parameter overrides: {set(overrides) - set(factors)}')
    factors.update(overrides)
    if case.get('mms') and (overrides or family == 'Q1' or
            case.get('geometry', 'shrink' if family == 'Q4' else 'fixed') !=
            ('shrink' if family == 'Q4' else 'fixed')):
        raise ValueError('The frozen MMS sources support only unscaled Q23/fixed and Q4/moving controls.')
    if not all(np.isfinite(v) and v > 0 for v in factors.values()):
        raise ValueError('All parameter factors must be finite and positive.')
    A, a, B = {'Q1': (7e-9, .89, 0.), 'Q23': (2.4e-3, .45, 3850.),
               'Q4': (4.2e-4, .30, 3850.)}[family]
    return {**factors, 'family': family, 'A': A*factors['A_scale'],
            'a': a*factors['a_scale'], 'B': B*factors['B_scale'],
            'h': 25.*factors['h_scale'], 'hm': 8e-7*factors['hm_scale'],
            'C0': 2.55*factors['C0_scale'], 'T0': 28.,
            'R0': .02*factors['R0_scale'],
            'geometry': case.get('geometry', 'shrink' if family == 'Q4' else 'fixed'),
            'radius_method': case.get('radius_method', 'pchip'),
            'environment_tail': case.get('environment_tail', 'E0'),
            'tail_T_delta': float(case.get('tail_T_delta', 0.)),
            'tail_C_delta': float(case.get('tail_C_delta', 0.)),
            'mms': bool(case.get('mms', False)),
            'closed': bool(case.get('closed', False)),
            'initial_profile': case.get('initial_profile', 'uniform')}


def material(c, p):
    if p['family'] == 'Q1':
        k, b = .36, 820.*2600.
    elif p['family'] == 'Q4':
        k = .12 + .20*c/(1+c)
        b = (760+90*c)*(1850+2150*c/(1+c))
    else:
        k = .21 + .38*c/(1+c)
        b = (650+128*c)*(1450+2736*c/(1+c))
    return k*p['k_scale'], b*p['b_scale']


class Inputs:
    def __init__(self, environment, radius_data, p):
        self.raw = np.asarray(environment, float)
        self.radius_data = np.asarray(radius_data, float)
        self.p = p
        rows = self.raw[(self.raw[:, 0] >= 10800.) & (self.raw[:, 0] <= 14400.), 1:]
        if rows.shape != (61, 2):
            raise ValueError('Expected the 61 inclusive final-hour observations.')
        tails = {'E0': rows.mean(axis=0),
                 'E1': self.raw[(self.raw[:, 0] >= 12600.) & (self.raw[:, 0] <= 14400.), 1:].mean(axis=0),
                 'E2': self.raw[self.raw[:, 0] == 14400., 1:][0],
                 'E3': np.array([50., .05])}
        self.tail = tails[p['environment_tail']] + [p['tail_T_delta'], p['tail_C_delta']]
        self.rp = PchipInterpolator(self.radius_data[:, 0], self.radius_data[:, 1]*.01,
                                    extrapolate=False)

    def radius(self, t):
        p = self.p
        if p['mms']:
            from 制造解参考 import radius
            return radius(t, p['geometry'] == 'shrink')
        if p['geometry'] == 'fixed':
            return np.full_like(np.asarray(t, float), p['R0'])
        if np.any(np.asarray(t) > self.radius_data[-1, 0]):
            raise ValueError('Measured radius time coverage exceeded.')
        raw = self.rp(t) if p['radius_method'] == 'pchip' else np.interp(
            t, self.radius_data[:, 0], self.radius_data[:, 1]*.01)
        R = .02 + p['shrink_amplitude_eta']*(raw-.02)
        if np.any(R <= 0):
            raise ValueError('Nonpositive radius.')
        return R

    def ambient(self, t, begin, finish):
        if self.p['mms']:
            from 制造解参考 import boundary
            return np.asarray(boundary(t, self.p['family'], self.p['geometry'] == 'shrink'))
        if begin >= 14400.:
            return self.tail
        va = np.array([np.interp(begin, self.raw[:, 0], self.raw[:, j]) for j in (1, 2)])
        vb = np.array([np.interp(finish, self.raw[:, 0], self.raw[:, j]) for j in (1, 2)])
        slope = (vb-va)/(finish-begin)
        return va+(t-begin)*slope

    def boundaries(self, limit):
        if self.p['mms']:
            return np.r_[np.arange(0., limit, 1800.), limit]
        knots = np.r_[0., self.raw[(self.raw[:, 0] > 0) & (self.raw[:, 0] < limit), 0], limit]
        if self.p['geometry'] == 'shrink':
            knots = np.r_[knots, self.radius_data[(self.radius_data[:, 0] > 0) &
                                                (self.radius_data[:, 0] < limit), 0]]
        elif self.p['family'] != 'Q1':
            knots = np.r_[knots, np.arange(16200., limit, 1800.)]
        return np.unique(knots)


@dataclass
class Accuracy:
    rtol: float = 2e-12
    atol_C: float = 1e-14
    atol_T: float = 1e-13
    max_step: float = 60.


class Grid:
    def __init__(self, cells, inputs, accuracy, sample_times, sample_xi):
        self.inputs, self.p, self.accuracy = inputs, inputs.p, accuracy
        self.cells = cells
        self.xi = 1-(1-np.linspace(0, 1, cells+1))**1.5
        self.n = cells+1
        self.faces = np.r_[0., (self.xi[1:]+self.xi[:-1])/2, 1.]
        self.volumes = np.diff(self.faces**2)/2
        self.dx = np.diff(self.xi)
        gauss, weights = np.polynomial.legendre.leggauss(8)
        self.gauss, self.weights = (gauss[:, None]+1)/2, weights/2
        self.source_xi = self.faces[:-1] + (self.faces[1:]-self.faces[:-1])*self.gauss
        self.source_weights = self.weights[:, None]*self.source_xi*np.diff(self.faces)/self.volumes
        self.sparse = diags([np.ones(2*self.n)]*7, range(-3, 4),
                           shape=(2*self.n, 2*self.n), format='csc')
        self.y = np.tile([self.p['C0'], self.p['T0']], self.n)
        if self.p['mms']:
            from 制造解参考 import exact
            self.y = np.asarray(exact(0., self.xi)).ravel()
        elif self.p['initial_profile'] == 'nonuniform':
            self.y.reshape(-1, 2)[:, 0] = 1+.2*(1-self.xi**2)**2
        self.times, self.targets = np.asarray(sample_times), np.asarray(sample_xi)
        self.fields = np.full((len(self.times), len(self.targets), 2), np.nan)
        self.native_fields = []
        self.physical = np.full((len(self.times), 5, 2), np.nan)
        self.exact_error = []
        self.mms_field_errors = []
        self.mms_native_fields = []
        self.index = 0
        self.blocks = []
        self.current_block = []
        self.event = None
        self.event_bracket = None
        self.nfev = self.njev = self.nlu = self.steps = 0
        self.min_step, self.max_step = np.inf, 0.
        self.begin = self.end = 0.
        self.elapsed = 0.
        if len(self.times) and self.times[0] == 0:
            self.sample(0, self.y)
            self.index = 1

    def rhs(self, t, y):
        p = self.p
        ct = y.reshape(self.n, 2)
        c, temperature = ct[:, 0], ct[:, 1]
        R = float(self.inputs.radius(t))
        if p['mms']:
            tair, cair = self.inputs.ambient(t, self.begin, self.end)
        else:
            tair, cair = self.ambient_begin+(t-self.begin)*self.ambient_slope
        dc = np.diff(c)
        cq = c[:-1][None, :]+self.gauss*dc[None, :]
        effective = self.weights @ np.exp(-p['a']/cq)
        thermal = np.exp(-p['B']/(temperature+273.15))
        df = p['A']*effective*(thermal[:-1]+thermal[1:])/2
        k, capacity = material(c, p)
        kf = (k[:-1]+k[1:])/2 if np.ndim(k) else k
        hm, h = (0. if p['closed'] else p['hm']), p['h']
        qc = np.r_[0., self.faces[1:-1]*df*dc/self.dx, R*hm*(cair-c[-1])]
        qt = np.r_[0., self.faces[1:-1]*kf*np.diff(temperature)/self.dx,
                   R*h*(tair-temperature[-1])]
        rate = np.empty_like(ct)
        rate[:, 0] = np.diff(qc)/(R*R*self.volumes)
        rate[:, 1] = np.diff(qt)/(R*R*self.volumes*capacity)
        if p['mms']:
            from 制造解参考 import source
            value = source(t, self.source_xi.ravel(), p['family']).reshape(8, self.n, 2)
            averaged = np.sum(self.source_weights[:, :, None]*value, axis=0)
            rate[:, 0] += averaged[:, 0]
            rate[:, 1] += averaged[:, 1]/capacity
        return rate.ravel()

    def sample(self, index, state):
        native = state.reshape(self.n, 2)
        self.native_fields.append(native.copy())
        t = self.times[index]
        interp = PchipInterpolator(self.xi, native, axis=0)
        self.fields[index] = interp(self.targets)
        physical_targets = np.arange(5)*.005/float(self.inputs.radius(t))
        inside = physical_targets <= 1+1e-14
        self.physical[index, inside] = interp(np.minimum(physical_targets[inside], 1.))
        if self.p['mms']:
            from 制造解参考 import exact, error_maximum, integrated_L2
            error = native-exact(t, self.xi)
            fine_error = self.fields[index]-exact(t, self.targets)
            entire_max, entire_location = error_maximum(t, self.xi, native)
            self.mms_field_errors.append(fine_error)
            self.mms_native_fields.append(native.copy())
            self.exact_error.append({'t': float(t),
                'L2': np.sqrt(np.sum(2*self.volumes[:, None]*error**2, axis=0)).tolist(),
                'L2_reconstructed': integrated_L2(t, self.xi, native).tolist(),
                'Linf_reconstructed': entire_max.tolist(),
                'Linf_reconstructed_xi': entire_location.tolist(),
                'Linf_native': np.max(np.abs(error), axis=0).tolist(),
                'Linf_eval': np.max(np.abs(fine_error), axis=0).tolist(),
                'axis': np.abs(error[0]).tolist(), 'surface': np.abs(error[-1]).tolist()})

    def advance(self, begin, finish):
        self.begin, self.end = begin, finish
        if not self.p['mms']:
            if begin >= 14400.:
                self.ambient_begin, self.ambient_slope = self.inputs.tail, np.zeros(2)
            else:
                raw = self.inputs.raw
                self.ambient_begin = np.array([np.interp(begin, raw[:, 0], raw[:, j]) for j in (1, 2)])
                vb = np.array([np.interp(finish, raw[:, 0], raw[:, j]) for j in (1, 2)])
                self.ambient_slope = (vb-self.ambient_begin)/(finish-begin)
        tic = time.perf_counter()
        previous = self.current_block
        current = []
        a = self.accuracy
        solver = BDF(self.rhs, begin, self.y, finish, rtol=a.rtol,
                     atol=np.tile([a.atol_C, a.atol_T], self.n),
                     max_step=a.max_step, jac_sparsity=self.sparse)
        while solver.status == 'running':
            old_t = solver.t
            old_max = float(solver.y[0::2].max())
            message = solver.step()
            if solver.status == 'failed':
                raise RuntimeError(message)
            dense = solver.dense_output()
            current.append(dense)
            dt = solver.t-old_t
            self.steps += 1
            self.min_step = min(self.min_step, dt)
            self.max_step = max(self.max_step, dt)
            stop = np.searchsorted(self.times, solver.t, side='right')
            while self.index < stop:
                self.sample(self.index, dense(self.times[self.index]))
                self.index += 1
            if self.event is None and old_max > .15 >= float(solver.y[0::2].max()):
                self.event = brentq(lambda t: float(dense(t)[0::2].max())-.15,
                                    old_t, solver.t, xtol=1e-8)
                self.event_bracket = [float(old_t), float(solver.t)]
        self.y = current[-1](finish)
        self.current_block = current
        self.blocks = previous + current
        self.nfev += solver.nfev
        self.njev += solver.njev
        self.nlu += solver.nlu
        self.elapsed += time.perf_counter()-tic

    def evaluate(self, t):
        ends = np.array([d.t for d in self.blocks])
        j = min(int(np.searchsorted(ends, t)), len(ends)-1)
        d = self.blocks[j]
        if not d.t_old-1e-8 <= t <= d.t+1e-8:
            raise ValueError(f'Time {t} outside actual dense interval [{d.t_old}, {d.t}].')
        return d(t).reshape(self.n, 2)

    def metadata(self):
        return {'cells': self.cells, 'grading': 1.5, 'rtol': self.accuracy.rtol,
                'atol_C': self.accuracy.atol_C, 'atol_T': self.accuracy.atol_T,
                'max_step_config_s': self.accuracy.max_step,
                'accepted_step_min_s': self.min_step, 'accepted_step_max_s': self.max_step,
                'accepted_steps': self.steps, 'nfev': self.nfev, 'njev': self.njev,
                'nlu': self.nlu, 'event_s': self.event, 'event_bracket': self.event_bracket,
                'actual_end_s': self.end, 'elapsed_s': self.elapsed}


def maximum_reconstruction(xfine, fine, xcoarse, coarse):
    """Exact maximum of the defined piecewise cubic extrapolated field."""
    p, q = PchipInterpolator(xfine, fine), PchipInterpolator(xcoarse, coarse)
    left = xfine[:-1]
    j = np.minimum(np.searchsorted(xcoarse, left, side='right')-1, len(xcoarse)-2)
    delta = left-xcoarse[j]
    a, b, c, d = q.c[:, j]
    shifted = np.array([a, 3*a*delta+b, 3*a*delta**2+2*b*delta+c,
                        a*delta**3+b*delta**2+c*delta+d])
    coeff = (4*p.c-shifted)/3.
    width = np.diff(xfine)
    values = (4*fine-q(xfine))/3.
    index = int(np.argmax(values))
    maximum, where = float(values[index]), float(xfine[index])
    A, B, C = 3*coeff[0], 2*coeff[1], coeff[2]
    disc = B*B-4*A*C
    valid = (disc >= 0) & (np.abs(A) > 1e-30)
    roots = []
    for sign in (-1., 1.):
        r = np.full_like(left, np.nan)
        r[valid] = (-B[valid]+sign*np.sqrt(disc[valid]))/(2*A[valid])
        roots.append(r)
    linear = (np.abs(A) <= 1e-30) & (np.abs(B) > 1e-30)
    r = np.full_like(left, np.nan)
    r[linear] = -C[linear]/B[linear]
    roots.append(r)
    for r in roots:
        inside = (r > 0) & (r < width)
        if np.any(inside):
            x = r[inside]
            a, b, c, d = coeff[:, inside]
            v = ((a*x+b)*x+c)*x+d
            k = int(np.argmax(v))
            if v[k] > maximum:
                maximum, where = float(v[k]), float(left[inside][k]+x[k])
    return maximum, where


def pack_dense(segments, prefix):
    """Store the actual BDF interpolation polynomials, without time extrapolation."""
    count = len(segments)
    dimension = segments[0].D.shape[1]
    coefficients = np.zeros((count, 6, dimension))
    shifts, denominators = np.zeros((count, 5)), np.ones((count, 5))
    for j, segment in enumerate(segments):
        order = segment.order
        coefficients[j, :order+1] = segment.D
        shifts[j, :order] = segment.t_shift
        denominators[j, :order] = segment.denom
        midpoint = (segment.t_old+segment.t)/2
        product = np.cumprod((midpoint-shifts[j, :order])/denominators[j, :order])
        reconstructed = coefficients[j, 1:order+1].T @ product + coefficients[j, 0]
        if not np.array_equal(reconstructed, segment(midpoint)):
            raise RuntimeError('Serialized BDF polynomial did not reproduce its original midpoint.')
    return {prefix+'_dense_starts': np.array([s.t_old for s in segments]),
            prefix+'_dense_ends': np.array([s.t for s in segments]),
            prefix+'_dense_orders': np.array([s.order for s in segments]),
            prefix+'_dense_shifts': shifts, prefix+'_dense_denominators': denominators,
            prefix+'_dense_coefficients': coefficients}


def evaluate_saved_dense(arrays, prefix, t):
    """Evaluate a saved event-neighborhood trajectory only inside actual coverage."""
    starts, ends = arrays[prefix+'_dense_starts'], arrays[prefix+'_dense_ends']
    j = min(int(np.searchsorted(ends, t)), len(ends)-1)
    if not starts[j]-1e-8 <= t <= ends[j]+1e-8:
        raise ValueError('Requested time is outside saved dense trajectory coverage.')
    order = int(arrays[prefix+'_dense_orders'][j])
    shifts = arrays[prefix+'_dense_shifts'][j, :order]
    denominators = arrays[prefix+'_dense_denominators'][j, :order]
    D = arrays[prefix+'_dense_coefficients'][j, :order+1]
    value = D[1:].T @ np.cumprod((t-shifts)/denominators) + D[0]
    return value.reshape(-1, 2)


def solve(case, environment, radius_data, coarse_cells=320, accuracy=None,
          sample_times=None, sample_xi=None, progress=None):
    p = parameters(case)
    data = Inputs(environment, radius_data, p)
    accuracy = accuracy or Accuracy()
    mms = p['mms']
    if mms:
        limit = 14400.
    elif p['family'] == 'Q1':
        limit = float(case.get('end_limit_s', 1800.))
    elif p['geometry'] == 'shrink':
        limit = min(float(radius_data[-1, 0]), float(case.get('end_limit_s', radius_data[-1, 0])))
    else:
        limit = float(case.get('end_limit_s', (240. if p['family'] == 'Q4' else 96.)*3600.))
    if sample_times is None:
        sample_times = np.unique(np.r_[0., EARLY, RANK_TIMES[p['family']]])
    sample_times = np.asarray(sample_times, float)
    if np.any(sample_times > limit):
        raise ValueError('Samples exceed declared time coverage.')
    sample_xi = RANK_XI if sample_xi is None else np.asarray(sample_xi, float)
    grids = [Grid(n, data, accuracy, sample_times, sample_xi) for n in (coarse_cells, 2*coarse_cells)]
    coarse, fine = grids
    critical = bracket = critical_xi = terminal_max = None
    terminal = limit
    event_state = None
    event_segments = [[], []]
    status = 'complete'
    boundaries = data.boundaries(limit)
    for begin, finish in zip(boundaries[:-1], boundaries[1:]):
        for grid in grids:
            grid.advance(begin, finish)
        def residual(t):
            return maximum_reconstruction(fine.xi, fine.evaluate(t)[:, 0],
                                          coarse.xi, coarse.evaluate(t)[:, 0])[0]-.15
        if p['family'] != 'Q1' and not p['closed']:
            ga, gb = residual(begin), residual(finish)
            if critical is None and ga > 0 >= gb:
                bracket = [float(begin), float(finish)]
                critical = float(brentq(residual, begin, finish, xtol=1e-8))
                critical_xi = maximum_reconstruction(fine.xi, fine.evaluate(critical)[:, 0],
                                                      coarse.xi, coarse.evaluate(critical)[:, 0])[1]
                event_state = [grid.evaluate(critical).copy() for grid in grids]
                if not mms:
                    terminal = (round(critical/3600., 4)+.0001)*3600.
                for saved, grid in zip(event_segments, grids):
                    saved.extend(d for d in grid.blocks if d.t >= critical-120. and d.t_old <= critical+120.)
            elif critical is not None and begin <= critical+120.:
                for saved, grid in zip(event_segments, grids):
                    saved.extend(d for d in grid.current_block if d.t_old <= critical+120.)
            coverage_target = min(limit, terminal+120.)
            if critical is not None and not mms and finish >= coverage_target:
                terminal_max = residual(terminal)+.15
                if not critical < terminal or terminal_max >= .15:
                    raise RuntimeError('Actual terminal field does not satisfy strict threshold.')
                break
        if progress:
            progress(float(finish))
    if p['family'] != 'Q1' and not p['closed'] and critical is None:
        exhausted_radius = p['geometry'] == 'shrink' and limit >= float(radius_data[-1, 0])-1e-8
        status = 'radius_data_coverage_exhausted' if exhausted_radius else 'right_censored'
    if min(grid.index for grid in grids) != len(sample_times):
        raise RuntimeError('Required output snapshots are missing.')
    out = {'sample_times_s': sample_times, 'sample_xi': sample_xi,
           'coarse_native_fields': np.asarray(coarse.native_fields),
           'fine_native_fields': np.asarray(fine.native_fields),
           'coarse_fields': coarse.fields, 'fine_fields': fine.fields,
           'fields': (4*fine.fields-coarse.fields)/3.,
           'physical_fields': (4*fine.physical-coarse.physical)/3.,
           'coarse_physical_fields': coarse.physical, 'fine_physical_fields': fine.physical,
           'sample_R_m': np.asarray(data.radius(sample_times)),
           'coarse_xi': coarse.xi, 'fine_xi': fine.xi,
           'coarse_final_state': coarse.y.reshape(-1, 2),
           'fine_final_state': fine.y.reshape(-1, 2)}
    if event_state is not None:
        out['coarse_event_state'], out['fine_event_state'] = event_state
        for prefix, segments in zip(('coarse', 'fine'), event_segments):
            out.update(pack_dense(segments, prefix))
    out['coarse_terminal_state'], out['fine_terminal_state'] = [
        grid.evaluate(terminal).copy() for grid in grids]
    if mms:
        for prefix, grid in zip(('coarse', 'fine'), grids):
            out[prefix+'_mms_error_fields'] = np.asarray(grid.mms_field_errors)
            out[prefix+'_mms_native_fields'] = np.asarray(grid.mms_native_fields)
    out['metadata'] = {'version': VERSION, 'case': case, 'parameters': p,
        'accuracy': vars(accuracy), 'numpy': np.__version__, 'scipy': scipy.__version__,
        'status': status, 'deterministic': True, 'seed': None, 'fields_order': ['C', 'T'],
        'critical_time_s': critical, 'critical_time_h': None if critical is None else critical/3600.,
        'root_tolerance_s': None if critical is None else 1e-8+4*np.finfo(float).eps*abs(critical),
        'event_maximum_xi': critical_xi, 'extrapolated_event_bracket_s': bracket,
        'terminal_time_s': terminal, 'terminal_max_C': terminal_max,
        'joint_trajectory_coverage': {'actual_ends_s': [g.end for g in grids],
             'root_bracket_covered': bracket is not None,
             'terminal_covered': all(g.end >= terminal for g in grids),
             'temporal_extrapolation_used': False},
        'grids': [g.metadata() for g in grids], 'environment_tail': data.tail.tolist(),
        'mms_errors': [g.exact_error for g in grids] if mms else None,
        'elapsed_solver_s': sum(g.elapsed for g in grids)}
    if not np.isfinite(out['fields']).all():
        raise RuntimeError('Nonfinite output field.')
    if not mms and (out['fields'][:, :, 0].min() <= 0 or
                   out['fields'][:, :, 0].max() > p['C0']+1e-8):
        raise RuntimeError('Moisture output outside case-specific physical range.')
    if not mms:
        lower_T = min(p['T0'], float(environment[:, 1].min()), float(data.tail[0]))
        upper_T = max(p['T0'], float(environment[:, 1].max()), float(data.tail[0]))
        if out['fields'][:, :, 1].min() < lower_T-1e-8 or out['fields'][:, :, 1].max() > upper_T+1e-8:
            raise RuntimeError('Temperature output outside the case-specific initial/boundary range.')
    return out
