#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { Worker } from 'node:worker_threads';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WRAPPER = path.join(__dirname, 'chunkbase-worker-wrapper.mjs');

const DEFAULT_RADII = {
  village: 2048,
  dungeon: 1536,
  midgame: 3072,
  anchor: 4096,
};

const DEFAULT_CAPS = {
  villageTaxi: 2500,
  dungeonTaxi: 2200,
  midgameTaxi: 4500,
  anchorTaxi: 6000,
  templeValue: 1.75,
  oceanMonuments: 8,
};

const DEFAULT_WEIGHTS = {
  village: 350,
  skeletonSpawner: 300,
  spiderSpawner: 200,
  witchHut: 220,
  pillagerOutpost: 180,
  desertTemple: 140,
  jungleTemple: 100,
  oceanMonument: 35,
  stronghold: 240,
  mansion: 220,
  extraStronghold: 120,
  extraMansion: 300,
};

const DEFAULT_PENALTIES = {
  missingWitchHut: 180,
  missingPillagerOutpost: 160,
  missingDesertTemple: 100,
  missingJungleTemple: 100,
  outpostTooCloseThreshold: 512,
  outpostTooCloseMax: 250,
  witchHutTooCloseThreshold: 384,
  witchHutTooCloseMax: 120,
};

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) args._.push(a);
    else {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) args[key] = true;
      else args[key] = next, i++;
    }
  }
  return args;
}

function usage() {
  console.log(`Usage:
  # Extract integer seeds from a cubiomes-viewer session file.
  node searches/dappled-forest/scripts/rank_dappled_forest.mjs extract \
    --session searches/dappled-forest/sessions/dappled-forest.session \
    --out searches/dappled-forest/data/analysis-inputs/seeds.json

  # Scan ChunkBase POIs and write enriched + ranked candidates.
  node searches/dappled-forest/scripts/rank_dappled_forest.mjs scan \
    --seeds searches/dappled-forest/data/analysis-inputs/seeds.json \
    --chunkbase-worker /path/to/chunkbase/worker.mjs \
    --out searches/dappled-forest/results/dappled-ranked.json

  # Re-rank a previously enriched JSON without calling ChunkBase again.
  node searches/dappled-forest/scripts/rank_dappled_forest.mjs rerank \
    --input searches/dappled-forest/results/dappled-ranked.json \
    --out searches/dappled-forest/results/dappled-ranked-rerank.json

Notes:
  - The ChunkBase web worker is not vendored here. Provide a local reviewed copy
    with --chunkbase-worker or CHUNKBASE_WORKER.
  - Scoring targets Minecraft Bedrock 26.30/26.31-style ChunkBase data and was
    tuned for the dappled-forest search discussion.
`);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
}

function extractSeeds(sessionPath) {
  const lines = fs.readFileSync(sessionPath, 'utf8').split(/\r?\n/);
  const seeds = [];
  const seen = new Set();
  for (const line of lines) {
    const trimmed = line.trim();
    if (!/^-?\d+$/.test(trimmed)) continue;
    if (trimmed.length < 6) continue;
    if (!seen.has(trimmed)) {
      seen.add(trimmed);
      seeds.push(trimmed);
    }
  }
  return seeds;
}

function eu(a, b) { return Math.hypot(a.x - b.x, a.z - b.z); }
function taxi(a, b) { return Math.abs(a.x - b.x) + Math.abs(a.z - b.z); }
function closeness(taxiDistance, cap) { return Math.max(0, 1 - taxiDistance / cap); }
function decayed(items, cap, max = Infinity) {
  return (items || []).slice(0, max).reduce((sum, item, index) => {
    return sum + (0.5 ** index) * closeness(item.taxi, cap);
  }, 0);
}
function tooClosePenalty(items, threshold, maxPenalty) {
  if (!items?.length) return 0;
  return maxPenalty * Math.max(0, 1 - items[0].taxi / threshold);
}

function box(spawn, radius) {
  const minx = Math.floor((spawn.x - radius) / 16) - 2;
  const minz = Math.floor((spawn.z - radius) / 16) - 2;
  const maxx = Math.ceil((spawn.x + radius) / 16) + 2;
  const maxz = Math.ceil((spawn.z + radius) / 16) + 2;
  return [minx, minz, maxx - minx, maxz - minz];
}

