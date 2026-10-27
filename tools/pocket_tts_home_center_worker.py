#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, os, shutil, sys, threading, time, wave
from pathlib import Path
from pocket_tts_render_v2 import CONTRACT_VERSION, VOICE_PROFILE_ID, BUILTIN_VOICE, VENICE_AUDIO_FILTER, PocketTtsEngine, RenderRejected, doctor_wav, normalized_text, sha256_bytes, validate_receipt

DEFAULT_REQUESTS = Path(os.environ.get('HOME_CENTER_POCKET_TTS_REQUESTS', '/storage/emulated/0/Download/HomeCenter/pocket-tts-requests'))
DEFAULT_OUTPUT = Path(os.environ.get('HOME_CENTER_POCKET_TTS_OUTPUT', '/storage/emulated/0/Documents/FortressAudio/HomeCenterPocketTts'))
HEARTBEAT = DEFAULT_OUTPUT / 'worker-heartbeat.json'
CONFIGURED_BACKEND = os.environ.get('HOME_CENTER_POCKET_TTS_BACKEND', 'local').strip().lower()
if CONFIGURED_BACKEND != 'local':
    raise ValueError('HOME_CENTER_POCKET_TTS_BACKEND is local-only')
WORKER_STATE = {'activeBackend': '', 'lastBackendError': '', 'contractVersion': CONTRACT_VERSION, 'voiceProfileId': VOICE_PROFILE_ID, 'voice': BUILTIN_VOICE, 'audioFilter': VENICE_AUDIO_FILTER, 'modelLoaded': False, 'lastAccepted': '', 'lastError': ''}
ENGINE = None

def local_engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = PocketTtsEngine()
    ENGINE.load()
    WORKER_STATE['modelLoaded'] = True
    return ENGINE


def atomic_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def is_android_owned_result(path: Path) -> bool:
    return '/Download/HomeCenter/pocket-tts-results/' in path.as_posix()


def overwrite_file_in_place(source: Path, target: Path) -> None:
    # MediaStore owns the target inode. Replacing it makes Android drop the row,
    # so validated worker output must be copied into the existing slot in place.
    with source.open('rb') as incoming, target.open('wb') as outgoing:
        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
        outgoing.flush()
        os.fsync(outgoing.fileno())


def overwrite_json_in_place(path: Path, value: dict) -> None:
    with path.open('w', encoding='utf-8') as outgoing:
        json.dump(value, outgoing, ensure_ascii=False, indent=2)
        outgoing.write('\n')
        outgoing.flush()
        os.fsync(outgoing.fileno())


def render_section(args: argparse.Namespace) -> int:
    if str(getattr(args, 'contract_version', CONTRACT_VERSION)) != CONTRACT_VERSION: raise ValueError('Pocket TTS request contract is stale')
    if str(getattr(args, 'voice_profile_id', VOICE_PROFILE_ID)) != VOICE_PROFILE_ID: raise ValueError('Pocket TTS request voice profile is stale')
    published_output = Path(args.output).resolve()
    published_output.parent.mkdir(parents=True, exist_ok=True)
    published_receipt = published_output.with_suffix('.json')
    android_owned = is_android_owned_result(published_output)
    output = published_output
    if android_owned:
        stage_dir = DEFAULT_OUTPUT / 'bridge-staging'
        stage_dir.mkdir(parents=True, exist_ok=True)
        output = stage_dir / published_output.name
        output.unlink(missing_ok=True)
        output.with_suffix('.json').unlink(missing_ok=True)
    receipt = output.with_suffix('.json')
    text = base64.b64decode(args.text_base64, validate=True).decode('utf-8')
    digest = sha256_bytes(normalized_text(text).encode('utf-8'))
    if not text.strip():
        raise ValueError('section text is empty')
    if published_output.exists() and published_receipt.exists():
        try:
            prior = validate_receipt(published_output, published_receipt, text=text)
            print(json.dumps({**prior, 'reused': True}), flush=True)
            return 0
        except Exception:
            pass
    backend = str(getattr(args, 'backend', CONFIGURED_BACKEND) or CONFIGURED_BACKEND).strip().lower()
    if backend != 'local':
        raise ValueError('Pocket TTS backend is local-only')
    used_backend = 'local'
    try:
        data = local_engine().render(text, output, args.request_id, backend=used_backend)
        if android_owned:
            data = validate_receipt(output, receipt, text=text)
            data['output'] = str(published_output)
            overwrite_file_in_place(output, published_output)
            overwrite_json_in_place(published_receipt, data)
            data = validate_receipt(published_output, published_receipt, text=text)
        WORKER_STATE.update({'activeBackend': used_backend, 'lastBackendError': '', 'lastAccepted': args.request_id, 'lastError': ''})
        print(json.dumps(data), flush=True)
        return 0
    except Exception as exc:
        WORKER_STATE['lastError'] = str(exc)
        failure = {'status':'failed','accepted':False,'contractVersion':CONTRACT_VERSION,'requestId':args.request_id,'textSha256':digest,'configuredBackend':backend,'voiceProfileId':VOICE_PROFILE_ID,'error':str(exc)}
        if android_owned and published_receipt.exists():
            overwrite_json_in_place(published_receipt, failure)
        else:
            atomic_json(receipt, failure)
        raise
    finally:
        if android_owned:
            output.unlink(missing_ok=True)
            receipt.unlink(missing_ok=True)


