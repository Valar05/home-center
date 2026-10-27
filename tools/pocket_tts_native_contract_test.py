#!/data/data/com.termux/files/usr/bin/python3
from pathlib import Path
import hashlib, json
ROOT=Path(__file__).resolve().parents[1]
asset_dir=ROOT/'app/src/main/assets/pockettts'
manifest=json.loads((asset_dir/'manifest.json').read_text())
assert manifest['schema']=='home-center-pocket-tts-native-assets-v1'
assert manifest['runtimeContract']=='pocket-tts-render-v4-native'
assert manifest['profileId']=='vera-venice-close-mic-v1'
assert manifest['voice']=='vera'
assert manifest['runtimeSource']['commit']=='b669b3c04e09295e629f4cbe6111c8e94202b9d7'
assert manifest['modelSource']['revision']=='66c9d2fb05fc44cc69cb14c15cff9574c4381788'
assert manifest['voiceConversion']['controlSha256']=='f0f15ebfae5aa690ed3a3f25b478198d1892bd3022f39ca738ced07fcaec8e7b'
expected={'pt_flowlm_fused_fp16.tflite','pt_mimi_dec_tx_fp16.tflite','pt_mimi_deconly_fp16.tflite','pt_embed_f16.bin','pt_input_linear_f32.bin','pt_bos_input_f32.bin','pt_neutral_latent_f32.bin','pt_tokenizer.tsv','pt_voice_vera.bin'}
rows={r['name']:r for r in manifest['files']}
assert set(rows)==expected
for name,row in rows.items():
 p=asset_dir/name
 assert p.is_file() and p.stat().st_size==row['bytes'],name
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 assert h.hexdigest()==row['sha256'],name
assert rows['pt_voice_vera.bin']['sha256']=='5d7154ac6cd31f33dc6b63ac9bf0e5401bdfae47c7c89747a786779d4fb0ee15'
print('Pocket TTS native asset contract: OK files=9 bytes='+str(sum(r['bytes'] for r in rows.values())))
