# Venice review — explicit overlay recovery

Verdict: CONTINUE_REQUIRED

The repair preserves the local kill switch: RESTORE surfaces the operator panel but resets control to OFF. It does not add a remote enable capability. Deliberate Hide remains respected by the ordinary Vlad heartbeat; only the explicit recovery lane restores visibility.

The prior implementation could report recovery success while `overlay_hidden=1`. That claim is now rejected by source verification, which requires `overlay_hidden=0` and `control_enabled=0`.

STOP_ALLOWED is not available from source evidence. It requires a fresh primary-phone recovery receipt and human-visible confirmation of the actual Home Center control surface.
