#!/usr/bin/env bash
#
# Read-only production diagnostics for Jadawel.
#
# Run on the VPS that hosts the Coolify deployment:
#
#   bash docs/diagnose-production.sh > jadawel-diagnostics.txt 2>&1
#
# Nothing here writes, restarts or changes anything — it only reads container
# state, logs and host metrics. Written to answer one question in particular:
# why does the app reload by itself while somebody is working in it?
#
# The three candidates it distinguishes between:
#   1. Containers dying and being restarted (OOM kill, crash) — the browser
#      loses its connection mid-session and the UI reloads.
#   2. The host running out of memory, so the kernel kills whatever is largest.
#   3. Neither, in which case the reload is client-side and the answer is in
#      the browser console instead.

set -uo pipefail

section() { printf '\n\n===== %s =====\n' "$1"; }

section "Host: memory and swap"
free -h
printf '\nSwap configured: '
swapon --show 2>/dev/null || echo "NONE — the Nuxt build needs >4GB and will be OOM-killed without it"

section "Host: uptime and load"
uptime

section "Host: disk"
df -h / /var/lib/docker 2>/dev/null | sort -u

section "Kernel OOM kills (the smoking gun for self-restarts)"
# An entry naming node/python/gunicorn here means the kernel killed the app.
if command -v journalctl >/dev/null 2>&1; then
  journalctl -k --since "7 days ago" 2>/dev/null |
    grep -iE "out of memory|oom-kill|killed process" | tail -40 ||
    echo "none in the last 7 days"
else
  grep -iE "out of memory|oom-kill|killed process" /var/log/syslog 2>/dev/null |
    tail -40 || echo "no journalctl and no readable syslog"
fi

section "Container restart counts (non-zero = something is dying)"
# RestartCount only resets when the container is recreated, so a high number on
# a container with a recent StartedAt is the clearest signal of a crash loop.
docker ps -a --filter "name=jadawel" --format '{{.Names}}' | while read -r c; do
  docker inspect "$c" --format \
    '{{.Name}} restarts={{.RestartCount}} status={{.State.Status}} oomkilled={{.State.OOMKilled}} exit={{.State.ExitCode}} started={{.State.StartedAt}}'
done

section "Container health"
docker ps -a --filter "name=jadawel" --format '{{.Names}}' | while read -r c; do
  status=$(docker inspect "$c" --format '{{if .State.Health}}{{.State.Health.Status}} failingStreak={{.State.Health.FailingStreak}}{{else}}no healthcheck{{end}}')
  echo "$c: $status"
done

section "Live resource usage"
docker stats --no-stream --format \
  'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' 2>/dev/null |
  grep -E "NAME|jadawel"

section "web-frontend log: crashes and restarts"
# "Listening on" appearing more than once means the Nuxt server restarted.
docker logs --tail 400 "$(docker ps -a --filter 'name=jadawel-web-frontend' --format '{{.Names}}' | head -1)" 2>&1 |
  grep -iE "listening|error|fatal|heap|out of memory|ECONNREFUSED|exit" | tail -40

section "backend log: worker churn and slow requests"
docker logs --tail 400 "$(docker ps -a --filter 'name=jadawel-backend' --format '{{.Names}}' | head -1)" 2>&1 |
  grep -iE "booting worker|worker exiting|worker timeout|WORKER TIMEOUT|error|traceback|sync_templates" | tail -40

section "Is template sync running on every boot?"
# SYNC_TEMPLATES_ON_STARTUP defaults to true and is allowed to run for 30
# minutes. While it runs it saturates Postgres and the whole app feels slow.
docker logs --tail 2000 "$(docker ps -a --filter 'name=jadawel-backend' --format '{{.Names}}' | head -1)" 2>&1 |
  grep -icE "sync_templates|syncing template" |
  xargs -I{} echo "template-sync log lines: {}"

section "Postgres: slowest statements"
DB=$(docker ps --filter "name=jadawel-db" --format '{{.Names}}' | head -1)
docker exec "$DB" psql -U "${DATABASE_USER:-baserow}" -d "${DATABASE_NAME:-baserow}" -c \
  "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;" 2>/dev/null ||
  echo "could not query pg_stat_activity (set DATABASE_USER/DATABASE_NAME if they are not the defaults)"

section "Done"
echo "Send the whole file back. The decisive lines are the OOM section and the"
echo "restart counts: if those are clean, the reload is happening in the browser"
echo "and the next step is the devtools console rather than the server."
