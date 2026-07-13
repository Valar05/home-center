#!/data/data/com.termux/files/usr/bin/sh
set -eu

case "${1:-status}" in
  start|stop|status|attach|logs|list)
    exec sh tools/home_center_scheduler_tmux.sh "$1"
    ;;
  once)
    exec sh tools/home_center_scheduler_tmux.sh once home-drive-profile-refresh
    ;;
  --help|-h|help)
    cat <<USAGE
Usage: sh tools/home_drive_profile_refresh_tmux.sh start|stop|status|attach|logs|once

Compatibility wrapper. The durable scheduler is now generalized:
  sh tools/home_center_scheduler_tmux.sh status
USAGE
    ;;
  *)
    exec sh tools/home_center_scheduler_tmux.sh "$@"
    ;;
esac
