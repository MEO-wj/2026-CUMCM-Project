"""Extract existing results for browser rendering; this script does not solve the PDE."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.interpolate import PchipInterpolator
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '题目要求结果数据/复算依据'
OUT = ROOT / '学术图像/src/data.json'


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (list, tuple)):
        return [clean(x) for x in value]
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def workbook(number):
    path = ROOT / f'代码/附件/附件{number}.xlsx'
    with path.open('rb') as stream:
        book = load_workbook(stream, read_only=True, data_only=True)
        rows = np.asarray(list(book.active.values)[1:], dtype=float)
        book.close()
    return rows


def select_rows(times, maximum=1000):
    # Use original samples, with extra resolution during preheating and at extrema.
    targets = np.r_[np.linspace(0, times[-1], maximum),
                    np.arange(0, min(times[-1], 14400) + 1, 60), times[-1]]
    return np.unique(np.minimum(np.searchsorted(times, targets), len(times) - 1))


env, radius = workbook(1), workbook(2)
pp = PchipInterpolator(radius[:, 0] / 3600, radius[:, 1])
rt = np.linspace(0, 72, 1441)
plateau = env[(env[:, 0] >= 10800) & (env[:, 0] <= 14400), 1:].mean(axis=0)
result = {
    'schema': 1,
    'environment': {'t': env[:, 0] / 3600, 'T': env[:, 1], 'C': env[:, 2], 'plateau': plateau},
    'radius': {'t': radius[:, 0] / 3600, 'R': radius[:, 1],
               'curveT': rt, 'curveR': pp(rt), 'rate': pp.derivative()(rt)},
    'q': {},
    'sources': {},
}
arrays = {}
for q in range(1, 5):
    path = SOURCE / f'result{q}_未舍入.npz'
    with np.load(path) as z:
        arrays[q] = {key: z[key] for key in ['time_s', 'radius_cm', 'R_m', 'domain_mask',
                                             'C', 'T', 'final_xi', 'final_C', 'final_T']}
    z = arrays[q]
    times = z['time_s']
    ids = select_rows(times)
    assert np.all(np.diff(times) > 0)
    assert np.all(np.isfinite(z['C'][z['domain_mask']]))
    assert np.all(np.isnan(z['C'][~z['domain_mask']]))
    fields_end = .5 if q == 1 else 3 if q == 2 else times[-1] / 3600
    field_ids = select_rows(times[times <= fields_end * 3600], 360)
    profiles = []
    for h in ([0, .1, .3, .5] if q == 1 else [0, 1, 2, 3] if q == 2 else [0, 6, 12, 24, 48]):
        j = int(np.argmin(abs(times - h * 3600)))
        mask = np.isfinite(z['radius_cm']) & z['domain_mask'][j]
        rx = np.r_[z['radius_cm'][mask], z['R_m'][j] * 100]
        ix = np.argsort(rx, kind='stable')
        rx, indices = np.unique(rx[ix], return_index=True)
        profiles.append({'t': times[j] / 3600, 'r': rx,
                         'C': np.r_[z['C'][j, mask], z['C'][j, -1]][ix][indices],
                         'T': np.r_[z['T'][j, mask], z['T'][j, -1]][ix][indices]})
    item = {'t': times[ids] / 3600, 'R': z['R_m'][ids] * 100,
            'C': z['C'][ids], 'T': z['T'][ids], 'r': z['radius_cm'],
            'field': {'t': times[field_ids] / 3600, 'R': z['R_m'][field_ids] * 100,
                      'C': z['C'][field_ids], 'T': z['T'][field_ids]},
            'endH': float(times[-1] / 3600), 'endR': float(z['R_m'][-1] * 100),
            'final': {'xi': z['final_xi'], 'C': z['final_C'], 'T': z['final_T']},
            'profiles': profiles, 'sourceRows': len(times), 'displayRows': len(ids)}
    if q == 3:
        xi = z['radius_cm'] / 2
        item['meanC'] = 2 * np.trapezoid(z['C'][ids] * xi, xi, axis=1)
        scales = []
        for col in [0, -1]:
            c, temp = z['C'][ids, col], z['T'][ids, col]
            alpha = (.21 + .38 * c / (1 + c)) / ((650 + 128 * c) * (1450 + 2736 * c / (1 + c)))
            d = 2.4e-3 * np.exp(-.45 / c - 3850 / (temp + 273.15))
            scales.append({'heat': .02**2 / alpha / 3600, 'moisture': .02**2 / d / 3600, 'ratio': alpha / d})
        item['scales'] = scales
    result['q'][str(q)] = item
    result['sources'][str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()

z2, z3 = arrays[2], arrays[3]
common = np.searchsorted(z2['time_s'], z3['time_s'])
assert np.allclose(z2['time_s'][common], z3['time_s'], rtol=0, atol=1e-6)
diffs = {key: z2[key][common] - z3[key] for key in ['C', 'T']}
di = select_rows(z3['time_s'], 320)
result['consistency'] = {
    't': z3['time_s'][di] / 3600, 'r': z3['radius_cm'],
    'C': diffs['C'][di], 'T': diffs['T'][di],
    'maxC': float(np.max(np.abs(diffs['C']))), 'maxT': float(np.max(np.abs(diffs['T']))),
    'checkedTimes': len(common), 'checkedRadii': len(z3['radius_cm']),
}
for i in [1, 2]:
    path = ROOT / f'代码/附件/附件{i}.xlsx'
    result['sources'][str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()
assert result['q']['4']['endR'] == 1.2
assert result['q']['3']['final']['C'].max() <= .15
assert result['q']['4']['final']['C'].max() <= .15
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(clean(result), ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf-8')
print(json.dumps({'bytes': OUT.stat().st_size, 'max_delta_C': result['consistency']['maxC'],
                  'max_delta_T': result['consistency']['maxT'], 'end_h': [result['q'][str(q)]['endH'] for q in (3,4)]}))
