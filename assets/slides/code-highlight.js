/* Automatic offline highlighting for <pre class="code"> blocks.
   Highlight.js colors the syntax, this layer handles lines and the accent. */

(() => {
  if (!window.hljs) return;

  // Typing a command. Lines listed in data-run-commands (the first one by
  // default) type out letter by letter, the other lines appear one by one
  // after their command. This script computes the delays, the theme sets the motion.
  const TYPE_STEP = 40;
  const AFTER_COMMAND = 300;
  const LINE_STEP = 150;
  function markRun(pre, code, lines) {
    const commands = new Set(
      (pre.dataset.runCommands || '1').split(',').map((value) => Number(value.trim())).filter(Number.isFinite),
    );
    let time = 200;
    code.querySelectorAll('.code-line').forEach((line, index) => {
      const number = index + 1;
      if (commands.has(number)) {
        const chars = lines[index].length;
        line.innerHTML = `<span class="run-type" style="--chars:${chars};--run-delay:${time}ms">${line.innerHTML}</span>`;
        time += chars * TYPE_STEP + AFTER_COMMAND;
      } else {
        line.classList.add('is-output');
        line.style.setProperty('--run-delay', `${time}ms`);
        time += LINE_STEP;
      }
    });
  }

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

    if (pre.classList.contains('code-run')) markRun(pre, code, lines);
    code.dataset.highlighted = 'true';
  });
})();
