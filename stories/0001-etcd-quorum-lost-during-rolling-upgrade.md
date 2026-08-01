---
id: "0001"
title: etcd quorum lost during rolling upgrade
stack: [kubernetes, etcd, kubespray]
severity: sev1
detection: manual
time_to_detect: 4m
time_to_resolve: 1h35m
root_cause_category: configuration
blast_radius: cluster
contributed_by: "@maintainer"
date: 2025-11
---

## Symptom

Midway through a planned control-plane upgrade, `kubectl` began returning
timeouts against every apiserver. Workloads already running stayed up and kept
serving traffic — no customer-visible impact — but the cluster could not be
changed: no deployments, no scaling, no rescheduling. The apiserver logs showed
a clean, graceful shutdown rather than a crash, which made the failure look
intentional and cost time later.

## Timeline

- `21:10` — Rolling upgrade starts. First control-plane node completes normally.
- `21:38` — Second control-plane node is drained and restarted.
- `21:42` — All `kubectl` calls start timing out. Running workloads unaffected.
- `21:55` — Apiserver logs reviewed; the shutdown looks graceful, so attention
  goes to the upgrade tooling rather than the datastore.
- `22:20` — `etcdctl endpoint status` against each member individually shows two
  of three members unreachable *from each other* while reachable from the
  operator's laptop.
- `22:40` — Root cause identified in the inventory.
- `23:15` — Members recovered, quorum restored, upgrade resumed and completed.

## What we thought it was

The first hypothesis was the upgrade tooling: a rolling upgrade that stalls
halfway is, in the overwhelming majority of cases, a playbook that failed on a
task and left the node half-configured. We spent roughly fifteen minutes reading
task output that turned out to be entirely clean.

The second hypothesis was the apiserver itself, because its log showed an
orderly shutdown sequence. A graceful shutdown reads as deliberate, so it
anchored us on "something told it to stop" rather than "it lost the thing it
depends on". In fact the apiserver was behaving correctly: it had lost its
datastore and shut itself down rather than serve stale reads. The log was
evidence of a healthy component reacting to an unhealthy dependency, and we read
it as the problem.

The signal that should have redirected us within two minutes: existing workloads
were completely unaffected. That excludes the network dataplane, the kubelets,
and the container runtime, and leaves only the control plane's own state store.
When the only thing broken is *change*, look at the datastore first.

## Actual root cause

The nodes were multi-homed: one interface for management and SSH, a second,
separate interface for cluster data traffic. The inventory had been written with
both an address for SSH connectivity and an address intended for peer traffic,
but the peer address had been populated with the management address on two of
the three control-plane nodes.

This is invisible while nothing restarts. Established etcd peer connections
continue working on whatever path they were built on. The mistake only
materialises when a member restarts and re-reads its peer URLs — at which point
it advertises and dials an address that the other members cannot route to. The
first node restart therefore succeeded and looked like proof the upgrade was
safe. The second restart took quorum below two and froze the control plane.

## Fix

Immediate: corrected the peer addresses in the inventory, then restarted the
affected members one at a time, verifying `endpoint health` from *another
member* rather than from the operator's workstation before touching the next.

Durable: the two address fields are now derived from a single source of truth in
the inventory rather than maintained independently, so they cannot disagree.

## What would have prevented it

A pre-upgrade gate that asserts every etcd member can reach every other member
on its configured peer URL, executed *from inside each node* rather than from
the operator's machine. The check is three lines and would have failed loudly
before the first node was touched.

Secondarily: never validate a rolling change against a sample of one. The first
node succeeding proved nothing, because the failure mode required a second
member to leave.

## Generalizable lesson

Distributed systems with a quorum will absorb a misconfiguration silently until
the exact moment a restart forces them to re-read it. Any config that is only
consulted at startup is a landmine with a delay fuse, and the delay is however
long it has been since your last restart.

The operational habit that follows: when you verify connectivity, verify it from
the perspective of the component that needs it, not from your own. Reachability
from a laptop on the management network is not evidence about a data network,
and on multi-homed hosts those two answers routinely differ.
