# Dappled Forest ChunkBase ranking scripts

This folder contains the ad hoc ChunkBase-backed ranking workflow used to score
Dappled Forest candidate seeds for long-term Bedrock survival/exploration.

The scripts intentionally keep the ChunkBase worker **out of the repository**.
Use a local, reviewed copy of the ChunkBase seed-map web worker and pass it with
`--chunkbase-worker` or `CHUNKBASE_WORKER`. This keeps the repo from vendoring a
minified third-party web asset while preserving the reproducible scoring logic.

## 1. Extract seeds from a cubiomes-viewer session

```bash
node searches/dappled-forest/scripts/rank_dappled_forest.mjs extract \
  --session searches/dappled-forest/sessions/dappled-forest.session \
  --out searches/dappled-forest/data/analysis-inputs/seeds.json
```

The extractor reads integer seed lines from the session and writes a JSON array
of unique seed strings.

## 2. Scan ChunkBase POIs and rank candidates

```bash
node searches/dappled-forest/scripts/rank_dappled_forest.mjs scan \
  --seeds searches/dappled-forest/data/analysis-inputs/seeds.json \
  --chunkbase-worker /path/to/chunkbase-worker.mjs \
  --out searches/dappled-forest/results/dappled-ranked.json \
  --concurrency 8
```

The scanner:

1. estimates spawn from ChunkBase,
2. keeps seeds with at least one Woodland Mansion and one Stronghold in the
   anchor ring,
3. enriches those candidates with villages, skeleton/spider spawners, Pillager
   Outposts, witch huts, desert temples, trail ruins, jungle temples, and ocean
   monuments,
4. scores and ranks the enriched records.

## 3. Rerank existing enriched output

```bash
node searches/dappled-forest/scripts/rank_dappled_forest.mjs rerank \
  --input searches/dappled-forest/results/dappled-ranked.json \
  --out searches/dappled-forest/results/dappled-ranked-rerank.json
```

Reranking does not call ChunkBase. It recomputes score fields from already
stored POI arrays.

## Current scoring model

Higher is better.

### Radii

| Feature group | Euclidean radius |
|---|---:|
| Villages | 2048 |
| Skeleton/Spider spawners | 1536 |
| Midgame structures | 3072 |
| Woodland Mansion / Stronghold anchors | 4096 |

Villages are excluded only if they are within 64 Euclidean blocks of a
Stronghold, to avoid counting overlapping/same-site structures while preserving
nearby useful villages.

### Utility weights

| Feature | Weight / rule |
|---|---:|
| Village cluster | `350 × rank-decayed value` |
| Skeleton spawners | `300 × rank-decayed value`, first 3 |
| Spider spawners | `200 × rank-decayed value`, first 3 |
| Witch huts | `220 × rank-decayed value` |
| Pillager Outposts | `180 × rank-decayed value`, first 3 |
| Desert temples | `140 × min(rank-decayed value, 1.75)` |
| Trail ruins | `120 × rank-decayed value` |
| Jungle temples | `100 × min(rank-decayed value, 1.75)` |
| Ocean monuments | `35 × min(count, 8)` |
| Strongholds | `240 × rank-decayed value` |
| Woodland Mansions | `220 × rank-decayed value` |
| Extra Strongholds | `120 × (count - 1)` |
| Extra Mansions | `300 × (count - 1)` |

Rank decay is `1.0, 0.5, 0.25, ...`, and distance value is:

```text
max(0, 1 - taxi_distance / cap)
```

### Penalties

| Condition | Penalty |
|---|---:|
| Missing witch hut | `-180` |
| Missing Pillager Outpost | `-160` |
| Missing desert temple | `-120` |
| Missing trail ruins | `-100` |
| Missing jungle temple | `-80` |
| Pillager Outpost closer than 512 taxi | up to `-250` |
| Witch hut closer than 384 taxi | up to `-120` |

The output includes:

- `rawUtility`
- `normalizedScore` on a 0-100 scale within the matched candidate set
- `percentile` within the matched candidate set
- `breakdown` and `penalties` for auditability