function world(seed) {
  return {
    edition: 'Bedrock',
    javaVersion: 260200,
    bedrockVersion: 263000,
    seed: String(seed),
    config: { flat: false, largeBiomes: false, biomeSize: null },
  };
}

const CONVERT = {
  woodlandMansion: (p) => ({ x: p[0] * 16 + 8, z: p[1] * 16 + 8 }),
  stronghold: (p) => ({ x: p[0] * 16 + 4, z: p[1] * 16 + 4 }),
  oceanMonument: (p) => ({ x: p[0] * 16 + 8, z: p[1] * 16 + 8 }),
  pillagerOutpost: (p) => ({ x: p[0] * 16 + 8, z: p[1] * 16 + 8 }),
  witchHut: (p) => ({ x: p[0] * 16 + 8, z: p[1] * 16 + 8 }),
  desertTemple: (p) => ({ x: p[0] * 16 + 8, z: p[1] * 16 + 8 }),
  jungleTemple: (p) => ({ x: p[0] * 16 + 8, z: p[1] * 16 + 8 }),
  village: (p) => ({ x: p[0] * 16 + 8, z: p[1] * 16 + 8 }),
};

function poiList(raw, type, spawn, radius) {
  return (raw?.[type] || [])
    .map(CONVERT[type])
    .map((p) => ({ ...p, eu: eu(p, spawn), taxi: taxi(p, spawn) }))
    .filter((p) => p.eu <= radius)
    .sort((a, b) => a.taxi - b.taxi);
}

function dungeonList(raw, spawn, radius) {
  const out = [];
  for (const entry of raw || []) {
    for (const d of entry[2] || []) {
      const p = { x: d[0], y: d[1], z: d[2], type: d[3] };
      p.eu = eu(p, spawn);
      p.taxi = taxi(p, spawn);
      if (p.eu <= radius && (p.type === 1 || p.type === 2)) out.push(p);
    }
  }
  return out.sort((a, b) => a.taxi - b.taxi);
}

function validVillages(raw, spawn, strongholds, radius, strongholdExclusion) {
  return (raw || [])
    .map(CONVERT.village)
    .map((p) => ({
      ...p,
      eu: eu(p, spawn),
      taxi: taxi(p, spawn),
      nearestStrongholdEu: strongholds.length ? Math.min(...strongholds.map((s) => eu(p, s))) : Infinity,
    }))
    .filter((p) => p.eu <= radius && p.nearestStrongholdEu > strongholdExclusion)
    .sort((a, b) => a.taxi - b.taxi);
}

function computeUtility(record, config) {
  const { radii, caps, weights, penalties } = config;
  const desertValue = Math.min(decayed(record.desertTemples, caps.midgameTaxi), caps.templeValue);
  const jungleValue = Math.min(decayed(record.jungleTemples, caps.midgameTaxi), caps.templeValue);
  const breakdown = {
    village: weights.village * decayed(record.validVillages, caps.villageTaxi),
    skeleton: weights.skeletonSpawner * decayed(record.skeletonSpawners, caps.dungeonTaxi, 3),
    spider: weights.spiderSpawner * decayed(record.spiderSpawners, caps.dungeonTaxi, 3),
    witchHut: weights.witchHut * decayed(record.witchHuts, caps.midgameTaxi),
    pillagerOutpost: weights.pillagerOutpost * decayed(record.pillagerOutposts, caps.midgameTaxi, 3),
    desertTemple: weights.desertTemple * desertValue,
    jungleTemple: weights.jungleTemple * jungleValue,
    oceanMonument: weights.oceanMonument * Math.min(record.oceanMonuments || 0, caps.oceanMonuments),
    stronghold: weights.stronghold * decayed(record.strongholds, caps.anchorTaxi),
    mansion: weights.mansion * decayed(record.mansions, caps.anchorTaxi),
    extraStrongholds: weights.extraStronghold * Math.max(0, (record.strongholds || []).length - 1),
    extraMansions: weights.extraMansion * Math.max(0, (record.mansions || []).length - 1),
  };
  const scorePenalties = {
    missingWitchHut: (record.witchHuts || []).length === 0 ? penalties.missingWitchHut : 0,
    missingPillagerOutpost: (record.pillagerOutposts || []).length === 0 ? penalties.missingPillagerOutpost : 0,
    missingDesertTemple: (record.desertTemples || []).length === 0 ? penalties.missingDesertTemple : 0,
    missingJungleTemple: (record.jungleTemples || []).length === 0 ? penalties.missingJungleTemple : 0,
    outpostTooClose: tooClosePenalty(record.pillagerOutposts, penalties.outpostTooCloseThreshold, penalties.outpostTooCloseMax),
    witchHutTooClose: tooClosePenalty(record.witchHuts, penalties.witchHutTooCloseThreshold, penalties.witchHutTooCloseMax),
  };
  const rawUtility = Object.values(breakdown).reduce((a, b) => a + b, 0)
    - Object.values(scorePenalties).reduce((a, b) => a + b, 0);
  return {
    rawUtility,
    breakdown,
    penalties: scorePenalties,
    effectiveTempleValue: { desert: desertValue, jungle: jungleValue },
  };
}

