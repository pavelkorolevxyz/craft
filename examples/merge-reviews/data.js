window.MERGE_REVIEW_DATA = {
  repository: "northstar/web-app",
  branch: "main",
  generatedAt: "2026-08-21T18:45:00+03:00",
  items: [
    {
      iid: 1842,
      title: "Сохранять фильтры каталога в URL",
      author: { name: "Лена Воронова", handle: "@lvoronova", initials: "ЛВ" },
      created: "2026-08-19T10:20:00+03:00",
      updated: "2026-08-21T18:31:00+03:00",
      source: "feat/catalog-query-state",
      status: "blocked",
      pipeline: "passed",
      changes: 18,
      comments: 24,
      unresolved: 3,
      labels: ["frontend", "catalog"],
      summary: "Навигация назад восстанавливает фильтры, сортировку и страницу выдачи. Остался спор о формате массива параметров.",
      checks: [
        { label: "Pipeline", state: "ok", detail: "128 тестов пройдено" },
        { label: "Обсуждения", state: "error", detail: "3 ветки не закрыты" },
        { label: "Review", state: "warn", detail: "1 из 2 одобрений" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Антон Белых", initials: "АБ", state: "approved", note: "Одобрил 42 минуты назад" },
        { name: "Майя Романова", initials: "МР", state: "changes", note: "Оставила 3 замечания" }
      ],
      threads: [
        { author: "Майя Романова", time: "17:56", text: "Массивы лучше сериализовать повторяющимся параметром. Так URL останется читаемым." },
        { author: "Лена Воронова", time: "18:12", text: "Поправлю парсер и добавлю кейс с двумя категориями." }
      ]
    },
    {
      iid: 1839,
      title: "Убрать повторный запрос профиля после логина",
      author: { name: "Кирилл Носов", handle: "@knosov", initials: "КН" },
      created: "2026-08-18T14:05:00+03:00",
      updated: "2026-08-21T18:04:00+03:00",
      source: "fix/auth-profile-race",
      status: "ready",
      pipeline: "passed",
      changes: 9,
      comments: 11,
      unresolved: 0,
      labels: ["frontend", "auth"],
      summary: "Профиль теперь берётся из ответа login mutation. Повторный запрос и скачок интерфейса после входа исчезли.",
      checks: [
        { label: "Pipeline", state: "ok", detail: "96 тестов пройдено" },
        { label: "Обсуждения", state: "ok", detail: "все закрыты" },
        { label: "Review", state: "ok", detail: "2 из 2 одобрений" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Лена Воронова", initials: "ЛВ", state: "approved", note: "Одобрила 1 час назад" },
        { name: "Олег Ким", initials: "ОК", state: "approved", note: "Одобрил 3 часа назад" }
      ],
      threads: []
    },
    {
      iid: 1848,
      title: "Новый экран управления API-ключами",
      author: { name: "Даша Ильина", handle: "@dilyina", initials: "ДИ" },
      created: "2026-08-21T09:14:00+03:00",
      updated: "2026-08-21T17:42:00+03:00",
      source: "feat/api-keys-screen",
      status: "review",
      pipeline: "running",
      changes: 31,
      comments: 8,
      unresolved: 1,
      labels: ["frontend", "settings", "security"],
      summary: "Добавлены выпуск, переименование и отзыв ключей. Pipeline ещё выполняет браузерные тесты.",
      checks: [
        { label: "Pipeline", state: "warn", detail: "браузерные тесты выполняются" },
        { label: "Обсуждения", state: "warn", detail: "1 ветка не закрыта" },
        { label: "Review", state: "warn", detail: "ожидает 2 ревьюеров" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Артур Пак", initials: "АП", state: "waiting", note: "Назначен 6 часов назад" },
        { name: "Майя Романова", initials: "МР", state: "waiting", note: "Назначена 6 часов назад" }
      ],
      threads: [
        { author: "Артур Пак", time: "16:48", text: "Нужно скрывать полный ключ сразу после ухода со страницы, не только после перезагрузки." }
      ]
    },
    {
      iid: 1827,
      title: "Пакетное редактирование ролей команды",
      author: { name: "Олег Ким", handle: "@okim", initials: "ОК" },
      created: "2026-08-15T11:32:00+03:00",
      updated: "2026-08-21T16:19:00+03:00",
      source: "feat/team-bulk-roles",
      status: "blocked",
      pipeline: "failed",
      changes: 42,
      comments: 37,
      unresolved: 2,
      labels: ["backend", "teams"],
      summary: "API принимает до 100 изменений ролей за запрос. Интеграционный тест падает на откате транзакции.",
      checks: [
        { label: "Pipeline", state: "error", detail: "1 интеграционный тест упал" },
        { label: "Обсуждения", state: "error", detail: "2 ветки не закрыты" },
        { label: "Review", state: "warn", detail: "1 из 2 одобрений" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Кирилл Носов", initials: "КН", state: "approved", note: "Одобрил вчера" },
        { name: "Артур Пак", initials: "АП", state: "changes", note: "Ждёт исправления теста" }
      ],
      threads: [
        { author: "Артур Пак", time: "15:41", text: "Если 48-я запись не проходит валидацию, первые 47 тоже должны откатиться." }
      ]
    },
    {
      iid: 1845,
      title: "Сократить CLS на странице оплаты",
      author: { name: "Майя Романова", handle: "@mromanova", initials: "МР" },
      created: "2026-08-20T13:47:00+03:00",
      updated: "2026-08-21T15:50:00+03:00",
      source: "perf/checkout-cls",
      status: "review",
      pipeline: "passed",
      changes: 14,
      comments: 6,
      unresolved: 0,
      labels: ["performance", "checkout"],
      summary: "Для итоговой суммы и виджета оплаты заранее резервируется место. Нужна проверка на Safari.",
      checks: [
        { label: "Pipeline", state: "ok", detail: "74 теста пройдено" },
        { label: "Обсуждения", state: "ok", detail: "все закрыты" },
        { label: "Review", state: "warn", detail: "ожидает 1 ревьюера" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Лена Воронова", initials: "ЛВ", state: "waiting", note: "Назначена 2 часа назад" }
      ],
      threads: []
    },
    {
      iid: 1816,
      title: "Перенести расчёт скидки в pricing-service",
      author: { name: "Артур Пак", handle: "@apak", initials: "АП" },
      created: "2026-08-12T16:22:00+03:00",
      updated: "2026-08-21T14:36:00+03:00",
      source: "refactor/pricing-discounts",
      status: "ready",
      pipeline: "passed",
      changes: 27,
      comments: 29,
      unresolved: 0,
      labels: ["backend", "pricing"],
      summary: "Единый расчёт скидки используется корзиной, чекаутом и предварительным счётом. MR готов к слиянию.",
      checks: [
        { label: "Pipeline", state: "ok", detail: "183 теста пройдено" },
        { label: "Обсуждения", state: "ok", detail: "все закрыты" },
        { label: "Review", state: "ok", detail: "2 из 2 одобрений" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Олег Ким", initials: "ОК", state: "approved", note: "Одобрил сегодня" },
        { name: "Кирилл Носов", initials: "КН", state: "approved", note: "Одобрил вчера" }
      ],
      threads: []
    },
    {
      iid: 1847,
      title: "Черновик нового поиска по заказам",
      author: { name: "Антон Белых", handle: "@abelyh", initials: "АБ" },
      created: "2026-08-21T08:30:00+03:00",
      updated: "2026-08-21T13:28:00+03:00",
      source: "draft/orders-search-v2",
      status: "draft",
      pipeline: "passed",
      changes: 22,
      comments: 3,
      unresolved: 0,
      labels: ["frontend", "search"],
      summary: "Черновой вариант поиска с подсветкой совпадений и сохранением последних запросов.",
      checks: [
        { label: "Pipeline", state: "ok", detail: "58 тестов пройдено" },
        { label: "Обсуждения", state: "ok", detail: "нет открытых веток" },
        { label: "Review", state: "warn", detail: "ревью не запрошено" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [],
      threads: []
    },
    {
      iid: 1831,
      title: "Добавить аудит экспорта пользовательских данных",
      author: { name: "Саша Юдин", handle: "@syudin", initials: "СЮ" },
      created: "2026-08-16T12:08:00+03:00",
      updated: "2026-08-21T12:17:00+03:00",
      source: "feat/export-audit-log",
      status: "blocked",
      pipeline: "passed",
      changes: 16,
      comments: 18,
      unresolved: 1,
      labels: ["backend", "security"],
      summary: "Каждая выгрузка записывает инициатора, основание и объём данных. Security review запросил маскирование IP.",
      checks: [
        { label: "Pipeline", state: "ok", detail: "112 тестов пройдено" },
        { label: "Обсуждения", state: "error", detail: "1 ветка не закрыта" },
        { label: "Review", state: "warn", detail: "1 из 2 одобрений" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Артур Пак", initials: "АП", state: "approved", note: "Одобрил вчера" },
        { name: "Даша Ильина", initials: "ДИ", state: "changes", note: "Запросила маскирование IP" }
      ],
      threads: [
        { author: "Даша Ильина", time: "11:54", text: "Полный IP в журнале не нужен. Оставим сеть /24 и срок хранения 30 дней." }
      ]
    },
    {
      iid: 1840,
      title: "Обновить тексты пустых состояний",
      author: { name: "Ира Соколова", handle: "@isokolova", initials: "ИС" },
      created: "2026-08-19T15:12:00+03:00",
      updated: "2026-08-21T11:42:00+03:00",
      source: "content/empty-states",
      status: "ready",
      pipeline: "passed",
      changes: 7,
      comments: 5,
      unresolved: 0,
      labels: ["content", "frontend"],
      summary: "Тексты объясняют причину пустого состояния и доступное действие. Все проверки завершены.",
      checks: [
        { label: "Pipeline", state: "ok", detail: "44 теста пройдено" },
        { label: "Обсуждения", state: "ok", detail: "все закрыты" },
        { label: "Review", state: "ok", detail: "2 из 2 одобрений" },
        { label: "Конфликты", state: "ok", detail: "нет" }
      ],
      reviewers: [
        { name: "Майя Романова", initials: "МР", state: "approved", note: "Одобрила сегодня" },
        { name: "Лена Воронова", initials: "ЛВ", state: "approved", note: "Одобрила сегодня" }
      ],
      threads: []
    }
  ]
};
