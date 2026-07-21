"""Fault 5: Configuration drift - simulates an unauthorized/accidental OSPF
cost change on a core link, silently shifting traffic engineering."""

FAULT_CLASS = "config_drift"
DEFAULT_SEVERITY = "medium"
DEFAULT_DURATION = 60
DEFAULTS = {"container": "clab-trinetra-hub-pe1", "iface": "eth2", "bad_cost": 999}


def start(exec_fn, container, iface, bad_cost=999, **params):
    exec_fn(container,
            f'vtysh -c "configure terminal" -c "interface {iface}" '
            f'-c "ip ospf cost {bad_cost}"')
    return {"container": container, "iface": iface, "bad_cost": bad_cost}


def stop(exec_fn, container, iface, **params):
    exec_fn(container,
            f'vtysh -c "configure terminal" -c "interface {iface}" '
            f'-c "no ip ospf cost"')
    return {"container": container, "iface": iface}