function normalize(results) {
  results.sort((a, b) => b.rawUtility - a.rawUtility);
  const values = results.map((r) => r.rawUtility);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const n = results.length;
  results.forEach((r, i) => {
    r.rank = i + 1;
    r.normalizedScore = max === min ? 100 : 100 * (r.rawUtility - min) / (max - min);
    r.percentile = n <= 1 ? 100 : 100 * (n - i - 1) / (n - 1);
  });
  return results;
}

function makeChunkbase(workerPath, timeoutMs) {
  const worker = new Worker(WRAPPER, {
    type: 'module',
    workerData: { workerPath: pathToFileURL(path.resolve(workerPath)).href },
  });
  const pending = new Map();
  worker.on('message', (data) => {
    if (data?.id && pending.has(data.id)) {
      pending.get(data.id)(data);
      pending.delete(data.id);
    }
  });
  worker.on('error', (err) => console.error('ChunkBase worker error:', err));
  function call(apiPath, args = []) {
    return new Promise((resolve, reject) => {
      const id = Math.random().toString(16).slice(2);
      const timeout = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`timeout calling ${apiPath.join('.')}`));
      }, timeoutMs);
      pending.set(id, (data) => {
        clearTimeout(timeout);
        if (data.type === 'HANDLER' && data.name === 'throw') reject(data.value);
        else resolve(data.value);
      });
      worker.postMessage({
        id,
        type: 'APPLY',
        path: apiPath,
        argumentList: args.map((value) => ({ type: 'RAW', value })),
      });
    });
  }
  return { worker, call };
}

async function pool(items, workers, fn, label) {
  let index = 0;
  let done = 0;
  const results = [];
  const errors = [];
  const start = Date.now();
  async function runner(w) {
    while (index < items.length) {
      const item = items[index++];
      try {
        const result = await fn(item, w);
        if (result) results.push(result);
      } catch (err) {
        errors.push({ item, error: String(err?.stack || err) });
      }
      done++;
      if (done % 25 === 0 || done === items.length) {
        console.error(`${label} ${done}/${items.length} elapsed ${Math.round((Date.now() - start) / 1000)}s hits ${results.length}`);
      }
    }
  }
  await Promise.all(workers.map(runner));
  return { results, errors };
}

function configFromArgs(args) {
  return {
    radii: { ...DEFAULT_RADII },
    caps: { ...DEFAULT_CAPS },
    weights: { ...DEFAULT_WEIGHTS },
    penalties: { ...DEFAULT_PENALTIES },
    villageStrongholdExclusion: Number(args['village-stronghold-exclusion'] || 64),
  };
}

