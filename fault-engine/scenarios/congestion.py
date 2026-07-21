"""Fault 2: Congestion - saturates a link by shrinking its own root HTB
ceiling, so any existing traffic immediately backs up (real queue depth,
real overlimits, real latency increase) without depending on flood
generators being alive."""

FAULT_CLASS = "congestion"
DEFAULT_SEVERITY = "high"
DEFAULT_DURATION = 45
DEFAULTS = {"container": "clab-trinetra-hub-pe1", "iface": "eth2", "squeeze_mbps": 3}


def start(exec_fn, container, iface, squeeze_mbps=3, **params):
    exec_fn(container, f"tc class change dev {iface} parent 1: classid 1:1 "
                        f"htb rate {squeeze_mbps}mbit ceil {squeeze_mbps}mbit")
    return {"container": container, "iface": iface, "squeeze_mbps": squeeze_mbps}


def stop(exec_fn, container, iface, **params):
    exec_fn(container, f"tc class change dev {iface} parent 1: classid 1:1 "
                        f"htb rate 100mbit ceil 100mbit")
    return {"container": container, "iface": iface}
