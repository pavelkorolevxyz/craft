/* Автоматическая офлайн-подсветка блоков <pre class="code">.
   Highlight.js красит синтаксис, этот слой отвечает за строки и акцент. */

(() => {
  if (!window.hljs) return;

  document.querySelectorAll('pre.code').forEach((pre) => {
    const code = pre.querySelector('code');
    if (!code || code.dataset.highlighted) return;

    const language = pre.dataset.language || code.dataset.language;
    const markedLines = new Set(
      (pre.dataset.highlightLines || '')
        .split(',')
        .flatMap((part) => {
          const [from, to = from] = part.trim().split('-').map(Number);
          if (!Number.isFinite(from) || !Number.isFinite(to)) return [];
          return Array.from({ length: Math.max(0, to - from + 1) }, (_, i) => from + i);
        }),
    );

    const source = code.textContent.replace(/^\n|\n$/g, '');
    const lines = source.split('\n');

    code.innerHTML = lines.map((line, index) => {
      let html;
      try {
        html = language
          ? hljs.highlight(line, { language, ignoreIllegals: true }).value
          : hljs.highlightAuto(line).value;
      } catch {
        html = line
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;');
      }

      const number = index + 1;
      const highlighted = markedLines.has(number) ? ' is-highlighted' : '';
      return `<span class="code-line${highlighted}" data-line="${number}">${html || ' '}</span>`;
    }).join('');

    code.dataset.highlighted = 'true';
  });
})();
