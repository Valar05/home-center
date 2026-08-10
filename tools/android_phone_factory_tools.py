#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import hashlib, json, os, shutil, struct, time
from pathlib import Path

HOME = Path.home().resolve()
DOWNLOADS = Path(os.path.expanduser(os.getenv('HC_PHONE_DOWNLOADS', '~/storage/downloads'))).resolve()
WORKSPACE = Path(os.path.expanduser(os.getenv('HC_PHONE_WORKSPACE', '~/workspace/home-center'))).resolve()
ARMORY = Path(os.path.expanduser(os.getenv('HC_PHONE_ARMORY', str(WORKSPACE / 'artifacts/fleshpunk-armory')))).resolve()
ALLOWED_ROOTS = (DOWNLOADS, WORKSPACE, ARMORY)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_path(value: str, *, must_exist: bool = False) -> Path:
    raw = str(value or '').strip()
    if not raw:
        raise ValueError('path is required')
    aliases = {
        'downloads:': DOWNLOADS,
        'workspace:': WORKSPACE,
        'armory:': ARMORY,
    }
    p = None
    for prefix, root in aliases.items():
        if raw.lower().startswith(prefix):
            rel = raw[len(prefix):].lstrip('/\\')
            p = (root / rel).resolve()
            break
    if p is None:
        candidate = Path(os.path.expanduser(raw))
        p = (candidate if candidate.is_absolute() else WORKSPACE / candidate).resolve()
    if not any(_inside(p, root) or p == root for root in ALLOWED_ROOTS):
        raise PermissionError(f'path outside allowed phone roots: {p}')
    if must_exist and not p.exists():
        raise FileNotFoundError(str(p))
    return p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def file_info(path: Path) -> dict:
    st = path.stat()
    out = {
        'path': str(path),
        'name': path.name,
        'isFile': path.is_file(),
        'isDir': path.is_dir(),
        'bytes': st.st_size,
        'mtimeMs': int(st.st_mtime * 1000),
    }
    if path.is_file():
        out['sha256'] = sha256_file(path)
    return out


def list_dir(path: Path, limit: int = 200) -> dict:
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    items = []
    for child in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:max(1, min(limit, 1000))]:
        st = child.stat()
        items.append({'name': child.name, 'path': str(child), 'isFile': child.is_file(), 'isDir': child.is_dir(), 'bytes': st.st_size})
    return {'path': str(path), 'items': items, 'count': len(items)}


def mkdir(path: Path) -> dict:
    path.mkdir(parents=True, exist_ok=True)
    return {'ok': True, 'path': str(path)}


def verified_copy(src: Path, dst: Path, *, move: bool = False, overwrite: bool = False) -> dict:
    if not src.is_file():
        raise FileNotFoundError(str(src))
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not overwrite:
        raise FileExistsError(str(dst))
    before = file_info(src)
    tmp = dst.with_name(dst.name + '.partial')
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(src, tmp)
    after_tmp = file_info(tmp)
    if before['bytes'] != after_tmp['bytes'] or before['sha256'] != after_tmp['sha256']:
        tmp.unlink(missing_ok=True)
        raise RuntimeError('copy verification failed')
    if dst.exists():
        dst.unlink()
    os.replace(tmp, dst)
    after = file_info(dst)
    if move:
        src.unlink()
    return {'ok': True, 'operation': 'move' if move else 'copy', 'source': before, 'destination': after, 'sourceRemoved': move}


def read_glb_json(path: Path) -> dict:
    with path.open('rb') as f:
        header = f.read(12)
        if len(header) != 12:
            raise ValueError('not a GLB: short header')
        magic, version, total = struct.unpack('<4sII', header)
        if magic != b'glTF' or version != 2:
            raise ValueError('not a GLB v2')
        if total != path.stat().st_size:
            raise ValueError(f'GLB length mismatch header={total} file={path.stat().st_size}')
        while f.tell() < total:
            chunk_header = f.read(8)
            if len(chunk_header) != 8:
                break
            length, kind = struct.unpack('<I4s', chunk_header)
            data = f.read(length)
            if kind == b'JSON':
                return json.loads(data.decode('utf-8').rstrip(' \t\r\n\x00'))
    raise ValueError('GLB JSON chunk missing')


