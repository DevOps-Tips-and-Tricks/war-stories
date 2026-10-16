# MongoDB volume-full incident — research notes (staging)

The data comes from read-only research on 2026-09-26. No command changed the cluster.
All times are UTC unless stated otherwise.

## The incident, as reported

- A MongoDB pod went into `CrashLoopBackOff` because its volume filled up.
- `df` showed the volume full, but `du` showed it half empty. So a deleted file was still held open by a running process.
- Suspicion: logs from the operator or its agent/sidecar took the space, not mongod itself, and log rotation was involved.
- The date was not known.

## What exists (and what does not)

- **There is no MongoDB Helm release on staging, in any status.**
  - `helm list -A` shows none (Helm 4.2.1, which lists every status by default and no longer accepts `-a`).
  - `--uninstalled --failed --superseded --pending` returned nothing either.
  - So there is no `helm history` and no values diff to reconstruct.
- **Operator:** Deployment `percona-server-mongodb-operator` in namespace `psmdb-operator`.
  - Installed with `kubectl apply` (server-side) on 2025-12-07 08:07.
  - Image `perconalab/percona-server-mongodb-operator:main`.
  - One ReplicaSet, 293 days old, so the pod template has never changed since install.
  - 2 replicas, which had restarted 29 and 31 times in 6 days (last 9 h before the check). Probably unrelated, but worth knowing.
- **Database:** `PerconaServerMongoDB` CR `carbill` in namespace `carbill-mongodb`.
  - `crVersion` 1.21.1. `generation` 8.
  - Replica set `rs0`, 3 members, StatefulSet `carbill-rs0`.
  - Image `perconalab/percona-server-mongodb-operator:main-mongod8.0`.
  - Backup (`pbm-agent`) disabled. `upgradeOptions.apply: disabled`.
- **Storage:** 3 × 22Gi PVCs `mongod-data-carbill-rs0-{0,1,2}`, StorageClass `openebs-lvmsc` (OpenEBS LVM local PV). Created 2025-12-07 and 2025-12-08.
- **Git (shipyard repo):** nothing here manages PSMDB or `carbill-mongodb`. No manifests exist for either.
  - The Mongo-related commits only change application connection strings or images: 2025-06-01, 2025-10-18, 2025-12-03, 2026-01-08.
  - None touch the operator, logging or log rotation.
- **Events:** none left in `carbill-mongodb`. They expired.
- **Prometheus** (`prometheus.kian.group`): no series for `carbill-mongodb`, so it does not scrape staging. Retention is 5 weeks anyway.

## Timeline

This is rebuilt from `managedFields`, CR conditions and file timestamps. Note that `managedFields` keeps only the **last** write time per writer, not a full history.

| When (UTC) | What | Source |
|---|---|---|
| 2025-12-07 08:07 | Operator installed with `kubectl apply` | Deployment managedFields |
| 2025-12-07 12:24 | `carbill` CR created; `initializing` | CR |
| 2025-12-08 07:15–07:16 | CR last edited with `kubectl` client-side apply. The 3 PVCs were bound and the replica set became `ready`. | CR / PVC managedFields |
| 2025-12-08 08:44 | CR condition `error: ErrorReconcile`, still the latest error condition today | CR status |
| **2026-08-01 09:48–10:10** | **The operator enlarged all 3 PVCs.** kubelet finished the filesystem resize at 09:49 (rs0-0), 09:49 (rs0-1) and 10:10 (rs0-2). | PVC managedFields |
| 2026-08-01 09:52:38 | CR last edited by `node-fetch`, which looks like a GUI client (Lens, Headlamp, Rancher or similar), not CI | CR managedFields |
| 2026-08-01 09:52:39 | StatefulSet `carbill-rs0` recreated. This is how the operator changes volume claim templates. | StatefulSet creationTimestamp |
| 2026-09-24 13:30 | StatefulSet updated and all pods restarted. That hour's `mongod.full.log.5` was 257 MB, against a usual ~100 MB. | managedFields, file sizes |

## Best guess at the incident window: shortly before 2026-08-01 09:48 UTC

- It is the only volume resize on record. Growing the disk is the usual first response to a full volume.
- The size is 22Gi. That odd number suggests a small emergency bump, probably from 20Gi. The old size is **not** confirmed.
- The CR edit came from an interactive GUI tool, not a pipeline, which fits hands-on firefighting.
- This is circumstantial. It dates a *response* to a full disk, not the crash itself.

## The pod: containers, and where each one writes logs

**All three containers mount the same PVC (`mongod-data`) at `/data/db`.** There is no separate log volume, so logs and data compete for the same disk. The only other volumes are two emptyDirs (`bin` → `/opt/percona`, `mongosh` → `/.mongodb`), a ConfigMap (`carbill-rs0-mongod`) and Secrets (keyfile, encryption key, TLS, users). One init container: `mongo-init`.

