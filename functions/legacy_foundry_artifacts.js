'use strict';

const {Storage} = require('@google-cloud/storage');
const {createHash} = require('node:crypto');
const LEGACY_PUBLICATIONS = 'foundryArtifactPromotions';
let client = null;
function storage() { if (!client) client = new Storage(); return client; }
function text(value, max = 600) { const clean = typeof value === 'string' ? value.trim() : ''; return clean.slice(0, max); }
function filename(value) { return text(value, 240).replace(/\\/g, '/').split('/').pop().replace(/[^A-Za-z0-9._-]/g, '-'); }
function installLegacyFoundryArtifactRoutes(app, {admin}) {
  app.get('/foundry/artifacts/:publicationId/:name', async (req, res) => {
    try {
      const publicationId = text(req.params.publicationId, 80), name = filename(req.params.name);
      if (!/^[a-f0-9]{40}$/.test(publicationId) || !name) return res.status(404).json({error: 'legacy_artifact.not_found'});
      const snapshot = await admin.firestore().collection(LEGACY_PUBLICATIONS).doc(publicationId).get();
      if (!snapshot.exists) return res.status(404).json({error: 'legacy_artifact.not_found'});
      const artifact = (snapshot.data() || {}).artifacts?.[name];
      if (!artifact || artifact.name !== name) return res.status(404).json({error: 'legacy_artifact.not_found'});
      res.set('Access-Control-Allow-Origin', '*'); res.set('Cache-Control', 'public, max-age=31536000, immutable'); res.set('Content-Type', artifact.mediaType); res.set('Content-Length', String(artifact.byteLength)); res.set('ETag', '"' + artifact.sha256 + '"'); res.set('X-Content-Type-Options', 'nosniff'); res.set('X-Home-Center-Capability', 'retired-historical-artifact-only');
      const hash = createHash('sha256'), stream = storage().bucket(artifact.bucket).file(artifact.objectName).createReadStream();
      stream.on('data', (chunk) => hash.update(chunk)); stream.on('end', () => { if (hash.digest('hex') !== artifact.sha256 && !res.headersSent) res.status(502).end(); }); stream.on('error', (error) => { if (!res.headersSent) res.status(502).json({error: 'legacy_artifact.read_failed', message: text(error.message)}); else res.destroy(error); }).pipe(res);
    } catch (error) { res.status(500).json({error: 'legacy_artifact.failed', message: text(error.message)}); }
  });
}
module.exports = {installLegacyFoundryArtifactRoutes};
