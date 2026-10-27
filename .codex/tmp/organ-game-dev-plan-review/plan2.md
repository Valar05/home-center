Revised bounded repair slice:
1. In the isolated recovered clean-campaign clone only, change tools/ssh_axis.py PROBE from Unix-only printf to cross-platform echo.
2. Add tools/test_ssh_axis.py using standard-library mocking. Prove the invoked remote command is exactly echo FORTRESS_SSH_AXIS_OK, Windows CRLF output promotes to callable, nonzero execution remains command_failed, and authentication failure remains distinct.
3. Run the new regression, the existing Fleshpunk clean-campaign contract, and Python syntax checks.
4. Run the repaired SSH Axis against the observed endpoint dclar@100.68.37.106; require callable and hostname TheCauldron through a separate authenticated read-only command.
5. Invoke only the clean campaign status/doctor surface from the isolated owner. It may copy the accepted PowerShell campaign files but must not bootstrap, download models, generate, stop processes, or touch VeniceImageBridge.
6. If status/doctor shows not deployed, record exact states and stop before expensive bootstrap. If it shows deployed, verify trusted localhost process and hashes without generating.
7. Keep canonical Home Center, Drive organization, Organ, and Diorama unchanged in this repair slice.

Done: probe regression passes; existing campaign contract remains green; live Axis is callable on TheCauldron; clean campaign status is observed through its owner; no quarantine crossing or expensive generation occurs.