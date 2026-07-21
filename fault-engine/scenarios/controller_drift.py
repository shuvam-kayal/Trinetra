"""Fault 9: Controller policy drift - calls sdwan-controller's malformed
policy push endpoint (Factory 1.5), which deliberately removes the voice
DSCP filter so EF traffic falls through to the default bulk class."""

import requests

FAULT_CLASS = "controller_policy_drift"
DEFAULT_SEVERITY = "high"
DEFAULT_DURATION = 45
DEFAULTS = {"container": "clab-trinetra-branch-ce1", "iface": "eth1"}

CONTROLLER_URL = "http://clab-trinetra-sdwan-controller:8000"


def start(exec_fn, container, iface, **params):
    r = requests.post(f"{CONTROLLER_URL}/api/qos/push-malformed-policy", timeout=10)
    return {"container": container, "iface": iface, "controller_response": r.json()}


def stop(exec_fn, container, iface, **params):
    r = requests.post(f"{CONTROLLER_URL}/api/qos/rollback-policy", timeout=10)
    return {"container": container, "iface": iface, "controller_response": r.json()}
