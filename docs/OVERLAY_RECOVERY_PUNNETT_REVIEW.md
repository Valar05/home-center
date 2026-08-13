# Punnett review — overlay recovery inheritance

Directive: CONTINUE_REQUIRED

Inheritance ruling: reuse the existing Home Center operator overlay, state provider, RESTORE action, Fortress notification menu, and phone-native recovery organism. Do not breed a second overlay, second state store, or alternate remote-enable path.

The failed phenotype was `provider readable + overlay hidden -> recovery success`. The corrected phenotype is `explicit recovery -> existing RESTORE action -> overlay visible + control disabled -> receipt`.

Falsifier: any recovery receipt that reports success while `overlay_hidden != 0` or `control_enabled != 0` invalidates this trait and requires repair before propagation.
