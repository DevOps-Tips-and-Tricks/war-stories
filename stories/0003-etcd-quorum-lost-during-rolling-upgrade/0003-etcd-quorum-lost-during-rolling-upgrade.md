---
id: "0003"
title: etcd quorum lost during rolling upgrade
concept: Config read only at startup fails at the next restart, not when it changes
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

## The general problem

A quorum system does not check its own configuration. It reads the parts it
needs at startup, builds connections from them, and then keeps using those
connections for as long as they stay up. Change the configuration underneath a
running member and nothing happens — not because the change is correct, but
because nothing re-reads it.

The failure therefore arrives at a restart, and the restart can be weeks later
and performed by someone who has never seen the change. Two properties make this
class of bug expensive:

- **The delay is unbounded.** The fuse is however long it has been since the
  last restart, so the change and the outage are almost never correlated by the
  people looking.
- **Reachability is asked from the wrong place.** On a multi-homed host, "can I
  reach this address" has a different answer from an operator's workstation than
  from the peer that actually needs the path. Every tool answers the question you
  typed, from where you typed it.

Anything with a quorum inherits this: etcd, ZooKeeper, Consul, a database
cluster's replication addresses, a message broker's advertised listeners.

## Reproduce it

Three etcd members on one host, then a peer address that no peer can route to.
`192.0.2.13` is documentation space and is unreachable by design — it stands in
for the wrong interface on a multi-homed node.

```bash
# 1. bring up a three-member cluster on loopback
for i in 1 2 3; do
  etcd --name "m$i" --data-dir "/tmp/etcd-m$i" \
    --listen-client-urls        "http://127.0.0.1:$((2379+(i-1)*2))" \
    --advertise-client-urls     "http://127.0.0.1:$((2379+(i-1)*2))" \
    --listen-peer-urls          "http://127.0.0.1:$((2380+(i-1)*2))" \
    --initial-advertise-peer-urls "http://127.0.0.1:$((2380+(i-1)*2))" \
    --initial-cluster 'm1=http://127.0.0.1:2380,m2=http://127.0.0.1:2382,m3=http://127.0.0.1:2384' \
    --initial-cluster-state new >"/tmp/etcd-m$i.log" 2>&1 &
done

export ETCDCTL_ENDPOINTS=http://127.0.0.1:2379,http://127.0.0.1:2381,http://127.0.0.1:2383
etcdctl endpoint health          # three healthy members
```

```bash
# 2. break m3's peer address — the cluster does not react
ID=$(etcdctl member list | awk -F', ' '$3=="m3" {print $1}')
etcdctl member update "$ID" --peer-urls=http://192.0.2.13:2380
etcdctl endpoint health          # still three healthy members
```

That second `endpoint health` is the whole point. The cluster is already broken
and every instrument says it is fine, because the existing peer connections were
built before the change and nothing rebuilds them.

```bash
# 3. restart m3 — it cannot rejoin, but two of three is still a quorum
kill %3
etcdctl endpoint health          # m3 unhealthy, cluster still writable

# 4. restart m2 — quorum is now below two
kill %2
etcdctl put canary 1             # hangs, then fails
```

A healthy run is step 4 succeeding. The instructive part is steps 2 and 3
looking survivable: one restart proves nothing, because the failure needs a
second member to leave.

```bash
pkill -f 'etcd --name m'; rm -rf /tmp/etcd-m1 /tmp/etcd-m2 /tmp/etcd-m3
```

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
