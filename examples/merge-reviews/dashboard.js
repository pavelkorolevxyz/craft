(() => {
  "use strict";

  const data = window.MERGE_REVIEW_DATA;
  const capturedAt = new Date(data.generatedAt);
  const state = {
    filter: "all",
    query: "",
    sort: "updated",
    selected: Number(location.hash.replace("#mr-", "")) || data.items[0].iid,
  };

  const list = document.getElementById("queue-list");
  const empty = document.getElementById("empty-state");
  const search = document.getElementById("search");
  const sort = document.getElementById("sort");
  const toast = document.getElementById("toast");
  const statusLabels = {
    blocked: ["блокер", "error"],
    ready: ["готов к слиянию", "ok"],
    review: ["на ревью", "neutral"],
    draft: ["черновик", "draft"],
  };
  const pipelineLabels = { passed: "pipeline пройден", running: "pipeline выполняется", failed: "pipeline упал" };
  const reviewLabels = { approved: "Одобрено", changes: "Есть замечания", waiting: "Ожидается" };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function icon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", `#icon-${name}`);
    svg.append(use);
    return svg;
  }

  function plural(value, one, few, many) {
    const mod10 = value % 10;
    const mod100 = value % 100;
    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
    return many;
  }

  function age(iso) {
    const hours = Math.max(1, Math.round((capturedAt - new Date(iso)) / 3600000));
    if (hours < 24) return `${hours} ${plural(hours, "час", "часа", "часов")}`;
    const days = Math.round(hours / 24);
    return `${days} ${plural(days, "день", "дня", "дней")}`;
  }

  function matches(item) {
    const filterMatch = state.filter === "all" || item.status === state.filter;
    const haystack = `${item.iid} ${item.title} ${item.author.name} ${item.author.handle} ${item.labels.join(" ")}`.toLocaleLowerCase("ru");
    return filterMatch && haystack.includes(state.query.toLocaleLowerCase("ru").trim());
  }

  function visibleItems() {
    const items = data.items.filter(matches);
    if (state.sort === "oldest") items.sort((a, b) => new Date(a.created) - new Date(b.created));
    if (state.sort === "comments") items.sort((a, b) => b.comments - a.comments);
    if (state.sort === "updated") items.sort((a, b) => new Date(b.updated) - new Date(a.updated));
    return items;
  }

  function statusNode(item) {
    const [label, tone] = statusLabels[item.status];
    return element("span", `status status--${tone} review-status`, label);
  }

  function pipelineNode(item) {
    const node = element("span", "build-status");
    node.dataset.state = item.pipeline;
    node.setAttribute("aria-label", pipelineLabels[item.pipeline]);
    node.title = pipelineLabels[item.pipeline];
    const iconName = item.pipeline === "passed" ? "check" : item.pipeline === "running" ? "clock" : "x";
    node.append(icon(iconName));
    return node;
  }

  function renderMetrics() {
    ["all", "blocked", "review", "ready", "draft"].forEach((key) => {
      const count = key === "all" ? data.items.length : data.items.filter((item) => item.status === key).length;
      document.getElementById(`count-${key}`).textContent = count;
    });
  }

  function renderQueue() {
    const items = visibleItems();
    list.replaceChildren();
    empty.hidden = items.length > 0;
    list.hidden = items.length === 0;
    document.getElementById("result-count").textContent = `${items.length} ${plural(items.length, "результат", "результата", "результатов")}`;

    if (items.length && !items.some((item) => item.iid === state.selected)) state.selected = items[0].iid;

    items.forEach((item) => {
      const row = element("button", "mr-row");
      row.type = "button";
      row.role = "option";
      row.dataset.iid = item.iid;
      row.setAttribute("aria-selected", String(item.iid === state.selected));
      row.setAttribute("aria-label", `MR ${item.iid}: ${item.title}`);

      const main = element("span", "mr-row__main");
      const titleLine = element("span", "mr-row__line");
      titleLine.append(element("span", "mr-row__id", `!${item.iid}`), element("span", "mr-row__title", item.title));
      const meta = element("span", "mr-row__meta");
      meta.append(element("span", "avatar", item.author.initials), element("span", "", item.author.name), element("span", "", `открыт ${age(item.created)} назад`));
      item.labels.slice(0, 2).forEach((label) => meta.append(element("span", "label", label)));
      main.append(titleLine, meta);

      row.append(main, statusNode(item), pipelineNode(item));
      row.addEventListener("click", () => selectItem(item.iid, true));
      const entry = element("div", "mr-entry");
      entry.dataset.selected = String(item.iid === state.selected);
      entry.append(element("span", "selection-rail"), row);
      list.append(entry);
    });
    renderDetail();
  }

  function selectItem(iid, focusRow) {
    state.selected = iid;
    try { history.replaceState(null, "", `#mr-${iid}`); } catch (error) { location.hash = `mr-${iid}`; }
    list.querySelectorAll(".mr-row").forEach((row) => {
      const selected = Number(row.dataset.iid) === iid;
      row.setAttribute("aria-selected", String(selected));
      row.closest(".mr-entry").dataset.selected = String(selected);
    });
    renderDetail();
    if (focusRow) list.querySelector(`[data-iid="${iid}"]`)?.focus();
  }

  function renderDetail() {
    const item = data.items.find((entry) => entry.iid === state.selected);
    if (!item) return;
    document.getElementById("detail-kicker").textContent = `Merge request !${item.iid} · открыт ${age(item.created)} назад`;
    document.getElementById("detail-title").textContent = item.title;
    const statusHost = document.getElementById("detail-status");
    statusHost.replaceChildren(statusNode(item));
    const host = document.getElementById("detail-content");
    host.replaceChildren(summarySection(item), checksSection(item), reviewersSection(item), threadsSection(item), actionsSection(item));
  }

  function summarySection(item) {
    const section = element("section", "detail-section");
    section.append(element("p", "detail-summary", item.summary));
    const meta = element("div", "detail-meta");
    [["Изменения", item.changes], ["Комментарии", item.comments], ["Открытые ветки", item.unresolved]].forEach(([label, value]) => {
      const cell = element("div");
      cell.append(element("span", "", label), element("strong", "", String(value)));
      meta.append(cell);
    });
    const branch = element("div", "branch");
    const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icon.setAttribute("class", "icon");
    icon.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#icon-branch");
    icon.append(use);
    branch.append(icon, element("code", "", item.source), document.createTextNode("в main"));
    section.append(meta, branch);
    return section;
  }

  function checksSection(item) {
    const section = element("section", "detail-section");
    section.append(element("h3", "", "Готовность к слиянию"));
    const ul = element("ul", "check-list");
    item.checks.forEach((check) => {
      const li = element("li");
      const mark = element("strong", "state-dot check-mark", check.label);
      mark.dataset.state = check.state;
      li.append(mark, element("span", "", check.detail));
      ul.append(li);
    });
    section.append(ul);
    return section;
  }

  function reviewersSection(item) {
    const section = element("section", "detail-section");
    section.append(element("h3", "", "Ревьюеры"));
    if (!item.reviewers.length) {
      section.append(element("p", "thread-empty", "Ревью пока не запрошено."));
      return section;
    }
    const ul = element("ul", "reviewers");
    item.reviewers.forEach((reviewer) => {
      const li = element("li");
      const copy = element("span", "reviewer-copy");
      copy.append(element("strong", "", reviewer.name), element("span", "", reviewer.note));
      const reviewState = element("span", "state-dot review-state", reviewLabels[reviewer.state]);
      reviewState.dataset.state = reviewer.state;
      li.append(element("span", "avatar", reviewer.initials), copy, reviewState);
      ul.append(li);
    });
    section.append(ul);
    return section;
  }

  function threadsSection(item) {
    const section = element("section", "detail-section");
    section.append(element("h3", "", "Последнее обсуждение"));
    if (!item.threads.length) {
      section.append(element("p", "thread-empty", "Открытых обсуждений нет."));
      return section;
    }
    const ul = element("ul", "threads");
    item.threads.forEach((thread) => {
      const li = element("li");
      const head = element("div", "thread-head");
      head.append(element("strong", "", thread.author), element("time", "", thread.time));
      li.append(head, element("p", "", thread.text));
      ul.append(li);
    });
    section.append(ul);
    return section;
  }

  function actionsSection(item) {
    const section = element("div", "detail-actions");
    const copy = element("button", "button button--primary", "Скопировать сводку");
    copy.type = "button";
    copy.addEventListener("click", async () => {
      const text = `!${item.iid} ${item.title}\n${statusLabels[item.status][0]} · ${item.comments} комментариев · ${item.unresolved} открытых обсуждений\n${item.summary}`;
      try {
        await navigator.clipboard.writeText(text);
        showToast("Сводка скопирована");
      } catch (error) {
        showToast("Буфер обмена недоступен");
      }
    });
    section.append(copy);
    return section;
  }

  let toastTimer;
  function showToast(message) {
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.dataset.open = "true";
    toastTimer = setTimeout(() => { toast.dataset.open = "false"; }, 1800);
  }

  function moveSelection(direction) {
    const items = visibleItems();
    if (!items.length) return;
    const current = items.findIndex((item) => item.iid === state.selected);
    const index = current < 0 ? 0 : (current + direction + items.length) % items.length;
    selectItem(items[index].iid, false);
  }

  document.querySelectorAll('input[name="filter"]').forEach((input) => {
    input.addEventListener("change", () => {
      state.filter = input.value;
      renderQueue();
    });
  });
  search.addEventListener("input", () => {
    state.query = search.value;
    renderQueue();
  });
  sort.addEventListener("change", () => {
    state.sort = sort.value;
    renderQueue();
  });
  document.getElementById("reset-filters").addEventListener("click", () => {
    state.filter = "all";
    state.query = "";
    search.value = "";
    document.querySelector('input[name="filter"][value="all"]').checked = true;
    renderQueue();
  });

  document.addEventListener("keydown", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const typing = target?.matches("input, select, textarea, [contenteditable]");
    if (event.key === "/" && !typing) {
      event.preventDefault();
      search.focus();
      return;
    }
    if (typing || event.repeat) return;
    if (event.code === "KeyJ") moveSelection(1);
    if (event.code === "KeyK") moveSelection(-1);
  });

  document.getElementById("next-mr").addEventListener("click", () => moveSelection(1));

  const themeButton = document.getElementById("theme");
  const systemTheme = matchMedia("(prefers-color-scheme: light)");
  function syncThemeButton() {
    themeButton.setAttribute("aria-pressed", String(document.documentElement.dataset.theme === "light"));
  }
  themeButton.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    document.documentElement.dataset.themeSource = "saved";
    try { localStorage.setItem("review-theme", next); } catch (error) { /* Хранилище необязательно. */ }
    syncThemeButton();
  });
  systemTheme.addEventListener("change", (event) => {
    if (document.documentElement.dataset.themeSource !== "system") return;
    document.documentElement.dataset.theme = event.matches ? "light" : "dark";
    syncThemeButton();
  });

  renderMetrics();
  renderQueue();
  syncThemeButton();
})();