def glb_inventory(path: Path) -> dict:
    doc = read_glb_json(path)
    accessors = doc.get('accessors') or []
    meshes = doc.get('meshes') or []
    nodes = doc.get('nodes') or []
    materials = doc.get('materials') or []
    mesh_rows = []
    primitive_count = 0
    for mi, mesh in enumerate(meshes):
        prims = []
        for pi, prim in enumerate(mesh.get('primitives') or []):
            primitive_count += 1
            attrs = prim.get('attributes') or {}
            pos_i = attrs.get('POSITION')
            idx_i = prim.get('indices')
            pos = accessors[pos_i] if isinstance(pos_i, int) and pos_i < len(accessors) else {}
            idx = accessors[idx_i] if isinstance(idx_i, int) and idx_i < len(accessors) else {}
            mode = int(prim.get('mode', 4))
            index_count = int(idx.get('count', 0) or 0)
            vertex_count = int(pos.get('count', 0) or 0)
            triangle_count = index_count // 3 if mode == 4 and index_count else 0
            prims.append({
                'primitiveIndex': pi,
                'material': prim.get('material'),
                'mode': mode,
                'vertexCount': vertex_count,
                'indexCount': index_count,
                'triangleCount': triangle_count,
                'attributes': sorted(attrs.keys()),
                'positionMin': pos.get('min'),
                'positionMax': pos.get('max'),
            })
        mesh_rows.append({'meshIndex': mi, 'name': mesh.get('name') or f'mesh_{mi:03d}', 'primitiveCount': len(prims), 'primitives': prims})
    node_rows = []
    for ni, node in enumerate(nodes):
        node_rows.append({
            'nodeIndex': ni,
            'name': node.get('name') or f'node_{ni:03d}',
            'mesh': node.get('mesh'),
            'children': node.get('children') or [],
            'translation': node.get('translation'),
            'rotation': node.get('rotation'),
            'scale': node.get('scale'),
            'matrix': node.get('matrix'),
        })
    material_rows = []
    for mi, mat in enumerate(materials):
        pbr = mat.get('pbrMetallicRoughness') or {}
        material_rows.append({
            'materialIndex': mi,
            'name': mat.get('name') or f'material_{mi:03d}',
            'baseColorTexture': (pbr.get('baseColorTexture') or {}).get('index'),
            'metallicRoughnessTexture': (pbr.get('metallicRoughnessTexture') or {}).get('index'),
            'normalTexture': (mat.get('normalTexture') or {}).get('index'),
            'emissiveTexture': (mat.get('emissiveTexture') or {}).get('index'),
            'occlusionTexture': (mat.get('occlusionTexture') or {}).get('index'),
        })
    return {
        'schemaVersion': 'fleshpunk-armory.glb-inventory.v1',
        'source': file_info(path),
        'asset': doc.get('asset') or {},
        'scene': doc.get('scene'),
        'sceneCount': len(doc.get('scenes') or []),
        'nodeCount': len(nodes),
        'meshCount': len(meshes),
        'primitiveCount': primitive_count,
        'materialCount': len(materials),
        'textureCount': len(doc.get('textures') or []),
        'imageCount': len(doc.get('images') or []),
        'meshes': mesh_rows,
        'nodes': node_rows,
        'materials': material_rows,
    }


def armory_ingest(source: Path, specimen: str, canonical_name: str = 'source.glb') -> dict:
    clean = ''.join(c for c in specimen if c.isalnum() or c in '-_').strip('-_')
    if not clean:
        raise ValueError('specimen is required')
    root = (ARMORY / clean).resolve()
    if not _inside(root, ARMORY):
        raise PermissionError('invalid specimen path')
    root.mkdir(parents=True, exist_ok=True)
    dest = root / canonical_name
    moved = verified_copy(source, dest, move=True, overwrite=False)
    inventory = glb_inventory(dest)
    inventory_path = root / 'source_inventory.json'
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + '\n')
    manifest = {
        'schemaVersion': 'fleshpunk-armory.specimen.v1',
        'specimen': clean,
        'canonicalSource': file_info(dest),
        'intake': moved,
        'inventoryPath': str(inventory_path),
        'recordedAtMs': int(time.time() * 1000),
    }
    manifest_path = root / 'source_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    return {**manifest, 'manifestPath': str(manifest_path), 'inventory': {k: inventory[k] for k in ('nodeCount','meshCount','primitiveCount','materialCount','textureCount','imageCount')}}


def execute(action: dict) -> dict:
    kind = str(action.get('action') or '')
    if kind == 'file_stat':
        return file_info(resolve_path(action.get('path'), must_exist=True))
    if kind == 'file_hash':
        p = resolve_path(action.get('path'), must_exist=True)
        return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
    if kind == 'file_list':
        return list_dir(resolve_path(action.get('path') or 'workspace:', must_exist=True), int(action.get('limit', 200)))
    if kind == 'file_mkdir':
        return mkdir(resolve_path(action.get('path')))
    if kind in {'file_copy','file_move'}:
        src = resolve_path(action.get('source'), must_exist=True)
        dst = resolve_path(action.get('destination'))
        return verified_copy(src, dst, move=(kind == 'file_move'), overwrite=bool(action.get('overwrite', False)))
    if kind == 'armory_inventory':
        p = resolve_path(action.get('path'), must_exist=True)
        inv = glb_inventory(p)
        out_path = action.get('outputPath')
        if out_path:
            out = resolve_path(out_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + '\n')
            inv['inventoryPath'] = str(out)
        return inv
    if kind == 'armory_ingest':
        return armory_ingest(resolve_path(action.get('source'), must_exist=True), str(action.get('specimen') or ''), str(action.get('canonicalName') or 'source.glb'))
    raise ValueError(f'unsupported deterministic phone factory action: {kind}')


if __name__ == '__main__':
    import sys
    payload = json.loads(sys.stdin.read() or '{}')
    print(json.dumps(execute(payload), ensure_ascii=False))
