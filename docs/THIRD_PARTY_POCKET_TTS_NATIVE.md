# Native Pocket TTS third-party provenance

Home Center embeds an Android LiteRT adaptation of Kyutai Pocket TTS for offline narration.

- Runtime source: `john-rocky/LiteRT-Models`, `pockettts/`, commit `b669b3c04e09295e629f4cbe6111c8e94202b9d7`, MIT license.
- Converted model: `mlboydaisuke/Pocket-TTS-LiteRT`, revision `66c9d2fb05fc44cc69cb14c15cff9574c4381788`, CC-BY-4.0.
- Original model and Vera preset: Kyutai `pocket-tts-without-voice-cloning`, voice `vera` / VCTK `p229_023_enhanced.wav`, CC-BY-4.0.
- Vera conversion uses the upstream `build_pockettts.py` prompt-state packing. A regenerated Alba control matched the published binary byte-for-byte before Vera was exported.

See `app/src/main/assets/pockettts/manifest.json` for exact file hashes and source revisions. The upstream MIT notice follows.

MIT License

Copyright (c) 2026 Daisuke Majima

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
