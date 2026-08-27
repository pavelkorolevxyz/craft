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

  const token = (name, value) => `<span class="syntax-${name}">${escapeHtml(value)}</span>`;

  const highlightTag = (source) => {
    if (source.startsWith("<!--")) return token("comment", source);
    if (/^<!doctype/i.test(source)) return token("doctype", source);

    let index = 0;
    let output = "";
    let expectsName = true;
    let expectsValue = false;

    while (index < source.length) {
      const rest = source.slice(index);
      const punctuation = rest.match(/^(<\/?|\/?>|=)/);
      const whitespace = rest.match(/^\s+/);
      const quoted = rest.match(/^("[^"]*"|'[^']*')/);
      const word = rest.match(/^[^\s=/>]+/);

      if (whitespace) {
        output += whitespace[0];
        index += whitespace[0].length;
      } else if (punctuation) {
        output += token("punctuation", punctuation[0]);
        expectsName = punctuation[0] === "<" || punctuation[0] === "</";
        expectsValue = punctuation[0] === "=";
        index += punctuation[0].length;
      } else if (quoted) {
        output += token(expectsValue ? "string" : "attr", quoted[0]);
        expectsValue = false;
        index += quoted[0].length;
      } else if (word) {
        output += token(expectsName ? "tag" : expectsValue ? "string" : "attr", word[0]);
        expectsName = false;
        expectsValue = false;
        index += word[0].length;
      } else {
        output += escapeHtml(source[index]);
        index += 1;
      }
    }

    return output;
  };

  const highlightHtml = (source) => {
    let index = 0;
    let output = "";

    while (index < source.length) {
      if (source.startsWith("<!--", index)) {
        const end = source.indexOf("-->", index + 4);
        const next = end === -1 ? source.length : end + 3;
        output += highlightTag(source.slice(index, next));
        index = next;
        continue;
      }

      if (source[index] !== "<") {
        const next = source.indexOf("<", index);
        const end = next === -1 ? source.length : next;
        output += escapeHtml(source.slice(index, end));
        index = end;
        continue;
      }

      let end = index + 1;
      let quote = "";
      while (end < source.length) {
        const character = source[end];
        if (quote) {
          if (character === quote) quote = "";
        } else if (character === '"' || character === "'") {
          quote = character;
        } else if (character === ">") {
          end += 1;
          break;
        }
        end += 1;
      }
      output += highlightTag(source.slice(index, end));
      index = end;
    }

    return output;
  };

  const revealCurrentNavigation = () => {
    const currentNavigation = document.querySelector(".docs-nav .system-links [aria-current='true']");
    if (!currentNavigation || !matchMedia("(max-width: 900px)").matches) return;
    const links = currentNavigation.parentElement;
    links.scrollLeft = currentNavigation.offsetLeft - (links.clientWidth - currentNavigation.clientWidth) / 2;
  };
  revealCurrentNavigation();
  document.fonts?.ready.then(revealCurrentNavigation);

  /* Витрине навигации нечего наблюдать: страницы примера не существует.
     Клик по ссылке переносит отметку и метку, чтобы поведение читалось
     прямо в каталоге. Разметка примера остаётся боевой. */
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

  document.querySelectorAll("[data-component-doc], [data-recipe-doc]").forEach((article) => {
    const preview = article.querySelector("[data-preview]");
    const output = article.querySelector("[data-preview-code]");
    if (!preview || !output) return;
    output.classList.add("language-html");
    output.innerHTML = highlightHtml(formatPreview(preview));
  });
})();
