import catmullClark from 'gl-catmull-clark';

const MAX_CAGE_VERTICES = 96;
const MAX_SUBDIVISION_TRIANGLES = 12000;

function fail(code, message, details = {}) {
  const error = new Error(message);
  error.code = code;
  error.status = 400;
  error.details = details;
  return error;
}

function options(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function finiteVector(value, length, fallback, field) {
  const source = Array.isArray(value) ? value : fallback;
  if (!Array.isArray(source) || source.length !== length || source.some((entry) => !Number.isFinite(Number(entry)))) {
    throw fail('foundry.script.invalid_argument', field + ' must contain ' + length + ' finite numbers.', {field});
  }
  return source.map(Number);
}

function edgeKey(a, b) {
  return a < b ? a + ':' + b : b + ':' + a;
}

export function createSubdivisionCage(specValue = {}) {
  const spec = options(specValue);
  if (String(spec.base || 'box') !== 'box') {
    throw fail('foundry.cage.base_unsupported', 'Subdivision cages must be box-derived.');
  }

  const segments = finiteVector(spec.segments, 3, [1, 1, 1], 'segments').map((value) => Math.floor(value));
  if (segments.some((value) => value < 1 || value > 8)) {
    throw fail('foundry.cage.invalid_segments', 'Cage segments must be integers from 1 to 8.', {segments});
  }
  const size = finiteVector(spec.size, 3, [1, 1, 1], 'size');
  if (size.some((value) => value <= 0 || value > 100)) {
    throw fail('foundry.cage.invalid_size', 'Cage size must contain positive values no larger than 100 meters.', {size});
  }

  const [sx, sy, sz] = segments;
  const positions = [];
  const ids = [];
  const indexById = new Map();
  const pointIndex = (i, j, k) => {
    const id = 'x' + i + ':y' + j + ':z' + k;
    if (!indexById.has(id)) {
      const index = positions.length;
      indexById.set(id, index);
      ids.push(id);
      positions.push([
        (i / sx - 0.5) * size[0],
        (j / sy - 0.5) * size[1],
        (k / sz - 0.5) * size[2],
      ]);
    }
    return indexById.get(id);
  };

  const faces = [];
  for (let j = 0; j < sy; j++) for (let k = 0; k < sz; k++) {
    faces.push([pointIndex(0, j, k), pointIndex(0, j, k + 1), pointIndex(0, j + 1, k + 1), pointIndex(0, j + 1, k)]);
    faces.push([pointIndex(sx, j, k), pointIndex(sx, j + 1, k), pointIndex(sx, j + 1, k + 1), pointIndex(sx, j, k + 1)]);
  }
  for (let i = 0; i < sx; i++) for (let k = 0; k < sz; k++) {
    faces.push([pointIndex(i, 0, k), pointIndex(i + 1, 0, k), pointIndex(i + 1, 0, k + 1), pointIndex(i, 0, k + 1)]);
    faces.push([pointIndex(i, sy, k), pointIndex(i, sy, k + 1), pointIndex(i + 1, sy, k + 1), pointIndex(i + 1, sy, k)]);
  }
  for (let i = 0; i < sx; i++) for (let j = 0; j < sy; j++) {
    faces.push([pointIndex(i, j, 0), pointIndex(i, j + 1, 0), pointIndex(i + 1, j + 1, 0), pointIndex(i + 1, j, 0)]);
    faces.push([pointIndex(i, j, sz), pointIndex(i + 1, j, sz), pointIndex(i + 1, j + 1, sz), pointIndex(i, j + 1, sz)]);
  }

  if (positions.length > MAX_CAGE_VERTICES) {
    throw fail('foundry.limit.cage_vertices', 'Subdivision cage exceeds the 96-control-vertex limit.', {
      controlVertexCount: positions.length,
      max: MAX_CAGE_VERTICES,
    });
  }

  const symmetryAxis = spec.symmetry && String(spec.symmetry.axis || '');
  if (symmetryAxis && symmetryAxis !== 'z') {
    throw fail('foundry.cage.symmetry_unsupported', 'Box cage symmetry currently supports only the z axis.');
  }
  const overrides = Array.isArray(spec.controlPoints) ? spec.controlPoints : [];
  if (overrides.length > MAX_CAGE_VERTICES) {
    throw fail('foundry.limit.cage_overrides', 'Subdivision cage has too many control-point overrides.');
  }
  for (const [overrideIndex, entryValue] of overrides.entries()) {
    const entry = options(entryValue);
    const id = typeof entry.id === 'string' ? entry.id.trim() : '';
    const index = indexById.get(id);
    if (index === undefined) {
      throw fail('foundry.cage.unknown_control_point', 'Unknown subdivision-cage control point: ' + id, {id});
    }
    const position = finiteVector(entry.position, 3, null, 'controlPoints[' + overrideIndex + '].position');
    positions[index] = position;
    if (symmetryAxis === 'z' && entry.mirror !== false) {
      const match = /^x(\d+):y(\d+):z(\d+)$/.exec(id);
      if (match) {
        const mirrorId = 'x' + match[1] + ':y' + match[2] + ':z' + (sz - Number(match[3]));
        const mirrorIndex = indexById.get(mirrorId);
        if (mirrorIndex !== undefined && mirrorIndex !== index) {
          positions[mirrorIndex] = [position[0], position[1], -position[2]];
        }
      }
    }
  }

  const edgeSet = new Set();
  for (const face of faces) {
    for (let index = 0; index < face.length; index++) {
      edgeSet.add(edgeKey(face[index], face[(index + 1) % face.length]));
    }
  }
  const edges = Array.from(edgeSet).map((value) => value.split(':').map(Number));
  return {
    contractVersion: 'home-center.foundry-subdivision-cage.v1',
    base: 'box',
    segments,
    size,
    symmetry: symmetryAxis ? {axis: symmetryAxis} : null,
    positions,
    ids,
    faces,
    edges,
  };
}

export function subdivideCage(cage, levelsValue = 2) {
  const levels = Math.floor(Number(levelsValue));
  if (levels < 1 || levels > 3) {
    throw fail('foundry.cage.invalid_levels', 'Catmull-Clark levels must be from 1 to 3.', {levels});
  }
  const result = catmullClark(
    cage.positions.map((point) => [...point]),
    cage.faces.map((face) => [...face]),
    levels,
    true,
  );
  if (!result || !Array.isArray(result.positions) || !Array.isArray(result.cells) || result.cells.some((face) => face.length !== 3)) {
    throw fail('foundry.cage.subdivision_failed', 'Catmull-Clark did not produce a triangle surface.');
  }
  if (result.cells.length > MAX_SUBDIVISION_TRIANGLES) {
    throw fail('foundry.limit.cage_triangles', 'Subdivided cage exceeds its 12,000-triangle safety limit.', {
      triangles: result.cells.length,
      max: MAX_SUBDIVISION_TRIANGLES,
    });
  }
  return {positions: result.positions, faces: result.cells, levels, triangleCount: result.cells.length};
}
