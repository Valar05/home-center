const {createHash} = require('node:crypto');

const NAME_RE = /^[A-Za-z][A-Za-z0-9_.-]{0,63}$/;
const HASH_RE = /^[a-f0-9]{64}$/;

function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}

function cleanLines(text) {
  return String(text || '')
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .map((raw, index) => ({raw, lineNo: index + 1, text: raw.trim()}))
    .filter((line) => line.text && !line.text.startsWith('#'));
}

function parseName(value, label, lineNo) {
  if (!NAME_RE.test(value || '')) fail('UAPL_NAME', `${label} is invalid at line ${lineNo}`);
  return value;
}

function parseCoord(value, lineNo) {
  if (!/^-?\d+$/.test(value || '')) fail('UAPL_COORD', `coordinate must be an integer at line ${lineNo}`);
  const n = Number(value);
  if (!Number.isSafeInteger(n) || Math.abs(n) > 100000) fail('UAPL_COORD', `coordinate out of range at line ${lineNo}`);
  return n;
}

function parseUapl(text) {
  const lines = cleanLines(text);
  if (!lines.length || lines[0].text !== 'UAPL 1') fail('UAPL_HEADER', 'file must begin with UAPL 1');

  const program = {
    version: 1,
    name: '',
    axes: {x: 'right', y: 'up', z: 'forward'},
    rigName: '',
    joints: [],
    poses: [],
    order: [],
  };

  const jointIds = new Set();
  const poseNames = new Set();
  let currentPose = null;
  let sawEnd = false;

  for (let i = 1; i < lines.length; i += 1) {
    const {text: line, lineNo} = lines[i];
    const parts = line.split(/\s+/);
    const op = parts[0];

    if (sawEnd) fail('UAPL_TRAILING', `content after ENDUAPL at line ${lineNo}`);

    if (currentPose) {
      if (op === 'ENDPOSE') {
        if (parts.length !== 1) fail('UAPL_POSE_END', `ENDPOSE takes no arguments at line ${lineNo}`);
        program.poses.push(currentPose);
        currentPose = null;
        continue;
      }
      if (parts.length !== 4) fail('UAPL_POSE_ROW', `pose row must be: JOINT X Y Z at line ${lineNo}`);
      const joint = parseName(parts[0], 'joint id', lineNo);
      if (!jointIds.has(joint)) fail('UAPL_UNKNOWN_JOINT', `unknown joint ${joint} at line ${lineNo}`);
      if (Object.prototype.hasOwnProperty.call(currentPose.coords, joint)) fail('UAPL_DUP_COORD', `duplicate coordinate for ${joint} at line ${lineNo}`);
      currentPose.coords[joint] = [parseCoord(parts[1], lineNo), parseCoord(parts[2], lineNo), parseCoord(parts[3], lineNo)];
      continue;
    }

    if (op === 'NAME') {
      if (parts.length !== 2 || program.name) fail('UAPL_NAME', `NAME must appear once with one value at line ${lineNo}`);
      program.name = parseName(parts[1], 'program name', lineNo);
      continue;
    }

    if (op === 'AXES') {
      if (parts.length !== 4 || parts[1] !== 'X=right' || parts[2] !== 'Y=up' || parts[3] !== 'Z=forward') {
        fail('UAPL_AXES', `AXES must be exactly: AXES X=right Y=up Z=forward at line ${lineNo}`);
      }
      continue;
    }

    if (op === 'RIG') {
      if (parts.length !== 2 || program.rigName) fail('UAPL_RIG', `RIG must appear once with one value at line ${lineNo}`);
      program.rigName = parseName(parts[1], 'rig name', lineNo);
      continue;
    }

    if (op === 'JOINT') {
      if (parts.length !== 3) fail('UAPL_JOINT', `JOINT must be: JOINT ID PARENT|ROOT at line ${lineNo}`);
      const id = parseName(parts[1], 'joint id', lineNo);
      const parent = parts[2] === 'ROOT' ? 'ROOT' : parseName(parts[2], 'parent id', lineNo);
      if (jointIds.has(id)) fail('UAPL_DUP_JOINT', `duplicate joint ${id} at line ${lineNo}`);
      program.joints.push({id, parent});
      jointIds.add(id);
      continue;
    }

    if (op === 'POSE') {
      if (parts.length !== 2) fail('UAPL_POSE', `POSE must have one name at line ${lineNo}`);
      const name = parseName(parts[1], 'pose name', lineNo);
      if (poseNames.has(name)) fail('UAPL_DUP_POSE', `duplicate pose ${name} at line ${lineNo}`);
      poseNames.add(name);
      currentPose = {name, coords: {}};
      continue;
    }

    if (op === 'ORDER') {
      if (program.order.length || parts.length < 2) fail('UAPL_ORDER', `ORDER must appear once with at least one pose at line ${lineNo}`);
      program.order = parts.slice(1).map((name) => parseName(name, 'pose name', lineNo));
      continue;
    }

    if (op === 'ENDUAPL') {
      if (parts.length !== 1) fail('UAPL_END', `ENDUAPL takes no arguments at line ${lineNo}`);
      sawEnd = true;
      continue;
    }

    fail('UAPL_OPCODE', `unknown opcode ${op} at line ${lineNo}`);
  }

  if (currentPose) fail('UAPL_UNCLOSED_POSE', `pose ${currentPose.name} is missing ENDPOSE`);
  if (!sawEnd) fail('UAPL_END', 'file must end with ENDUAPL');
  if (!program.name || !program.rigName) fail('UAPL_REQUIRED', 'NAME and RIG are required');
  if (!program.joints.length) fail('UAPL_REQUIRED', 'at least one JOINT is required');
  const roots = program.joints.filter((joint) => joint.parent === 'ROOT');
  if (roots.length !== 1) fail('UAPL_ROOT', 'rig must contain exactly one ROOT joint');
  for (const joint of program.joints) {
    if (joint.parent !== 'ROOT' && !jointIds.has(joint.parent)) fail('UAPL_PARENT', `joint ${joint.id} references missing parent ${joint.parent}`);
    if (joint.parent === joint.id) fail('UAPL_PARENT', `joint ${joint.id} cannot parent itself`);
  }

  const parentMap = new Map(program.joints.map((joint) => [joint.id, joint.parent]));
  for (const joint of program.joints) {
    const seen = new Set([joint.id]);
    let cursor = joint.parent;
    while (cursor !== 'ROOT') {
      if (seen.has(cursor)) fail('UAPL_CYCLE', `rig contains a cycle at ${cursor}`);
      seen.add(cursor);
      cursor = parentMap.get(cursor);
      if (!cursor) fail('UAPL_PARENT', `joint chain for ${joint.id} is broken`);
    }
  }

  if (!program.poses.length) fail('UAPL_REQUIRED', 'at least one POSE is required');
  for (const pose of program.poses) {
    const keys = Object.keys(pose.coords);
    if (keys.length !== program.joints.length) fail('UAPL_INCOMPLETE_POSE', `pose ${pose.name} does not define every joint exactly once`);
    for (const joint of program.joints) if (!pose.coords[joint.id]) fail('UAPL_INCOMPLETE_POSE', `pose ${pose.name} is missing ${joint.id}`);
  }

  if (program.order.length !== program.poses.length) fail('UAPL_ORDER', 'ORDER must name every pose exactly once');
  const orderSet = new Set(program.order);
  if (orderSet.size !== program.order.length) fail('UAPL_ORDER', 'ORDER contains duplicates');
  for (const pose of program.poses) if (!orderSet.has(pose.name)) fail('UAPL_ORDER', `ORDER is missing ${pose.name}`);

  const poseMap = new Map(program.poses.map((pose) => [pose.name, pose]));
  program.poses = program.order.map((name) => {
    const pose = poseMap.get(name);
    if (!pose) fail('UAPL_ORDER', `ORDER references unknown pose ${name}`);
    return pose;
  });

  return program;
}

