const formatTokenValue = (value) => {
  if (!value.startsWith('rgb')) return value;
  const channels = value.match(/[\d.]+/g)?.map(Number) || [];
  if (channels.length < 3) return value;
  const hex = `#${channels.slice(0, 3).map((channel) => Math.round(channel).toString(16).padStart(2, '0')).join('')}`;
  // Тихие роли заданы прозрачностью, и доля важна: она объясняет, почему
  // тот же токен на красном фоне выглядит иначе, чем на фоне страницы.
  const alpha = channels.length > 3 ? channels[3] : 1;
  return alpha < 1 ? `${hex} · ${Math.round(alpha * 100)}%` : hex;
};

const syncTokenValues = () => {
  const styles = getComputedStyle(document.documentElement);
  document.querySelectorAll('[data-token-value]').forEach((element) => {
    const value = styles.getPropertyValue(element.dataset.tokenValue).trim();
    element.textContent = formatTokenValue(value);
  });
};

syncTokenValues();
addEventListener('craft-themechange', syncTokenValues);

const queueRows = [...document.querySelectorAll('.queue-row')];
const queueDetail = {
  title: document.querySelector('[data-queue-title]'),
  summary: document.querySelector('[data-queue-summary]'),
  group: document.querySelector('[data-queue-group]'),
  state: document.querySelector('[data-queue-state]'),
};

const selectQueueRow = (selected) => {
  for (const row of queueRows) row.setAttribute('aria-pressed', String(row === selected));
  queueDetail.title.textContent = selected.dataset.title;
  queueDetail.summary.textContent = selected.dataset.summary;
  queueDetail.group.textContent = selected.dataset.group;
  queueDetail.state.textContent = selected.dataset.state;
};

queueRows.forEach((row) => row.addEventListener('click', () => selectQueueRow(row)));

/* Частично выбранную группу нельзя выразить разметкой: состояние ставится
   механикой каталога. */
for (const box of document.querySelectorAll("[data-catalog-mixed]")) box.indeterminate = true;
