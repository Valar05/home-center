const motionPaths = [
  "../v2-strikes-025-rear-clearance-gates-commit-step-debt/motion.json",
  "../v2-contact-017-distal-tool-brace-load-path/motion.json",
  "../v2-airborne-017-offaxis-tool-landing-debt/motion.json",
  "../v2-locomotion-011-support-height-catch-drop-repair/motion.json",
  "../v2-defense-008-parry-exit-plant-repair/motion.json",
  "../v2-timing-016-tempo-debt-catchup/motion.json",
  "../v2-video-motion-005-throw-release-force-chain/motion.json",
  "../v2-video-motion-006-loaded-squat-reversal-cost/motion.json",
  "../v2-video-motion-003-shove-it-dual-clock-recapture/motion.json",
  "../v2-video-motion-001-black-pirate-compression-release/motion.json",
  "../v2-video-motion-002-ground-somersault-support-release/motion.json",
  "../v2-contact-024-dual-anchor-couple-moment-release-gate/motion.json",
  "../v2-contact-022-slack-taut-tension-support-gate/motion.json",
  "../v2-contact-018-moving-base-contact-frame/motion.json",
  "../v2-contact-016-stick-slip-traction-hysteresis/motion.json",
  "../v2-contact-015-slack-taut-tension-coupling/motion.json",
  "../v2-contact-014-impulse-without-custody/motion.json",
  "../v2-contact-011-occlusion-anchor-custody-repair/motion.json",
  "../v2-contact-006-custody-latch-load-release/motion.json",
  "../v2-contact-005-locked-pivot-before-release/motion.json",
  "../v2-contact-004-occlusion-anchor-invariants/motion.json",
  "../v2-contact-002-root-clock-custody-fork/motion.json",
  "../v2-contact-001-scoped-sync-grapple/motion.json",
  "../v2-airborne-032-slope-impact-tangential-slide-debt/motion.json",
  "../v2-airborne-026-wall-glance-shear-floor-recovery/motion.json",
  "../v2-airborne-024-pole-plant-vault-chase-recovery/motion.json",
  "../v2-airborne-022-ceiling-tuck-palm-catch-debt/motion.json",
  "../v2-airborne-021-whiff-commit-wrong-foot-recovery/motion.json",
  "../v2-airborne-020-asymmetric-stall-flare-runout/motion.json",
  "../v2-airborne-019-counterspin-hook-catch-recovery/motion.json",
  "../v2-airborne-011-staggered-precontact-catch/motion.json",
  "../v2-airborne-006-facing-survives-air-task/motion.json",
  "../v2-airborne-005-side-support-gates-second-impulse/motion.json",
  "../v2-airborne-004-drag-capture-descent/motion.json",
  "../v2-airborne-003-apex-spacing-window/motion.json",
  "../v2-airborne-002-precontact-landing-window/motion.json",
  "../v2-airborne-001-air-task-rides-root-arc/motion.json",
  "../v2-locomotion-018-riser-catch-momentum-redirect/motion.json",
  "../v2-locomotion-016-load-release-stride-overrun/motion.json",
  "../v2-locomotion-010-cadence-surge-brake-repair/motion.json",
  "../v2-locomotion-009-overhead-support-handoff-repair/motion.json",
  "../v2-locomotion-008-slingshot-catch-handoff-repair/motion.json",
  "../v2-locomotion-007-forward-catch-handoff-repair/motion.json",
  "../v2-locomotion-006-stride-phase-airborne-handoff/motion.json",
  "../v2-locomotion-005-brake-debt-support-cascade/motion.json",
  "../v2-locomotion-004-support-height-handoff/motion.json",
  "../v2-locomotion-003-cadence-phase-continuity/motion.json",
  "../v2-locomotion-002-overhead-support-handoff/motion.json",
  "../v2-locomotion-001-forward-catch-handoff/motion.json",
  "../v2-defense-027-slip-contact-trust-reacquisition/motion.json",
  "../v2-defense-026-moving-base-guard-inertia-rebase/motion.json",
  "../v2-defense-024-glance-line-arc-reentry/motion.json",
  "../v2-defense-019-high-line-duck-heel-roll-recovery/motion.json",
  "../v2-defense-018-guard-custody-handoff-exit/motion.json",
  "../v2-defense-017-overhead-roof-shear-scissor-recovery/motion.json",
  "../v2-defense-016-shield-knee-post-torque-recovery/motion.json",
  "../v2-defense-015-traveling-guard-phase-slip/motion.json",
  "../v2-defense-002-parry-exit-plant/motion.json",
  "../v2-strikes-028-axial-thrust-recovery-reset-repair/motion.json",
  "../v2-strikes-026-yielding-contact-chase-step-debt/motion.json",
  "../v2-strikes-016-recoil-loaded-second-strike-debt/motion.json",
  "../v2-strikes-015-distal-mass-reversal-lag-debt/motion.json",
  "../v2-strikes-014-offhand-countertorque-impact-debt/motion.json",
  "../v2-strikes-010-midshaft-contact-repivot-debt/motion.json",
  "../v2-strikes-009-sliding-staff-bind-reassignment/motion.json",
  "../v2-strikes-008-off-axis-hammer-drop-rebound-debt/motion.json",
  "../v2-strikes-007-rear-clearance-sidestep-thrust/motion.json",
  "../v2-strikes-006-deflected-hook-recovery-reframe/motion.json",
  "../v2-strikes-005-crossed-blade-bind-shear-release/motion.json",
  "../v2-strikes-002-contact-pin-disengage/motion.json",
  "../v2-strikes-001-axial-thrust-recovery/motion.json",
  "../v2-timing-020-support-gate-latency-localization/motion.json",
  "../v2-timing-010-variant-bank-commitment-repair/motion.json",
  "../v2-timing-009-clock-rendezvous-reacquire-repair/motion.json",
  "../v2-timing-008-inertial-join-sparse-rekey-repair/motion.json",
  "../v2-timing-007-shared-profile-stride-repair/motion.json",
  "../v2-timing-006-scoped-freeze-release-repair/motion.json",
  "../v2-timing-005-variant-bank-zero-time/motion.json",
  "../v2-timing-003-inertial-join-sparse-rekey/motion.json",
  "../v2-timing-002-observed-variant-profile-reuse/motion.json",
  "../v2-timing-001-scoped-freeze-release/motion.json"
];

