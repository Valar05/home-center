export const BELLY_PHASES = ["LOAD", "COMMIT", "HIT", "CONSEQUENCE", "RECOVERY"];

export function textOf(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.join(" · ");
  if (typeof value === "object") {
    return Object.entries(value).map(function (entry) {
      return entry[0] + "=" + textOf(entry[1]);
    }).join(" · ");
  }
  return String(value);
}

export function timingWeight(key) {
  const raw = String(key.timing_class || key.timing || key.expose || "").toUpperCase();
  if (raw === "ONES" || raw === "1" || raw === "1S") return 1;
  if (raw === "TWOS" || raw === "2" || raw === "2S") return 2;
  if (raw === "FOURS" || raw === "4" || raw === "4S") return 4;
  const numeric = Number(key.expose || key.timing);
  if (Number.isFinite(numeric) && numeric > 0) return Math.min(8, numeric);
  return 2;
}

export function contactOf(key) {
  return textOf(
    key.contact_state ??
    key.contact ??
    key.tool_contact ??
    key.relationship_state ??
    key.guard_authority ??
    "NONE"
  );
}

export function supportOf(key) {
  return textOf(
    key.support_contact ??
    key.support ??
    key.support_A ??
    key.root_state ??
    "UNSPECIFIED"
  );
}

export function rootOf(key) {
  const pieces = [];
  if (key.root_owner) pieces.push("root " + textOf(key.root_owner));
  if (key.root_state) pieces.push(textOf(key.root_state));
  if (key.custody) pieces.push("custody " + textOf(key.custody));
  if (key.tool_custody) pieces.push("custody " + textOf(key.tool_custody));
  if (key.force_owner) pieces.push("force " + textOf(key.force_owner));
  if (!pieces.length) pieces.push("not explicitly named");
  return pieces.join(" · ");
}

export function roleOf(key) {
  return textOf(
    key.causal_role ??
    key.role ??
    key.note ??
    key.attitude ??
    key.name ??
    ""
  );
}

export function motionNoteOf(key) {
  return textOf(
    key.motion_arc_root_note ??
    key.arc ??
    key.clearance_note ??
    key.note ??
    key.causal_role ??
    ""
  );
}

export function phaseForKey(key) {
  const hay = [
    key.phase,
    key.name,
    key.causal_role,
    key.role,
    key.note,
    key.contact,
    key.contact_state,
    key.tool_contact,
    key.support_contact
  ].map(textOf).join(" ").toUpperCase();

  if (/PRE.?CONTACT/.test(hay)) return "COMMIT";
  if (/(CONTACT_PIN|CONTACT INSTANT|HIT[-_ ]?STOP|IMPACT INSTANT|COLLISION|STRIKE HIT|TIP_PINNED|TARGET_HOLD)/.test(hay)) return "HIT";
  if (/(FOLLOW|CONSEQUENCE|OVERTRAVEL|OVERSHOOT|RECOIL|WITHDRAW|DISENGAGE|RUNOUT|AFTERMATH|LAG|DEBT)/.test(hay)) return "CONSEQUENCE";
  if (/(RECOVER|RECOVERY|SETTLE|RESTACK|REACQUIRE|EXIT|DISPLACED_READY|READY_COMPLETE|CATCH_COMPRESSION|RETURN)/.test(hay)) return "RECOVERY";
  if (/(COMMIT|LAUNCH|SURGE|DRIVE|WHIP|RELEASE|THRUST|PRECONTACT|AXIS|FLIGHT|TAKEOFF)/.test(hay)) return "COMMIT";
  if (/(LOAD|ANTICIP|COIL|BRACE|CROUCH|WIND|PREP|READ|READY|STORE|DENIED)/.test(hay)) return "LOAD";

  const contact = contactOf(key).toUpperCase();
  if (contact && !/(NONE|FREE|UNSPECIFIED)/.test(contact)) return "HIT";
  return "LOAD";
}

function numericPoint(value) {
  if (Array.isArray(value) && value.length >= 2) {
    const x = Number(value[0]);
    const y = Number(value[1]);
    if (Number.isFinite(x) && Number.isFinite(y)) return {x:x, y:y};
  }
  if (value && typeof value === "object") {
    const x = Number(value.x);
    const y = Number(value.y);
    if (Number.isFinite(x) && Number.isFinite(y)) return {x:x, y:y};
  }
  return null;
}

function pointObject(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return {};
  const out = {};
  Object.entries(candidate).forEach(function (entry) {
    const p = numericPoint(entry[1]);
    if (p) out[entry[0]] = p;
  });
  return out;
}

