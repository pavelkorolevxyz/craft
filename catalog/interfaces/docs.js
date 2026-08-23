(() => {
  const dedent = (value) => {
    const lines = value.replace(/^\n+|\s+$/g, "").split("\n");
    const indents = lines.filter((line) => line.trim()).map((line) => line.match(/^\s*/)[0].length);
    const indent = indents.length ? Math.min(...indents) : 0;
    return lines.map((line) => line.slice(indent)).join("\n");
  };

  document.querySelectorAll("[data-component-doc], [data-recipe-doc]").forEach((article) => {
    const preview = article.querySelector("[data-preview]");
    const output = article.querySelector("[data-preview-code]");
    if (!preview || !output) return;
    output.textContent = dedent(preview.innerHTML);
  });
})();