async function runScan(args) {
  const workerPath = args['chunkbase-worker'] || process.env.CHUNKBASE_WORKER;
  if (!workerPath) throw new Error('--chunkbase-worker or CHUNKBASE_WORKER is required for scan');
  const seeds = readJson(args.seeds || 'searches/dappled-forest/data/analysis-inputs/seeds.json').map(String);
  const out = args.out || 'searches/dappled-forest/results/dappled-ranked.json';
  const concurrency = Number(args.concurrency || 8);
  const timeoutMs = Number(args.timeout || 600000);
  const config = configFromArgs(args);
  const workers = Array.from({ length: concurrency }, () => makeChunkbase(workerPath, timeoutMs));
  for (const w of workers) await w.call(['initWorker']);

  const anchor = await pool(seeds, workers, async (seed, w) => {
    const spawnOut = await w.call(['getPois'], [world(seed), ['spawn'], ...box({ x: 0, z: 0 }, 256)]);
    const spawn = spawnOut.spawn?.[0]?.[2]
      ? { x: spawnOut.spawn[0][2].x, z: spawnOut.spawn[0][2].z }
      : { x: 0, z: 0 };
    const out = await w.call(['getPois'], [
      world(seed),
      ['woodlandMansion', 'stronghold', 'oceanMonument'],
      ...box(spawn, config.radii.anchor),
    ]);
    const mansions = poiList(out, 'woodlandMansion', spawn, config.radii.anchor);
    const strongholds = poiList(out, 'stronghold', spawn, config.radii.anchor);
    const ocean = poiList(out, 'oceanMonument', spawn, config.radii.midgame);
    if (!mansions.length || !strongholds.length) return null;
    return { seed, spawn, mansions, strongholds, oceanMonuments: ocean.length, nearestOceanMonument: ocean[0] || null };
  }, 'anchor');

  const enriched = await pool(anchor.results, workers, async (record, w) => {
    const [dungeonOut, midOut, villageOut] = await Promise.all([
      w.call(['getPois'], [world(record.seed), ['dungeon'], ...box(record.spawn, config.radii.dungeon)]),
      w.call(['getPois'], [world(record.seed), ['pillagerOutpost', 'witchHut', 'desertTemple', 'jungleTemple'], ...box(record.spawn, config.radii.midgame)]),
      w.call(['getPois'], [world(record.seed), ['village'], ...box(record.spawn, config.radii.village)]),
    ]);
    const dungeons = dungeonList(dungeonOut.dungeon, record.spawn, config.radii.dungeon);
    const r = {
      ...record,
      skeletonSpawners: dungeons.filter((d) => d.type === 2),
      spiderSpawners: dungeons.filter((d) => d.type === 1),
      validVillages: validVillages(villageOut.village, record.spawn, record.strongholds, config.radii.village, config.villageStrongholdExclusion),
      pillagerOutposts: poiList(midOut, 'pillagerOutpost', record.spawn, config.radii.midgame),
      witchHuts: poiList(midOut, 'witchHut', record.spawn, config.radii.midgame),
      desertTemples: poiList(midOut, 'desertTemple', record.spawn, config.radii.midgame),
      jungleTemples: poiList(midOut, 'jungleTemple', record.spawn, config.radii.midgame),
    };
    return { ...r, ...computeUtility(r, config) };
  }, 'enrich');

  workers.forEach((w) => w.worker.terminate());
  const results = normalize(enriched.results);
  writeJson(out, {
    model: 'dappled forest ChunkBase Bedrock scan; phase radii; revised utility; desert edge; temple cap 1.75',
    generatedAt: new Date().toISOString(),
    tested: seeds.length,
    matched: results.length,
    config,
    errors: { anchor: anchor.errors, enrich: enriched.errors },
    results,
  });
}

function runExtract(args) {
  if (!args.session) throw new Error('--session is required');
  const out = args.out || 'searches/dappled-forest/data/analysis-inputs/seeds.json';
  const seeds = extractSeeds(args.session);
  writeJson(out, seeds);
  console.error(`wrote ${seeds.length} seeds to ${out}`);
}

function runRerank(args) {
  if (!args.input) throw new Error('--input is required');
  const out = args.out || args.input.replace(/\.json$/, '.reranked.json');
  const data = readJson(args.input);
  const config = configFromArgs(args);
  const results = (data.results || []).map((r) => ({ ...r, ...computeUtility(r, config) }));
  normalize(results);
  writeJson(out, {
    ...data,
    model: 'dappled forest rerank; phase radii; revised utility; desert edge; temple cap 1.75',
    rerankedAt: new Date().toISOString(),
    config,
    matched: results.length,
    results,
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0];
  if (!command || args.help) return usage();
  if (command === 'extract') return runExtract(args);
  if (command === 'scan') return runScan(args);
  if (command === 'rerank') return runRerank(args);
  throw new Error(`unknown command: ${command}`);
}

main().catch((err) => {
  console.error(err?.stack || err);
  process.exit(1);
});
