# Episode 01 lab

Extracted from `../0001-script-df-vs-du.md`. If you change a file here, change
the block in the script too. Needs a Linux box with root, systemd, tmux,
logrotate, `watch` (procps) and bash 4.2+.

| Order | File | What it does |
|---|---|---|
| 1 | `lab-panes.sh` | tmux session `ep01`: driver plus four monitor panes. Start it first so the panes fill as you build |
| 2 | `lab-setup.sh` | 128M loop filesystem on `/var/log/demo-app`; stops if the mount did not take |
| 3 | `install.sh` | Installs `demo-hoarder.sh`, `demo-hoarder.service` and `logrotate-demo-app`. Does not start anything |
| 4 | — | On camera: `sudo systemctl start demo-hoarder`. Never `./demo-hoarder.sh` |
| 5 | `logrotate-demo-app.fixed` | Beat 6: `sudo install -m 0644 logrotate-demo-app.fixed /etc/logrotate.d/demo-app` |
| 6 | `teardown.sh` | Removes everything above. Run it between takes, then start again at 2 |

Run the shell scripts with `sudo`. `lab-panes.sh` attaches to the session, so
run it in its own terminal.
