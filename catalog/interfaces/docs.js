(() => {
  const escapeHtml = (value) => value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

  const escapeMarkup = (value) => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const escapeAttribute = (value) => escapeMarkup(value).replaceAll('"', "&quot;");
  const voidElements = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]);

  const formatNode = (node, depth = 0) => {
    const indent = "  ".repeat(depth);
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent.trim();
      return text ? `${indent}${escapeMarkup(text)}` : "";
    }
    if (node.nodeType === Node.COMMENT_NODE) return `${indent}<!--${node.textContent}-->`;
    if (node.nodeType !== Node.ELEMENT_NODE) return "";

    const name = node.localName;
    const attributes = [...node.attributes]
      .map((attribute) => ` ${attribute.name}="${escapeAttribute(attribute.value)}"`)
      .join("");
    const opening = `<${name}${attributes}>`;
    if (voidElements.has(name)) return `${indent}${opening}`;

    const children = [...node.childNodes].filter((child) => child.nodeType !== Node.TEXT_NODE || child.textContent.trim());
    if (!children.length) return `${indent}${opening}</${name}>`;
    if (children.length === 1 && children[0].nodeType === Node.TEXT_NODE) {
      return `${indent}${opening}${escapeMarkup(children[0].textContent.trim())}</${name}>`;
    }

    const content = children.map((child) => formatNode(child, depth + 1)).filter(Boolean).join("\n");
    return `${indent}${opening}\n${content}\n${indent}</${name}>`;
  };

  const formatPreview = (preview) => [...preview.childNodes]
    .map((node) => formatNode(node))
    .filter(Boolean)
    .join("\n");

  /* The system code-highlight.js colors the listing, so the catalog shows
     the same classes a code block gets in a project. */
  const highlightHtml = (source) => window.CraftCode ? window.CraftCode.highlight(source, "html") : escapeHtml(source);

  const revealCurrentNavigation = () => {
    const currentNavigation = document.querySelector(".docs-nav .system-links [aria-current='true']");
    if (!currentNavigation || !matchMedia("(max-width: 900px)").matches) return;
    const links = currentNavigation.parentElement;
    links.scrollLeft = currentNavigation.offsetLeft - (links.clientWidth - currentNavigation.clientWidth) / 2;
  };
  revealCurrentNavigation();
  document.fonts?.ready.then(revealCurrentNavigation);

  /* The navigation sample has nothing to observe because the sample page does
     not exist. A click on a link moves the marker and aria-current, so the
     behavior is visible right in the catalog. The sample markup stays production markup. */
  document.querySelectorAll("[data-preview] [data-section-nav]").forEach((container) => {
    const links = [...container.querySelectorAll("a")];
    for (const link of links) {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        for (const other of links) other.removeAttribute("aria-current");
        link.setAttribute("aria-current", "true");
        container.style.setProperty("--nav-marker-y", `${link.offsetTop}px`);
        container.style.setProperty("--nav-marker-h", `${link.offsetHeight}px`);
        container.style.setProperty("--nav-marker-x", `${link.offsetLeft}px`);
        container.style.setProperty("--nav-marker-w", `${link.offsetWidth}px`);
        container.setAttribute("data-nav-marker", "");
      });
    }
  });

  document.querySelectorAll("[data-foundation-doc], [data-component-doc], [data-recipe-doc]").forEach((article) => {
    const preview = article.querySelector("[data-preview]");
    const output = article.querySelector("[data-preview-code]");
    if (!preview || !output) return;
    output.classList.add("language-html");
    output.innerHTML = highlightHtml(formatPreview(preview));
  });
})();
