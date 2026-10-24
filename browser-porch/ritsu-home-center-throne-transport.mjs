// Inject into Home Center on THECAULDRON only. Never embed this bearer in APK.
// Loopback restriction prevents accidentally disclosing the Throne capability.
export function createLocalThroneTransport({
  baseUrl='http://127.0.0.1:9234/v1/throne',
  capability, fetchImpl=fetch,
}={}) {
  const base=new URL(baseUrl);
  if (base.protocol !== 'http:' || base.hostname !== '127.0.0.1' ||
      base.pathname.replace(/\/$/,'') !== '/v1/throne' || base.search || base.hash)
    throw new Error('throne_transport_must_be_loopback');
  if (typeof capability !== 'string' || capability.length < 32)
    throw new Error('throne_local_bearer_required');
  if (typeof fetchImpl !== 'function') throw new Error('fetch_adapter_required');
  const root=base.origin+'/v1/throne';
  const headers={authorization:'Bearer '+capability};
  async function jsonReply(response) {
    let value=null;
    try { value=await response.json(); } catch {}
    if (!response.ok) throw new Error('throne_http_'+response.status);
    if (!value || typeof value !== 'object') throw new Error('throne_response_invalid');
    return value;
  }
  return Object.freeze({
    async submit(command) {
      const reply=await fetchImpl(root+'/command',{
        method:'POST',headers:{...headers,'content-type':'application/json'},
        body:JSON.stringify(command),
      });
      return jsonReply(reply);
    },
    async readResult(commandId) {
      if (typeof commandId !== 'string' ||
          !/^[A-Za-z0-9_.:-]{6,180}$/.test(commandId))
        throw new Error('invalid_command_identifier');
      const reply=await fetchImpl(root+'/result?commandId='+encodeURIComponent(commandId),{
        method:'GET', headers,
      });
      if (reply.status===404) return null;
      return jsonReply(reply);
    },
  });
}
