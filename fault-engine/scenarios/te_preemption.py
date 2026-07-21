"""Fault 7: TE tunnel preemption cascade - thin wrapper around te-engine's
already-built and tested /fault/te-preempt and /fault/te-restore endpoints
(Factory 1.4). Addressed by container DNS name, not IP - survives redeploys."""

import requests

FAULT_CLASS = "te_preemption"
DEFAULT_SEVERITY = "high"
DEFAULT_DURATION = 40
DEFAULTS = {"container": "clab-trinetra-hub-pe1", "iface": "eth2"}

TE_ENGINE_URL = "http://clab-trinetra-te-engine:8000"


def start(exec_fn, container, iface, **params):
    r = requests.post(f"{TE_ENGINE_URL}/fault/te-preempt", timeout=10)
    return {"container": container, "iface": iface, "te_engine_response": r.json()}


def stop(exec_fn, container, iface, **params):
    r = requests.post(f"{TE_ENGINE_URL}/fault/te-restore", timeout=10)
    return {"container": container, "iface": iface, "te_engine_response": r.json()}