def heartbeat_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        # Shared Android storage is indexed by MediaProvider. Replacing a temporary
        # heartbeat file creates duplicate-path rename noise there, so overwrite
        # this disposable liveness record in place.
        HEARTBEAT.write_text(json.dumps({'status':'running','pid':os.getpid(),'updatedAtMs':int(time.time() * 1000),'configuredBackend':CONFIGURED_BACKEND,**WORKER_STATE}) + '\n', encoding='utf-8')
        stop.wait(2.0)


def serve(request_dir: Path) -> int:
    request_dir.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    heartbeat = threading.Thread(target=heartbeat_loop, args=(stop,), name='pocket-tts-heartbeat', daemon=True)
    heartbeat.start()
    print(json.dumps({'status':'ready','requestDir':str(request_dir),'heartbeat':str(HEARTBEAT)}), flush=True)
    try:
        while True:
            handled = False
            for request in sorted(request_dir.glob('*.json')):
                if request.name.endswith(('.done.json', '.failed.json')):
                    continue
                handled = True
                try:
                    payload = json.loads(request.read_text(encoding='utf-8'))
                    args = argparse.Namespace(
                        request_id=str(payload['requestId']),
                        text_base64=str(payload['textBase64']),
                        output=str(payload['output']),
                        backend=CONFIGURED_BACKEND,
                        contract_version=str(payload.get('contractVersion', '')),
                        voice_profile_id=str(payload.get('voiceProfileId', '')),
                    )
                    render_section(args)
                    request.unlink(missing_ok=True)
                except Exception as exc:
                    failed = request.with_name(request.stem + '.failed.json')
                    try:
                        payload = {'status':'failed','request':request.name,'error':str(exc)}
                        atomic_json(failed, payload)
                        request.unlink(missing_ok=True)
                    except Exception:
                        pass
                    print(json.dumps({'status':'failed','request':request.name,'error':str(exc)}), file=sys.stderr, flush=True)
            if not handled:
                time.sleep(0.25)
    finally:
        stop.set()
        heartbeat.join(timeout=3.0)
        HEARTBEAT.unlink(missing_ok=True)


def main() -> int:
    parser=argparse.ArgumentParser(prog='pocket-tts-home-center-worker')
    sub=parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    doctor_parser=sub.add_parser('doctor')
    doctor_parser.add_argument('--wav')
    serve_parser=sub.add_parser('serve')
    serve_parser.add_argument('--request-dir', default=str(DEFAULT_REQUESTS))
    render_parser=sub.add_parser('render-section')
    render_parser.add_argument('--request-id', required=True)
    render_parser.add_argument('--text-base64', required=True)
    render_parser.add_argument('--output', required=True)
    render_parser.add_argument('--backend', choices=('local',), default=CONFIGURED_BACKEND)
    render_parser.add_argument('--contract-version', default=CONTRACT_VERSION)
    render_parser.add_argument('--voice-profile-id', default=VOICE_PROFILE_ID)
    args=parser.parse_args()
    if args.command == 'render-section': return render_section(args)
    if args.command == 'serve': return serve(Path(args.request_dir))
    if args.command == 'doctor':
        pocket_ok=shutil.which('pocket-tts') is not None
        ffmpeg_path=shutil.which(os.environ.get('FFMPEG_PATH', 'ffmpeg'))
        ok=pocket_ok and ffmpeg_path is not None
        data={'status':'ok' if ok else 'missing','pocketTts':pocket_ok,'ffmpeg':bool(ffmpeg_path),'requestDir':str(DEFAULT_REQUESTS),'configuredBackend':CONFIGURED_BACKEND,'contractVersion':CONTRACT_VERSION,'voiceProfileId':VOICE_PROFILE_ID,'voice':BUILTIN_VOICE,'audioFilter':VENICE_AUDIO_FILTER}
        if args.wav:
            data['artifact']=doctor_wav(Path(args.wav))
            if data['artifact']['status'] != 'accepted': data['status']='rejected'
        print(json.dumps(data, sort_keys=True))
        return 0 if data['status']=='ok' else 1
    DEFAULT_REQUESTS.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    print(json.dumps({'status':'ready','requestDir':str(DEFAULT_REQUESTS),'configuredBackend':CONFIGURED_BACKEND,'contractVersion':CONTRACT_VERSION,'voiceProfileId':VOICE_PROFILE_ID,'voice':BUILTIN_VOICE}))
    return 0

if __name__ == '__main__': raise SystemExit(main())