export function rawPointMap(key) {
  const candidates = [
    key.pose_rig,
    key.joints,
    key.points,
    key.pose,
    key.A,
    key.rig
  ];
  for (const candidate of candidates) {
    const map = pointObject(candidate);
    if (Object.keys(map).length >= 2) return map;
  }
  return {};
}

function firstPoint(map, names) {
  for (const name of names) if (map[name]) return map[name];
  return null;
}

export function canonicalPointMap(key) {
  const raw = rawPointMap(key);
  if (!Object.keys(raw).length) return {};

  const out = Object.assign({}, raw);
  const aliases = {
    root: ["root", "pelvis", "hips", "hip", "center", "body", "torso"],
    head: ["head", "skull"],
    shoulder_l: ["shoulder_l", "left_shoulder", "rear_shoulder"],
    shoulder_r: ["shoulder_r", "right_shoulder", "front_shoulder"],
    hand_l: ["hand_l", "left_hand", "rear_hand", "hand_rear"],
    hand_r: ["hand_r", "right_hand", "front_hand", "hand_front"],
    knee_l: ["knee_l", "left_knee", "rear_knee"],
    knee_r: ["knee_r", "right_knee", "front_knee"],
    foot_l: ["foot_l", "left_foot", "rear_foot", "support_rear"],
    foot_r: ["foot_r", "right_foot", "front_foot", "support_front"],
    tool_rear: ["rear_end", "tool_rear", "butt", "tool_base", "shaft_rear"],
    tool_front: ["front_end", "tool_front", "tip", "tool_tip", "shaft_front"]
  };

  Object.entries(aliases).forEach(function (entry) {
    const p = firstPoint(raw, entry[1]);
    if (p) out[entry[0]] = p;
  });

  if (!out.root && out.knee_l && out.knee_r) {
    out.root = {
      x:(out.knee_l.x + out.knee_r.x) / 2,
      y:Math.min(out.knee_l.y, out.knee_r.y) - 4
    };
  }
  return out;
}

export function asciiOf(key) {
  const direct = [key.ascii, key.pose_rig, key.pose].find(function (value) {
    return typeof value === "string" && value.trim().length;
  });
  if (direct) return direct.replace(/^\n/, "");
  const points = canonicalPointMap(key);
  return Object.keys(points).length ? asciiFromPoints(points, key) : "(No literal ASCII field in this specimen key.)";
}

export function fitPointMap(points, width, height, padding) {
  const entries = Object.entries(points).filter(function (entry) {
    return entry[1] && Number.isFinite(entry[1].x) && Number.isFinite(entry[1].y);
  });
  if (!entries.length) return {};
  const xs = entries.map(function (entry) { return entry[1].x; });
  const ys = entries.map(function (entry) { return entry[1].y; });
  let minX = Math.min.apply(null, xs);
  let maxX = Math.max.apply(null, xs);
  let minY = Math.min.apply(null, ys);
  let maxY = Math.max.apply(null, ys);
  if (maxX - minX < 1) maxX = minX + 1;
  if (maxY - minY < 1) maxY = minY + 1;
  const sx = (width - padding * 2) / (maxX - minX);
  const sy = (height - padding * 2) / (maxY - minY);
  const scale = Math.min(sx, sy);
  const usedW = (maxX - minX) * scale;
  const usedH = (maxY - minY) * scale;
  const ox = (width - usedW) / 2;
  const oy = (height - usedH) / 2;
  const out = {};
  entries.forEach(function (entry) {
    out[entry[0]] = {
      x:ox + (entry[1].x - minX) * scale,
      y:oy + (entry[1].y - minY) * scale
    };
  });
  return out;
}

export function interpolatePointMaps(a, b, t) {
  const out = {};
  const names = new Set(Object.keys(a || {}).concat(Object.keys(b || {})));
  names.forEach(function (name) {
    const pa = a && a[name];
    const pb = b && b[name];
    if (pa && pb) {
      out[name] = {x:pa.x + (pb.x-pa.x)*t, y:pa.y + (pb.y-pa.y)*t};
    } else {
      out[name] = pa || pb;
    }
  });
  return out;
}

