"""Run frozen cases; one independent parameter instance and output per case."""
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
import zipfile
import numpy as np
from 数值模型 import Accuracy, solve
from 输入读取 import load_observations

ROOT = Path(__file__).resolve().parents[1]


def file_stem(case):
    """Use semantic names: APFS cannot distinguish parameter A from parameter a."""
    name = case['case_id']
    labels = [('A_scale', '扩散前因子'), ('a_scale', '含水率指数系数'),
              ('B_scale', '温度指数系数'), ('h_scale', '对流换热系数'),
              ('hm_scale', '对流传质系数'), ('k_scale', '导热系数'),
              ('b_scale', '体积热容量'), ('C0_scale', '初始含水率'),
              ('R0_scale', '初始半径'), ('shrink_amplitude_eta', '收缩幅度'),
              ('Q23', '问题二三'), ('Q1', '问题一'), ('Q4', '问题四'),
              ('baseline', '基准'), ('interaction', '交互'),
              ('tail_T', '平台温度'), ('tail_C', '平台含水参考量'),
              ('radius_linear', '半径线性插值'), ('MMS', '制造解'),
              ('moving', '移动域'), ('fixed', '固定域'),
              ('minus', '降低'), ('plus', '增加'), ('pct', '%'),
              ('0p5', '0点5'), ('0p25', '0点25'),
              ('G3S', '附录三物性_收缩'), ('G4F', '附录四物性_固定半径')]
    for old, new in labels:
        name = name.replace(old, new)
    if '/' in name or '\\' in name or name in ['', '.', '..']:
        raise ValueError('Invalid case output name.')
    return name


def run_case(case, cells, precision, folder, reference_grid=False):
    folder = Path(folder)
    path = folder/file_stem(case)
    if path.with_suffix('.json').exists() or path.with_suffix('.npz').exists():
        raise FileExistsError(f'Existing evidence is not overwritten: {path}')
    started = datetime.now().astimezone().isoformat()
    tic = time.perf_counter()
    raw = load_observations(ROOT/'输入资料')
    accuracy = {'production': Accuracy(), 'screen': Accuracy(1e-9, 1e-11, 1e-10, 60.),
                'tight': Accuracy(2e-13, 1e-15, 1e-14, 60.),
                'tight_cap': Accuracy(2e-13, 1e-15, 1e-14, 30.),
                'tight_cap15': Accuracy(2e-13, 1e-15, 1e-14, 15.)}[precision]
    sample_times = np.asarray(case['sample_times_s'], float) if 'sample_times_s' in case else None
    sample_xi = None
    if case.get('mms'):
        root = 3600*np.log(25.)
        sample_times = np.unique(np.r_[np.arange(0., 14401., 60.),
                                      1., 5., 10., 30., 100., root-60, root, root+60])
        sample_xi = np.unique(np.r_[np.linspace(0., 1., 401),
                                    np.sqrt(np.arange(201)/200)])
    elif reference_grid:
        end = 1800. if case['family'] == 'Q1' else (10800. if case['family'] == 'Q23' else 21600.)
        sample_times = np.unique(np.r_[np.arange(0., end+.01, 60.),
                                      1., 5., 10., 30., 100., 300., 900., 1500.,
                                      [14399., 14401.] if end > 14400 else []])
        sample_xi = np.unique(np.r_[np.linspace(0., 1., 201), np.sqrt(np.arange(201)/200)])
    try:
        result = solve(case, raw['environment'], raw['radius_data'], cells, accuracy,
                       sample_times, sample_xi)
        metadata = result.pop('metadata')
        np.savez_compressed(path.with_suffix('.npz'), **result)
        metadata.update(started_at=started, finished_at=datetime.now().astimezone().isoformat(),
                        wall_elapsed_s=time.perf_counter()-tic, 
                        python=sys.version.split()[0],
                        input_files=['附件1.xlsx','附件2.xlsx'],
                        arrays_file=path.with_suffix('.npz').name)
    except Exception as exc:
        metadata = {'status': 'solver_failed', 'case': case, 'cells': cells,
                    'precision': precision, 'started_at': started,
                    'wall_elapsed_s': time.perf_counter()-tic,
                    'exception': type(exc).__name__+': '+str(exc),
                    'traceback': traceback.format_exc()}
    path.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    return {'case_id': case['case_id'], 'status': metadata['status'],
            'critical_time_s': metadata.get('critical_time_s'),
            'elapsed_s': metadata['wall_elapsed_s']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=Path, default=ROOT/'输入资料'/'全部工况.json')
    parser.add_argument('--select', default='', help='Comma-separated case IDs; empty runs every supplied case.')
    parser.add_argument('--cells', type=int, default=320)
    parser.add_argument('--precision', choices=['production', 'screen', 'tight', 'tight_cap', 'tight_cap15'], default='screen')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--reference-grid', action='store_true')
    args = parser.parse_args()
    document = json.loads(args.cases.read_text())
    cases = document['cases'] if isinstance(document, dict) else document
    selected = set(args.select.split(',')) if args.select else None
    if selected is not None:
        cases = [case for case in cases if case['case_id'] in selected]
        if {case['case_id'] for case in cases} != selected:
            raise ValueError('One or more selected cases are absent from the case file.')
    names = [file_stem(c).casefold() for c in cases]
    if len(names) != len(set(names)):
        raise ValueError('Case output names collide on a case-insensitive filesystem.')
    folder = ROOT/'复算输出'/args.tag
    folder.mkdir(parents=True, exist_ok=False)
    code_files = [Path(__file__).parent/name for name in ['运行分析.py', '数值模型.py', '制造解参考.py', '输入读取.py']]
    with zipfile.ZipFile(folder/'code_snapshot.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for source in code_files:
            archive.write(source, source.name)
    started = datetime.now().astimezone().isoformat()
    manifest = {'status': 'running', 'started_at': started, 'command': sys.argv,
                'case_ids': [c['case_id'] for c in cases],
                'case_source': str(args.cases), 'cells': args.cells, 'precision': args.precision,
                'jobs': args.jobs, 'code_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in code_files}}
    manifest_path = folder/'run.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    summary = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        tasks = [pool.submit(run_case, c, args.cells, args.precision, str(folder), args.reference_grid) for c in cases]
        for task in as_completed(tasks):
            result = task.result()
            summary.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    manifest.update(status='failed' if any(s['status'] == 'solver_failed' for s in summary) else 'complete',
                    finished_at=datetime.now().astimezone().isoformat(), summary=summary)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    if manifest['status'] == 'failed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
