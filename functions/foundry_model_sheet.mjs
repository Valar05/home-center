import {createHash} from 'node:crypto';
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


function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}

export function subdivisionCageDigest(cage) {
  const identity = {
    contractVersion: cage.contractVersion,
    base: cage.base,
    segments: cage.segments,
    size: cage.size,
    symmetry: cage.symmetry || null,
    ids: cage.ids,
    positions: cage.positions,
    faces: cage.faces,
    edges: cage.edges,
  };
  return createHash('sha256').update(JSON.stringify(stable(identity))).digest('hex');
}

function dot3(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function projectPoint(point, view) {
  const relative = point.map((value, index) => value - view.originWorld[index]);
  return [
    view.originPx[0] + dot3(relative, view.camera.horizontal) * view.pixelsPerMeter,
    view.originPx[1] - dot3(relative, view.camera.up) * view.pixelsPerMeter,
  ];
}

function convexHull(points) {
  const unique = [...new Map(points.map((point) => [point[0].toFixed(7) + ':' + point[1].toFixed(7), point])).values()]
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (unique.length < 3) return unique;
  const cross = (origin, a, b) => (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0]);
  const lower = [], upper = [];
  for (const point of unique) {
    while (lower.length >= 2 && cross(lower.at(-2), lower.at(-1), point) <= 0) lower.pop();
    lower.push(point);
  }
  for (let index = unique.length - 1; index >= 0; index--) {
    const point = unique[index];
    while (upper.length >= 2 && cross(upper.at(-2), upper.at(-1), point) <= 0) upper.pop();
    upper.push(point);
  }
  lower.pop();
  upper.pop();
  return lower.concat(upper);
}

function samplePolygon(points, spacingPx = 4) {
  const samples = [];
  for (let index = 0; index < points.length; index++) {
    const a = points[index], b = points[(index + 1) % points.length];
    const count = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / spacingPx));
    for (let step = 0; step < count; step++) samples.push([a[0] + (b[0] - a[0]) * step / count, a[1] + (b[1] - a[1]) * step / count]);
  }
  return samples;
}

function pointSegmentDistance(point, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], denominator = dx * dx + dy * dy;
  const amount = denominator ? Math.max(0, Math.min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / denominator)) : 0;
  return Math.hypot(point[0] - (a[0] + dx * amount), point[1] - (a[1] + dy * amount));
}

function nearestBoundaryDistance(point, polygon) {
  let best = Infinity;
  for (let index = 0; index < polygon.length; index++) best = Math.min(best, pointSegmentDistance(point, polygon[index], polygon[(index + 1) % polygon.length]));
  return best;
}

function percentile(values, fraction) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * fraction))] || 0;
}

function registeredBoundaryMetrics(cage, modelSheet, viewNames, levels) {
  const surface = subdivideCage(cage, levels);
  const views = {};
  let objective = 0;
  for (const viewName of viewNames) {
    const view = modelSheet.views[viewName];
    const target = view.contourPx;
    const projectedHull = convexHull(surface.positions.map((point) => projectPoint(point, view)));
    if (projectedHull.length < 3) throw fail('foundry.cage.fit_projection_failed', 'Subdivision cage did not project to a valid silhouette.', {view: viewName});
    const targetSamples = samplePolygon(target), surfaceSamples = samplePolygon(projectedHull);
    const targetErrors = targetSamples.map((point) => nearestBoundaryDistance(point, projectedHull));
    const surfaceErrors = surfaceSamples.map((point) => nearestBoundaryDistance(point, target));
    const p95BoundaryErrorPx = percentile(targetErrors, 0.95);
    const reverseP95BoundaryErrorPx = percentile(surfaceErrors, 0.95);
    const maxBoundaryErrorPx = Math.max(0, ...targetErrors, ...surfaceErrors);
    const ringPixels = modelSheet.scaleAnchor.meters * view.pixelsPerMeter;
    const p95BoundaryErrorRingFraction = p95BoundaryErrorPx / ringPixels;
    const reverseP95BoundaryErrorRingFraction = reverseP95BoundaryErrorPx / ringPixels;
    const maxBoundaryErrorRingFraction = maxBoundaryErrorPx / ringPixels;
    const score = p95BoundaryErrorRingFraction + reverseP95BoundaryErrorRingFraction + 0.12 * maxBoundaryErrorRingFraction;
    objective += score;
    views[viewName] = {p95BoundaryErrorPx, reverseP95BoundaryErrorPx, maxBoundaryErrorPx, ringPixels, p95BoundaryErrorRingFraction, reverseP95BoundaryErrorRingFraction, maxBoundaryErrorRingFraction, score};
  }
  return {objective, views};
}

