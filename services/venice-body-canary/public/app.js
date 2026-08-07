'use strict';

const root = document.getElementById('venice-body');
const caption = document.getElementById('caption');
const status = document.getElementById('status');
const cut = document.getElementById('cut');
const voice = document.getElementById('voice');
let current = {state: 'DORMANT', epoch: 0, sequence: -1, speaking: false};

function stopVoice() {
  voice.pause();
  voice.currentTime = 0;
}

function render(next) {
  const changedSequence = next.sequence !== current.sequence;
  current = next;
  root.className = `is-${next.state.toLowerCase()} expression-${next.expression} gesture-${next.gesture}`;
  caption.textContent = next.state === 'PRESENT' ? next.caption : '';
  status.textContent = `Venice ${next.state.toLowerCase()}; epoch ${next.epoch}; ${next.assets.portraitReady ? 'portrait verified' : 'portrait unavailable'}; ${next.assets.voiceReady ? 'voice verified' : 'voice unavailable'}.`;
  if (next.state !== 'PRESENT' || !next.speaking) {
    stopVoice();
  } else if (changedSequence) {
    stopVoice();
    voice.play().catch(() => { status.textContent += ' Voice playback requires browser permission.'; });
  }
}

async function cutCamera() {
  stopVoice();
  root.className = 'is-cut expression-neutral gesture-still';
  caption.textContent = '';
  await fetch('/cut', {method: 'POST', cache: 'no-store'}).catch(() => {});
}

cut.addEventListener('click', cutCamera);
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') cutCamera();
});
voice.addEventListener('ended', () => {
  fetch('/ended', {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({epoch: current.epoch}),
  }).catch(() => {});
});

const events = new EventSource('/events');
events.onmessage = (event) => render(JSON.parse(event.data));
events.onerror = () => {
  stopVoice();
  root.className = 'is-cut expression-neutral gesture-still';
  caption.textContent = '';
  status.textContent = 'Venice body connection lost; camera cut locally.';
};
