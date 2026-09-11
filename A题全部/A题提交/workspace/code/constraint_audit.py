# -*- coding: utf-8 -*-
"""约束核对：对照 LOGIC_CONTRACT 的 constraints_with_margin 与 equivalence_claims，
在 all_results.json 上逐条判 PASS/FAIL（裕度、等价、方向），导出 figures/constraint_audit.json。

自带闸门，独立于 _utils/logic_audit.py，作交叉复核；限值全部取自合同，脚本不预置常量。
"""
from __future__ import annotations
import json
import sys
import params as P

CONTRACT = P.FIG_DIR.parent / "LOGIC_CONTRACT.json"
RESULTS = P.FIG_DIR / "all_results.json"
JSON_OUT = P.FIG_DIR / "constraint_audit.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_constraint_audit(write=True):
    contract = _load(CONTRACT)["LOGIC_CONTRACT_MACHINE"]
    res = _load(RESULTS)
    rows, fails = [], []

    for c in contract.get("constraints_with_margin", []):
        q, limit, kind = c["quantity"], float(c["limit"]), c.get("kind", "le")
        val = res.get(q)
        if val is None:
            rows.append({"quantity": q, "status": "MISSING"})
            fails.append(q)
            continue
        val = float(val)
        ok = (val <= limit + 1e-12) if kind == "le" else (val >= limit - 1e-12)
        denom = abs(limit) if abs(limit) > 1e-12 else 1.0
        margin = (limit - val) / denom if kind == "le" else (val - limit) / denom
        rows.append({"quantity": q, "value": val, "limit": limit, "kind": kind,
                     "margin_rel": margin, "status": "PASS" if ok else "FAIL"})
        if not ok:
            fails.append(q)

    for c in contract.get("equivalence_claims", []):
        qa, qb = c["quantity_a"], c["quantity_b"]
        va, vb = res.get(qa), res.get(qb)
        if va is None or vb is None:
            rows.append({"equivalence": f"{qa}~{qb}", "status": "MISSING"})
            fails.append(f"{qa}~{qb}")
            continue
        va, vb = float(va), float(vb)
        rel_tol = float(c.get("rel_tol", 0.02))
        abs_tol = float(c.get("abs_tol", 0.0))
        ok = abs(va - vb) <= abs_tol + rel_tol * max(abs(va), abs(vb))
        rows.append({"equivalence": f"{qa}~{qb}", "a": va, "b": vb,
                     "rel_tol": rel_tol, "abs_tol": abs_tol,
                     "status": "PASS" if ok else "FAIL"})
        if not ok:
            fails.append(f"{qa}~{qb}")

    probes = res.get("logic_probes", {})
    for b in probes.get("bounds", []):
        claim, sign = b.get("claim"), b.get("probe_delta_sign")
        ok = (sign < 0) if claim == "upper" else (sign > 0)
        rows.append({"bound": b.get("quantity"), "claim": claim,
                     "probe_delta_sign": sign, "status": "PASS" if ok else "FAIL"})
        if not ok:
            fails.append(b.get("quantity"))
    for m in probes.get("monotonic", []):
        os_, es = m.get("observed_sign"), m.get("expect_sign")
        ok = (os_ > 0) == (es > 0)
        rows.append({"monotonic": f"{m.get('more')}->{m.get('then')}",
                     "observed_sign": os_, "expect_sign": es,
                     "status": "PASS" if ok else "FAIL"})
        if not ok:
            fails.append(m.get("more"))

    verdict = "PASS" if not fails else "FAIL"
    out = {"verdict": verdict, "n_checks": len(rows), "failures": fails, "rows": rows}
    if write:
        P.FIG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    return out


if __name__ == "__main__":
    o = run_constraint_audit()
    print(f"Constraint audit: {o['verdict']} ({o['n_checks']} checks)")
    for r in o["rows"]:
        print(" ", r.get("status"), {k: v for k, v in r.items() if k != "status"})
    sys.exit(0 if o["verdict"] == "PASS" else 1)
