// Refresh every Verdikta job 1..MAX from the public API (anonymous limit ~60 req / 35 s).
import fs from 'fs';
const MAX = +(process.argv[2] || 480);
const out = fs.existsSync('data/jobs.json') ? JSON.parse(fs.readFileSync('data/jobs.json', 'utf8')) : {};
const sleep = ms => new Promise(r => setTimeout(r, ms));
let miss = 0;
for (let id = 1; id <= MAX; id++) {
  for (let t = 0; t < 6; t++) {
    const r = await fetch(`https://bounties.verdikta.org/api/jobs/${id}`).catch(() => null);
    if (r && r.status === 429) { await sleep(8000); continue; }
    if (!r || !r.ok) { miss++; break; }
    const j = await r.json(); out[id] = j.job || j; break;
  }
  await sleep(620);
  if (id % 50 === 0) { fs.writeFileSync('data/jobs.json', JSON.stringify(out)); console.log(new Date().toISOString(), 'id', id, 'have', Object.keys(out).length, 'miss', miss); }
}
fs.writeFileSync('data/jobs.json', JSON.stringify(out));
console.log('DONE have', Object.keys(out).length, 'miss', miss);
