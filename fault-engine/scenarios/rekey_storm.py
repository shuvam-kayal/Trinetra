"""Fault 8: IPSec rekey timeout storm - delays/drops IKE (UDP 500/4500)
specifically, via a dedicated tc class + filters, without touching ESP data
traffic. Forces strongSwan rekey retransmits and eventual tunnel flap."""

FAULT_CLASS = "ipsec_rekey_anomaly"
DEFAULT_SEVERITY = "high"
DEFAULT_DURATION = 40
DEFAULTS = {"container": "clab-trinetra-branch-ce1", "iface": "eth1",
            "delay_ms": 500, "loss_pct": 20}


def start(exec_fn, container, iface, delay_ms=500, loss_pct=20, **params):
    exec_fn(container, f"tc class add dev {iface} parent 1:1 classid 1:40 "
                        f"htb prio 4 rate 1mbit ceil 1mbit")
    exec_fn(container, f"tc qdisc add dev {iface} parent 1:40 handle 40: "
                        f"netem delay {delay_ms}ms loss {loss_pct}%")
    exec_fn(container, f"tc filter add dev {iface} protocol ip parent 1:0 prio 0 "
                        f"u32 match ip dport 500 0xffff flowid 1:40")
    exec_fn(container, f"tc filter add dev {iface} protocol ip parent 1:0 prio 0 "
                        f"u32 match ip dport 4500 0xffff flowid 1:40")
    return {"container": container, "iface": iface, "delay_ms": delay_ms, "loss_pct": loss_pct}


def stop(exec_fn, container, iface, **params):
    exec_fn(container, f"tc filter del dev {iface} parent 1:0 prio 0")
    exec_fn(container, f"tc qdisc del dev {iface} parent 1:40 handle 40:")
    exec_fn(container, f"tc class del dev {iface} parent 1:1 classid 1:40")
    return {"container": container, "iface": iface}
