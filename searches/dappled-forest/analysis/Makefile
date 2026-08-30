# Builds the ocean-connectivity scorer against cubiomes.
#
# cubiomes is not vendored: this clones it on first build, pinned to the same
# commit the session notes are verified against, into a gitignored directory.
# Nothing else in this repo needs a compiler, so the dependency stays local to
# this tool.

CUBIOMES_REPO := https://github.com/Cubitect/cubiomes.git
CUBIOMES_REF  := e61f905
CUBIOMES_DIR  := cubiomes

SRCS := $(CUBIOMES_DIR)/biomenoise.c $(CUBIOMES_DIR)/biomes.c \
        $(CUBIOMES_DIR)/generator.c $(CUBIOMES_DIR)/layers.c \
        $(CUBIOMES_DIR)/noise.c $(CUBIOMES_DIR)/finders.c \
        $(CUBIOMES_DIR)/quadbase.c $(CUBIOMES_DIR)/util.c

CFLAGS := -O2 -I$(CUBIOMES_DIR)
LDLIBS := -lm

ocean_connectivity: ocean_connectivity.c | $(CUBIOMES_DIR)
	$(CC) $(CFLAGS) -o $@ $< $(SRCS) $(LDLIBS)

$(CUBIOMES_DIR):
	git clone --quiet $(CUBIOMES_REPO) $(CUBIOMES_DIR)
	git -C $(CUBIOMES_DIR) checkout --quiet $(CUBIOMES_REF)

clean:
	rm -f ocean_connectivity

distclean: clean
	rm -rf $(CUBIOMES_DIR)

.PHONY: clean distclean
