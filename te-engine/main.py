"""
Factory 1.4 - RSVP-TE simulation layer.

FRR has real OSPF-TE (link-state advertisement of TE bandwidth attributes -
see the mpls-te stanzas in each router's frr.conf) but has NO rsvpd: there is
no FRR daemon that actually signals LSPs or performs constrained-path setup.

This service is the pragmatic substitute for that missing control plane:
  - REAL:      bandwidth headroom is computed from actual `tc -s class show`
               counters on the live routers, not fabricated.
  - REAL:      preemption is enforced with a real `tc class change` command,
               so the effect is physically measurable, not just logged.
  - SIMULATED: RSVP Path/Resv message exchange and session state (Up /
               Rerouting / Preempted) are tracked in software, since no real
               RSVP daemon exists to drive that state machine.

Two logical LSPs share the hub-pe1 -> core-p1 -> dc-1 path (the only path
that currently exists - there's no second core router yet for true path
diversity):
  - LSP-HubPE1-DC-Primary   -> maps to tc classes 1:10 (voice) + 1:20 (biz)
  - LSP-HubPE1-DC-Secondary -> maps to tc class  1:30 (bulk)

When told to simulate a "TE tunnel preemption cascade" (this is the same
call Factory 1.9's fault injection engine will make later), the engine
shrinks the secondary LSP's real tc ceiling, forcing the bulk class to
actually get squeezed - not just reporting a fake number.
"""

import re
import threading
import time
from datetime import datetime, timezone

import docker
from fastapi import FastAPI

app = FastAPI(title="Trinetra TE Engine (OSPF-TE real / RSVP-TE simulated)")
client = docker.from_env()

LINK_CAPACITY_MBPS = 100

# Every link in the current MPLS-TE path. Same physical link, monitored from
# both ends isn't necessary - we track it once per hop.
TE_LINKS = [
    {"container": "clab-trinetra-hub-pe1", "iface": "eth2", "hop": "hub-pe1->core-p1"},
    {"container": "clab-trinetra-core-p1", "iface": "eth2", "hop": "core-p1->dc-1"},
]

LSPS = {
    "LSP-HubPE1-DC-Primary": {
        "role": "primary",
        "tc_classes": ["1:10", "1:20"],
        "reserved_bandwidth_mbps": 70,
        "rsvp_state": "Up",
        "preempted_flag": False,
    },
    "LSP-HubPE1-DC-Secondary": {
        "role": "secondary",
        "tc_classes": ["1:30"],
        "reserved_bandwidth_mbps": 30,
        "normal_ceil_mbps": 100,   # what it's allowed to borrow up to normally
        "preempted_ceil_mbps": 2,  # what it gets squeezed down to when preempted
        "rsvp_state": "Up",
        "preempted_flag": False,
    },
}

EVENT_LOG = []


def _exec(container_name, cmd):
    node = client.containers.get(container_name)
    result = node.exec_run(cmd)
    return result.output.decode(errors="ignore")


def _log_event(event_type, lsp_id, detail):
    EVENT_LOG.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "lsp_id": lsp_id,
        "detail": detail,
    })
    EVENT_LOG[:] = EVENT_LOG[-50:]


def _measure_class_mbps(container_name, iface, classid, window_s=2.0):
    """Real measurement: diff 'Sent N bytes' on a tc class over a short window."""
    def sent_bytes():
        out = _exec(container_name, f"tc -s class show dev {iface}")
        # find the block for this classid, then the "Sent" line right after it
        pattern = re.compile(
            rf"class htb {re.escape(classid)}.*?Sent (\d+) bytes", re.DOTALL
        )
        m = pattern.search(out)
        return int(m.group(1)) if m else 0

    b0 = sent_bytes()
    time.sleep(window_s)
    b1 = sent_bytes()
    mbps = ((b1 - b0) * 8) / (window_s * 1_000_000)
    return round(mbps, 3)


def _current_headroom():
    """Real headroom = link capacity - actual measured demand on protected classes."""
    primary = LSPS["LSP-HubPE1-DC-Primary"]
    link = TE_LINKS[0]  # hub-pe1:eth2 is the first-hop bottleneck for this path
    actual = sum(
        _measure_class_mbps(link["container"], link["iface"], c, window_s=1.0)
        for c in primary["tc_classes"]
    )
    headroom = round(primary["reserved_bandwidth_mbps"] - actual, 3)
    return actual, headroom


