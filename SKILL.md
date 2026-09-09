---
name: craft
description: "Используй Craft для автономных HTML-страниц и слайдов."
---

# Craft

1. Определи носитель. Доклад или презентация используют `slides`; страница для чтения или управления использует `interface`. Если носитель неясен, прочитай [карту форматов](references/surfaces.md).
2. Прочитай общие [правила оформления](references/identity.md) и [процесс сборки и проверки](references/workflow.md).
3. Пройди только выбранную ветку ниже. Не загружай весь реестр, каталог и все справочники.

## Слайды

До HTML прочитай [выбор формы и сценария](references/slides/selection.md), затем [визуальную грамматику](references/slides/design-language.md) и [механику](references/slides/authoring.md).

Если есть числовой график, дополнительно прочитай [графики](references/slides/charts.md). Контракт выбранного фрагмента получи через `compose.py --list-placeholders`.

## Интерфейс

Прочитай [геометрию страницы](references/interfaces/patterns.md) и [визуальную грамматику](references/interfaces/design-language.md). [Каркас и указатель компонентов](references/interfaces/components.md) ведут к нужной разметке.

Открывай только используемые ветки:
- [формы](references/interfaces/components/forms.md): поля, кнопки, выбор значения и проверка;
- [данные](references/interfaces/components/data.md): таблицы, статусы, графики, значения, события и код;
- [обратная связь](references/interfaces/components/feedback.md): уведомления, загрузка, раскрытие, окна и пустые состояния;
- [навигация](references/interfaces/components/navigation.md): вкладки, фильтры, шаги, список с деталями и клавиатура.

## Другой носитель или расширение системы

Прочитай [правила расширения](references/extending.md). Теория уровней, устройство каталога и релизов не нужны для обычной сборки материала.
