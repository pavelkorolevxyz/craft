# Компоненты и примитивы

Базовые классы находятся в `assets/interfaces/theme.css`. Для конкретной композиции добавляй локальный CSS. Не копируй `specimen.css` целиком: он нужен только каталогу дизайн-системы.

## Каркас

```html
<main class="shell">
  <header class="report-head">...</header>
  <section class="scoreboard">...</section>
  <section class="section">...</section>
  <aside class="callout">...</aside>
</main>
```

`.shell` занимает всю ширину и минимум всю высоту области просмотра. Не добавляй внешний центрированный контейнер.

## Заголовок инструмента или отчёта

```html
<header class="report-head">
  <div class="report-head__main">
    <p class="eyebrow">Состояние системы</p>
    <h1>Отчёт за неделю</h1>
    <p class="report-head__lede">Главный вывод одной фразой.</p>
  </div>
  <div class="report-head__aside" aria-label="Параметры отчёта">
    <p>Период: 7 дней</p>
    <p>Обновлено: 2026-08-14</p>
    <p>Источник: локальные данные</p>
  </div>
</header>
```

Оставляй правую колонку только для параметров, фильтров или действий. Если их нет, удали колонку и сделай заголовок одноколоночным.

## Метрики

```html
<section class="scoreboard" aria-label="Ключевые показатели" style="--metrics: 3">
  <div class="metric">
    <strong class="metric__value">98,7%</strong>
    <span class="metric__label">Успешных операций</span>
  </div>
</section>
```

Используй 2–4 метрики в поддержку главного вывода. Указывай единицу измерения. По умолчанию значения нейтральные; добавляй `.metric--accent` только приоритетной метрике.

## Секция

```html
<section class="section">
  <div class="section-head">
    <h2>Что произошло</h2>
    <p>Источник, период или инструкция по чтению.</p>
  </div>
  <!-- содержательная композиция -->
</section>
```

`.section--tight` подходит для таблиц и плотных журналов. `.section--accent` применяется редко, обычно один раз на странице.

## Компоновка

```html
<div class="split">
  <div>Главный материал</div>
  <aside>Сигналы или пояснение</aside>
</div>

<div class="stack" style="--stack-gap: 16px">...</div>
```

`.split` создаёт неравные колонки. Для иной структуры добавь локальный класс сетки, сохраняя поля `var(--gutter)` и интервалы 8–48 px.

## Полосы данных

```html
<div class="bar-list" aria-label="Распределение нагрузки">
  <div class="bar">
    <div class="bar__head"><span>Основной поток</span><strong>82%</strong></div>
    <div class="bar__track"><div class="bar__fill" style="--value:82%"></div></div>
  </div>
</div>
```

Шкала начинается с нуля. Продублируй значение текстом: длины полосы недостаточно для передачи данных.

## Статусы

```html
<span class="status status--good">стабильно</span>
<span class="status status--warn">проверить</span>
<span class="status status--bad">блокер</span>
```

Всегда подписывай статус. Цветная точка только дополняет текст.

## Таблица

```html
<table class="data-table">
  <thead><tr><th>Поток</th><th>Состояние</th><th>Задачи</th></tr></thead>
  <tbody>
    <tr><td>Основной</td><td><span class="status status--good">норма</span></td><td>64</td></tr>
    <tr class="total"><td>Всего</td><td>1 поток</td><td>64</td></tr>
  </tbody>
</table>
```

Если назначение таблицы неочевидно, добавь `<caption>` или заголовок секции. Не выделяй итоговую строку красным без содержательного приоритета.

## Кнопки и поля

```html
<button class="button button--primary">Сформировать</button>
<button class="button">Экспортировать</button>
<label for="period">Период</label>
<select id="period"><option>7 дней</option></select>
```

Базовый `theme.css` содержит кнопки. Стили полей, фильтров и сложных элементов управления добавляй локально под задачу, опираясь на каталог. Минимальная высота интерактивного элемента — 44 px.

## Текстовый отчёт

```html
<section class="section">
  <article class="prose">
    <h2>Вывод</h2>
    <p>...</p>
    <pre><code>...</code></pre>
  </article>
</section>
```

`.prose` ограничивает длину строки, но не ширину всей рабочей поверхности.

## Финальное действие

```html
<aside class="callout">
  <strong>Следующий шаг</strong>
  <p>Решение, срок и ответственный.</p>
</aside>
```

Добавляй блок, только если у страницы есть следующее действие. Справочнику или исследовательскому инструменту он обычно не нужен.