export function asciiFromPoints(points, key) {
  const width = 58;
  const height = 21;
  const fitted = fitPointMap(points, width - 2, height - 3, 1);
  const grid = Array.from({length:height}, function () {
    return Array.from({length:width}, function () { return " "; });
  });

  function stamp(name, glyph) {
    const p = fitted[name];
    if (!p) return;
    const x = Math.max(0, Math.min(width-1, Math.round(p.x)));
    const y = Math.max(0, Math.min(height-2, Math.round(p.y)));
    grid[y][x] = glyph;
  }

  stamp("head", "O");
  stamp("root", "+");
  stamp("shoulder_l", "s");
  stamp("shoulder_r", "s");
  stamp("hand_l", "o");
  stamp("hand_r", "o");
  stamp("knee_l", "k");
  stamp("knee_r", "k");
  stamp("foot_l", "=");
  stamp("foot_r", "=");
  stamp("tool_rear", "<");
  stamp("tool_front", ">");

  const support = supportOf(key).toUpperCase();
  const footer = "SUPPORT: " + support.slice(0, width - 9);
  Array.from(footer).forEach(function (ch, i) { if (i < width) grid[height-1][i] = ch; });
  return grid.map(function (row) { return row.join("").replace(/\s+$/,""); }).join("\n");
}

export function normalizeSpecimen(raw, meta) {
  const keys = Array.isArray(raw && raw.keys) ? raw.keys : [];
  const id =
    raw.specimen_id ||
    raw.experiment_id ||
    raw.id ||
    (meta && meta.id) ||
    "unknown-specimen";
  const lane =
    raw.lane ||
    (meta && meta.lane) ||
    inferLane(id);
  const principle =
    raw.principle ||
    raw.lesson ||
    raw.quality_thesis ||
    raw.pocket_rule ||
    raw.concept ||
    "";

  return {
    raw:raw,
    id:id,
    lane:String(lane || "unknown").toLowerCase(),
    title:raw.title || humanize(id),
    principle:typeof principle === "string" ? principle : textOf(principle),
    keys:keys,
    source:raw.source || {},
    quality:raw.quality || raw.quality_gate || raw.quality_gates || {},
    meta:meta || {}
  };
}

export function inferLane(id) {
  const match = String(id || "").match(/v2-([a-z-]+?)-\d+/i);
  return match ? match[1] : "unknown";
}

export function humanize(value) {
  return String(value || "")
    .replace(/^v2-/, "")
    .replace(/-\d+-/, " · ")
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, function (m) { return m.toUpperCase(); });
}

export function lintSpecimen(specimen) {
  const issues = [];
  const keys = specimen.keys || [];
  if (!keys.length) {
    issues.push({severity:"error", code:"NO_KEYS", message:"No decisive keys were found."});
    return issues;
  }

  keys.forEach(function (key, index) {
    if (!key.timing_class && key.timing == null && key.expose == null) {
      issues.push({severity:"warn", code:"TIMING_UNNAMED", key:index, message:"Key " + index + " has no explicit timing class."});
    }
    const role = roleOf(key);
    if (!role) {
      issues.push({severity:"warn", code:"ROLE_UNNAMED", key:index, message:"Key " + index + " has no causal role or note."});
    }
  });

  const phases = keys.map(phaseForKey);
  if (!phases.includes("COMMIT")) {
    issues.push({severity:"warn", code:"COMMIT_UNREADABLE", message:"No key reads clearly as commitment."});
  }
  if (!phases.includes("HIT")) {
    issues.push({severity:"info", code:"NO_HIT", message:"No explicit hit/contact phase detected; valid for non-impact studies."});
  }
  if (!phases.includes("RECOVERY")) {
    issues.push({severity:"warn", code:"RECOVERY_UNREADABLE", message:"No key reads clearly as recovery or displaced return."});
  }

  const firstPoints = canonicalPointMap(keys[0]);
  const lastPoints = canonicalPointMap(keys[keys.length - 1]);
  if (Object.keys(firstPoints).length && Object.keys(lastPoints).length) {
    const shared = Object.keys(firstPoints).filter(function (name) { return lastPoints[name]; });
    if (shared.length >= 4) {
      let delta = 0;
      shared.forEach(function (name) {
        delta += Math.hypot(firstPoints[name].x-lastPoints[name].x, firstPoints[name].y-lastPoints[name].y);
      });
      delta /= shared.length;
      if (delta < 0.2) {
        issues.push({severity:"info", code:"RESET_RISK", message:"First and last geometry are nearly identical; verify that recovery is earned rather than a reset."});
      }
    }
  }

  return issues.slice(0, 8);
}

export function lintScore(issues) {
  let score = 100;
  issues.forEach(function (issue) {
    score -= issue.severity === "error" ? 35 : issue.severity === "warn" ? 12 : 3;
  });
  return Math.max(0, score);
}
