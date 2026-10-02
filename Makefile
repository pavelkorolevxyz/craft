PYTHON ?= python3
TESTS = test-scaffold test-compose test-probe test-deck-release test-release

.PHONY: help check css-audit smoke test $(TESTS) verify render visual-test visual-update release-test dist all ci clean

# Stages grow in cost and shrink in how often they are needed:
#   0 check   contracts, no browser             every edit
#   1 smoke   catalogs rendered in Chromium     before a commit that touches UI
#   2 test    behavior tests, run in parallel   before a push, in CI
#   3 visual  baselines and release archives    in CI and before a release
help:
	@printf '%s\n' \
	  'make check         Fast checks of sources and design contracts, no browser (stage 0)' \
	  'make smoke         Render the catalogs in Chromium at three widths (stage 1)' \
	  'make test          Behavior tests in parallel: scaffold, compose, deck states, releases (stage 2)' \
	  'make verify        Run check, smoke and test' \
	  'make render        Build the artifacts/render review gallery' \
	  'make visual-test   Render once and compare with approved baselines (stage 3)' \
	  'make visual-update Render once and replace baselines after a manual review' \
	  'make release-test  Test built archives outside the source tree' \
	  'make dist          Verify and build reproducible ZIP releases' \
	  'make ci            Everything CI runs: verify, render and archives' \
	  'make css-audit     Show usage of public CSS classes' \
	  'make clean         Remove generated artifacts and dist'

check:
	$(PYTHON) scripts/check.py
	$(PYTHON) scripts/audit_css.py --fail-on-unused

css-audit:
	$(PYTHON) scripts/audit_css.py

smoke:
	$(PYTHON) scripts/check_project.py catalog/interfaces --resource-root .
	$(PYTHON) scripts/check_project.py catalog/slides --resource-root .

test:
	$(MAKE) -j4 --output-sync=target $(TESTS)

test-scaffold:
	$(PYTHON) tests/test_scaffold.py

test-compose:
	$(PYTHON) tests/test_compose.py

test-probe:
	$(PYTHON) tests/test_probe.py

test-deck-release:
	$(PYTHON) tests/test_deck_release.py

test-release:
	$(PYTHON) scripts/build.py --clean --output artifacts/test-dist
	$(PYTHON) tests/test_release.py --dist artifacts/test-dist

verify: check smoke test

render:
	$(PYTHON) scripts/render.py --clean

visual-test: render
	$(PYTHON) tests/visual/visual_test.py --rendered artifacts/render

visual-update: render
	$(PYTHON) tests/visual/visual_test.py --rendered artifacts/render --update

release-test:
	$(PYTHON) tests/test_release.py

dist: verify
	$(PYTHON) scripts/build.py --clean
	$(PYTHON) tests/test_release.py

ci: verify render

all: ci dist

clean:
	rm -rf artifacts dist
