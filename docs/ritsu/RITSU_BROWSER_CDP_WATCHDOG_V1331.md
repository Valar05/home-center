# Ritsu browser watchdog v1.3.31

Source: Valar05/home-center, campaign/ritsu-local-tailnet-20261024.

A dedicated Chrome profile and launcher live under `%LOCALAPPDATA%\HomeCenter\ChromiumThrone`; CDP binds only to `127.0.0.1:9236`. The owner signs into ChatGPT interactively, once per expired session. Existing personal Chrome profiles are not modified.

The managed task `Ritsu Browser CDP Watchdog Managed` runs at logon and indefinitely every five minutes. The boot trigger runs when interactive Windows conditions permit. The source is installed at `~\.ritsu-control\watchdogs\Ritsu-Browser-Watchdog-v1.3.31.ps1`. The task does not terminate Chrome processes or resend uncertain turns.

The runtime JSON receipt is `~\.ritsu-control\watchdogs\Ritsu-Browser-Watchdog-LAST.json`. A Git commit is source publication only; live CDP, authenticated ChatGPT catalog, Android acceptance and phone audio are independently verified.