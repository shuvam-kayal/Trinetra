Plus two standalone service nodes (no router links): `te-engine`, `fault-engine`.

| Node | Role | Loopback | AS (if BGP) |
|---|---|---|---|
| branch-ce1 | CE | 10.0.0.3 | 65001 |
| hub-pe1 | PE | 10.0.0.2 | 65000 |
| core-p1 | P | 10.0.0.1 | — |
| dc-1 | DC | 10.0.0.4 | — |

Routing: OSPF area 0 across the core (hub-pe1↔core-p1↔dc-1). CE↔PE (branch-ce1↔hub-pe1)
runs eBGP only, deliberately kept out of the core OSPF domain. A static route +
`redistribute static`/`redistribute ospf` bridge the two domains so branch's loopback
is reachable from the core and vice versa.

## Services and Ports

| Service | Container | Port | Purpose |
|---|---|---|---|
| SD-WAN Controller | `clab-trinetra-sdwan-controller` | 8000 | QoS push, policy version/history, `/telemetry/state` (REST stand-in for gNMI — point Telegraf's `http` input plugin here) |
| TE Engine | `clab-trinetra-te-engine` | 8000 | Real OSPF-TE-derived bandwidth headroom, RSVP-TE state simulation, real `tc`-enforced preemption |
| Fault Injection Engine | `clab-trinetra-fault-engine` | 8000 | 7 fault scenarios matching the ML ensemble's fault-class vocabulary |

## Fault Injection — 7 Classes

Scoped to exactly the classes the 1D-CNN fault-fingerprinting model (Factory 1.3B)
trains on. `link_flap` and `config_drift` scenario code exists in
`fault-engine/scenarios/` but is **not registered** — dropped because neither
appears in the actual 7-class ML vocabulary from the architecture spec.

| Scenario key | `fault_class` | Mechanism |
|---|---|---|
| `congestion` | `congestion` | Shrinks root HTB ceiling on a link |
| `bgp_drop` | `bgp_instability` | Admin-shuts a BGP neighbor |
| `tunnel_jitter` | `tunnel_degradation` | `netem` delay/jitter/loss on the IPsec-bearing tc class |
| `asymmetric_delay` | `routing_asymmetry` | One-directional `netem` delay on a single link |
| `te_preemption` | `te_preemption` | Calls te-engine's real preemption endpoint |
| `rekey_storm` | `ipsec_rekey_anomaly` | Delay/loss targeted at IKE ports 500/4500 only |
| `controller_drift` | `controller_policy_drift` | Controller removes the voice DSCP filter |

Every fault: has a `start()`/`stop()` pair, auto-reverts on a timer, and logs an entry
matching `topic.fault.events` (schema v3.0 confirmed compatible — no code changes
needed there). `GET /fault/history` on the fault-engine **is** that feed — this is
the ground-truth label source for Person C's model training.

`POST /fault/reset-all` is a panic-button that force-reverts every scenario and
honestly reports per-scenario whether anything was actually active (idempotent
scenarios always report `"reverted"`; deletion-based ones report
`"no_action_or_partial"` with the real `tc`/vtysh error if nothing was running).

## Known Limitations / Honest Deviations from Spec

- **Single-branch topology.** One CE, one PE, one P, one DC — not the "multi-site"
  topology in the original doc. Phase-1 scope; multi-branch would require topology
  file changes only, not architectural changes.
- **RSVP-TE is simulated, not real.** FRR has no `rsvpd`. OSPF-TE (link-state
  advertisement of bandwidth via opaque LSAs) is genuinely real and verified via
  `show ip ospf database opaque-area`. RSVP session signaling and preemption
  decisions are tracked as a Python state machine in `te-engine/`, but the
  bandwidth enforcement it performs (`tc class change`) is real and measurable.
- **No path diversity.** Only one physical path exists (hub-pe1→core-p1→dc-1), so:
  - `routing_asymmetry` fault produces real one-directional latency divergence on
    a single link, not true ECMP multi-path divergence.
  - TE's "secondary LSP" can be throttled/preempted but cannot reroute to an
    alternate path. Adding a parallel `core-p2` node would unlock true path
    diversity for both of these.
- **Ostinato → iperf3.** Traffic generation uses iperf3 instead of the
  spec-named Ostinato — simpler to script reliably, still produces DSCP-marked
  voice (real UDP)/business/bulk traffic patterns.
- **No VRF/L3VPN.** Routing is real BGP/OSPF, but there's no actual customer VPN
  segmentation (VRF + MP-BGP VPNv4) yet — noted as a Tier 2 stretch item.
- **IPFIX collector target unconfirmed.** `softflowd` on every node exports to
  `10.0.0.99:2055` — a placeholder pending Person B's real pmacct collector IP.

## Scripts

| Script | Purpose |
|---|---|
| `0_init_network.sh` | Builds all 4 Docker images (router, controller, te-engine, fault-engine) |
| `1_start_telemetry.sh` | Starts softflowd on every interface, every node |
| `2_apply_qos.sh` | Applies the 3-class DSCP QoS hierarchy to every interface, every node |
| `3_generate_traffic.sh` | Fires voice (UDP)/bulk/bursty business traffic |
| `4_test_te_preemption.sh` | End-to-end TE preemption demo against te-engine directly |
| `5_test_fault_injection.sh` | Smoke test: congestion + BGP drop + reset-all |
| `6_test_remaining_faults.sh` | Fire-tests the other 5 fault scenarios individually |

## Team Handoff

- **Person B** consumes: the topology structure (for seeding Neo4j — a formal
  `topology_map.json` export is still pending), all Kafka-bound telemetry once L2
  is wired up, and `/fault/history` as the ground-truth label feed.
- **Person C** consumes: labeled feature vectors that B derives from this
  telemetry, plus the fault-class taxonomy documented above.
- **Person D** consumes: prediction/recommendation objects downstream of B/C —
  no direct dependency on this repo.