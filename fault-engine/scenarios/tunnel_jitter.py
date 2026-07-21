"""Fault 4: Tunnel jitter - injects delay/jitter/loss on the class that
IPsec ESP traffic actually falls into (the default/bulk class 1:30, since
ESP isn't DSCP-marked and hits the QoS default)."""

FAULT_CLASS = "tunnel_degradation"
DEFAULT_SEVERITY = "medium"
DEFAULT_DURATION = 40
DEFAULTS = {"container": "clab-trinetra-branch-ce1", "iface": "eth1",
            "delay_ms": 15, "jitter_ms": 8, "loss_pct": 0.5}


def start(exec_fn, container, iface, delay_ms=15, jitter_ms=8, loss_pct=0.5, **params):
    exec_fn(container, f"tc qdisc add dev {iface} parent 1:30 handle 30: "
                        f"netem delay {delay_ms}ms {jitter_ms}ms loss {loss_pct}%")
    return {"container": container, "iface": iface, "delay_ms": delay_ms,
            "jitter_ms": jitter_ms, "loss_pct": loss_pct}


def stop(exec_fn, container, iface, **params):
    exec_fn(container, f"tc qdisc del dev {iface} parent 1:30 handle 30:")
    return {"container": container, "iface": iface}
