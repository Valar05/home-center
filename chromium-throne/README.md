# Chromium Throne

Chromium Throne is Venice's local, inspectable parallel conversation-and-command room for Home Center. It runs persistent Playwright Chromium contexts, keeps logical conversational nerves separate from tabs, streams peripheral state changes, captures screenshots on demand, and lets Drew speak socially or issue an explicit command without switching personalities or products.

This first slice is runnable but not deployed. Human-submitted conversation is carried into an explicitly selected included-Chat tab through a semantic selector ladder. It does not infer shell work from arbitrary text or bypass provider quotas. A tab is a visible execution surface; Home Center remains the durable policy, receipt, and learning seam.

The interface uses humane fleshpunk metaphor: threads are nerves, status is pulse, screenshots are remembered views, pause is rest, and close is release. Metaphor must clarify care and agency; it must never obscure cost, blockers, consent, or evidence.

## Run

```sh
cd chromium-throne
npm install
npx playwright install chromium
npm test
npm start
```

Open `http://127.0.0.1:4777`. Set `CHROMIUM_THRONE_HEADLESS=false` for visible windows. Headless contexts still use the full page/UI surface and can be screenshotted.

## Create a thread

```sh
curl -X POST http://127.0.0.1:4777/api/threads \
  -H 'content-type: application/json' \
  -d '{"threadId":"thread:primary","title":"Primary Chat","url":"https://chatgpt.com/","owner":"CHAT_MCP_SUPERVISOR","tasteOwner":"Venice","costClass":"INCLUDED_CHAT","pluginIds":["thread-observatory"]}'
```

Credit-bearing cost classes require `explicitCostAuthority: true`. The server binds to loopback by default. Authentication and a Home Center durable-event adapter are required before non-loopback exposure.

## Venice design authority

`plugins/manifest.json` marks all visual design provisional until Venice accepts it. UI and API are generated from the same plugin identities. Adam may implement behavior and accessibility; Adam may not silently become the taste authority.
