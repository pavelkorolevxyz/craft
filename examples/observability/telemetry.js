/* Модель телеметрии: детерминированный генератор рядов для демонстрации дашборда.
   Значения вычисляются функцией от времени, поэтому любой диапазон и любое
   разрешение согласованы между собой, а данные не хранятся в памяти. */
const Telemetry = (() => {
  const SEC = 1000;
  const MIN = 60 * SEC;
  const HOUR = 60 * MIN;
  const DAY = 24 * HOUR;

  const ORIGIN = Date.now();
  const INCIDENT_START = ORIGIN - 2 * HOUR - 12 * MIN;
  const INCIDENT_END = INCIDENT_START + 19 * MIN;
  const DEPLOY_AT = INCIDENT_START - 4 * MIN;
  const ROLLBACK_AT = INCIDENT_END - 3 * MIN;

  /* Хеш строки и целого числа в диапазон [0, 1). */
  function hash(seed, index) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < seed.length; i += 1) {
      h = Math.imul(h ^ seed.charCodeAt(i), 16777619) >>> 0;
    }
    h = Math.imul(h ^ (index & 0xffff), 2246822519) >>> 0;
    h = Math.imul(h ^ (index >>> 16), 3266489917) >>> 0;
    h ^= h >>> 15;
    return (h >>> 0) / 4294967296;
  }

  function smooth(x) {
    return x * x * (3 - 2 * x);
  }

  /* Плавный шум с интерполяцией между узлами решётки заданного периода. */
  function noise(seed, t, period) {
    const p = t / period;
    const i = Math.floor(p);
    const f = smooth(p - i);
    return hash(seed, i) * (1 - f) + hash(seed, i + 1) * f;
  }

  /* Сумма октав: медленная база плюс мелкие колебания. */
  function fbm(seed, t, period) {
    return (
      noise(seed, t, period) * 0.6 +
      noise(seed + "-2", t, period / 3) * 0.28 +
      noise(seed + "-3", t, period / 9) * 0.12
    ) * 2 - 1;
  }

  /* Суточный профиль нагрузки с провалом ночью и спадом в выходные. */
  function seasonal(t) {
    const d = new Date(t);
    const hour = d.getHours() + d.getMinutes() / 60;
    const daily = 0.58 + 0.42 * Math.sin(((hour - 7.5) / 24) * 2 * Math.PI);
    const weekend = d.getDay() === 0 || d.getDay() === 6 ? 0.72 : 1;
    return Math.max(0.2, daily) * weekend;
  }

  /* Форма инцидента: быстрый рост, плато, спад после отката. */
  function incident(t) {
    if (t < INCIDENT_START || t > INCIDENT_END) return 0;
    const rise = Math.min(1, (t - INCIDENT_START) / (3 * MIN));
    const fall = t < ROLLBACK_AT ? 1 : Math.max(0, 1 - (t - ROLLBACK_AT) / (4 * MIN));
    return rise * fall;
  }

  const SERVICES = [
    { key: "gate", label: "Шлюз", base: 1180, tone: "neutral" },
    { key: "store", label: "Витрина", base: 760, tone: "cool" },
    { key: "jobs", label: "Обработчик", base: 235, tone: "warm" },
    { key: "search", label: "Поиск", base: 305, tone: "good" },
  ];

  const NODES = [
    { key: "n1", label: "узел-1", base: 46 },
    { key: "n2", label: "узел-2", base: 52 },
    { key: "n3", label: "узел-3", base: 41 },
  ];

  const ENDPOINTS = [
    { path: "/v1/orders", share: 0.26, latency: 1.45, errors: 3.2, service: "Шлюз" },
    { path: "/v1/catalog", share: 0.23, latency: 0.72, errors: 0.6, service: "Витрина" },
    { path: "/v1/search", share: 0.17, latency: 1.9, errors: 1.1, service: "Поиск" },
    { path: "/v1/cart", share: 0.14, latency: 0.95, errors: 1.8, service: "Шлюз" },
    { path: "/v1/profile", share: 0.11, latency: 0.64, errors: 0.4, service: "Витрина" },
    { path: "/internal/jobs", share: 0.09, latency: 2.6, errors: 0.9, service: "Обработчик" },
  ];

  function rps(key, t) {
    const service = SERVICES.find((item) => item.key === key);
    let value = service.base * seasonal(t) * (1 + 0.11 * fbm("rps-" + key, t, 9 * MIN));
    if (key === "gate") value *= 1 - 0.42 * incident(t);
    if (key === "jobs") value *= 1 + 0.3 * incident(t);
    return Math.max(0, value);
  }

  function rpsTotal(t) {
    return SERVICES.reduce((sum, service) => sum + rps(service.key, t), 0);
  }

  function p50(t) {
    return 38 + 7 * fbm("p50", t, 7 * MIN) + 26 * incident(t);
  }

  function p95(t) {
    return p50(t) * (2.35 + 0.25 * fbm("p95", t, 11 * MIN)) + 470 * incident(t);
  }

  function p99(t) {
    return p95(t) * (1.6 + 0.2 * fbm("p99", t, 5 * MIN)) + 900 * incident(t);
  }

  function errors4xx(t) {
    return rpsTotal(t) * 0.0115 * (1 + 0.35 * fbm("e4", t, 13 * MIN));
  }

  function errors5xx(t) {
    const base = rpsTotal(t) * 0.0008 * (1 + 0.5 * fbm("e5", t, 6 * MIN));
    return base + rpsTotal(t) * 0.085 * incident(t);
  }

  function timeouts(t) {
    const base = rpsTotal(t) * 0.00022 * (1 + 0.6 * fbm("to", t, 8 * MIN));
    return base + rpsTotal(t) * 0.021 * incident(t);
  }

  function cpu(key, t) {
    const node = NODES.find((item) => item.key === key);
    const load = node.base * (0.72 + 0.5 * seasonal(t)) + 9 * fbm("cpu-" + key, t, 6 * MIN);
    const spike = key === "n2" ? 44 * incident(t) : 12 * incident(t);
    return Math.min(100, Math.max(2, load + spike));
  }

  function memory(key, t) {
    return Math.min(100, 54 + NODES.findIndex((item) => item.key === key) * 4 + 6 * fbm("mem-" + key, t, 40 * MIN) + 8 * incident(t));
  }

  const METRICS = {
    "rps.gate": (t) => rps("gate", t),
    "rps.store": (t) => rps("store", t),
    "rps.jobs": (t) => rps("jobs", t),
    "rps.search": (t) => rps("search", t),
    "rps.total": rpsTotal,
    "lat.p50": p50,
    "lat.p95": p95,
    "lat.p99": p99,
    "err.4xx": errors4xx,
    "err.5xx": errors5xx,
    "err.timeout": timeouts,
    "err.share": (t) => (errors5xx(t) + timeouts(t)) / Math.max(1, rpsTotal(t)) * 100,
    "cpu.n1": (t) => cpu("n1", t),
    "cpu.n2": (t) => cpu("n2", t),
    "cpu.n3": (t) => cpu("n3", t),
    "cpu.max": (t) => Math.max(cpu("n1", t), cpu("n2", t), cpu("n3", t)),
    "mem.n1": (t) => memory("n1", t),
    "mem.n2": (t) => memory("n2", t),
    "mem.n3": (t) => memory("n3", t),
  };

  /* Запрос ряда: диапазон делится на равные корзины, значение каждой корзины —
     среднее нескольких выборок модели. Так грубое разрешение согласовано с точным. */
  function query(metric, from, to, points) {
    const fn = METRICS[metric];
    const step = (to - from) / points;
    const subs = Math.min(8, Math.max(1, Math.round(step / (20 * SEC))));
    const t = new Float64Array(points);
    const v = new Float64Array(points);
    for (let i = 0; i < points; i += 1) {
      const start = from + i * step;
      let sum = 0;
      for (let s = 0; s < subs; s += 1) {
        sum += fn(start + (step * (s + 0.5)) / subs);
      }
      t[i] = start + step / 2;
      v[i] = sum / subs;
    }
    return { t, v, step };
  }

  function latest(metric, at) {
    return METRICS[metric](at === undefined ? Date.now() : at);
  }

  /* Среднее значения метрики по диапазону. */
  function average(metric, from, to, points) {
    const series = query(metric, from, to, points || 120);
    let sum = 0;
    for (let i = 0; i < series.v.length; i += 1) sum += series.v[i];
    return sum / series.v.length;
  }

  function erf(x) {
    const sign = x < 0 ? -1 : 1;
    const a = Math.abs(x);
    const tt = 1 / (1 + 0.3275911 * a);
    const y = 1 - ((((1.061405429 * tt - 1.453152027) * tt + 1.421413741) * tt - 0.284496736) * tt + 0.254829592) * tt * Math.exp(-a * a);
    return sign * y;
  }

  function normalCdf(z) {
    return 0.5 * (1 + erf(z / Math.SQRT2));
  }

  const BUCKETS = [0, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, Infinity];

  /* Распределение задержки восстанавливается из p50 и p99 как логнормальное:
     медиана задаёт масштаб, отношение p99/p50 — разброс. */
  function histogram(from, to, columns) {
    const step = (to - from) / columns;
    const grid = [];
    for (let i = 0; i < columns; i += 1) {
      const t = from + step * (i + 0.5);
      const median = Math.max(1, p50(t));
      const tail = Math.max(1.05, p99(t) / median);
      const sigma = Math.log(tail) / 2.3263;
      const column = new Array(BUCKETS.length - 1);
      let previous = 0;
      for (let b = 1; b < BUCKETS.length; b += 1) {
        const edge = BUCKETS[b];
        const cdf = edge === Infinity ? 1 : normalCdf((Math.log(edge) - Math.log(median)) / sigma);
        column[b - 1] = Math.max(0, cdf - previous);
        previous = cdf;
      }
      grid.push({ t, column });
    }
    return { grid, edges: BUCKETS, step };
  }

  function endpoints(from, to) {
    const load = average("rps.total", from, to, 60);
    const latency = average("lat.p95", from, to, 60);
    const errorShare = average("err.share", from, to, 60);
    return ENDPOINTS.map((endpoint) => ({
      path: endpoint.path,
      service: endpoint.service,
      rps: load * endpoint.share,
      p95: latency * endpoint.latency,
      errors: errorShare * endpoint.errors,
      share: endpoint.share,
    }));
  }

  const LOG_TEMPLATES = [
    { level: "info", text: "запрос обработан", detail: "маршрут={path} код=200" },
    { level: "info", text: "фоновая задача завершена", detail: "очередь=выгрузка длительность={ms} мс" },
    { level: "info", text: "кеш обновлён", detail: "ключей={count} источник=витрина" },
    { level: "warn", text: "повторная попытка запроса", detail: "маршрут={path} попытка=2" },
    { level: "warn", text: "очередь растёт", detail: "длина={count} обработчик=узел-3" },
    { level: "error", text: "ответ сервиса не получен", detail: "маршрут={path} причина=таймаут" },
  ];

  const INCIDENT_LOGS = [
    { level: "error", text: "пул соединений исчерпан", detail: "узел=узел-2 ожидание={ms} мс" },
    { level: "error", text: "ошибка обращения к хранилищу", detail: "маршрут={path} код=503" },
    { level: "warn", text: "превышен порог задержки", detail: "p99={ms} мс порог=500 мс" },
  ];

  /* Журнал строится детерминированно: на каждую минуту диапазона приходится
     от нуля до нескольких записей, во время инцидента их заметно больше. */
  function logs(from, to, limit) {
    const entries = [];
    const startMinute = Math.floor(from / MIN);
    const endMinute = Math.ceil(to / MIN);
    for (let minute = endMinute; minute >= startMinute && entries.length < limit * 3; minute -= 1) {
      const t = minute * MIN;
      const hot = incident(t) > 0.15;
      const count = hot ? 3 + Math.floor(hash("log-n" + minute, minute) * 4) : Math.floor(hash("log-n" + minute, minute) * 2.4);
      for (let i = 0; i < count; i += 1) {
        const pick = hash("log-p" + minute, i);
        const source = hot && pick < 0.62 ? INCIDENT_LOGS : LOG_TEMPLATES;
        const template = source[Math.floor(hash("log-t" + minute, i) * source.length)];
        const endpoint = ENDPOINTS[Math.floor(hash("log-e" + minute, i) * ENDPOINTS.length)];
        const at = t + Math.floor(hash("log-s" + minute, i) * 60) * SEC;
        if (at > to || at < from) continue;
        entries.push({
          at,
          level: template.level,
          text: template.text,
          detail: template.detail
            .replace("{path}", endpoint.path)
            .replace("{ms}", String(Math.round(50 + hash("log-m" + minute, i) * (hot ? 1800 : 320))))
            .replace("{count}", String(Math.round(12 + hash("log-c" + minute, i) * 400))),
          service: endpoint.service,
        });
      }
    }
    entries.sort((a, b) => b.at - a.at);
    return entries.slice(0, limit);
  }

  const ANNOTATIONS = [
    { at: DEPLOY_AT, kind: "deploy", label: "Выкладка 4.18.2", note: "шлюз, 3 узла" },
    { at: INCIDENT_START + 2 * MIN, kind: "alert", label: "Сработало правило «5xx выше 1%»", note: "окно 5 мин" },
    { at: ROLLBACK_AT, kind: "deploy", label: "Откат на 4.18.1", note: "шлюз, 3 узла" },
    { at: INCIDENT_END + 3 * MIN, kind: "resolve", label: "Правило «5xx выше 1%» снято", note: "восстановление 3 мин" },
  ];

  function annotations(from, to) {
    return ANNOTATIONS.filter((item) => item.at >= from && item.at <= to);
  }

  return {
    SERVICES,
    NODES,
    ENDPOINTS,
    ORIGIN,
    INCIDENT_START,
    INCIDENT_END,
    query,
    latest,
    average,
    histogram,
    endpoints,
    logs,
    annotations,
    units: { MIN, HOUR, DAY },
  };
})();
