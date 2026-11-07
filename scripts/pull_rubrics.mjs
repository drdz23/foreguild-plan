import fs from 'fs';
const J = JSON.parse(fs.readFileSync('data/jobs.json', 'utf8'));
const seen = new Set(); const tasks = [];
for (const j of Object.values(J)) {
  if (!j.rubricCid || seen.has(j.jobId)) continue; seen.add(j.jobId);
  if (fs.existsSync(`../392/work/rubrics/${j.jobId}.json`) || fs.existsSync(`data/rubrics/${j.jobId}.json`)) continue;
  tasks.push({ id: j.jobId, cid: j.rubricCid });
}
console.log('to fetch', tasks.length);
for (const t of tasks) {
  let ok = false;
  for (const gw of ['https://ipfs.filebase.io/ipfs/', 'https://gateway.pinata.cloud/ipfs/', 'https://ipfs.io/ipfs/']) {
    try { const r = await fetch(gw + t.cid, { signal: AbortSignal.timeout(25000) }); if (!r.ok) continue;
      const j = JSON.parse(await r.text()); fs.writeFileSync(`data/rubrics/${t.id}.json`, JSON.stringify(j)); ok = true; break; } catch (e) {}
  }
  console.log(t.id, ok ? 'ok' : 'FAIL');
}
