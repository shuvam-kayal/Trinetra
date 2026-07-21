"""Fault 6: Asymmetric divergence - one-directional delay applied only to
this node's egress on one traffic class, so forward and reverse latency
diverge on the same link. NOTE: this is a scoped-down version of "ECMP
divergence" from the architecture spec - true ECMP needs a second parallel
core path, which this topology doesn't have yet. The resulting asymmetric
latency signal is real; the "equal-cost multi-path" mechanism is not."""

FAULT_CLASS = "routing_asymmetry"
DEFAULT_SEVERITY = "medium"
DEFAULT_DURATION = 40
DEFAULTS = {"container": "clab-trinetra-core-p1", "iface": "eth2", "delay_ms": 20}


def start(exec_fn, container, iface, delay_ms=20, **params):
    exec_fn(container, f"tc qdisc add dev {iface} parent 1:20 handle 20: "
                        f"netem delay {delay_ms}ms")
    return {"container": container, "iface": iface, "delay_ms": delay_ms}


def stop(exec_fn, container, iface, **params):
    exec_fn(container, f"tc qdisc del dev {iface} parent 1:20 handle 20:")
    return {"container": container, "iface": iface}
