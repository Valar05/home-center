// The wire-to-text half of the Ritsu read-only browser-network canary.
// No DOM reads, no HTTP interception, and no conversational data logging.
const MAX_TEXT = 4096;
const MAX_WIRE = 2 * 1024 * 1024;

export class RitsuNetworkSse {
  #decoder = new TextDecoder('utf-8', {fatal: true});
  #buffer = '';
  #wire = 0;
  #candidate = null;
  #messageId = null;
  #done = false;
  #events = 0;
  #unknown = 0;
  #conflict = false;
  #shapes = [];

  push(bytes) {
    if (this.#done) throw Error('sse_data_after_done');
    if (!(bytes instanceof Uint8Array)) throw Error('sse_bytes_required');
    this.#wire += bytes.length;
    if (this.#wire > MAX_WIRE) throw Error('sse_canary_wire_size_exceeded');
    this.#buffer += this.#decoder.decode(bytes, {stream: true});
    this.#drain();
  }
  #drain() {
    // A stateful decoder and framing loop avoid splitting UTF-8 or SSE events.
    this.#buffer = this.#buffer.replace(/\r\n/g, '\n');
    for (;;) {
      const at = this.#buffer.indexOf('\n\n');
      if (at < 0) break;
      const frame = this.#buffer.slice(0, at);
      this.#buffer = this.#buffer.slice(at + 2);
      const data = frame.split('\n').filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).replace(/^ /, '')).join('\n');
      if (!data) continue;
      this.#events++;
      if (data === '[DONE]') {this.#done = true; continue;}
      let payload;
      try {payload = JSON.parse(data);} catch {this.#unknown++; continue;}
      // Only structural metadata, never response data/text or token headers.
      if (this.#shapes.length < 8 && payload && typeof payload === 'object') {
        const safe = v => typeof v === 'string' &&
          /^[A-Za-z0-9_.-]{1,80}$/.test(v) ? v : null;
        this.#shapes.push({
          keys: Object.keys(payload).slice(0, 12).filter(k=>/^[A-Za-z0-9_.-]{1,64}$/.test(k)),
          type: safe(payload.type),
          role: safe(payload.message?.author?.role),
          channel: safe(payload.message?.metadata?.channel),
          contentType: safe(payload.message?.content?.content_type),
        });
      }
      const m = payload?.message;
      // Only assistant-to-user final text snapshots are eligible. No reasoning,
      // tool, system, or invisible messages are exported.
      if (!m || m?.author?.role !== 'assistant' ||
          (m.recipient && m.recipient !== 'all') ||
          m.metadata?.is_visually_hidden_from_conversation === true ||
          ![undefined, null, 'final'].includes(m.metadata?.channel)) continue;
      const parts = m.content?.parts;
      if (!Array.isArray(parts) || !parts.length ||
          !parts.every(p => typeof p === 'string') ||
          !['text', 'markdown'].includes(m.content?.content_type)) continue;
      const text = parts.join('');
      if (!text.trim()) continue;
      if (text.length > MAX_TEXT) throw Error('sse_canary_text_size_exceeded');
      if (typeof m.id !== 'string' || !m.id) {this.#unknown++; continue;}
      if (this.#messageId && this.#messageId !== m.id) {
        // One small canary may not silently merge multiple assistant replies.
        this.#conflict = true; continue;
      }
      this.#messageId = m.id;
      this.#candidate = text; // snapshots revise previous snapshots
    }
  }
  diagnostic() {
    return Object.freeze({
      wireBytes: this.#wire, eventCount: this.#events,
      unparseableEvents: this.#unknown, terminalDone: this.#done,
      textCandidate: Boolean(this.#candidate),
      bufferedChars: this.#buffer.length,
      shapes: this.#shapes.map(s=>({...s})),
    });
  }
  result({marker, requestFinished = false} = {}) {
    if (!requestFinished || !this.#done) throw Error('sse_stream_not_terminal');
    if (this.#conflict) throw Error('sse_multiple_final_messages');
    if (!this.#candidate || !this.#candidate.includes(marker))
      throw Error('sse_no_matching_final_canary_text');
    return Object.freeze({text: this.#candidate, messageId: this.#messageId,
      eventCount: this.#events, unknownEventCount: this.#unknown,
      wireBytes: this.#wire, terminal: true});
  }
}
