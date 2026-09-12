"""Independent equal-area cell-centered reference from review report section 15.

The RHS and parameter handling here do not import the analysis solver. The
spatial method preserves its Gauss-8 concentration integral and algebraic
second-order Robin surface without a surface storage node.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from scipy.sparse import diags

ROOT = Path(__file__).resolve().parents[1]
from 输入读取 import load_observations
from 运行分析 import file_stem
VERSION = 'independent-equal-area-robin-20260912-v2'
FACTOR_KEYS = ('A_scale', 'a_scale', 'B_scale', 'h_scale', 'hm_scale',
               'k_scale', 'b_scale', 'C0_scale', 'R0_scale', 'shrink_amplitude_eta')


def parameter_instance(case):
    family = case['family']
    if family not in ('Q1', 'Q23', 'Q4'):
        raise ValueError(family)
    scales = dict.fromkeys(FACTOR_KEYS, 1.)
    overrides = case.get('overrides', {})
    if set(overrides)-set(scales):
        raise ValueError('Unsupported overrides: '+str(set(overrides)-set(scales)))
    scales.update(overrides)
    if not all(np.isfinite(v) and v > 0 for v in scales.values()):
        raise ValueError('Parameter scales must be positive and finite.')
    geometry = case.get('geometry', 'shrink' if family == 'Q4' else 'fixed')
    if geometry not in ('fixed', 'shrink'):
        raise ValueError('Unsupported geometry.')
    if geometry == 'shrink' and scales['R0_scale'] != 1.:
        raise ValueError('The measured-radius amplitude scenario keeps R0=0.02 m.')
    if case.get('environment_tail', 'E0') != 'E0':
        raise ValueError('This bounded independent run freezes the E0 tail.')
    constants = {'Q1': (7e-9, .89, 0.), 'Q23': (2.4e-3, .45, 3850.),
                 'Q4': (4.2e-4, .30, 3850.)}[family]
    return {**scales, 'family': family, 'geometry': geometry,
            'A': constants[0]*scales['A_scale'], 'a': constants[1]*scales['a_scale'],
            'B_D_K': constants[2]*scales['B_scale'], 'h_W_m2_K': 25.*scales['h_scale'],
            'hm_m_s': 8e-7*scales['hm_scale'], 'C0_kg_kg': 2.55*scales['C0_scale'],
            'T0_C': 28., 'R0_m': .02*scales['R0_scale'], 'latent_heat': False,
            'environment_tail': 'E0', 'tail_T_delta_K': float(case.get('tail_T_delta', 0.)),
            'tail_C_delta_kg_kg': float(case.get('tail_C_delta', 0.))}


class EqualAreaReference:
    def __init__(self, case, cells, environment, radii, rtol, max_step, wall_cap):
        self.case, self.p, self.n = case, parameter_instance(case), cells
        self.environment, self.radii = environment, radii
        self.rtol, self.max_step, self.wall_cap = rtol, max_step, wall_cap
        self.dx = 1./cells
        self.x = (np.arange(cells)+.5)*self.dx
        self.faces = np.arange(1, cells)*self.dx
        g, w = np.polynomial.legendre.leggauss(8)
        self.g, self.w = (g+1.)/2., w/2.
        rows = environment[(environment[:, 0] >= 10800.) & (environment[:, 0] <= 14400.), 1:3]
        if rows.shape != (61, 2):
            raise ValueError('E0 requires the 61 inclusive final-hour records.')
        self.plateau = rows.mean(axis=0)+[self.p['tail_T_delta_K'], self.p['tail_C_delta_kg_kg']]
        self.radius_curve = PchipInterpolator(radii[:, 0], radii[:, 1]*.01, extrapolate=False)
        self.tail_active = False
        self.started = self.last_progress = time.perf_counter()
        self.minimum_sampled_C = np.inf
        self.surface_calls = 0
        self.surface_max_iterations = 0

    def properties(self, c):
        if self.p['family'] == 'Q1':
            k, b = np.full_like(c, .36), np.full_like(c, 820.*2600.)
        elif self.p['family'] == 'Q23':
            k = .21+.38*c/(1.+c)
            b = (650.+128.*c)*(1450.+2736.*c/(1.+c))
        else:
            k = .12+.20*c/(1.+c)
            b = (760.+90.*c)*(1850.+2150.*c/(1.+c))
        return k*self.p['k_scale'], b*self.p['b_scale']

    def concentration_integral(self, left, right):
        samples = left+(right-left)*self.g
        if np.any(samples <= 0.):
            raise FloatingPointError('Nonpositive concentration in the independent integral; no silent clipping.')
        return (right-left)*np.dot(self.w, np.exp(-self.p['a']/samples))

    def air_and_radius(self, t):
        if self.tail_active:
            ta, ca = self.plateau
        else:
            ta, ca = [np.interp(t, self.environment[:, 0], self.environment[:, j]) for j in (1, 2)]
        if self.p['geometry'] == 'fixed':
            radius = self.p['R0_m']
        else:
            if t > self.radii[-1, 0]+1e-8:
                raise ValueError('Measured-radius coverage exceeded; no extrapolation or endpoint clamp.')
            nominal = float(self.radius_curve(t))
            radius = .02+self.p['shrink_amplitude_eta']*(nominal-.02)
        if radius <= 0. or not np.isfinite(radius):
            raise ValueError('Invalid radius.')
        return float(ta), float(ca), float(radius)

    def surface(self, c, temperature, t):
        ta, ca, radius = self.air_and_radius(t)
        tb, cb = float(temperature[-1]), float(c[-1])
        beta = 1.5*self.dx*radius*self.p['hm_m_s']
        gamma = 1.5*self.dx*radius*self.p['h_W_m2_K']
        inner = self.concentration_integral(c[-1], c[-2])
        self.surface_calls += 1
        for iteration in range(12):
            if tb <= -273.15:
                raise FloatingPointError('Nonpositive absolute surface temperature.')
            af = self.p['A']*np.exp(-self.p['B_D_K']/(tb+273.15))
            def residual(v):
                return af*(8.*self.concentration_integral(c[-1], v)+inner)+beta*(v-ca)
            cb_new = brentq(residual, 1e-10, max(float(c[-1]), float(c[-2]), ca)*1.001,
                            xtol=1e-13, rtol=1e-13)
            kb = float(self.properties(np.array(cb_new))[0])
            tb_new = (kb*(9.*temperature[-1]-temperature[-2])+gamma*ta)/(8.*kb+gamma)
            change = max(abs(cb_new-cb), abs(tb_new-tb))
            cb, tb = cb_new, tb_new
            if change < 1e-11:
                self.surface_max_iterations = max(self.surface_max_iterations, iteration+1)
                return cb, tb, ta, ca, radius
        raise RuntimeError('Algebraic surface coupling did not converge in 12 iterations.')

    def rhs(self, t, y):
        now = time.perf_counter()
        if now-self.started > self.wall_cap:
            raise TimeoutError('Independent case exceeded its fixed wall-time budget.')
        if now-self.last_progress > 20.:
            print(json.dumps({'progress_case': self.case['case_id'], 'N': self.n,
                              'time_h': t/3600., 'elapsed_s': now-self.started}), flush=True)
            self.last_progress = now
        state = y.reshape(self.n, 2)
        c, temperature = state[:, 0], state[:, 1]
        if np.any(c <= 0.) or np.any(temperature <= -273.15) or not np.isfinite(y).all():
            raise FloatingPointError('State left the stated concentration/absolute-temperature domain.')
        self.minimum_sampled_C = min(self.minimum_sampled_C, float(c.min()))
        cb, tb, ta, ca, radius = self.surface(c, temperature, t)
        cq = c[:-1, None]+np.diff(c)[:, None]*self.g
        effective = np.exp(-self.p['a']/cq) @ self.w
        thermal = np.exp(-self.p['B_D_K']/(temperature+273.15))
        diffusion = self.p['A']*effective*(thermal[:-1]+thermal[1:])/2.
        conductivity, capacity = self.properties(c)
        qc = np.r_[0., self.faces*diffusion*np.diff(c)/self.dx,
                   -.5*radius*self.p['hm_m_s']*(cb-ca)]
        qt = np.r_[0., self.faces*(conductivity[:-1]+conductivity[1:])/2.*np.diff(temperature)/self.dx,
                   -.5*radius*self.p['h_W_m2_K']*(tb-ta)]
        rate = np.empty_like(state)
        rate[:, 0] = 4.*np.diff(qc)/(radius*radius*self.dx)
        rate[:, 1] = 4.*np.diff(qt)/(radius*radius*self.dx*capacity)
        return rate.ravel()

    @staticmethod
    def center(field):
        return (15.*field[0]-10.*field[1]+3.*field[2])/8.

    def reconstruct(self, t, y):
        state = y.reshape(self.n, 2)
        cb, tb, *_ = self.surface(state[:, 0], state[:, 1], t)
        coordinates = np.r_[0., self.x, 1.]
        fields = np.vstack(([self.center(state[:, 0]), self.center(state[:, 1])], state, [cb, tb]))
        return coordinates, fields

    def maximum(self, t, y):
        coordinates, fields = self.reconstruct(t, y)
        polynomial = PchipInterpolator(coordinates, fields[:, 0])
        maximum = float(fields[:, 0].max())
        location = float(coordinates[np.argmax(fields[:, 0])])
        a, b, c = 3.*polynomial.c[0], 2.*polynomial.c[1], polynomial.c[2]
        disc = b*b-4.*a*c
        curved = (disc >= 0.) & (np.abs(a) > 1e-30)
        width = np.diff(coordinates)
        candidates = []
        for sign in (-1., 1.):
            roots = np.full_like(a, np.nan)
            roots[curved] = (-b[curved]+sign*np.sqrt(disc[curved]))/(2.*a[curved])
            candidates.append(roots)
        roots = np.full_like(a, np.nan)
        linear = (np.abs(a) <= 1e-30) & (np.abs(b) > 1e-30)
        roots[linear] = -c[linear]/b[linear]
        candidates.append(roots)
        for roots in candidates:
            keep = (roots > 0.) & (roots < width)
            if keep.any():
                positions = coordinates[:-1][keep]+roots[keep]
                values = polynomial(positions)
                best = int(np.argmax(values))
                if values[best] > maximum:
                    maximum, location = float(values[best]), float(positions[best])
        return maximum, float(np.sqrt(location))

    def integrate(self, technical_cap_s):
        family = self.p['family']
        data_cap = float(self.radii[-1, 0]) if self.p['geometry'] == 'shrink' else None
        cap = min(technical_cap_s, data_cap) if data_cap is not None else technical_cap_s
        times = (np.array([100., 300., 600., 900., 1200., 1500., 1800.]) if family == 'Q1' else
                 np.arange(1800., 10801. if family == 'Q23' else 21601., 1800.))
        times = times[times <= cap]
        samples = {}
        state = np.tile([self.p['C0_kg_kg'], self.p['T0_C']], self.n)
        sparsity = diags([np.ones(2*self.n)]*7, range(-3, 4), shape=(2*self.n, 2*self.n), format='csc')
        boundaries = [0., min(cap, 14400.)]
        if cap > 14400.:
            boundaries.append(cap)
        if family == 'Q1':
            boundaries = np.r_[np.arange(0., cap, 60.), cap].tolist()
        def event(t, y):
            return self.maximum(t, y)[0]-.15
        event.direction, event.terminal = -1., True
        totals = {'nfev': 0, 'njev': 0, 'nlu': 0}
        event_time, event_state = None, None
        accepted_final_t = 0.
        for begin, finish in zip(boundaries[:-1], boundaries[1:]):
            if finish <= begin:
                continue
            self.tail_active = begin >= 14400.
            wanted = sorted(set(times[(times > begin) & (times <= finish)].tolist()+[finish]))
            solution = solve_ivp(self.rhs, (begin, finish), state, method='BDF', rtol=self.rtol,
                                 atol=np.tile([self.rtol*.005, self.rtol*.05], self.n),
                                 max_step=self.max_step, jac_sparsity=sparsity, t_eval=wanted,
                                 first_step=min(1e-4, finish-begin) if begin == 0. else None,
                                 events=event if family != 'Q1' else None)
            if not solution.success:
                raise RuntimeError(solution.message)
            for key in totals:
                totals[key] += getattr(solution, key)
            if len(solution.t):
                for t, y in zip(solution.t, np.asarray(solution.y).T):
                    if t in times:
                        samples[float(t)] = y.copy()
            if solution.t_events and len(solution.t_events[0]):
                event_time = float(solution.t_events[0][0])
                event_state = solution.y_events[0][0].copy()
                state, accepted_final_t = event_state, event_time
                break
            state, accepted_final_t = solution.y[:, -1].copy(), float(finish)
        status = 'complete' if event_time is not None or family == 'Q1' else (
            'radius_data_coverage_exhausted' if data_cap is not None and cap == data_cap else 'right_censored_at_technical_cap')
        sample_times = np.array(sorted(samples))
        xi = np.array([0., .25, .5, .75, 1.])
        sample_fields, sample_radius = [], []
        for t in sample_times:
            self.tail_active = t > 14400.
            x, values = self.reconstruct(float(t), samples[float(t)])
            sample_fields.append(PchipInterpolator(x, values, axis=0)(xi*xi))
            sample_radius.append(self.air_and_radius(float(t))[2])
        arrays = {'sample_times_s': sample_times, 'sample_xi': xi, 'fields': np.asarray(sample_fields),
                  'sample_native_states': np.asarray([samples[float(t)].reshape(self.n, 2) for t in sample_times]),
                  'sample_R_m': np.asarray(sample_radius), 'cell_centers_x': self.x,
                  'cell_centers_xi': np.sqrt(self.x), 'final_native_state': state.reshape(self.n, 2)}
        peak = location = None
        if event_time is not None:
            self.tail_active = event_time >= 14400.
            peak, location = self.maximum(event_time, event_state)
            coordinates, values = self.reconstruct(event_time, event_state)
            arrays.update(event_native_state=event_state.reshape(self.n, 2),
                          event_reconstruction_x=coordinates, event_reconstruction_fields=values)
        metadata = {'version': VERSION, 'case': self.case, 'parameters': self.p, 'cells': self.n,
                    'coordinate': 'x=(r/R)^2', 'cell_layout': 'equal-area cell centers; no surface storage node',
                    'surface': 'algebraic second-order coupled Robin, same coefficients as source report section 15',
                    'face_quadrature_order': 8, 'center_extrapolation': '(15*u0-10*u1+3*u2)/8 in x',
                    'event_definition': 'Continuous time root of full PCHIP reconstructed radial maximum C minus 0.15; endpoints and all interior stationary candidates evaluated.',
                    'method': 'BDF', 'rtol': self.rtol, 'atol_C': self.rtol*.005, 'atol_T': self.rtol*.05,
                    'max_step_s': self.max_step, 'time_restart_boundaries_s': boundaries,
                    'tail_boundary_convention': 'Observed piecewise-linear input through the left interval; E0 right limit on the interval starting at 4h.',
                    'sample_at_exactly_4h': 'Observed left-limit boundary, matching source section 15; no right-limit replacement in the fixed-time output.',
                    'environment_tail_T_C': self.plateau.tolist(), 'status': status,
                    'critical_time_s': event_time, 'critical_time_h': None if event_time is None else event_time/3600.,
                    'event_max_C': peak, 'event_maximum_xi': location, 'actual_end_s': accepted_final_t,
                    'technical_cap_s': technical_cap_s, 'radius_data_cap_s': data_cap,
                    'minimum_C_seen_by_RHS': self.minimum_sampled_C, 'surface_calls': self.surface_calls,
                    'surface_max_iterations': self.surface_max_iterations, **totals,
                    'elapsed_solver_s': time.perf_counter()-self.started,
                    'claim': 'Independent discretization cross-check only; no independent error bound has yet been established.'}
        return arrays, metadata


def run_case(case, cells, output, rtol, max_step, wall_cap):
    target = Path(output)/(file_stem(case)+f'_网格{cells}')
    if target.with_suffix('.json').exists() or target.with_suffix('.npz').exists():
        raise FileExistsError(target)
    started = datetime.now().astimezone().isoformat()
    try:
        raw = load_observations(ROOT/'输入资料')
        model = EqualAreaReference(case, cells, raw['environment'], raw['radius_data'], rtol, max_step, wall_cap)
        cap = 1800. if case['family'] == 'Q1' else (240.*3600. if case['family'] == 'Q4' and model.p['geometry'] == 'fixed' else 96.*3600.)
        arrays, metadata = model.integrate(cap)
        np.savez_compressed(target.with_suffix('.npz'), **arrays)
        legacy = {'Q23_baseline': 57.47399953, 'Q4_baseline': 51.08850303}.get(case['case_id'])
        if cells == 640 and legacy is not None:
            metadata['legacy_rounded_regression_reference_h'] = legacy
            metadata['difference_from_legacy_reference_s'] = (metadata['critical_time_h']-legacy)*3600.
            metadata['legacy_reference_used_for_tuning'] = False
    except Exception as exc:
        metadata = {'case': case, 'cells': cells, 'status': 'budget_limited' if isinstance(exc, TimeoutError) else 'failed',
                    'exception': type(exc).__name__+': '+str(exc), 'traceback': traceback.format_exc()}
    metadata.setdefault('parameters', parameter_instance(case))
    metadata.setdefault('rtol', rtol)
    metadata.setdefault('max_step_s', max_step)
    metadata.update(started_at=started, finished_at=datetime.now().astimezone().isoformat(),
                    numpy=np.__version__, scipy=scipy.__version__, python=sys.version.split()[0])
    target.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    short = {key: metadata.get(key) for key in ('status', 'critical_time_s', 'critical_time_h', 'elapsed_solver_s', 'difference_from_legacy_reference_s')}
    return {'case_id': case['case_id'], 'cells': cells, **short}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--select', required=True)
    parser.add_argument('--cells', default='640')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--rtol', type=float, default=2e-12)
    parser.add_argument('--max-step', type=float, default=60.)
    parser.add_argument('--case-wall-cap', type=float, default=600.)
    args = parser.parse_args()
    cases_doc = json.loads((ROOT/'输入资料/全部工况.json').read_text())
    cases = cases_doc['cases'] if isinstance(cases_doc, dict) else cases_doc
    selected = args.select.split(',')
    chosen = [next(c for c in cases if c['case_id'] == name) for name in selected]
    cells = [int(n) for n in args.cells.split(',')]
    stems = [file_stem(c)+f'_网格{n}' for c in chosen for n in cells]
    if len({stem.casefold() for stem in stems}) != len(stems):
        raise ValueError('Case-insensitive artifact names collide; use distinct semantic case identifiers.')
    if min(cells) < 3:
        raise ValueError('At least three cells are required by the center extrapolation.')
    output = ROOT/'复算输出/独立空间复核'/args.tag
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (output/'独立空间方法源码.py').write_bytes(source)
    manifest = {'status':'running','version':VERSION,'started_at':datetime.now().astimezone().isoformat(),'command':sys.argv,'case_ids':selected,'cells':cells,'jobs':args.jobs,'shared_RHS':False,'shares_only_input_reader':True,'summary':[]}
    (output/'run.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_case, c, n, str(output), args.rtol, args.max_step, args.case_wall_cap)
                   for c in chosen for n in cells]
        for future in as_completed(futures):
            result = future.result(); manifest['summary'].append(result)
            (output/'run.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps(result, ensure_ascii=False), flush=True)
    manifest['status'] = 'finished_with_explicit_case_statuses'
    manifest['finished_at'] = datetime.now().astimezone().isoformat()
    (output/'run.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
