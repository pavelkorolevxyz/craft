/* Один исходный фрагмент повторно используется на нескольких слайдах с разным фокусом. */
(() => {
  document.querySelectorAll('pre[data-code-source]').forEach((pre) => {
    const source = document.getElementById(`code-${pre.dataset.codeSource}`);
    const code = pre.querySelector('code');
    if (!source || !code) return;
    code.textContent = source.textContent.replace(/^\n|\n$/g, '');
  });
})();
