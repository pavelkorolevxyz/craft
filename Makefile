PYTHON ?= python3

.PHONY: help check css-audit test verify render visual-test visual-update release-test dist all clean

help:
	@printf '%s\n' \
	  'make check         Быстрые проверки исходников и дизайн-контрактов' \
	  'make css-audit     Показать использование публичных CSS-классов' \
	  'make test          Интеграционные тесты генератора, Chromium и PDF' \
	  'make verify        Полный набор check + test' \
	  'make render        Создать галерею artifacts/render для проверки' \
	  'make visual-test   Сравнить рендеры с проверенными эталонами' \
	  'make visual-update Заменить эталоны после ручной проверки' \
	  'make release-test  Проверить собранные архивы вне исходного дерева' \
	  'make dist          Проверить и собрать воспроизводимые ZIP-релизы' \
	  'make all           Проверить, отрендерить и собрать ZIP-релизы' \
	  'make clean         Удалить созданные артефакты и дистрибутивы'

check:
	$(PYTHON) scripts/check.py

css-audit:
	$(PYTHON) scripts/audit_css.py --fail-on-unused

test:
	$(PYTHON) scripts/test_scaffold.py
	$(PYTHON) scripts/test_compose.py

verify: check test

render:
	$(PYTHON) scripts/render.py --clean

visual-test:
	$(PYTHON) scripts/visual_test.py

visual-update:
	$(PYTHON) scripts/visual_test.py --update

release-test:
	$(PYTHON) scripts/test_release.py

dist: verify
	$(PYTHON) scripts/build.py --clean
	$(PYTHON) scripts/test_release.py

all: verify render
	$(PYTHON) scripts/build.py --clean
	$(PYTHON) scripts/test_release.py

clean:
	rm -rf artifacts dist
