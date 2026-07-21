"""Fault 3: BGP peer drop - administratively shuts a BGP session, forcing
route withdrawal and reconvergence."""

FAULT_CLASS = "bgp_instability"
DEFAULT_SEVERITY = "high"
DEFAULT_DURATION = 30
DEFAULTS = {"container": "clab-trinetra-hub-pe1", "asn": 65000, "neighbor_ip": "10.1.1.1"}


def start(exec_fn, container, asn, neighbor_ip, **params):
    exec_fn(container,
            f'vtysh -c "configure terminal" -c "router bgp {asn}" '
            f'-c "neighbor {neighbor_ip} shutdown"')
    return {"container": container, "asn": asn, "neighbor_ip": neighbor_ip}


def stop(exec_fn, container, asn, neighbor_ip, **params):
    exec_fn(container,
            f'vtysh -c "configure terminal" -c "router bgp {asn}" '
            f'-c "no neighbor {neighbor_ip} shutdown"')
    return {"container": container, "asn": asn, "neighbor_ip": neighbor_ip}