function canonicalUapl(program) {
  const lines = [
    'UAPL 1',
    `NAME ${program.name}`,
    'AXES X=right Y=up Z=forward',
    `RIG ${program.rigName}`,
  ];
  for (const joint of program.joints) lines.push(`JOINT ${joint.id} ${joint.parent}`);
  for (const pose of program.poses) {
    lines.push(`POSE ${pose.name}`);
    for (const joint of program.joints) {
      const [x, y, z] = pose.coords[joint.id];
      lines.push(`${joint.id} ${x} ${y} ${z}`);
    }
    lines.push('ENDPOSE');
  }
  lines.push(`ORDER ${program.order.join(' ')}`);
  lines.push('ENDUAPL');
  return `${lines.join('\n')}\n`;
}

function uaplHash(programOrText) {
  const program = typeof programOrText === 'string' ? parseUapl(programOrText) : programOrText;
  return createHash('sha256').update(canonicalUapl(program), 'utf8').digest('hex');
}

function parseUat(text, programOrText) {
  const program = typeof programOrText === 'string' ? parseUapl(programOrText) : programOrText;
  const expectedSource = uaplHash(program);
  const lines = cleanLines(text);
  if (!lines.length || lines[0].text !== 'UAT 1') fail('UAT_HEADER', 'timing file must begin with UAT 1');
  let source = '';
  let fps = 60;
  let ended = false;
  const steps = [];
  const poseNames = new Set(program.poses.map((pose) => pose.name));

  for (let i = 1; i < lines.length; i += 1) {
    const {text: line, lineNo} = lines[i];
    const parts = line.split(/\s+/);
    if (ended) fail('UAT_TRAILING', `content after ENDUAT at line ${lineNo}`);
    if (parts[0] === 'SOURCE') {
      if (parts.length !== 2 || source || !HASH_RE.test(parts[1])) fail('UAT_SOURCE', `invalid SOURCE at line ${lineNo}`);
      source = parts[1];
    } else if (parts[0] === 'FPS') {
      if (parts.length !== 2 || !/^\d+$/.test(parts[1])) fail('UAT_FPS', `invalid FPS at line ${lineNo}`);
      fps = Number(parts[1]);
      if (!Number.isInteger(fps) || fps < 1 || fps > 240) fail('UAT_FPS', `FPS out of range at line ${lineNo}`);
    } else if (parts[0] === 'STEP') {
      if (parts.length !== 3) fail('UAT_STEP', `STEP must be STEP POSE TICKS at line ${lineNo}`);
      const pose = parseName(parts[1], 'pose name', lineNo);
      if (!poseNames.has(pose)) fail('UAT_STEP', `unknown pose ${pose} at line ${lineNo}`);
      if (!/^\d+$/.test(parts[2])) fail('UAT_STEP', `ticks must be a positive integer at line ${lineNo}`);
      const ticks = Number(parts[2]);
      if (!Number.isInteger(ticks) || ticks < 1 || ticks > 10000) fail('UAT_STEP', `ticks out of range at line ${lineNo}`);
      steps.push({pose, ticks});
    } else if (parts[0] === 'ENDUAT') {
      if (parts.length !== 1) fail('UAT_END', `ENDUAT takes no arguments at line ${lineNo}`);
      ended = true;
    } else {
      fail('UAT_OPCODE', `unknown timing opcode ${parts[0]} at line ${lineNo}`);
    }
  }

  if (!ended || !source || !steps.length) fail('UAT_REQUIRED', 'SOURCE, at least one STEP, and ENDUAT are required');
  if (source !== expectedSource) fail('UAT_SOURCE_MISMATCH', 'timing profile is pinned to a different UAPL source hash');
  return {version: 1, source, fps, steps};
}

