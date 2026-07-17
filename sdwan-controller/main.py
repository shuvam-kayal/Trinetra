from fastapi import FastAPI
from datetime import datetime, timezone
import docker

app = FastAPI(title="Trinetra SD-WAN Controller")
client = docker.from_env()

# --- Minimal policy database -------------------------------------------
# Real deployment would persist this (Qdrant/etcd/etc). For the prototype,
# an in-memory store is enough to give Person B something structured to poll,
# instead of nothing at all.
STATE = {
    "policy_version": "v1.0-initial",
    "push_history": [],   # list of {timestamp, target_devices, event_type, push_success_flag}
}

# Node name -> its QoS-managed interface (kept in sync with scripts/2_apply_qos.sh)
MANAGED_NODES = {
    "Branch-09-CE": ("clab-trinetra-branch-ce1", "eth1"),
}

QOS_COMMANDS = [
    "tc qdisc del dev {iface} root",
    "tc qdisc add dev {iface} root handle 1: htb default 30",
    "tc class add dev {iface} parent 1: classid 1:1 htb rate 100mbit ceil 100mbit",
    "tc class add dev {iface} parent 1:1 classid 1:10 htb rate 20mbit ceil 100mbit prio 1",
    "tc class add dev {iface} parent 1:1 classid 1:20 htb rate 50mbit ceil 100mbit prio 2",
    "tc class add dev {iface} parent 1:1 classid 1:30 htb rate 5mbit  ceil 100mbit prio 3",
    "tc filter add dev {iface} protocol ip parent 1:0 prio 1 u32 match ip tos 0xb8 0xff flowid 1:10",
    "tc filter add dev {iface} protocol ip parent 1:0 prio 2 u32 match ip tos 0x48 0xff flowid 1:20",
    "tc filter add dev {iface} protocol ip parent 1:0 prio 3 u32 match ip tos 0x00 0xff flowid 1:30",
]


def _log_push(target_devices, event_type, success):
    STATE["push_history"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "target_devices": target_devices,
        "push_success_flag": success,
    })
    # keep last 50 pushes only
    STATE["push_history"] = STATE["push_history"][-50:]


@app.post("/api/qos/apply")
def apply_qos():
    target_name, (container_name, iface) = next(iter(MANAGED_NODES.items()))
    try:
        node = client.containers.get(container_name)
        for cmd in QOS_COMMANDS:
            node.exec_run(cmd.format(iface=iface))
        STATE["policy_version"] = f"v1.{len(STATE['push_history']) + 1}-qos-update"
        _log_push([target_name], "policy_push", True)
        return {"status": "success", "message": f"QoS rules applied to {target_name}",
                "policy_version": STATE["policy_version"]}
    except Exception as e:
        _log_push([target_name], "policy_push", False)
        return {"status": "error", "message": str(e)}


@app.post("/api/qos/clear")
def clear_qos():
    target_name, (container_name, iface) = next(iter(MANAGED_NODES.items()))
    try:
        node = client.containers.get(container_name)
        node.exec_run(f"tc qdisc del dev {iface} root")
        return {"status": "success", "message": "QoS rules cleared. Link is wide open."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/telemetry/state")
def telemetry_state():
    """
    Pragmatic substitute for a full gNMI gRPC server (out of scope for the
    prototype). Structured JSON matching topic.controller.events so Person B
    can point Telegraf's http input plugin at this every 30s instead of gNMIc.
    """
    return {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": "SDWAN-Controller-1",
        "role": "SDWANController",
        "controller_metrics": {
            "active_policy_version": STATE["policy_version"],
            "push_history": STATE["push_history"][-10:],
            "managed_devices": list(MANAGED_NODES.keys()),
        },
    }
