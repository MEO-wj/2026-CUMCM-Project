"""Bounded FFE-PINN pilot for the unchanged material-coordinate drying PDE.

Commands: smoke, train, evaluate. Importing or running smoke never trains.
Training has no FVM-reference argument. Evaluation alone accepts a reference.
MMS uses only its initial profile, continuous sources and Robin data in training.
The analytic full MMS field is used solely in smoke/evaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from scipy.integrate import cumulative_trapezoid
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from torch import nn
from torch.nn import functional as F

import 制造解参考 as mms
from 输入读取 import load_observations

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "输入资料" / "网络试点配置.json"
SCALES = np.array([2.55, 22.0])


def read_config(path):
    path = Path(path)
    data = path.read_bytes()
    cfg = json.loads(data)
    if (cfg["target_id"] != "coarse_window_v1" or cfg["dtype"] != "float64"
            or cfg["device"] != "cpu" or cfg["hidden_layers"] != 4
            or cfg["width"] != 64 or cfg["fourier_frequencies"] != 32):
        raise ValueError("Configuration does not match the declared pilot architecture/dtype.")
    torch.set_default_dtype(torch.float64)
    torch.set_num_threads(int(cfg["threads"]))
    return cfg, hashlib.sha256(data).hexdigest(), path.parent


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


class FourierField(nn.Module):
    def __init__(self, cfg, case, seed):
        super().__init__()
        self.case, self.window = case, float(cfg["windows_s"][case])
        self.time_scale = float(cfg["early_time_scale_s"])
        torch.manual_seed(seed)
        count = int(cfg["fourier_frequencies"])
        sigma = torch.tensor([cfg["fourier_sigmas"][i % len(cfg["fourier_sigmas"])] for i in range(count)])
        self.register_buffer("frequencies", torch.randn(count, 2) * sigma[:, None])
        layers, dimension = [], 2 + 2 * count
        for _ in range(cfg["hidden_layers"]):
            layers.extend([nn.Linear(dimension, cfg["width"]), nn.Tanh()])
            dimension = cfg["width"]
        self.hidden = nn.Sequential(*layers)
        self.output = nn.Linear(dimension, 2)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, points):
        x, t = points[:, 0], points[:, 1]
        tau = t / self.window
        log_time = torch.log1p(t / self.time_scale) / np.log1p(self.window / self.time_scale)
        phase = 2 * np.pi * torch.stack((x, log_time), dim=1) @ self.frequencies.T
        features = torch.cat((torch.stack((x, tau), dim=1), torch.sin(phase), torch.cos(phase)), dim=1)
        raw = self.output(self.hidden(features))
        initial_c = 0.05 + 2.5 * (1 - 0.3*x + 0.1*x*x) if self.case == "MMS" else torch.full_like(x, 2.55)
        initial_latent = torch.log(torch.expm1(initial_c / 2.55))
        gate = tau if self.case == "MMS" else torch.ones_like(tau)
        c = 2.55 * F.softplus(initial_latent + gate * raw[:, 0])
        temperature = 28.0 + 22.0 * gate * raw[:, 1]
        return torch.stack((c, temperature), dim=1)


def derivatives(value, points, create_graph=True):
    return torch.autograd.grad(value, points, torch.ones_like(value),
                               create_graph=create_graph, retain_graph=True)[0]


def properties(c, temperature):
    # No clipping: invalid learned states are an explicit failed trial.
    if torch.any(c <= 0) or torch.any(temperature + 273.15 <= 0):
        raise FloatingPointError("Learned state is outside the constitutive domain.")
    diffusion = 4.2e-4 * torch.exp(-0.30/c - 3850.0/(temperature+273.15))
    conductivity = 0.12 + 0.20*c/(1+c)
    capacity = (760+90*c)*(1850+2150*c/(1+c))
    return diffusion, conductivity, capacity


class Physics:
    def __init__(self, cfg, case, config_dir):
        self.case, self.window = case, float(cfg["windows_s"][case])
        self.capacity_scale = (760+90*2.55)*(1850+2150*2.55/3.55)
        self.input_hash = None
        if case == "Q4":
            arrays = load_observations(config_dir)
            self.environment = arrays["environment"].copy()
            radii = arrays["radius_data"].copy()
            self.input_hash = hashlib.sha256(self.environment.tobytes()+radii.tobytes()).hexdigest()
            final_hour = self.environment[(self.environment[:, 0] >= 10800) &
                                          (self.environment[:, 0] <= 14400), 1:]
            if final_hour.shape != (61, 2):
                raise ValueError("The inclusive 61-point environment tail is required.")
            self.tail = final_hour.mean(axis=0)
            self.radius_function = PchipInterpolator(radii[:, 0], radii[:, 1]*0.01, extrapolate=False)

    def inputs(self, t):
        values = np.asarray(t, dtype=float)
        if np.any(values < 0) or np.any(values > self.window):
            raise ValueError("Time outside the declared training/evaluation window.")
        if self.case == "MMS":
            radius = mms.radius(values, True)
            ct = mms.exact(values.ravel(), np.ones(values.size))
            c, temp = ct[:, 0], ct[:, 1]
            q = np.exp(-values.ravel()/3600.)
            d = 4.2e-4*np.exp(-.30/c-3850/(temp+273.15))
            k = .12+.20*c/(1+c)
            ambient = np.column_stack((temp+k*7.2*(1-q)/(25*np.ravel(radius)),
                                       c-d*.5*q/(8e-7*np.ravel(radius))))
        else:
            radius = self.radius_function(values)
            ambient = np.column_stack([np.interp(values.ravel(), self.environment[:, 0],
                                                self.environment[:, j]) for j in [1, 2]])
            ambient[values.ravel() >= 14400.] = self.tail
        if not np.isfinite(radius).all() or np.any(radius <= 0):
            raise ValueError("Radius input does not cover the requested window.")
        return np.ravel(radius), ambient

    def residuals(self, field, interior, boundary, initial):
        z = interior.detach().clone().requires_grad_(True)
        state = field(z)
        c, temp = state[:, 0], state[:, 1]
        dc, dt = derivatives(c, z), derivatives(temp, z)
        d, k, b = properties(c, temp)
        radius, _ = self.inputs(z[:, 1].detach().numpy())
        radius = torch.as_tensor(radius)
        lc = 4 * derivatives(z[:, 0]*d*dc[:, 0], z)[:, 0] / radius**2
        lt = 4 * derivatives(z[:, 0]*k*dt[:, 0], z)[:, 0] / radius**2
        source = torch.zeros_like(state)
        if self.case == "MMS":
            source = torch.as_tensor(mms.source(z[:, 1].detach().numpy(),
                                               np.sqrt(z[:, 0].detach().numpy()), "Q4"))
        pde_c = (dc[:, 1]-lc-source[:, 0]) * self.window / 2.55
        pde_t = (b*dt[:, 1]-lt-source[:, 1]) * self.window/(self.capacity_scale*22.)
        zb = boundary.detach().clone().requires_grad_(True)
        sb = field(zb)
        cb, tb = sb[:, 0], sb[:, 1]
        db, kb, _ = properties(cb, tb)
        cbx, tbx = derivatives(cb, zb)[:, 0], derivatives(tb, zb)[:, 0]
        rb, ambient = self.inputs(zb[:, 1].detach().numpy())
        rb, ambient = torch.as_tensor(rb), torch.as_tensor(ambient)
        robin_c = (-2*db*cbx/rb-8e-7*(cb-ambient[:, 1]))/(8e-7*2.55)
        robin_t = (-2*kb*tbx/rb-25*(tb-ambient[:, 0]))/(25*22.)
        si = field(initial)
        target_c = 0.05+2.5*(1-.3*initial[:, 0]+.1*initial[:, 0]**2) if self.case == "MMS" else torch.full_like(initial[:, 0], 2.55)
        return {"pde_C": pde_c, "pde_T": pde_t, "Robin_C": robin_c, "Robin_T": robin_t,
                "IC_C": (si[:, 0]-target_c)/2.55, "IC_T": (si[:, 1]-28.)/22.}


def samples(cfg, case, seed, purpose):
    rng = np.random.default_rng(seed)
    window = cfg["windows_s"][case]
    n = cfg[f"{purpose}_interior_points"]
    nb = cfg[f"{purpose}_boundary_points"]
    ni = cfg.get(f"{purpose}_initial_points", cfg["score_x_count"])
    def positive_times(count):
        u = rng.random(count)
        t = np.where(np.arange(count)%2 == 0, u*window, np.expm1(u*np.log1p(window)))
        return np.maximum(t, cfg["minimum_positive_time_s"])
    x = rng.random(n)
    x[::4] = 1-rng.random(len(x[::4]))**3
    x[:cfg["axis_points"]] = 0.0  # Axis PDE limit; never a C_x = 0 penalty.
    interior = np.column_stack((x, positive_times(n)))
    boundary = np.column_stack((np.ones(nb), positive_times(nb)))
    initial = np.column_stack((rng.random(ni), np.zeros(ni)))
    return tuple(torch.as_tensor(v) for v in (interior, boundary, initial))


def residual_stats(parts):
    return {k: {"rmse": float(torch.mean(v.detach()**2).sqrt()),
                "max_abs": float(v.detach().abs().max())} for k, v in parts.items()}


def gate(path, case, config_hash):
    if path is None:
        raise ValueError(f"A completed {case} acceptance artifact is required.")
    value = json.loads(Path(path).read_text())
    required = ["L2", "Linf", "IC", "heldout_PDE_Robin"] + (["MMS_event"] if case == "MMS" else [])
    if not (value.get("accepted") is True and value.get("target_id") == "coarse_window_v1"
            and value.get("case") == case and value.get("seed") == 17
            and value.get("config_sha256") == config_hash
            and all(value.get("checks", {}).get(k) is True for k in required)):
        raise ValueError(f"The {case} prerequisite did not pass the frozen target/configuration.")


def train(args, cfg, config_hash, config_dir):
    if args.case == "MMS" and args.seed != 17:
        raise ValueError("This stage only admits MMS seed 17.")
    if args.case == "Q4":
        gate(args.mms_gate, "MMS", config_hash)
        if args.seed != 17:
            gate(args.pilot_gate, "Q4", config_hash)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    physics = Physics(cfg, args.case, config_dir)
    model = FourierField(cfg, args.case, args.seed)
    dev = samples(cfg, args.case, args.seed+10000, "dev")
    data = samples(cfg, args.case, args.seed, "training")
    started = time.perf_counter()
    deadline = started+cfg["training_seconds"][args.case]
    adam_end = started+cfg["training_seconds"][args.case]*cfg["adam_time_fraction"]
    history, steps = [], 0
    best_score, best_state, best_step = float("inf"), None, None
    def select_checkpoint():
        nonlocal best_score, best_state, best_step
        parts = physics.residuals(model, *dev)
        score = float(sum(torch.mean(v.detach()**2) for v in parts.values()))
        if not np.isfinite(score):
            raise FloatingPointError("Nonfinite physics-dev loss.")
        history.append({"step": steps, "elapsed_s": time.perf_counter()-started,
                        "physics_dev_score": score, "parts": residual_stats(parts)})
        if score < best_score:
            best_score, best_step = score, steps
            best_state = {k:v.detach().clone() for k,v in model.state_dict().items()}
    select_checkpoint()
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["adam_learning_rate"])
    while time.perf_counter() < adam_end:
        if steps and steps % cfg["resample_every"] == 0:
            data = samples(cfg, args.case, args.seed+steps, "training")
        optimizer.zero_grad(set_to_none=True)
        parts = physics.residuals(model, *data)
        loss = sum(torch.mean(v**2) for v in parts.values())
        if not torch.isfinite(loss):
            raise FloatingPointError("Nonfinite training residual.")
        loss.backward(); optimizer.step(); steps += 1
        if steps % cfg["checkpoint_every"] == 0:
            select_checkpoint()
    # This fixed batch remains unchanged throughout all L-BFGS line searches.
    data = samples(cfg, args.case, args.seed+9000, "training")
    optimizer = torch.optim.LBFGS(model.parameters(), lr=1., max_iter=cfg["lbfgs_max_iter_per_step"],
                                  history_size=30, line_search_fn="strong_wolfe")
    while time.perf_counter() < deadline:
        def closure():
            if time.perf_counter() >= deadline:
                raise TimeoutError("Predeclared training budget reached.")
            optimizer.zero_grad(set_to_none=True)
            parts = physics.residuals(model, *data)
            loss = sum(torch.mean(v**2) for v in parts.values())
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite L-BFGS residual.")
            loss.backward()
            return loss
        try:
            optimizer.step(closure); steps += 1; select_checkpoint()
        except TimeoutError:
            break
    model.load_state_dict(best_state)
    record = {"status":"frozen_not_yet_evaluated", "case":args.case, "seed":args.seed,
              "target_id":cfg["target_id"], "config_sha256":config_hash, "config":cfg,
              "window_s":physics.window, "observations_sha256":physics.input_hash,
              "best_physics_dev_score":best_score, "best_step":best_step, "steps":steps,
              "selection":"independent_physics_dev_only", "FVM_training_labels_used":False,
              "elapsed_training_s":time.perf_counter()-started, "history":history,
              "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    torch.save({"state_dict":best_state,"metadata":record}, output/"model.pt")
    record["checkpoint_sha256"] = hashlib.sha256((output/"model.pt").read_bytes()).hexdigest()
    write_json(output/"training.json", record)
    print(json.dumps({k:record[k] for k in ["status","case","seed","steps","elapsed_training_s"]}))


def predict(model, x, t):
    points = np.column_stack((np.asarray(x).ravel(), np.asarray(t).ravel()))
    values = []
    with torch.no_grad():
        for begin in range(0, len(points), 2048):
            values.append(model(torch.as_tensor(points[begin:begin+2048])).numpy())
    return np.concatenate(values)


def score_times(cfg, case):
    times = np.r_[np.arange(0.,cfg["windows_s"][case]+.01,cfg["score_time_step_s"]), cfg["score_extra_times_s"]]
    if case == "MMS":
        times = np.r_[times,mms.EVENT_TIME_S-60,mms.EVENT_TIME_S,mms.EVENT_TIME_S+60]
    else:
        times = np.r_[times,cfg["Q4_switch_neighbors_s"]]
    return np.unique(times)


def trapezoid_weights(x):
    dx = np.diff(x)
    return np.r_[dx[0]/2,(dx[:-1]+dx[1:])/2,dx[-1]/2]


def reference_fields(path, budget_path, times, x):
    if path is None or budget_path is None:
        raise ValueError("Q4 evaluation needs both an independent reference and its qualified error budget.")
    with np.load(path) as data:
        rt = data["sample_times_s"]
        rx = data["sample_xi"]**2 if "sample_xi" in data else data["x"]
        rows = [int(np.flatnonzero(np.isclose(rt,t,rtol=0,atol=1e-8))[0]) for t in times]
        cols = [int(np.flatnonzero(np.isclose(rx,v,rtol=0,atol=1e-13))[0]) for v in x]
        fields = data["fields"][rows][:,cols,:]
    budget = json.loads(Path(budget_path).read_text())
    if budget.get("status") != "established_working_estimate" or budget.get("scope") != "all_frozen_Q4_score_points":
        raise ValueError("Reference error qualification does not cover the frozen Q4 point set.")
    uncertainty = np.asarray(budget["U_ref_C_T"],float)
    if uncertainty.shape not in [(2,),fields.shape] or np.any(uncertainty<0) or not np.isfinite(uncertainty).all():
        raise ValueError("Invalid reference uncertainty dimensions/values.")
    return fields, np.broadcast_to(uncertainty,fields.shape)


def event_estimate(model, cfg, deadline):
    times = score_times(cfg,"MMS")
    def maximum(t, count, local):
        if time.perf_counter() >= deadline:
            raise TimeoutError("Evaluation budget reached during event search.")
        x = np.linspace(0.,1.,count)
        values = predict(model,x,np.full(count,t))[:,0]
        answer = float(values.max())
        if local:
            points = torch.tensor(np.column_stack((x,np.full(count,t))),requires_grad=True)
            slope = derivatives(model(points)[:,0],points,create_graph=False)[:,0].detach().numpy()
            def gradient(at):
                p=torch.tensor([[at,t]],requires_grad=True)
                return float(derivatives(model(p)[:,0],p,create_graph=False)[0,0].detach())
            for j in np.flatnonzero(slope[:-1]*slope[1:]<0):
                root=brentq(gradient,x[j],x[j+1],xtol=1e-12)
                answer=max(answer,float(predict(model,[root],[t])[0,0]))
        return answer
    roots=[]
    for count,local in [(n,False) for n in cfg["event_spatial_counts"]]+[(cfg["event_spatial_counts"][-1],True)]:
        previous=maximum(times[0],count,local)-.15
        root=0. if previous<=0 else None
        for left,right in zip(times[:-1],times[1:]):
            if root is not None:break
            value=maximum(right,count,local)-.15
            if previous>0>=value:
                root=float(brentq(lambda t:maximum(t,count,local)-.15,left,right,xtol=1e-7))
            previous=value
        roots.append(root)
    if any(r is None for r in roots):
        return {"passed":False,"roots_s":roots,"reason":"no_downward_crossing_in_window"}
    stability=max(abs(roots[-2]-roots[-3]),abs(roots[-1]-roots[-2]))
    error=abs(roots[-1]-mms.EVENT_TIME_S)
    return {"passed":bool(stability<=cfg["thresholds"]["MMS_event_spatial_stability_s"] and error<=cfg["thresholds"]["MMS_event_error_s"]),
            "roots_s":roots,"spatial_stability_s":stability,"analytic_error_s":error,
            "method":"201/401/801 fixed-grid maxima, then 801 plus derivative roots and endpoints; no global certificate"}


def evaluate(args,cfg,config_hash,config_dir):
    start=time.perf_counter();deadline=start+cfg["evaluation_seconds"]
    checkpoint=Path(args.checkpoint);saved=torch.load(checkpoint,map_location="cpu",weights_only=True)
    metadata=saved["metadata"]
    if metadata["config_sha256"]!=config_hash:
        raise ValueError("Evaluation configuration differs from the frozen checkpoint.")
    case,seed=metadata["case"],metadata["seed"]
    model=FourierField(cfg,case,seed);model.load_state_dict(saved["state_dict"]);model.eval()
    physics=Physics(cfg,case,config_dir)
    if physics.input_hash!=metadata["observations_sha256"]:
        raise ValueError("Observed inputs changed after training.")
    x=np.linspace(0.,1.,cfg["score_x_count"]);times=score_times(cfg,case)
    xx,tt=np.meshgrid(x,times);prediction=predict(model,xx,tt).reshape(len(times),len(x),2)
    if case=="MMS":
        truth=mms.exact(tt.ravel(),np.sqrt(xx.ravel())).reshape(prediction.shape);u=np.zeros_like(truth)
    else:truth,u=reference_fields(args.reference,args.reference_budget,times,x)
    absolute=np.abs(prediction-truth)+u
    wx,wt=trapezoid_weights(x),trapezoid_weights(times)
    l2=np.sqrt(np.sum(absolute**2*wt[:,None,None]*wx[None,:,None],axis=(0,1))/(wt.sum()*wx.sum()))
    linf=absolute.max(axis=(0,1));normalized_l2=l2/SCALES;normalized_linf=linf/SCALES
    locations=[]
    for column in range(2):
        row,position=np.unravel_index(np.argmax(absolute[:,:,column]),absolute[:,:,column].shape)
        locations.append({"time_s":float(times[row]),"x":float(x[position]),"xi":float(np.sqrt(x[position]))})
    initial=mms.exact(0.,np.sqrt(x)) if case=="MMS" else np.tile([2.55,28.],(len(x),1))
    ic_error=np.max(abs(prediction[0]-initial),axis=0)/SCALES
    holdout=samples(cfg,case,seed+20000,"holdout")
    parts=physics.residuals(model,*holdout);stats=residual_stats(parts)
    thresholds=cfg["thresholds"]
    gates={"L2":bool(np.all(normalized_l2<=thresholds["normalized_L2_C_T"])),
           "Linf":bool(np.all(normalized_linf<=thresholds["normalized_Linf_C_T"])),
           "IC":bool(np.all(ic_error<=thresholds["normalized_IC_Linf_C_T"])),
           "heldout_PDE_Robin":all(v["rmse"]<=thresholds["residual_rmse"] and v["max_abs"]<=thresholds["residual_max"] for k,v in stats.items() if not k.startswith("IC"))}
    event={"status":"not_tested_for_real_event"}
    if case=="MMS":
        if all(gates.values()):
            try:event=event_estimate(model,cfg,deadline)
            except TimeoutError:event={"passed":False,"reason":"evaluation_budget_limited"}
        else:event={"passed":False,"reason":"earlier_required_field_or_residual_gate_failed"}
        gates["MMS_event"]=event["passed"]
    radius,ambient=physics.inputs(times)
    mean_c=np.trapezoid(prediction[:,:,0],x,axis=1)
    rate=-2*8e-7/radius*(prediction[:,-1,0]-ambient[:,1])
    if case=="MMS":rate+=np.trapezoid(mms.source(tt.ravel(),np.sqrt(xx.ravel()),"Q4")[:,0].reshape(xx.shape),x,axis=1)
    water=mean_c-mean_c[0]-cumulative_trapezoid(rate,times,initial=0.)
    result={"target_id":cfg["target_id"],"case":case,"seed":seed,"config_sha256":config_hash,
            "checkpoint_sha256":hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            "accepted":all(gates.values()),"status":"accuracy_target_met" if all(gates.values()) else "accuracy_target_not_met",
            "checks":gates,"window_s":cfg["windows_s"][case],"score_points":[len(times),len(x)],
            "L2_C_T":l2.tolist(),"Linf_C_T":linf.tolist(),"normalized_L2_C_T":normalized_l2.tolist(),
            "maximum_error_locations_C_T":locations,
            "normalized_Linf_C_T":normalized_linf.tolist(),"normalized_IC_C_T":ic_error.tolist(),
            "heldout_residuals":stats,"event":event,"water_budget_sampled_max_abs":float(np.max(abs(water))),
            "water_budget_scope":"Trapezoid diagnostic on frozen score times/x; not a conservation error bound.",
            "claims_not_tested":cfg["claims_not_tested"],"elapsed_evaluation_s":time.perf_counter()-start,
            "FVM_training_labels_used":False}
    write_json(args.output,result);print(json.dumps({k:result[k] for k in ["status","case","seed","checks"]}))


def smoke(args,cfg,config_hash,config_dir):
    physics=Physics(cfg,"MMS",config_dir)
    def analytic(points):
        x,t=points[:,0],points[:,1];q=torch.exp(-t/3600.)
        return torch.stack((.05+2.5*q*(1-.3*x+.1*x*x),28+12*(1-q)*(1+.2*x+.05*x*x)),dim=1)
    interior=torch.tensor([[0.,1.],[.01,60.],[.25,3600.],[.8,mms.EVENT_TIME_S],[1.,14400.]])
    boundary=torch.tensor([[1.,t] for t in [1.,60.,3600.,mms.EVENT_TIME_S,14400.]])
    initial=torch.tensor([[x,0.] for x in [0.,.1,.5,1.]])
    residual=residual_stats(physics.residuals(analytic,interior,boundary,initial))
    model=FourierField(cfg,"MMS",17)
    torch.nn.init.normal_(model.output.weight,std=.03)
    hard_ic=float((model(initial)-analytic(initial)).detach().abs().max())
    small=physics.residuals(model,interior,boundary,initial)
    loss=sum(v.square().mean() for v in small.values());loss.backward()
    finite=bool(torch.isfinite(loss) and all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters()))
    real_model=FourierField(cfg,"Q4",17)
    real_physics=Physics(cfg,"Q4",config_dir)
    real_parts=real_physics.residuals(real_model,interior,boundary,initial)
    real_loss=sum(v.square().mean() for v in real_parts.values());real_loss.backward()
    real_finite=bool(torch.isfinite(real_loss) and all(p.grad is None or torch.isfinite(p.grad).all() for p in real_model.parameters()))
    analytic_event=event_estimate(analytic,cfg,time.perf_counter()+30.)
    passed=all(v["max_abs"]<1e-10 for v in residual.values()) and hard_ic<1e-12 and finite and real_finite and analytic_event["passed"]
    result={"status":"PASS" if passed else "FAIL","scope":"float64 second-AD, cylindrical flux/axis/Robin/source and hard-IC smoke only",
            "config_sha256":config_hash,"analytic_normalized_residuals":residual,"hard_IC_max_abs_C_T":hard_ic,
            "network_backward_finite":finite,"dtype":str(next(model.parameters()).dtype),"device":"cpu",
            "Q4_fresh_initialization_backward_finite":real_finite,
            "analytic_function_event_search_check":analytic_event,
            "optimizer_steps":0,"formal_training_status":"NOT_STARTED","torch_version":torch.__version__}
    write_json(args.output,result);print(json.dumps(result,ensure_ascii=False))
    if not passed:raise SystemExit(1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=DEFAULT_CONFIG)
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("smoke");p.add_argument("--output",type=Path,required=True)
    p=sub.add_parser("train");p.add_argument("--case",choices=["MMS","Q4"],required=True)
    p.add_argument("--seed",type=int,choices=[17,29,43],default=17);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--mms-gate",type=Path);p.add_argument("--pilot-gate",type=Path)
    p=sub.add_parser("evaluate");p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--reference",type=Path);p.add_argument("--reference-budget",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();cfg,digest,directory=read_config(args.config)
    try:
        {"smoke":smoke,"train":train,"evaluate":evaluate}[args.command](args,cfg,digest,directory)
    except Exception as exc:
        failure={"status":"failed","command":args.command,"case":getattr(args,"case",None),
                 "config_sha256":digest,"reason":type(exc).__name__+": "+str(exc),"accepted":False}
        output=Path(args.output)
        if args.command=="train":
            if output.is_dir():write_json(output/"training_failure.json",failure)
        elif output.parent.is_dir():write_json(output,failure)
        raise


if __name__=="__main__":main()