function boneSegments(program, pose) {
  const byId = new Map(program.joints.map((joint) => [joint.id, joint]));
  return program.joints
    .filter((joint) => joint.parent !== 'ROOT')
    .map((joint) => ({
      parent: joint.parent,
      child: joint.id,
      a: pose.coords[byId.get(joint.id).parent],
      b: pose.coords[joint.id],
    }));
}

function plotLine(canvas, x0, y0, x1, y1, ch) {
  let x = x0;
  let y = y0;
  const dx = Math.abs(x1 - x0);
  const sx = x0 < x1 ? 1 : -1;
  const dy = -Math.abs(y1 - y0);
  const sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  while (true) {
    if (canvas[y] && canvas[y][x] === ' ') canvas[y][x] = ch;
    if (x === x1 && y === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x += sx; }
    if (e2 <= dx) { err += dx; y += sy; }
  }
}

function contactBounds(program) {
  const xs = [];
  const ys = [];
  for (const pose of program.poses) {
    for (const joint of program.joints) {
      const [x, y] = pose.coords[joint.id];
      xs.push(x * 2);
      ys.push(y);
    }
  }
  return {minX: Math.min(...xs) - 2, maxX: Math.max(...xs) + 2, minY: Math.min(...ys) - 1, maxY: Math.max(...ys) + 1};
}

