# Home Center Scheduler

Home Center scheduled maintenance runs through one durable Termux/tmux scheduler instead of one-off loops. Jobs are configured in `tools/home_center_scheduler_jobs.json` and executed by `tools/home_center_scheduler.py`.

## Commands

Start the durable tmux loop:

```sh
sh tools/home_center_scheduler_tmux.sh start
```

Check status:

```sh
sh tools/home_center_scheduler_tmux.sh status
```

Run all jobs once:

```sh
sh tools/home_center_scheduler_tmux.sh once
```

Run one job once:

```sh
sh tools/home_center_scheduler_tmux.sh once home-drive-profile-refresh
sh tools/home_center_scheduler_tmux.sh once shizuku-readiness
sh tools/home_center_scheduler_tmux.sh once backend-automation-introspect
```

Attach, tail logs, or stop:

```sh
sh tools/home_center_scheduler_tmux.sh attach
sh tools/home_center_scheduler_tmux.sh logs
sh tools/home_center_scheduler_tmux.sh stop
```

## Built-In Jobs

- `home-drive-profile-refresh`: refreshes durable Home Drive character voice profiles from exported Drive docs.
- `shizuku-readiness`: writes a non-mutating Shizuku/rish readiness report for Android automation access.
- `backend-automation-introspect`: writes a backend automation report from Command Center and Home Center source.

## Outputs

- Scheduler state: `generated/home_center_scheduler/state.json`
- Scheduler logs: `generated/home_center_scheduler/logs/*.log`
- Shizuku readiness: `generated/shizuku_setup/home_center_shizuku_readiness.json`
- Backend automation introspection: `generated/backend_automation/introspection.json`

Jobs may declare `requiresShizuku: true`; the scheduler then runs the Shizuku readiness probe first and skips the job if Termux is not authorized through rish. The built-in readiness job is non-mutating and safe to run periodically.
