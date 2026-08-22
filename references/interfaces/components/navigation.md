# Навигация и структура

Навигация появляется тогда, когда материал не помещается на один экран или делится на самостоятельные части. Короткому отчёту она только отнимает место.

## Вкладки

```html
<div class="tabs" data-tabs>
  <div class="tablist" role="tablist" aria-label="Представления очереди">
    <button role="tab" type="button" id="tab-open" aria-controls="panel-open"
      aria-selected="true">Открытые</button>
    <button role="tab" type="button" id="tab-done" aria-controls="panel-done"
      aria-selected="false">Закрытые</button>
  </div>
  <div role="tabpanel" id="panel-open" aria-labelledby="tab-open" tabindex="0">...</div>
  <div role="tabpanel" id="panel-done" aria-labelledby="tab-done" tabindex="0" hidden>...</div>
</div>
```

Механика `tabs.js` переносит выбор мышью и стрелками, доводит до края клавишами перехода в начало и конец и прячет неактивные панели. Разметка уже описывает связи, поэтому скрипт не создаёт параллельную модель доступности.

Вкладки подходят равноправным представлениям одного набора. Последовательные шаги, вложенные разделы и материал для сравнения бок о бок вкладками не решаются. Держи 2–5 вкладок с короткими подписями и не прячь за ними то, что нужно видеть одновременно.

В печати панель вкладок скрывается, а всё содержимое печатается подряд.

Фрагмент — `tabs.html`.

## Цепочка разделов

```html
<nav aria-label="Путь к материалу">
  <ol class="breadcrumbs">
    <li><a href="#index">Отчёты</a></li>
    <li><a href="#weekly">Неделя</a></li>
    <li><span aria-current="page">Задержки</span></li>
  </ol>
</nav>
```

Цепочка называет положение материала в иерархии, поэтому текущий уровень — обычный текст, а не ссылка. Она нужна вложенному материалу и бесполезна на самостоятельной странице.

Фрагмент — `breadcrumbs.html`.

## Постраничная навигация

```html
<nav class="pagination" aria-label="Страницы очереди">
  <a class="button" href="#page-1">Назад</a>
  <a class="pagination__page" href="#page-1">1</a>
  <a class="pagination__page" href="#page-2" aria-current="page">2</a>
  <a class="button" href="#page-3">Вперёд</a>
  <p class="pagination__status" role="status">21–40 из 84</p>
</nav>
```

Положение в наборе указывается словами: одни номера страниц не отвечают на вопрос, сколько записей осталось. Недоступное направление помечается `aria-disabled` и не исчезает: пропадающая кнопка сдвигает соседние.

Небольшой набор целиком помещается на одну страницу и в навигации не нуждается.

Фрагмент — `pagination.html`.

## Полоса параметров

```html
<div class="filter-bar" role="group" aria-label="Параметры очереди">
  <label class="field__label" for="stream">Поток</label>
  <span class="select-control">
    <select id="stream"><option>Все</option></select>
    <svg class="select-control__icon" viewBox="0 0 12 8" aria-hidden="true"><path d="m1 1 5 5 5-5"/></svg>
  </span>
  <p class="filter-bar__count" role="status">Отобрано 18 из 84</p>
</div>
```

Полоса стоит непосредственно над областью, которую меняет, и заканчивается числом отобранных записей. Изменение параметра сразу меняет данные, поэтому отдельная кнопка применения не нужна; если запрос долгий, область получает `aria-busy` и заглушку.

Не превращай полосу в глобальную панель инструментов: параметры, действующие на всю страницу, живут в шапке рабочей поверхности.

Фрагмент — `filter-bar.html`.

## Шаги процесса

```html
<ol class="steps" aria-label="Ход публикации">
  <li data-state="done"><span class="steps__index">01</span><span class="steps__title">Сборка</span></li>
  <li data-state="current"><span class="steps__index">02</span><span class="steps__title">Проверка</span></li>
  <li><span class="steps__index">03</span><span class="steps__title">Публикация</span></li>
</ol>
```

Шаги показывают конечную последовательность с известным концом. Текущий шаг выделен плоскостью и акцентным номером, пройденный отличается от предстоящего яркостью подписи. На узком экране ряд разворачивается в колонку.

Для потока событий без завершения бери [ленту](data.md).

Фрагмент — `steps.html`.

## Навигация по длинному документу

Ссылки на разделы страницы описаны в [основном справочнике](../components.md) вместе с механикой `section-nav.js`.