const featured = new Set([
  "v2-strikes-025-rear-clearance-gates-commit-step-debt",
  "v2-contact-017-distal-tool-brace-load-path",
  "v2-airborne-017-offaxis-tool-landing-debt",
  "v2-locomotion-011-support-height-catch-drop-repair",
  "v2-defense-008-parry-exit-plant-repair",
  "v2-timing-016-tempo-debt-catchup"
]);

function idFromPath(path) {
  const parts = path.split("/");
  return parts[parts.length - 2] || path;
}

function laneFromId(id) {
  const match = id.match(/^v2-([a-z-]+?)-\d+/);
  return match ? match[1] : "unknown";
}

function titleFromId(id) {
  return id
    .replace(/^v2-/, "")
    .replace(/-\d+-/, " · ")
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, function (m) { return m.toUpperCase(); });
}

export const SPECIMENS = motionPaths.map(function (path) {
  const id = idFromPath(path);
  return {
    id:id,
    lane:laneFromId(id),
    title:titleFromId(id),
    path:path,
    featured:featured.has(id),
    authority:"EVIDENCE",
    note:featured.has(id)
      ? "Featured cross-section. Visible specimen truth still outranks this index."
      : "Corpus evidence. Not automatically positive taste authority."
  };
});

export const LANES = Array.from(new Set(SPECIMENS.map(function (item) {
  return item.lane;
}))).sort();
