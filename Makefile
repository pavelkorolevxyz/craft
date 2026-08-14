PYTHON ?= python3

.PHONY: help check test verify render visual-test visual-update dist all clean

help:
	@printf '%s\n' \
	  'make check         Быстрые проверки исходников и дизайн-контрактов' \
	  'make test          Интеграционные тесты генератора, Chromium и PDF' \
	  'make verify        Полный набор check + test' \
	  'make render        Создать галерею artifacts/render для проверки' \
	  'make visual-test   Сравнить рендеры с проверенными эталонами' \
	  'make visual-update Заменить эталоны после ручной проверки' \
	  'make dist          Проверить и собрать воспроизводимые ZIP-релизы' \
	  'make all           Проверить, отрендерить и собрать ZIP-релизы' \
	  'make clean         Удалить созданные артефакты и дистрибутивы'

check:
	$(PYTHON) scripts/check.py

test:
	$(PYTHON) scripts/test_scaffold.py

verify: check test

render:
	$(PYTHON) scripts/render.py --clean

visual-test:
	$(PYTHON) scripts/visual_test.py

visual-update:
	$(PYTHON) scripts/visual_test.py --update

dist: verify
	$(PYTHON) scripts/build.py --clean

all: verify render
	$(PYTHON) scripts/build.py --clean

clean:
	rm -rf artifacts dist