function renderAsciiPose(program, pose, bounds = contactBounds(program)) {
  const width = bounds.maxX - bounds.minX + 1;
  const height = bounds.maxY - bounds.minY + 1;
  const canvas = Array.from({length: height}, () => Array(width).fill(' '));
  const toCanvas = ([x, y]) => [x * 2 - bounds.minX, bounds.maxY - y];
  const childCount = new Map(program.joints.map((joint) => [joint.id, 0]));
  for (const joint of program.joints) if (joint.parent !== 'ROOT') childCount.set(joint.parent, childCount.get(joint.parent) + 1);

  for (const bone of boneSegments(program, pose)) {
    const [x0, y0] = toCanvas(bone.a);
    const [x1, y1] = toCanvas(bone.b);
    const sx = Math.sign(x1 - x0);
    const sy = Math.sign(y1 - y0);
    const ch = sx === 0 ? '|' : sy === 0 ? '-' : sx === sy ? '\\' : '/';
    plotLine(canvas, x0, y0, x1, y1, ch);
  }

  for (const joint of program.joints) {
    const [x, y] = toCanvas(pose.coords[joint.id]);
    const isRoot = joint.parent === 'ROOT';
    const isLeaf = childCount.get(joint.id) === 0;
    canvas[y][x] = isRoot ? '+' : isLeaf ? '*' : 'o';
  }
  return canvas.map((row) => row.join('').replace(/\s+$/g, '')).join('\n');
}

function renderAsciiContactSheet(programOrText) {
  const program = typeof programOrText === 'string' ? parseUapl(programOrText) : programOrText;
  const bounds = contactBounds(program);
  const rendered = program.poses.map((pose) => renderAsciiPose(program, pose, bounds).split('\n'));
  const labels = program.poses.map((pose, i) => pose.name.padEnd(Math.max(pose.name.length, ...rendered[i].map((line) => line.length)), ' '));
  const widths = rendered.map((rows, i) => Math.max(labels[i].length, ...rows.map((row) => row.length)));
  const height = Math.max(...rendered.map((rows) => rows.length));
  const out = [program.poses.map((pose, i) => pose.name.padEnd(widths[i], ' ')).join('   ').replace(/\s+$/g, '')];
  for (let row = 0; row < height; row += 1) {
    out.push(rendered.map((rows, i) => (rows[row] || '').padEnd(widths[i], ' ')).join('   ').replace(/\s+$/g, ''));
  }
  return `${out.join('\n')}\n`;
}

function toVectorNoodle(programOrText) {
  const program = typeof programOrText === 'string' ? parseUapl(programOrText) : programOrText;
  return {
    schema: 'uapl.vector-noodle.v1',
    sourceSha256: uaplHash(program),
    axes: program.axes,
    rig: {
      name: program.rigName,
      joints: program.joints.map((joint) => ({...joint})),
    },
    poses: program.poses.map((pose) => ({
      name: pose.name,
      joints: program.joints.map((joint) => ({id: joint.id, xyz: [...pose.coords[joint.id]]})),
      bones: boneSegments(program, pose).map((bone) => ({parent: bone.parent, child: bone.child})),
    })),
    order: [...program.order],
  };
}

function expandTiming(uat) {
  const ticks = [];
  for (const step of uat.steps) for (let i = 0; i < step.ticks; i += 1) ticks.push(step.pose);
  return ticks;
}

module.exports = {
  parseUapl,
  canonicalUapl,
  uaplHash,
  parseUat,
  renderAsciiPose,
  renderAsciiContactSheet,
  toVectorNoodle,
  expandTiming,
};