| Container | Image | Role | Writes to |
|---|---|---|---|
| `mongod` | `perconalab/percona-server-mongodb-operator:main-mongod8.0` | The database. 2 CPU and 10G, requests equal to limits. | `/data/db/logs/mongod.log` |
| `logs` | `perconalab/fluentbit:main-logcollector` | fluent-bit. It tails `mongod.log` and writes it to stdout **and** to a second, full copy. | `/data/db/logs/mongod.full.log` + stdout |
| `logrotate` | `perconalab/fluentbit:main-logcollector` | Runs logrotate from `go-cron` | Rotates `/data/db/logs/*.log`; state in `/data/db/logs/logrotate.status` |

- The CR's custom `configuration` sets `systemLog.path: /var/log/mongodb/mongod.log`.
- That directory does not exist in the container. The operator's entrypoint (`/opt/percona/ps-entry.sh`) overrides the path, so mongod actually logs to `/data/db/logs/mongod.log`.
- The CR also sets `operationProfiling.mode: slowOp` with a 1000 ms threshold, which writes to the same log.
- All images are floating `:main` dev tags. What ran in August may differ from what runs today. The logrotate config inside today's image is dated 2026-01-03.

### logrotate configuration (from the image)

```
/data/db/logs/*.log {
   daily
   minsize 10M
   maxsize 100M
   rotate 10
   missingok
   nocompress
   notifempty
   sharedscripts
   postrotate
       mongosh "mongodb://<REDACTED>" --eval 'db.adminCommand({ logRotate: 1 })'
       find /data/db/logs/ -type f -name 'mongod.log.*' -mtime +7 -delete
       find /data/db/logs/ -type f -name 'mongod.full.log' -mtime +7 -delete
   endscript
}
```

It is started as `go-cron "0 0 * * *" sh -c "logrotate -s /data/db/logs/logrotate.status …"`.

### fluent-bit configuration (from the image)

- Input `tail` on `${LOG_DATA_DIR}/mongod.log`, `read_from_head true`, offsets DB at `/tmp/flb_kube.db`.
- Output 1: `stdout`, JSON lines.
- Output 2: `file` → `${LOG_DATA_DIR}/mongod.full.log`.
- `custom/default.conf` is empty.

## Evidence pointing at log rotation and a log-filled volume

1. **Every log line is stored twice** on the data volume: `mongod.log*` and `mongod.full.log*`. Logs use 1.6–2.5G of the 2.2–3.1G used on each member.
2. **Rotation runs every hour, not daily.**
   - go-cron's first field is seconds, so `"0 0 * * *"` means "minute 0 of every hour".
   - Confirmed by the rotation times (17:59, 16:59, 13:59, 23:59) and by `logrotate.status` (last rotation of `mongod.full.log`: 2026-09-26 18:00).
   - With `maxsize 100M`, any file over 100 MB is rotated at the next hour.
3. **`postrotate` only tells mongod to reopen its log.** It never signals fluent-bit, although fluent-bit's `mongod.full.log` is rotated by the same rule (`sharedscripts`, one glob).
4. **mongod's `logRotate` fails some of the time.**
   - The `logrotate` container's recent output on `rs0-0` shows `MongoServerError: Log rotation failed due to one or more errors` in **2 of 5** runs that reached the postrotate step.
   - It also shows `EACCES: permission denied, mkdir '/home/mysql'` warnings from mongosh. The image reuses a `mysql` user for UID 1001.
   - If mongod keeps writing to a file that logrotate renamed, and that file is later deleted (by `rotate 10`, or by `find … -mtime +7 -delete`), the result is exactly `df` full and `du` half empty.
   - **This is the strongest lead, but still a hypothesis.** It would make **mongod** the holder, not the agent.
5. **The mongod log carries a `Log rotation initiated` line in each rotated file.** On `rs0-0` there are 10 rotated files with one line each; the live `mongod.log` has none. Timestamped names like `mongod.log.2026-09-19T18-00-00` come from mongod's own rename-style rotation. Numbered ones like `mongod.log.1` come from logrotate. Both schemes act on the same file.
6. **A path fluent-bit could hold is possible, but not shown.**
   - Its `tail` input follows the rotated `mongod.log` for a short time.
   - Its `file` output did not show a held handle on `mongod.full.log` at the moment of the scans.
7. **The cleanup rule has a bug.** `find … -name 'mongod.full.log' -mtime +7 -delete` matches the *live* file, not the rotated ones. The rotated `mongod.full.log.N` files are only limited by `rotate 10`, which is up to ~1 GB uncompressed per member.

## Open questions only the operator can answer

- Was the 2026-08-01 resize the fix for this incident? What was the size before (20Gi?)?
- Who edited the CR through the GUI client (`node-fetch`) that day? Was there a chat thread or ticket?
- Did anyone capture `lsof` / `/proc/*/fd` output during the incident, showing which process held the deleted file?
- Which `:main` image digests were running then? Floating tags cannot be tied to a date after the fact.
- Was the incident on staging itself, or a production incident replayed on staging?