function cloneCage(cage) {
  return {
    ...cage,
    segments: [...cage.segments],
    size: [...cage.size],
    symmetry: cage.symmetry ? {...cage.symmetry} : null,
    positions: cage.positions.map((point) => [...point]),
    ids: [...cage.ids],
    faces: cage.faces.map((face) => [...face]),
    edges: cage.edges.map((edge) => [...edge]),
  };
}

export function fitSubdivisionCageToModelSheet(cageValue, modelSheet, specValue = {}) {
  const spec = options(specValue);
  const viewNames = Array.isArray(spec.views) ? [...new Set(spec.views.map(String))] : [];
  if (viewNames.length < 2 || !viewNames.includes('front') || !viewNames.includes('side') || viewNames.some((name) => !modelSheet?.views?.[name])) {
    throw fail('foundry.cage.fit_views_required', 'Subdivision-cage fitting requires calibrated front and side model-sheet views.', {views: viewNames});
  }
  const levels = Math.floor(Number(spec.levels ?? 2));
  if (levels < 1 || levels > 3) throw fail('foundry.cage.invalid_levels', 'Catmull-Clark levels must be from 1 to 3.', {levels});
  const cage = cloneCage(cageValue);
  const initialDigest = subdivisionCageDigest(cage);
  const initialPositions = cage.positions.map((point) => [...point]);
  let best = registeredBoundaryMetrics(cage, modelSheet, viewNames, levels);
  const initial = JSON.parse(JSON.stringify(best));
  const stepFractions = [0.08, 0.04, 0.02, 0.01, 0.005];
  const maxEvaluations = Math.max(100, Math.min(4096, Math.floor(Number(spec.maxEvaluations) || 4096)));
  const relevantAxes = [0, 1, 2].filter((axis) => viewNames.some((viewName) => {
    const view = modelSheet.views[viewName];
    return Math.abs(view.camera.horizontal[axis]) > 0.001 || Math.abs(view.camera.up[axis]) > 0.001;
  }));
  let evaluations = 1;
  outer: for (const fraction of stepFractions) {
    const step = modelSheet.scaleAnchor.meters * fraction;
    for (let sweep = 0; sweep < 2; sweep++) {
      let changed = false;
      for (let pointIndex = 0; pointIndex < cage.positions.length; pointIndex++) {
        for (const axis of relevantAxes) {
          const original = cage.positions[pointIndex][axis];
          let accepted = original, acceptedMetrics = best;
          for (const direction of [-1, 1]) {
            if (evaluations >= maxEvaluations) break outer;
            const candidate = original + direction * step;
            const limit = modelSheet.scaleAnchor.meters * 0.55;
            if (Math.abs(candidate - initialPositions[pointIndex][axis]) > limit) continue;
            cage.positions[pointIndex][axis] = Math.round(candidate * 1e9) / 1e9;
            const metrics = registeredBoundaryMetrics(cage, modelSheet, viewNames, levels);
            evaluations += 1;
            if (metrics.objective + 1e-10 < acceptedMetrics.objective) {
              accepted = cage.positions[pointIndex][axis];
              acceptedMetrics = metrics;
            }
          }
          cage.positions[pointIndex][axis] = accepted;
          if (accepted !== original) {
            best = acceptedMetrics;
            changed = true;
          }
        }
      }
      if (!changed) break;
    }
  }
  const fittedDigest = subdivisionCageDigest(cage);
  cage.fit = {
    contractVersion: 'home-center.foundry-cage-fit.v1',
    solver: 'deterministic-coordinate-descent-v1',
    views: viewNames,
    subdivisionLevels: levels,
    evaluations,
    maxEvaluations,
    stepFractions,
    initialCageSha256: initialDigest,
    fittedCageSha256: fittedDigest,
    initial,
    final: best,
  };
  return cage;
}
