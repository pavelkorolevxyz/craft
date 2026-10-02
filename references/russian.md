# Material in Russian

Craft is written in English. Read this file when the page or deck is in Russian: it lists the fixed words, labels and typography that change. Layouts, rules and checks stay the same.

## Project

Create the project with `scaffold.py --lang ru`. The bundled fonts cover Cyrillic.

## Fixed slide words

| Place | Russian |
|---|---|
| Plan title | План |
| Speaker context title | Обо мне |
| End slide line | Спасибо за внимание |
| Takeaway summary title | Что я из этого вынес (вынесла) |
| Comparison sides | Было / Стало |
| Source caption | Источник |
| Draft badge, `data-status-label` | Черновик |

Write takeaways in the first person and match the speaker's gender in verbs.

## Deck controls

The control panel labels live in `index.html`. Replace each `aria-label`:

| English | Russian |
|---|---|
| Presentation controls | Управление презентацией |
| Slide overview | Обзор слайдов |
| Slide strip view | Обзор лентой |
| Full screen | Полный экран |
| Stop motion | Остановить движение |
| Switch to light theme | Включить светлую тему |
| Slide navigation | Навигация по слайдам |
| Previous slide, Next slide | Предыдущий слайд, Следующий слайд |
| Go to page | Перейти к странице |
| Hide control panel, Show control panel | Скрыть управление, Показать управление |

`deck.js` writes some labels itself. Override them on `.deck`:

```html
<div class="deck" data-labels='{"draft":"Черновик","skip":"Исключён","stopMotion":"Остановить движение","startMotion":"Запустить движение","darkTheme":"Включить тёмную тему","lightTheme":"Включить светлую тему","strip":"Обзор лентой","stripHorizontal":"Лента по горизонтали","stripVertical":"Лента по вертикали"}'>
```

## Page controls

On a page, the theme toggle gets `data-label-dark="Включить тёмную тему"` and `data-label-light="Включить светлую тему"`. The copy button reads «Копировать» and «Скопировано».

## Numbers and dates

- Group digits with a no-break space and use a decimal comma: `12 400`, `2,4`. In a `ru` deck the counter reads a comma as the decimal mark, so `12,400` would animate as twelve.
- Join a number and its unit with a no-break space: `25 минут`, `30 %`.
- Dates: `1 октября 2026`, time `14:30`.

## Typography

- Quotes are «ёлочки», nested quotes „лапки“.
- Prefer a period or a comma to a dash, as in English text.
- Put a no-break space after a one-letter word (в, к, с, и, а, о, у) in headings so it does not end a line.
- Headings use sentence case. A one-sentence subtitle has no trailing period.
- Use ё where it changes meaning, and keep the choice consistent within one material.
