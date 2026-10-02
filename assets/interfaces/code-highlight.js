/* Offline syntax highlighting for code blocks. No network, no library. Small
   rule sets mark up HTML, CSS, JavaScript, JSON and shell, and the syntax-*
   classes from theme.css set the colors.

   The language comes from class="language-..." or data-language on code or pre.
   Without an explicit language the script guesses it from the first character
   and the content. The text stays the same, so copy and search see the source.

   Another script can color a string itself. window.CraftCode.highlight(text, "html")
   returns safe HTML. */
(() => {
  "use strict";

  const CLASS = {
    tag: "syntax-tag",
    keyword: "syntax-keyword",
    attr: "syntax-attr",
    string: "syntax-string",
    number: "syntax-number",
    comment: "syntax-comment",
    doctype: "syntax-doctype",
    punctuation: "syntax-punctuation",
  };

  const escape = (value) => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const token = (kind, value) => (value ? `<span class="${CLASS[kind]}">${escape(value)}</span>` : "");

  /* Shared pass over the rules. At each position the first matching rule
     wins, and the rest of the text goes through unchanged. */
  function scan(source, rules) {
    const sticky = rules.map(([pattern, kind]) => [new RegExp(pattern.source, `${pattern.flags.replace("g", "")}y`), kind]);
    let index = 0;
    let output = "";
    let plain = "";
    while (index < source.length) {
      let matched = false;
      for (const [pattern, kind] of sticky) {
        pattern.lastIndex = index;
        const match = pattern.exec(source);
        if (!match || !match[0]) continue;
        output += escape(plain);
        plain = "";
        output += typeof kind === "function" ? kind(match, source, index) : kind ? token(kind, match[0]) : escape(match[0]);
        index += match[0].length;
        matched = true;
        break;
      }
      if (!matched) {
        plain += source[index];
        index += 1;
      }
    }
    return output + escape(plain);
  }

  const STRING = /"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?/;
  const JS_KEYWORDS = /\b(?:async|await|break|case|catch|class|const|continue|default|delete|do|else|export|extends|false|finally|for|from|function|if|import|in|instanceof|let|new|null|of|return|static|switch|this|throw|true|try|typeof|undefined|var|void|while|yield)\b/;

  const javascript = (source) => scan(source, [
    [/\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$)/, "comment"],
    [/`(?:\\[\s\S]|[^`\\])*`?/, "string"],
    [STRING, "string"],
    [JS_KEYWORDS, "keyword"],
    [/[A-Za-z_$][\w$]*/, null],
    [/\b(?:0x[\da-fA-F]+|\d[\d_]*(?:\.\d+)?(?:e[+-]?\d+)?)\b/, "number"],
  ]);

  const json = (source) => scan(source, [
    [/"(?:\\.|[^"\\\n])*"(?=\s*:)/, "attr"],
    [/"(?:\\.|[^"\\\n])*"?/, "string"],
    [/\b(?:true|false|null)\b/, "keyword"],
    [/-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/, "number"],
  ]);

  /* Property values and at-rule parameters, such as strings, colors and numbers with units. */
  const cssValue = (source) => scan(source, [
    [/\/\*[\s\S]*?(?:\*\/|$)/, "comment"],
    [STRING, "string"],
    [/#[\da-fA-F]{3,8}\b/, "number"],
    [/-{0,2}[A-Za-z_][\w-]*/, null],
    [/-?(?:\d*\.)?\d+(?:[A-Za-z]+|%)?/, "number"],
  ]);

  /* In CSS a property name and a selector look the same, so the nearest
     delimiter decides. A selector or at-rule comes before "{", a declaration
     comes before ";" or "}". */
  function css(source) {
    let index = 0;
    let output = "";
    while (index < source.length) {
      const rest = source.slice(index);
      const space = rest.match(/^\s+/);
      if (space) { output += space[0]; index += space[0].length; continue; }
      const comment = rest.match(/^\/\*[\s\S]*?(?:\*\/|$)/);
      if (comment) { output += token("comment", comment[0]); index += comment[0].length; continue; }
      if ("{};".includes(rest[0])) { output += token("punctuation", rest[0]); index += 1; continue; }

      const stop = rest.search(/[{};]/);
      const end = stop === -1 ? rest.length : stop;
      const part = rest.slice(0, end);
      if (rest[end] === "{") {
        const at = part.match(/^@[\w-]+/);
        output += at ? token("keyword", at[0]) + cssValue(part.slice(at[0].length)) : token("tag", part.trimEnd()) + part.slice(part.trimEnd().length);
      } else {
        const declaration = part.match(/^(-{0,2}[\w-]+)(\s*:)([\s\S]*)$/);
        if (declaration) output += token("attr", declaration[1]) + escape(declaration[2]) + cssValue(declaration[3]);
        else output += part.startsWith("@") ? token("keyword", part.match(/^@[\w-]+/)[0]) + cssValue(part.replace(/^@[\w-]+/, "")) : cssValue(part);
      }
      index += end;
    }
    return output;
  }

  function markupTag(source) {
    if (source.startsWith("<!--")) return token("comment", source);
    if (/^<!doctype/i.test(source)) return token("doctype", source);
    return scan(source, [
      [/^<\/?[\w:-]+/, (match) => token("punctuation", match[0].match(/^<\/?/)[0]) + token("tag", match[0].replace(/^<\/?/, ""))],
      [/(=)(\s*)("[^"]*"?|'[^']*'?|[^\s"'=<>`]+)/, (match) => token("punctuation", match[1]) + match[2] + token("string", match[3])],
      [/\/?>/, "punctuation"],
      [/[^\s=/>]+/, "attr"],
    ]);
  }

  /* HTML. Tags one at a time, the contents of <style> and <script> go to their own language. */
  function html(source) {
    let index = 0;
    let output = "";
    while (index < source.length) {
      if (source.startsWith("<!--", index)) {
        const end = source.indexOf("-->", index + 4);
        const next = end === -1 ? source.length : end + 3;
        output += markupTag(source.slice(index, next));
        index = next;
        continue;
      }
      if (source[index] !== "<") {
        const next = source.indexOf("<", index);
        const end = next === -1 ? source.length : next;
        output += escape(source.slice(index, end));
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
      const tag = source.slice(index, end);
      output += markupTag(tag);
      index = end;
      const embedded = tag.match(/^<(style|script)\b/i);
      if (embedded && !tag.endsWith("/>")) {
        const close = source.toLowerCase().indexOf(`</${embedded[1].toLowerCase()}`, index);
        const stop = close === -1 ? source.length : close;
        const inner = source.slice(index, stop);
        output += embedded[1].toLowerCase() === "style" ? css(inner) : javascript(inner);
        index = stop;
      }
    }
    return output;
  }

  /* Shell. The first word of a command, flags, strings, variables and comments.
     A command starts at the beginning of a line and after |, &&, || and ;. */
  function shell(source) {
    let command = true;
    return scan(source, [
      [/(^|(?<=\s))#[^\n]*/, "comment"],
      [/\n/, () => { command = true; return "\n"; }],
      [/\\\n/, () => "\\\n"],
      [/^\$(?= )/m, () => { command = true; return token("punctuation", "$"); }],
      [/\|\||&&|[|;]/, (match) => { command = true; return token("punctuation", match[0]); }],
      [/[ \t]+/, (match) => match[0]],
      [/"(?:\\.|[^"\\])*"?|'[^']*'?/, (match) => { command = false; return token("string", match[0]); }],
      [/([A-Za-z_]\w*=)("[^"]*"|'[^']*'|[^\s|;&]*)/, (match) => (command ? token("attr", match[1]) + escape(match[2]) : escape(match[0]))],
      [/--?[A-Za-z][\w-]*/, (match) => { command = false; return token("attr", match[0]); }],
      [/\$\{?[\w@#?]+\}?/, (match) => { command = false; return token("attr", match[0]); }],
      [/-?\b\d+(?:\.\d+)?\b(?![\w./-])/, (match) => { command = false; return token("number", match[0]); }],
      [/[^\s|;&"'#]+/, (match) => {
        const kind = command ? "keyword" : null;
        command = false;
        return kind ? token(kind, match[0]) : escape(match[0]);
      }],
    ]);
  }

  const LANGUAGES = { html, xml: html, svg: html, css, js: javascript, javascript, mjs: javascript, json, sh: shell, shell, bash: shell, console: shell, zsh: shell };

  function guess(source) {
    const text = source.trimStart();
    if (text.startsWith("<")) return "html";
    if (/^[[{]/.test(text)) {
      try { JSON.parse(text); return "json"; } catch { /* not JSON */ }
    }
    if (/^(?:[.#@:]|[\w-]+\s*\{|\*)/.test(text) && /\{[\s\S]*:[\s\S]*\}/.test(text)) return "css";
    if (/\b(?:const|let|function|import|export|document|window)\b|=>/.test(text)) return "javascript";
    return "shell";
  }

  function languageOf(code) {
    const pre = code.closest("pre");
    const named = code.dataset.language || pre?.dataset.language
      || [...code.classList, ...(pre ? [...pre.classList] : [])].find((name) => name.startsWith("language-"))?.slice(9);
    return (named || guess(code.textContent || "")).toLowerCase();
  }

  function highlight(source, language) {
    const run = LANGUAGES[(language || guess(source)).toLowerCase()];
    return run ? run(source) : escape(source);
  }

  function apply(root = document) {
    root.querySelectorAll(".code-block pre > code:not([data-highlighted])").forEach((code) => {
      const language = languageOf(code);
      if (LANGUAGES[language]) code.innerHTML = highlight(code.textContent || "", language);
      code.dataset.highlighted = language;
    });
  }

  window.CraftCode = { highlight, apply };
  /* The markup changes after the document is parsed. Deferred scripts that
     read the source text of the examples get to see it without spans. */
  if (document.readyState === "complete") apply();
  else document.addEventListener("DOMContentLoaded", () => apply());
})();
