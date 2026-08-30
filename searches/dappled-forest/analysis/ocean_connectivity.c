/* Scores seeds on the geographic "visual grammar" that cubiomes-viewer cannot
 * express as search conditions.
 *
 * The viewer's filters can require that a biome exists, that a biome set covers
 * some fraction of an area, or that a structure generates -- but nothing in
 * search.cpp measures *connectivity*. F_BIOME_CENTER does run a connected-
 * component pass, but only over a single biome id, and it reports cluster
 * centres rather than how much of the biome sits in its largest component. A sea
 * spans ocean, deep_ocean, cold_ocean and the rest, so single-id clustering
 * cannot answer "is this one navigable ocean or several ponds".
 *
 * So this runs as a scoring pass over search results instead of as a gate. It
 * generates the biome map once per seed at 1:4 and flood-fills it, which takes
 * about a second -- fine for ranking a results list, hopeless as a filter.
 *
 * Reads seeds (one per line, decimal, signed) on stdin. Writes TSV on stdout.
 *
 *   water_pct        share of the home region that is ocean-family
 *   ocean_conn_pct   share of that ocean sitting in its single largest connected
 *                    component: 100% is one sea, low values mean scattered ponds
 *   spawn_biome      the biome at world spawn
 *   plains_pct       plains-family share within PLAINS_HALF of spawn
 *   local_water_pct  ocean-family share within LOCAL_HALF of spawn
 *   island_blocks    area of the connected land mass containing spawn
 *   island_open      1 if that land mass reaches the edge of the sampled region,
 *                    i.e. it is not demonstrably framed by water within it
 *
 * Build and run: see the Makefile in this directory.
 */
#include "generator.h"
#include "finders.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HALF        2048   /* home region half-width: a 4096x4096 map */
#define SCALE       4      /* biome sampling scale (1:4) */
#define PLAINS_HALF 256    /* window for the "plains identity at spawn" score */
#define LOCAL_HALF  256    /* window for the "sheltered local water" score */

static Generator g;

static int is_ocean(int b)
{
    switch (b) {
    case ocean: case frozen_ocean: case deep_ocean: case warm_ocean:
    case lukewarm_ocean: case cold_ocean: case deep_lukewarm_ocean:
    case deep_cold_ocean: case deep_frozen_ocean: case deep_warm_ocean:
        return 1;
    }
    return 0;
}

static int is_plains(int b)
{
    return b == plains || b == sunflower_plains || b == meadow;
}

/* Share of `set` within +/-half of (cx,cz), sampled at 1:4. */
static double local_share(int cx, int cz, int half, int (*pred)(int))
{
    int w = (2 * half) / SCALE + 1;
    Range r = { SCALE, (cx - half) >> 2, (cz - half) >> 2, w, w, 64, 1 };
    int *cache = allocCache(&g, r);
    genBiomes(&g, cache, r);
    long hit = 0;
    for (int i = 0; i < w * w; i++)
        hit += pred(cache[i]);
    free(cache);
    return 100.0 * hit / (double)(w * w);
}

int main(void)
{
    setupGenerator(&g, MC_1_21_WD, 0);

    const int W = (2 * HALF) / SCALE;          /* cells across the region */
    const size_t N = (size_t)W * W;
    char *ocean_map = malloc(N);
    int  *comp      = malloc(N * sizeof(int));
    int  *stack     = malloc(N * sizeof(int));
    if (!ocean_map || !comp || !stack) { fprintf(stderr, "out of memory\n"); return 1; }

    printf("seed\twater_pct\tocean_conn_pct\tspawn_biome\tplains_pct\tlocal_water_pct\t"
           "island_blocks\tisland_open\n");

    long long seed;
    while (scanf("%lld", &seed) == 1)
    {
        applySeed(&g, DIM_OVERWORLD, (uint64_t)seed);

        Range r = { SCALE, -HALF / SCALE, -HALF / SCALE, W, W, 64, 1 };
        int *cache = allocCache(&g, r);
        genBiomes(&g, cache, r);

        long ocean_cells = 0;
        for (size_t i = 0; i < N; i++) {
            ocean_map[i] = (char)is_ocean(cache[i]);
            ocean_cells += ocean_map[i];
        }
        free(cache);

        /* Largest connected ocean component, 4-connectivity. Also, separately,
         * the land component containing spawn -- the same flood fill run over
         * the complement, which is what "a home landform framed by water" means
         * if you can measure it. */
        memset(comp, 0, N * sizeof(int));
        long largest = 0;
        int cid = 0;
        for (size_t i = 0; i < N; i++) {
            if (!ocean_map[i] || comp[i]) continue;
            cid++;
            long size = 0;
            int sp = 0;
            stack[sp++] = (int)i;
            comp[i] = cid;
            while (sp) {
                int c = stack[--sp];
                size++;
                int x = c % W, y = c / W;
                int nb[4] = { x > 0 ? c-1 : -1, x < W-1 ? c+1 : -1,
                              y > 0 ? c-W : -1, y < W-1 ? c+W : -1 };
                for (int k = 0; k < 4; k++) {
                    int t = nb[k];
                    if (t >= 0 && ocean_map[t] && !comp[t]) { comp[t] = cid; stack[sp++] = t; }
                }
            }
            if (size > largest) largest = size;
        }

        Pos spawn = getSpawn(&g);
        int spawn_biome = getBiomeAt(&g, SCALE, spawn.x >> 2, 64, spawn.z >> 2);

        /* land mass containing spawn */
        long island_cells = 0;
        int island_open = 0;
        int sx = (spawn.x + HALF) / SCALE, sz = (spawn.z + HALF) / SCALE;
        if (sx >= 0 && sx < W && sz >= 0 && sz < W && !ocean_map[(size_t)sz * W + sx]) {
            memset(comp, 0, N * sizeof(int));
            int sp = 0, start = sz * W + sx;
            stack[sp++] = start;
            comp[start] = 1;
            while (sp) {
                int c = stack[--sp];
                island_cells++;
                int x = c % W, y = c / W;
                if (x == 0 || x == W-1 || y == 0 || y == W-1) island_open = 1;
                int nb[4] = { x > 0 ? c-1 : -1, x < W-1 ? c+1 : -1,
                              y > 0 ? c-W : -1, y < W-1 ? c+W : -1 };
                for (int k = 0; k < 4; k++) {
                    int t = nb[k];
                    if (t >= 0 && !ocean_map[t] && !comp[t]) { comp[t] = 1; stack[sp++] = t; }
                }
            }
        }

        printf("%lld\t%.1f\t%.1f\t%s\t%.1f\t%.1f\t%ld\t%d\n",
               seed,
               100.0 * ocean_cells / (double)N,
               ocean_cells ? 100.0 * largest / (double)ocean_cells : 0.0,
               biome2str(MC_1_21_WD, spawn_biome),
               local_share(spawn.x, spawn.z, PLAINS_HALF, is_plains),
               local_share(spawn.x, spawn.z, LOCAL_HALF, is_ocean),
               island_cells * SCALE * SCALE,
               island_open);
        fflush(stdout);
    }
    free(ocean_map); free(comp); free(stack);
    return 0;
}
