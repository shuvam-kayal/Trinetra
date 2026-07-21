"""
Factory 1.9 - Fault Injection Engine.

Scoped to the 7 fault classes the ML ensemble (Factory 1.3B) actually
trains on: congestion, bgp_instability, tunnel_degradation,
routing_asymmetry, te_preemption, ipsec_rekey_anomaly, controller_policy_drift.
link_flap and config_drift were dropped - they were L1 mechanisms in the
original doc, never part of the 7-class vocabulary.
"""

import threading
import uuid
from datetime import datetime, timezone

import docker
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any

from scenarios import (
    congestion, bgp_drop, tunnel_jitter,
    asymmetric_delay, te_preemption, rekey_storm, controller_drift,
)

app = FastAPI(title="Trinetra Fault Injection Engine")
client = docker.from_env()

SCENARIOS = {
    "congestion": congestion,
    "bgp_drop": bgp_drop,
    "tunnel_jitter": tunnel_jitter,
    "asymmetric_delay": asymmetric_delay,
    "te_preemption": te_preemption,
    "rekey_storm": rekey_storm,
    "controller_drift": controller_drift,
}

CONTAINER_TO_DEVICE = {
    "clab-trinetra-branch-ce1": "Branch-CE1",
    "clab-trinetra-hub-pe1": "Hub-PE1",
    "clab-trinetra-core-p1": "Core-P1",
    "clab-trinetra-dc-1": "DC-1",
}

ACTIVE: Dict[str, dict] = {}
HISTORY: list = []
_timers: Dict[str, threading.Timer] = {}


def exec_cmd(container_name, cmd):
    """Strict executor - raises on non-zero exit. Used only for starting a
    fault, where we want to know immediately if injection actually worked."""
    node = client.containers.get(container_name)
    result = node.exec_run(["sh", "-c", cmd])
    output = result.output.decode(errors="ignore")
    if result.exit_code != 0:
        raise RuntimeError(f"exit={result.exit_code}: {cmd.strip()} -> {output.strip()}")
    return output


def _run_stop(scenario, target):
    """
    Tolerant executor for stopping/reverting. Always attempts every command
    in a multi-step stop() even if an earlier one fails, so cleanup never
    gets abandoned partway through. Returns (all_ok, errors) so callers -
    especially reset-all - can honestly report whether anything actually
    happened, instead of a blanket 'reverted' regardless of outcome.
    """
    errors = []

    def tolerant_exec(container_name, cmd):
        node = client.containers.get(container_name)
        result = node.exec_run(["sh", "-c", cmd])
        output = result.output.decode(errors="ignore")
        if result.exit_code != 0:
            errors.append(f"[{container_name}] exit={result.exit_code}: "
                           f"{cmd.strip()} -> {output.strip()}")
        return output

    try:
        scenario.stop(tolerant_exec, **target)
    except Exception as e:
        errors.append(str(e))

    return (len(errors) == 0), errors


def _describe_target(target):
    container = target.get("container")
    device = CONTAINER_TO_DEVICE.get(container, container)
    ifaces = [target["iface"]] if target.get("iface") else []
    return [device], ifaces


class FaultStartRequest(BaseModel):
    scenario: str
    duration_seconds: Optional[int] = None
    params: Optional[Dict[str, Any]] = None


def _finalize(fault_id, status):
    """Runs the scenario's stop() and moves the fault from ACTIVE to HISTORY."""
    entry = ACTIVE.pop(fault_id, None)
    if entry is None:
        return None
    scenario = SCENARIOS[entry["fault_class_key"]]
    ok, errors = _run_stop(scenario, entry["target"])
    if not ok:
        entry["stop_errors"] = errors
    entry["end_time"] = datetime.now(timezone.utc).isoformat()
    entry["status"] = status
    HISTORY.append(entry)
    HISTORY[:] = HISTORY[-200:]
    _timers.pop(fault_id, None)
    return entry


@app.post("/fault/start")
def start_fault(req: FaultStartRequest):
    if req.scenario not in SCENARIOS:
        return {"status": "error", "message": f"Unknown scenario '{req.scenario}'. "
                                               f"Valid: {list(SCENARIOS.keys())}"}
    scenario = SCENARIOS[req.scenario]
    target = {**scenario.DEFAULTS, **(req.params or {})}
    duration = req.duration_seconds or scenario.DEFAULT_DURATION

    fault_id = f"FLT-{uuid.uuid4().hex[:8]}"
    devices, ifaces = _describe_target(target)
    now = datetime.now(timezone.utc).isoformat()

    try:
        start_result = scenario.start(exec_cmd, **target)
    except Exception as e:
        return {"status": "error", "message": f"Failed to start scenario: {e}"}

    entry = {
        "schema_version": "1.0",
        "timestamp": now,
        "fault_id": fault_id,
        "fault_class": scenario.FAULT_CLASS,
        "fault_class_key": req.scenario,
        "start_time": now,
        "end_time": None,
        "affected_devices": devices,
        "affected_interfaces": ifaces,
        "severity": scenario.DEFAULT_SEVERITY,
        "status": "active",
        "target": target,
        "start_result": start_result,
    }
    ACTIVE[fault_id] = entry

    timer = threading.Timer(duration, _finalize, args=[fault_id, "auto_reverted"])
    timer.daemon = True
    timer.start()
    _timers[fault_id] = timer

    return entry


@app.post("/fault/stop/{fault_id}")
def stop_fault(fault_id: str):
    timer = _timers.get(fault_id)
    if timer:
        timer.cancel()
    entry = _finalize(fault_id, "stopped_manually")
    if entry is None:
        return {"status": "error", "message": f"No active fault with id {fault_id}"}
    return entry


@app.post("/fault/reset-all")
def reset_all():
    """
    Panic button - best-effort stop of every scenario, active or not,
    regardless of tracked state. Now honestly reports per-scenario whether
    a stop actually did anything vs. failed/no-op, instead of a blanket
    'reverted' for everything.
    """
    results = {}
    for key, scenario in SCENARIOS.items():
        ok, errors = _run_stop(scenario, scenario.DEFAULTS)
        results[key] = "reverted" if ok else {"status": "no_action_or_partial", "detail": errors}

    for fault_id in list(_timers.keys()):
        _timers[fault_id].cancel()
        _timers.pop(fault_id, None)
    for fault_id in list(ACTIVE.keys()):
        entry = ACTIVE.pop(fault_id)
        entry["end_time"] = datetime.now(timezone.utc).isoformat()
        entry["status"] = "force_reset"
        HISTORY.append(entry)

    return {"status": "reset_complete", "per_scenario": results}


@app.get("/fault/active")
def get_active():
    return ACTIVE


@app.get("/fault/history")
def get_history():
    """This is the topic.fault.events feed - ground truth labels for training."""
    return HISTORY[-100:]


@app.get("/fault/scenarios")
def list_scenarios():
    return {
        key: {
            "fault_class": mod.FAULT_CLASS,
            "default_severity": mod.DEFAULT_SEVERITY,
            "default_duration_seconds": mod.DEFAULT_DURATION,
            "default_target": mod.DEFAULTS,
        }
        for key, mod in SCENARIOS.items()
    }