## ⚠️ Identifying details to strip before publishing

- **Clusters and contexts:**
  - `itoll-staging`, `staging.itoll`, `itoll-production`, `itoll-eu`;
  - `staging-ai-agent`, `kubernetes-admin@staging.itoll`;
  - the kubeconfig file name `itoll-staging-hakimieh.conf`.
- **IPs:** 192.168.200.241 (staging API server); pod IPs in 10.244.0.0/16.
- **Nodes and volume group:** `staging-k8s-control-plane-01/02/03`, `staging-k8s-worker-01/02/03`; LVM volume group `itoll-vg`.
- **Namespaces and object names:**
  - `carbill-mongodb`, `carbill` (CR), `carbill-rs0`, `psmdb-operator`;
  - Secrets `carbill-mongodb-keyfile`, `carbill-mongodb-encryption-key`, `carbill-ssl`, `carbill-ssl-internal`, `internal-carbill-users`;
  - neighbour namespaces `growthbook`, `itoll-*`, `carbill-*`.
- **PV / PVC IDs:** `pvc-6dc0595a-…`, `pvc-34b2ecbd-…`, `pvc-240028a5-…`.
- **Company, team and product names:** iToll, Carbill, eToll, Kian (`kian.group`).
- **Hostnames and domains:** `prometheus.kian.group`, `toll-test.ir`. `check.percona.com` is a public Percona endpoint and is fine to keep.
- **Images and registries:** `perconalab/*` on Docker Hub (public). No private registry was involved.
- **Other:** git author names in commits; the `keyId` / cluster-time values in the logrotate output.

---

# MongoDB replica set — deleted-but-open file check (staging)

- **Date:** 2026-09-26 (~18:50 UTC)
- **Cluster:** `staging` — context `kubernetes-admin@staging.itoll` (in-pod `exec` needs it; the read-only `staging-ai-agent` account cannot exec)
- **Namespace / CR:** `carbill-mongodb` / `PerconaServerMongoDB carbill`, replica set `rs0`
- **Mode:** read-only. `df`, `du`, `ls`, `cat` and `/proc` reads only. Nothing on the cluster changed.

## Method

Each pod runs three containers: `mongod`, `logs` (fluent-bit) and `logrotate`. They do not share a process namespace, so the scan ran in every container separately. In each container:

1. `df -h /data/db` vs `du -sh /data/db` — a large gap would point to space held by deleted files.
2. `ls -l /proc/*/fd | grep deleted` — lists file descriptors that point to deleted files.
3. Sanity check: the fds of each process were counted, to prove that the scan could read them. An empty result could otherwise just mean "permission denied".

## Results

| Pod | PVC used (`df`) | `du /data/db` | `du /data/db/logs` | Deleted-but-open (mongod / logs / logrotate) |
|---|---|---|---|---|
| `carbill-rs0-0` | 2.4G / 22G (11%) | 2.2G | ~1.6G | none / none / none |
| `carbill-rs0-1` | 2.6G / 22G (12%) | 2.4G | 1.8G | none / none / none |
| `carbill-rs0-2` | 3.3G / 22G (15%) | 3.1G | 2.5G | none / none / none |

The `df`/`du` gap is about 0.2G on every member, which is normal filesystem overhead. This is not the 50% gap from the incident.

Scan visibility (fds visible to the scan / fds on `/data/db/logs`):

| Pod | `mongod` | `fluent-bit` |
|---|---|---|
| `carbill-rs0-0` | 141 / 1 | 75 / 1 |
| `carbill-rs0-1` | 147 / 1 | 75 / 1 |
| `carbill-rs0-2` | 220 / 1 | 75 / 1 |

The `logrotate` container runs only `go-cron` between runs. Its `logrotate` process lives only a few seconds each hour, so this scan cannot catch it.

## Conclusion

- **No member currently holds a deleted file open.** The incident condition is not present today on any of the three members.
- At the moment of the scan, each of `mongod` and `fluent-bit` held exactly one handle under `/data/db/logs`: its current log file.
  - fluent-bit's `mongod.full.log` output did not show as a second held handle at that moment.
  - This is one snapshot. It does not rule out that a handle gets held briefly around rotation.
- Logs make up most of the used space on every member: 1.6–2.5G of 2.2–3.1G, because each log line is stored twice (`mongod.log*` and `mongod.full.log*`).
  - `rs0-2` carries the most at 2.5G.
  - Worth watching, but nowhere near full.

## Limits

- This is a point-in-time check. It cannot say what held the deleted file during the past incident.
- The failures of the `logRotate` postrotate step (`MongoServerError: Log rotation failed…`, seen in 2 of 5 recent runs on `rs0-0`) are still the leading hypothesis for how mongod could end up writing to a deleted file. Catching it in the act would need this scan to run shortly after an hourly rotation that failed.
