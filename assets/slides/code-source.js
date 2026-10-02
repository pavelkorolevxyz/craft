/* One source snippet is reused on several slides with a different focus on each. */
(() => {
  document.querySelectorAll('pre[data-code-source]').forEach((pre) => {
    const source = document.getElementById(`code-${pre.dataset.codeSource}`);
    const code = pre.querySelector('code');
    if (!source || !code) return;
    code.textContent = source.textContent.replace(/^\n|\n$/g, '');
  });
})();
