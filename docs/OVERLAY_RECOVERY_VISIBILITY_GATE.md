# Overlay recovery visibility gate

`fortress-campaign overlay` and the notification action labelled `Overlay on` are explicit local recovery actions. They are required to restore a visible Home Center operator panel while leaving remote control disabled.

Acceptance for this recovery operation requires all of:

- package `com.homecenter.operatoroverlay` is installed;
- `SYSTEM_ALERT_WINDOW` is allowed;
- the operator state provider is readable;
- `overlay_hidden=0`;
- `control_enabled=0`;
- the recovery receipt records `visible=true` and `controlEnabled=false`.

A readable provider alone is not proof that the overlay is visible. A hidden overlay must not be reported as successfully recovered.

This gate does not change the meaning of the ordinary local Hide action. Vlad's background health loop must continue to respect deliberate Hide state. Visibility restoration occurs only through the explicit restore/recovery lane.
