try {
  const result = await chrome.runtime.sendMessage({type: 'throne.relay.poll'});
  document.body.textContent = result?.ok ? 'Chromium Throne awake.' : `Chromium Throne wake failed: ${result?.error || 'unknown'}`;
  if (result?.ok) setTimeout(() => window.close(), 350);
} catch (error) {
  document.body.textContent = `Chromium Throne wake failed: ${error.message}`;
}