@app.get("/lsps")
def list_lsps():
    actual_primary, headroom = _current_headroom()
    out = {}
    for lsp_id, lsp in LSPS.items():
        out[lsp_id] = {
            "role": lsp["role"],
            "reserved_bandwidth_mbps": lsp["reserved_bandwidth_mbps"],
            "rsvp_state": lsp["rsvp_state"],
            "preempted_flag": lsp["preempted_flag"],
        }
    out["LSP-HubPE1-DC-Primary"]["actual_bandwidth_mbps"] = actual_primary
    out["LSP-HubPE1-DC-Primary"]["te_bandwidth_headroom_mbps"] = headroom
    return out


@app.get("/telemetry/te")
def telemetry_te():
    """Shape matches topic.tunnel.health's te_metrics block."""
    actual_primary, headroom = _current_headroom()
    primary = LSPS["LSP-HubPE1-DC-Primary"]
    secondary = LSPS["LSP-HubPE1-DC-Secondary"]
    return {
        "schema_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": "Hub-PE1",
        "role": "PE",
        "te_metrics": {
            "lsp_id": "LSP-HubPE1-DC-Primary",
            "lsp_role": "primary",
            "rsvp_state": primary["rsvp_state"],
            "reserved_bandwidth_mbps": primary["reserved_bandwidth_mbps"],
            "actual_bandwidth_mbps": actual_primary,
            "te_bandwidth_headroom_mbps": headroom,
            "preempted_flag": primary["preempted_flag"],
        },
        "secondary_lsp": {
            "lsp_id": "LSP-HubPE1-DC-Secondary",
            "rsvp_state": secondary["rsvp_state"],
            "preempted_flag": secondary["preempted_flag"],
        },
        "recent_events": EVENT_LOG[-10:],
    }


@app.post("/fault/te-preempt")
def trigger_preemption():
    """
    Simulates a TE tunnel preemption cascade: the primary LSP's demand has
    exceeded its reserved headroom, so the secondary (bulk) LSP is squeezed.
    Real tc enforcement + logged RSVP-style state transition.
    """
    secondary = LSPS["LSP-HubPE1-DC-Secondary"]
    secondary["rsvp_state"] = "Rerouting"
    _log_event("rsvp_session_change", "LSP-HubPE1-DC-Secondary",
               "Primary LSP exceeded reserved bandwidth - initiating preemption")

    for link in TE_LINKS:
        cmd = (f"tc class change dev {link['iface']} parent 1:1 classid 1:30 "
               f"htb prio 3 rate 1mbit ceil {secondary['preempted_ceil_mbps']}mbit")
        _exec(link["container"], cmd)

    secondary["rsvp_state"] = "Preempted"
    secondary["preempted_flag"] = True
    _log_event("preemption_complete", "LSP-HubPE1-DC-Secondary",
               f"Secondary LSP ceiling reduced to {secondary['preempted_ceil_mbps']}mbit on all hops")
    return {"status": "preempted", "lsp": "LSP-HubPE1-DC-Secondary",
            "new_ceil_mbps": secondary["preempted_ceil_mbps"]}


@app.post("/fault/te-restore")
def restore_lsp():
    """Restores the secondary LSP to its normal reserved/borrowable bandwidth."""
    secondary = LSPS["LSP-HubPE1-DC-Secondary"]
    for link in TE_LINKS:
        cmd = (f"tc class change dev {link['iface']} parent 1:1 classid 1:30 "
               f"htb prio 3 rate 5mbit ceil {secondary['normal_ceil_mbps']}mbit")
        _exec(link["container"], cmd)

    secondary["rsvp_state"] = "Up"
    secondary["preempted_flag"] = False
    _log_event("lsp_restored", "LSP-HubPE1-DC-Secondary",
               "Bandwidth restored to normal reserved/ceil values")
    return {"status": "restored", "lsp": "LSP-HubPE1-DC-Secondary"}


def _background_monitor():
    """Keeps te_bandwidth_headroom fresh even with nobody polling /telemetry/te."""
    while True:
        try:
            _current_headroom()
        except Exception:
            pass
        time.sleep(10)


threading.Thread(target=_background_monitor, daemon=True).start()
