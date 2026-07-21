"""Fault 1: Link flap - brings an interface down and back up, forcing
BGP/OSPF reconvergence."""

FAULT_CLASS = "link_flap"
DEFAULT_SEVERITY = "medium"
DEFAULT_DURATION = 15
DEFAULTS = {"container": "clab-trinetra-hub-pe1", "iface": "eth2"}


def start(exec_fn, container, iface, **params):
    exec_fn(container, f"ip link set {iface} down")
    return {"container": container, "iface": iface}


def stop(exec_fn, container, iface, **params):
    exec_fn(container, f"ip link set {iface} up")
    return {"container": container, "iface": iface}
