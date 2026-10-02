/* ============================================================
   deck.js: deck navigation. Shared by all themes.

   Every .frag becomes a separate slide state. On load the script
   expands the states into standalone pages, so each one has its own
   number, hash, overview tile and PDF page.

   ← → Space PgUp PgDn  navigate
   Clicker back/forward navigate
   Home / End           first / last
   ← ↑ → ↓ in overview  move between tiles
   Enter in overview    open the selected slide
   G                    grid overview
   L                    strip overview
   F                    full screen
   T                    light / dark theme
   M                    motion: show / static
   H / ?                show or hide the help panel

   Page address: #12 (number), #key (first state of the slide) or
   #key/2 (second reveal). The number changes when slides move, the
   key from data-key stays with its source slide.

   URL parameters:
   ?reveal=steps|final   every reveal or final frames only
   ?motion=show|auto|static  motion policy, see below
   ?skipped=show         show slides with data-status="skip"
   ============================================================ */

(() => {
  const deck = document.querySelector('.deck');
  if (!deck) return;

  const root = document.documentElement;
  const params = new URLSearchParams(location.search);
  const slidesRoot = deck.querySelector('.slides');
  const sourceSlides = [...slidesRoot.querySelectorAll(':scope > .slide')];

  // The reveal mode belongs to the showing, not to the source. steps turns
  // every .frag into a page, final keeps only the final frame of a slide for
  // review and a short PDF. Both modes use the same source HTML.
  const requestedReveal = params.get('reveal');
  const revealMode = requestedReveal === 'steps' || requestedReveal === 'final'
    ? requestedReveal
    : deck.dataset.revealMode === 'final' ? 'final' : 'steps';
  deck.dataset.revealMode = revealMode;
  const showSkipped = params.get('skipped') === 'show';
  // Labels the script writes itself. A deck in another language overrides
  // them with JSON in data-labels on .deck; labels in the HTML stay in HTML.
  const labels = {
    draft: 'Draft', skip: 'Skipped',
    stopMotion: 'Stop motion', startMotion: 'Start motion',
    darkTheme: 'Switch to dark theme', lightTheme: 'Switch to light theme',
    strip: 'Slide strip view', stripHorizontal: 'Switch strip to horizontal', stripVertical: 'Switch strip to vertical',
  };
  try {
    Object.assign(labels, JSON.parse(deck.dataset.labels || '{}'));
  } catch (error) {
    console.warn('Craft: data-labels on .deck is not valid JSON');
  }
  const statusLabels = { draft: labels.draft, skip: labels.skip };

  function splitWords(heading) {
    const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      // A counter rewrites its own text, so its words stay whole.
      if (node.parentElement.closest('[data-count], .word')) return;
      const parts = node.textContent.split(/(\s+)/);
      if (!parts.some((part) => part.trim())) return;
      const fragment = document.createDocumentFragment();
      parts.forEach((part) => {
        if (!part) return;
        if (!part.trim()) {
          fragment.append(part);
          return;
        }
        const word = document.createElement('span');
        word.className = 'word';
        const inner = document.createElement('span');
        inner.textContent = part;
        word.append(inner);
        fragment.append(word);
      });
      node.replaceWith(fragment);
    });
  }

  // Number the visual lines of split text on the page being shown. The
  // count runs through the heading and its note, so the note follows.
  function markLines(page) {
    let line = -1;
    let top = null;
    page.querySelectorAll('.word').forEach((word) => {
      const y = Math.round(word.getBoundingClientRect().top);
      if (top === null || Math.abs(y - top) > 4) {
        line += 1;
        top = y;
      }
      word.style.setProperty('--line', line);
    });
  }

  // The author writes each slide once. For the showing we create a page
  // per step, each with one more revealed .frag.
  sourceSlides.forEach((source, sourceIndex) => {
    // The key is the permanent address of the source slide. The deck works
    // without it, but the project check requires an explicit data-key.
    if (!source.dataset.key) {
      source.dataset.key = `slide-${sourceIndex + 1}`;
      source.setAttribute('data-key-generated', '');
    }
    const status = source.dataset.status;
    if (status === 'skip' && !showSkipped) {
      source.remove();
      return;
    }

    // Separate the physical page from the inner layout area. When printing,
    // Firefox may give the page the proportions of the chosen paper, and the
    // nested size container then recomputes cqw/cqh for it.
    const canvas = document.createElement('div');
    canvas.className = 'slide-canvas';
    canvas.append(...source.childNodes);
    source.append(canvas);

    if (status === 'draft' || status === 'skip') {
      const badge = document.createElement('p');
      badge.className = 'slide-status';
      badge.textContent = source.dataset.statusLabel || statusLabels[status];
      canvas.append(badge);
    }

    // Bento tiles appear in reading order.
    source.querySelectorAll('.bento-tile').forEach((tile, order) => tile.style.setProperty('--order', order));

    // Large headings and quotes rise line by line. Each word sits in its own mask;
    // the line index comes from the real layout when the page is shown.
    source.querySelectorAll('.type-hero, .s-statement .type-note, .s-quote blockquote, .s-quote figcaption').forEach(splitWords);

    // Reveal step. data-frag="with-previous" shows a part on the same
    // press as the previous one, so a label in a sibling container
    // appears together with its item.
    let fragmentCount = 0;
    source.querySelectorAll('.frag').forEach((fragment, index) => {
      if (index === 0 || fragment.dataset.frag !== 'with-previous') fragmentCount += 1;
      fragment.dataset.fragStep = fragmentCount;
    });
    const pages = document.createDocumentFragment();

    for (let step = revealMode === 'final' ? fragmentCount : 0; step <= fragmentCount; step += 1) {
      const page = source.cloneNode(true);
      const fragments = [...page.querySelectorAll('.frag')];

      fragments.forEach((fragment) => {
        const shown = Number(fragment.dataset.fragStep) <= step;
        fragment.toggleAttribute('data-shown', shown);
        if (shown) fragment.removeAttribute('aria-hidden');
        else fragment.setAttribute('aria-hidden', 'true');
      });

      page.dataset.source = sourceIndex + 1;
      page.dataset.step = step;
      page.dataset.steps = fragmentCount;
      // Every on-screen step becomes a separate PDF page. Text and layout
      // are already in their final state, CSS removes the animation.
      page.setAttribute('data-print-page', '');

      pages.append(page);
    }

    source.replaceWith(pages);
  });

  const slides = [...slidesRoot.querySelectorAll(':scope > .slide')];
  const helpPanel = document.querySelector('.help-panel');
  const helpReveal = document.querySelector('.help-reveal');
  const helpRevealZone = document.querySelector('.help-reveal-zone');
  const helpPageInput = helpPanel?.querySelector('.help-page-input');
  const helpPageTotal = helpPanel?.querySelector('.help-page-total');
  const previousButton = helpPanel?.querySelector('[data-deck-go="-1"]');
  const nextButton = helpPanel?.querySelector('[data-deck-go="1"]');
  const stripButton = helpPanel?.querySelector('[data-deck-action="strip"]');
  const themeButton = helpPanel?.querySelector('[data-deck-action="theme"]');
  const systemTheme = matchMedia('(prefers-color-scheme: light)');
  const themeStorageKey = 'craft-theme';
  const isTheme = (value) => value === 'light' || value === 'dark';
  const total = slides.length;
  const pad = (n) => String(n).padStart(2, '0');

  slides.forEach((slide, index) => {
    slide.dataset.index = index + 1;
    slide.setAttribute('role', 'group');
    slide.setAttribute('aria-roledescription', 'slide');
    const page = pad(index + 1);
    const heading = slide.querySelector('h1, h2, h3, .slide-title');
    const title = heading?.textContent.trim();
    slide.setAttribute('aria-label', title
      ? `Slide ${index + 1} of ${total}: ${title}`
      : `Slide ${index + 1} of ${total}`);

    slide.querySelectorAll('table').forEach((table, tableIndex) => {
      const caption = table.querySelector('caption');
      const labels = [];
      if (heading) {
        heading.id ||= `slide-${index + 1}-title`;
        labels.push(heading.id);
      }
      if (caption) {
        caption.id ||= `slide-${index + 1}-table-${tableIndex + 1}-caption`;
        labels.push(caption.id);
      }
      if (labels.length) table.setAttribute('aria-labelledby', labels.join(' '));
    });

    const number = slide.querySelector('.slide-number');
    if (number) {
      number.innerHTML = `${page}<span>/ ${total}</span>`;
      number.setAttribute('aria-hidden', 'true');
    }
  });

  const clamp = (n) => Math.max(0, Math.min(total - 1, n));

  // One motion policy per deck. Components do not read the system setting
  // themselves, they look at :root[data-motion-state="on|off"].
  // show     author animations always play, for the talk;
  // auto     follow the viewer's prefers-reduced-motion;
  // static   final frames with no motion, for reading and export.
  // The browser does not store the mode. A stray M press at a rehearsal
  // must not turn animations off for the talk.
  const motionModes = ['show', 'auto', 'static'];
  const systemMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const motionButton = document.querySelector('[data-deck-action="motion"]');
  const requestedMotion = params.get('motion');
  let motionMode = motionModes.includes(requestedMotion)
    ? requestedMotion
    : motionModes.includes(root.dataset.motion) ? root.dataset.motion : 'auto';

  const motionActive = () => motionMode === 'show' || (motionMode === 'auto' && !systemMotion.matches);

  function applyMotion(mode = motionMode) {
    motionMode = mode;
    const active = motionActive();
    root.dataset.motion = motionMode;
    root.dataset.motionState = active ? 'on' : 'off';
    if (motionButton) {
      const action = active ? labels.stopMotion : labels.startMotion;
      motionButton.setAttribute('aria-label', action);
      motionButton.setAttribute('title', action);
      motionButton.setAttribute('aria-pressed', String(!active));
    }
    if (!active) finishCounters();
    dispatchEvent(new CustomEvent('craft-motionchange', { detail: { mode: motionMode, active } }));
  }

  const toggleMotion = () => applyMotion(motionActive() ? 'static' : 'show');

  function readSavedTheme() {
    try {
      const value = localStorage.getItem(themeStorageKey);
      return isTheme(value) ? value : null;
    } catch (error) {
      return null;
    }
  }

  function syncThemeButton() {
    if (!themeButton) return;
    const light = root.dataset.theme === 'light';
    const action = light ? labels.darkTheme : labels.lightTheme;
    themeButton.setAttribute('aria-label', action);
    themeButton.setAttribute('title', action);
    themeButton.setAttribute('aria-pressed', String(light));
  }

  function applyTheme(theme, source = 'saved', persist = false) {
    if (!isTheme(theme)) return;
    root.dataset.theme = theme;
    root.dataset.themeSource = source;
    if (persist) {
      try {
        localStorage.setItem(themeStorageKey, theme);
      } catch (error) {
        // The deck keeps working even if the browser blocks storage for file://.
      }
    }
    syncThemeButton();
    dispatchEvent(new CustomEvent('craft-themechange', { detail: { theme, source } }));
  }

  // A deck can set its default theme in markup with
  // <html data-theme="dark" data-theme-source="default">. The viewer's
  // system theme then does not override it, and the button still saves a choice.
  const requestedTheme = new URLSearchParams(location.search).get('theme');
  const savedTheme = readSavedTheme();
  const authoredTheme = root.dataset.themeSource === 'default' && isTheme(root.dataset.theme) ? root.dataset.theme : null;
  applyTheme(
    isTheme(requestedTheme) ? requestedTheme : savedTheme || authoredTheme || (systemTheme.matches ? 'light' : 'dark'),
    isTheme(requestedTheme) ? 'query' : savedTheme ? 'saved' : authoredTheme ? 'default' : 'system',
  );
  const runningCounters = new Map();

  // data-count keeps the final value in HTML for print, screenshots and
  // direct links. On a forward reveal only the first number in the text
  // changes, so the unit and the number format stay as the author wrote them.
  // In English documents (lang empty or "en*") a comma groups thousands
  // ("12,400") and "." is the decimal mark. Other languages use a comma as
  // the decimal mark and a space between groups. A no-break or narrow
  // no-break space groups digits in both cases.
  function animateCounter(element) {
    if (!motionActive()) return;

    const finalText = element.textContent;
    const lang = (document.documentElement.lang || '').toLowerCase();
    const english = !lang || lang.startsWith('en');
    const match = finalText.match(english
      ? /-?\d{1,3}(?:[,\u00a0\u202f]\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?/
      : /-?\d(?:[\d\u00a0\u202f ]*\d)?(?:[.,]\d+)?/);
    if (!match) return;

    const token = match[0];
    const groupPattern = english ? /[,\u00a0\u202f]/ : /[\u00a0\u202f ]/;
    const digits = token.replace(new RegExp(groupPattern.source, 'g'), '');
    const target = Number(english ? digits : digits.replace(',', '.'));
    if (!Number.isFinite(target) || target === 0) return;

    const decimalMark = english
      ? (token.includes('.') ? '.' : '')
      : token.includes(',') ? ',' : token.includes('.') ? '.' : '';
    const decimals = decimalMark ? token.split(decimalMark)[1].length : 0;
    const groupMark = token.match(groupPattern)?.[0] ?? '';
    const durationValue = Number(element.dataset.countDuration);
    const duration = Number.isFinite(durationValue) && durationValue >= 0
      ? Math.min(durationValue, 10_000)
      : 900;
    const prefix = finalText.slice(0, match.index);
    const suffix = finalText.slice(match.index + token.length);

    if (!element.hasAttribute('aria-label')) {
      element.setAttribute('aria-label', finalText.trim());
    }

    // Reserve the width of the final text without padding missing digits
    // with visible zeros. The right edge of the number stays in place.
    const range = document.createRange();
    range.selectNodeContents(element);
    const finalWidth = Math.ceil(range.getBoundingClientRect().width);
    range.detach();
    // An intermediate value never wraps to a second line, even if the
    // source uses a plain space as the group separator.
    element.style.whiteSpace = 'nowrap';
    if (finalWidth) {
      element.style.display = 'inline-block';
      element.style.inlineSize = `${finalWidth}px`;
      // The anchor edge follows how the metric is aligned. While counting,
      // the number holds that edge, otherwise it drifts sideways and only
      // returns at the end. A value above a chart bar sits at the bar's
      // center and holds the center. A value in a row or a table is
      // right-aligned and holds the right edge. A large metric and a
      // comparison number start at the left margin and grow to the right.
      const styles = getComputedStyle(element);
      const placement = styles.justifySelf;
      const alignment = styles.textAlign;
      if (placement === 'center' || alignment === 'center') {
        element.style.textAlign = 'center';
      } else if (alignment === 'left' || alignment === 'start') {
        element.style.textAlign = 'start';
        if (placement === 'auto' || placement === 'normal' || placement === 'stretch') {
          element.style.justifySelf = 'start';
        }
      } else {
        element.style.textAlign = 'end';
        if (placement === 'auto' || placement === 'normal' || placement === 'stretch') {
          element.style.justifySelf = 'start';
        }
      }
    }

    const format = (value) => {
      const fixed = Math.abs(value).toFixed(decimals).split('.');
      if (groupMark) fixed[0] = fixed[0].replace(/\B(?=(\d{3})+(?!\d))/g, groupMark);
      return `${value < 0 ? '-' : ''}${fixed[0]}${decimals ? decimalMark + fixed[1] : ''}`;
    };

    const startedAt = performance.now();
    const state = { frameId: 0, finalText };
    runningCounters.set(element, state);
    element.textContent = `${prefix}${format(0)}${suffix}`;

    const frame = (now) => {
      const progress = duration === 0 ? 1 : Math.max(0, Math.min(1, (now - startedAt) / duration));
      const eased = 1 - (1 - progress) ** 2;
      const value = decimals
        ? target * eased
        : Math.round(target * eased);
      element.textContent = progress < 1
        ? `${prefix}${format(value)}${suffix}`
        : finalText;
      if (progress < 1) {
        state.frameId = requestAnimationFrame(frame);
      } else {
        runningCounters.delete(element);
      }
    };

    state.frameId = requestAnimationFrame(frame);
  }

  function finishCounters() {
    runningCounters.forEach((state, element) => {
      cancelAnimationFrame(state.frameId);
      element.textContent = state.finalText;
    });
    runningCounters.clear();
  }

  function animateCounters(root) {
    if (!root || deck.dataset.mode) return;
    if (root.matches('[data-count]')) animateCounter(root);
    root.querySelectorAll('[data-count]').forEach(animateCounter);
  }

  // #12 is the page number, #key is the first shown state of the slide,
  // #key/2 is the state after the second reveal. In final mode a slide has
  // one state, and any step leads to it.
  const pageFromHash = () => {
    let raw = location.hash.slice(1);
    try { raw = decodeURIComponent(raw); } catch { /* keep it as is */ }
    if (/^\d+$/.test(raw)) return clamp(Number(raw) - 1);
    const [key, stepText] = raw.split('/');
    const states = slides.filter((slide) => slide.dataset.key === key);
    if (!states.length) return 0;
    const step = Number(stepText);
    const match = Number.isInteger(step)
      ? states.find((slide) => Number(slide.dataset.step) === step) ?? states[states.length - 1]
      : states[0];
    return slides.indexOf(match);
  };
  let current = pageFromHash();
  let previous = null;
  let revealed = [];
  let leavingTimer = 0;
  let hideHelpAfterPageInput = false;

  function render(scroll = false) {
    finishCounters();
    // Motion belongs to the forward transition, not to the slide state.
    // Only what this step revealed gets it, marked with data-reveal for
    // the theme. Everything else is already in its final position. That
    // covers the first frame of the deck (direct link, screenshot, PDF
    // print), going back, and steps shown earlier. The theme then writes
    // the animation as one rule and does not count steps itself.
    const forward = previous !== null && current > previous;
    const from = previous;
    previous = current;

    slides.forEach((slide, index) => {
      const active = index === current;
      slide.toggleAttribute('data-active', active);
      if (active) slide.setAttribute('aria-current', 'page');
      else slide.removeAttribute('aria-current');
    });

    revealed.forEach((element) => element.removeAttribute('data-reveal'));
    // A slide without steps reveals as a whole, so the slide gets the mark.
    // Otherwise every part of the current step gets it.
    const page = slides[current];
    const step = Number(page.dataset.step);
    revealed = !forward ? [] : step > 0
      ? [...page.querySelectorAll(`.frag[data-frag-step="${step}"]`)]
      : [page];
    if (forward) markLines(page);
    revealed.forEach((element) => {
      element.setAttribute('data-reveal', '');
      animateCounters(element);
    });

    // The page we left stays marked for a moment on a forward move to
    // another slide. The theme may keep it on screen under a transition,
    // such as the curtain before a chapter divider.
    slides.forEach((slide) => slide.removeAttribute('data-leaving'));
    clearTimeout(leavingTimer);
    if (forward && slides[from] && slides[from].dataset.source !== page.dataset.source) {
      const leaving = slides[from];
      leaving.setAttribute('data-leaving', '');
      leavingTimer = setTimeout(() => leaving.removeAttribute('data-leaving'), 1200);
    }

    if (helpPageInput) helpPageInput.value = pad(current + 1);
    if (helpPageTotal) helpPageTotal.textContent = `/ ${total}`;
    if (previousButton) previousButton.disabled = current === 0;
    if (nextButton) nextButton.disabled = current === total - 1;
    history.replaceState(null, '', `#${current + 1}`);

    if (scroll && deck.dataset.mode === 'strip') {
      centerStripOnCurrent();
    } else if (scroll && deck.dataset.mode === 'grid') {
      // The grid scrolls by rows, so scrolling to the nearest edge is enough.
      slides[current].scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }

    document.title = document.title.replace(/^\d+ · /, '');

    // Video, prewarming and deck-local mechanics listen to this event
    // instead of watching attributes, so they all see the same order and direction.
    dispatchEvent(new CustomEvent('craft-slidechange', {
      detail: { page: current + 1, previous: from === null ? null : from + 1, forward, slide: slides[current] },
    }));
  }

  function go(delta) {
    const next = clamp(current + delta);
    if (next === current) return;
    current = next;
    render(true);
  }

  if (helpPageInput) {
    const resetPageInput = () => { helpPageInput.value = pad(current + 1); };
    const commitPageInput = () => {
      const page = Number.parseInt(helpPageInput.value, 10);
      if (!Number.isInteger(page)) {
        resetPageInput();
        return;
      }
      current = clamp(page - 1);
      render(true);
      helpPageInput.blur();
    };

    helpPageInput.maxLength = String(total).length;
    helpPageInput.addEventListener('focus', () => helpPageInput.select());
    helpPageInput.addEventListener('input', () => {
      helpPageInput.value = helpPageInput.value.replace(/\D/g, '');
    });
    helpPageInput.addEventListener('keydown', (event) => {
      event.stopPropagation();
      if (event.key === 'Enter') {
        event.preventDefault();
        commitPageInput();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        resetPageInput();
        helpPageInput.blur();
      }
    });
    helpPageInput.addEventListener('blur', () => {
      resetPageInput();
      if (hideHelpAfterPageInput) {
        hideHelpAfterPageInput = false;
        toggleHelp(false);
      }
    });
  }

  function toggleOverview(mode, force) {
    const on = force ?? deck.dataset.mode !== mode;
    // A strip without a direction has no layout, since the whole layout
    // depends on data-strip-direction. Opened by ?view=strip or by the
    // button, it starts vertical.
    if (on && mode === 'strip') deck.dataset.stripDirection ||= 'vertical';
    if (on) deck.dataset.mode = mode;
    else delete deck.dataset.mode;
    document.body.style.overflow = on ? 'auto' : 'hidden';
    if (on && mode === 'strip') {
      centerStripOnCurrent();
    } else if (on) {
      // Grid tiles get their size only after the new mode is laid out.
      requestAnimationFrame(() => {
        slides[current].scrollIntoView({ block: 'center', inline: 'center' });
      });
    }
    syncStripButton();
  }

  const toggleGrid = (force) => toggleOverview('grid', force);

  // How many tiles fit in a row. The grid uses auto-fill, so the column
  // count is known only after layout. The first row is every tile with
  // the same vertical position as the first tile.
  function overviewColumns() {
    if (deck.dataset.mode !== 'grid') return 1;
    const top = slides[0].offsetTop;
    let columns = 0;
    while (columns < total && slides[columns].offsetTop === top) columns += 1;
    return Math.max(1, columns);
  }

  // In the overview, arrows move between tiles, not in show order.
  // Left and right go to the next tile, up and down go one row. Moving
  // past the edge does nothing, otherwise the cursor would silently jump
  // to another column.
  function overviewKey(event) {
    const sideways = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (sideways !== undefined) {
      event.preventDefault();
      go(sideways);
      return true;
    }

    const columns = overviewColumns();
    const rowwise = {
      ArrowDown: columns, PageDown: columns,
      ArrowUp: -columns, PageUp: -columns,
    }[event.key];
    if (rowwise !== undefined) {
      event.preventDefault();
      const next = current + rowwise;
      if (next >= 0 && next < total) go(rowwise);
      return true;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      toggleOverview(deck.dataset.mode, false);
      render();
      return true;
    }

    return false;
  }

  function syncStripButton() {
    if (!stripButton) return;
    const direction = deck.dataset.stripDirection || 'vertical';
    stripButton.dataset.direction = direction;
    if (deck.dataset.mode !== 'strip') {
      stripButton.setAttribute('aria-label', labels.strip);
      return;
    }
    const nextDirection = direction === 'vertical' ? 'horizontal' : 'vertical';
    stripButton.setAttribute('aria-label', nextDirection === 'horizontal' ? labels.stripHorizontal : labels.stripVertical);
  }

  function centerStripOnCurrent() {
    // Reset the old axis before measuring. After a direction change its
    // scroll offset means nothing. Reading the rect applies the new layout
    // synchronously, and the second scrollTo lands exactly in the center.
    deck.scrollTo({ left: 0, top: 0 });
    const slideRect = slides[current].getBoundingClientRect();
    const deckRect = deck.getBoundingClientRect();
    const horizontal = deck.dataset.stripDirection === 'horizontal';
    deck.scrollTo({
      left: horizontal
        ? slideRect.left + slideRect.width / 2 - (deckRect.left + deck.clientWidth / 2)
        : 0,
      top: horizontal
        ? 0
        : slideRect.top + slideRect.height / 2 - (deckRect.top + deck.clientHeight / 2),
    });
  }

  function toggleStrip() {
    if (deck.dataset.mode !== 'strip') {
      deck.dataset.stripDirection ||= 'vertical';
      toggleOverview('strip', true);
    } else {
      deck.dataset.stripDirection = deck.dataset.stripDirection === 'horizontal'
        ? 'vertical'
        : 'horizontal';
      centerStripOnCurrent();
    }
    syncStripButton();
  }

  let lastMousePosition = null;

  function updateHelpReveal(clientX, clientY) {
    if (!helpRevealZone || !helpPanel?.hidden) return;
    const inZone = clientX >= window.innerWidth - 112
      && clientY <= 96;
    helpRevealZone.classList.toggle('is-active', inZone);
  }

  function toggleHelp(force) {
    if (!helpPanel) return;
    const on = force ?? helpPanel.hidden;
    helpPanel.hidden = !on;
    helpPanel.setAttribute('aria-hidden', String(!on));
    if (helpReveal) helpReveal.hidden = on;
    if (helpRevealZone && on) helpRevealZone.classList.remove('is-active');
    if (!on && lastMousePosition) {
      updateHelpReveal(lastMousePosition.x, lastMousePosition.y);
    }
  }

  document.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey) return;

    const target = event.target;
    // A text field takes every key. A link or button takes only its own
    // Enter and Space. After a panel button press the focus stays on it,
    // and clicker arrows must keep moving through the deck.
    const isField = target instanceof Element
      && Boolean(target.closest('input, textarea, select, [contenteditable]'));
    const isControl = target instanceof Element && Boolean(target.closest('a, button'));
    if (isField && event.key !== 'Escape') return;
    if (isControl && (event.key === 'Enter' || event.key === ' ')) return;

    // The overview is driven by keys, so hover is off until the mouse moves.
    deck.dataset.input = 'keyboard';

    const isEditing = target instanceof HTMLInputElement
      || target instanceof HTMLTextAreaElement
      || target instanceof HTMLSelectElement
      || target?.isContentEditable;
    if (/^\d$/.test(event.key) && helpPageInput && !isEditing) {
      event.preventDefault();
      hideHelpAfterPageInput = Boolean(helpPanel?.hidden);
      toggleHelp(true);
      helpPageInput.focus();
      helpPageInput.value = event.key;
      helpPageInput.setSelectionRange(helpPageInput.value.length, helpPageInput.value.length);
      return;
    }

    // Some clickers present themselves to the browser as Alt + ←/→,
    // others as separate BrowserBack/BrowserForward keys.
    if (event.altKey) {
      if (event.key === 'ArrowRight') {
        event.preventDefault(); go(1);
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault(); go(-1);
      }
      return;
    }

    const inOverview = deck.dataset.mode === 'grid' || deck.dataset.mode === 'strip';
    if (inOverview && overviewKey(event)) return;

    switch (event.key) {
      case 'ArrowRight': case 'ArrowDown': case 'PageDown': case ' ': case 'Enter':
      case 'BrowserForward': case 'MediaTrackNext':
        event.preventDefault(); go(1); break;
      case 'ArrowLeft': case 'ArrowUp': case 'PageUp': case 'Backspace':
      case 'BrowserBack': case 'MediaTrackPrevious':
        event.preventDefault(); go(-1); break;
      case 'Home':
        event.preventDefault(); current = 0; render(true); break;
      case 'End':
        event.preventDefault(); current = total - 1; render(true); break;
      // The escaped letters are the same keys on the Russian keyboard layout.
      case 'g': case 'G': case '\u043f': case '\u041f':
        event.preventDefault(); toggleGrid(); break;
      case 'l': case 'L': case '\u0434': case '\u0414':
        event.preventDefault(); toggleStrip(); break;
      case 'f': case 'F': case '\u0430': case '\u0410':
        event.preventDefault();
        document.fullscreenElement
          ? document.exitFullscreen()
          : document.documentElement.requestFullscreen();
        break;
      case 't': case 'T': case '\u0435': case '\u0415':
        event.preventDefault();
        applyTheme(root.dataset.theme === 'light' ? 'dark' : 'light', 'saved', true);
        break;
      case 'm': case 'M': case '\u044c': case '\u042c':
        event.preventDefault(); toggleMotion(); break;
      case 'h': case 'H': case '\u0440': case '\u0420': case '?':
        event.preventDefault(); toggleHelp(); break;
      case 'Escape':
        if (helpPanel && !helpPanel.hidden) {
          event.preventDefault(); toggleHelp(false);
        } else if (deck.dataset.mode === 'grid' || deck.dataset.mode === 'strip') {
          event.preventDefault(); toggleOverview(deck.dataset.mode, false);
        }
        break;
    }
  });

  document.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'mouse') return;
    if (deck.dataset.input) delete deck.dataset.input;
    lastMousePosition = { x: event.clientX, y: event.clientY };
    updateHelpReveal(event.clientX, event.clientY);
  });
  helpReveal?.addEventListener('click', () => toggleHelp(true));
  helpPanel?.addEventListener('click', (event) => {
    const navButton = event.target.closest('[data-deck-go]');
    if (navButton) {
      go(Number(navButton.dataset.deckGo));
      return;
    }

    const actionButton = event.target.closest('[data-deck-action]');
    if (!actionButton) return;
    switch (actionButton.dataset.deckAction) {
      case 'grid': toggleGrid(); break;
      case 'strip': toggleStrip(); break;
      case 'fullscreen':
        document.fullscreenElement
          ? document.exitFullscreen()
          : document.documentElement.requestFullscreen();
        break;
      case 'theme':
        applyTheme(root.dataset.theme === 'light' ? 'dark' : 'light', 'saved', true);
        break;
      case 'motion': toggleMotion(); break;
      case 'hide-help': toggleHelp(false); break;
    }
  });

  deck.addEventListener('click', (event) => {
    if (deck.dataset.mode === 'grid' || deck.dataset.mode === 'strip') {
      const slide = event.target.closest('.slide');
      if (!slide) return;
      current = slides.indexOf(slide);
      toggleOverview(deck.dataset.mode, false);
      render();
      return;
    }

    // As in regular presentation apps, a click on empty space moves forward.
    // Links, controls and text selection keep their own behavior.
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) return;
    if (!event.target.closest('a, button, input, select, textarea')) go(1);
  });

  // Some clickers show up as a mouse with side buttons.
  // Button 3 is back, button 4 is forward.
  deck.addEventListener('pointerdown', (event) => {
    if (event.button !== 3 && event.button !== 4) return;
    event.preventDefault();
    go(event.button === 4 ? 1 : -1);
  });
  deck.addEventListener('auxclick', (event) => {
    if (event.button === 3 || event.button === 4) event.preventDefault();
  });

  // Wheel down moves forward, wheel up moves back. A series of inertial
  // touchpad events counts as one gesture, so slides are not skipped.
  let wheelDelta = 0;
  let wheelLocked = false;
  let wheelIdle = null;
  deck.addEventListener('wheel', (event) => {
    if (deck.dataset.mode === 'grid') return;
    if (deck.dataset.mode === 'strip') {
      event.preventDefault();
      const rawDelta = Math.abs(event.deltaY) >= Math.abs(event.deltaX)
        ? event.deltaY
        : event.deltaX;
      const scale = event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? 16
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? (deck.dataset.stripDirection === 'horizontal' ? deck.clientWidth : deck.clientHeight)
          : 1;
      const delta = rawDelta * scale;
      deck.scrollBy({
        left: deck.dataset.stripDirection === 'horizontal' ? delta : 0,
        top: deck.dataset.stripDirection === 'vertical' ? delta : 0,
      });
      return;
    }
    event.preventDefault();

    clearTimeout(wheelIdle);
    wheelIdle = setTimeout(() => {
      wheelDelta = 0;
      wheelLocked = false;
    }, 180);

    if (wheelLocked) return;
    const delta = Math.abs(event.deltaY) >= Math.abs(event.deltaX)
      ? event.deltaY
      : event.deltaX;
    wheelDelta += delta;

    if (Math.abs(wheelDelta) < 40) return;
    go(wheelDelta > 0 ? 1 : -1);
    wheelLocked = true;
  }, { passive: false });

  let touchX = null;
  deck.addEventListener('touchstart', (event) => {
    touchX = event.changedTouches[0].clientX;
  }, { passive: true });

  deck.addEventListener('touchend', (event) => {
    if (touchX === null) return;
    const dx = event.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 45) go(dx < 0 ? 1 : -1);
    touchX = null;
  }, { passive: true });

  const printSlides = slides.filter((slide) => slide.hasAttribute('data-print-page'));
  let screenNumbers = null;

  function preparePrint() {
    finishCounters();
    screenNumbers = new Map();
    printSlides.forEach((slide, index) => {
      const number = slide.querySelector('.slide-number');
      if (!number) return;
      screenNumbers.set(number, number.innerHTML);
      number.innerHTML = `${pad(index + 1)}<span>/ ${printSlides.length}</span>`;
    });
  }

  function finishPrint() {
    screenNumbers?.forEach((html, number) => { number.innerHTML = html; });
    screenNumbers = null;
  }

  addEventListener('beforeprint', preparePrint);
  addEventListener('afterprint', finishPrint);

  systemTheme.addEventListener('change', (event) => {
    if (root.dataset.themeSource !== 'system') return;
    applyTheme(event.matches ? 'light' : 'dark', 'system');
  });

  systemMotion.addEventListener('change', () => {
    if (motionMode === 'auto') applyMotion();
  });

  window.addEventListener('hashchange', () => {
    const next = pageFromHash();
    if (next !== current) {
      current = next;
      render(true);
    }
  });

  // Public API for checks, the deck map and deck-local mechanics.
  // Page numbers start at one, as in the address and on the slide.
  window.craftDeck = Object.freeze({
    revealMode,
    total,
    get current() { return current + 1; },
    get motion() { return { mode: motionMode, active: motionActive() }; },
    pages: () => slides.map((slide) => ({
      page: Number(slide.dataset.index),
      key: slide.dataset.key,
      step: Number(slide.dataset.step),
      steps: Number(slide.dataset.steps),
      layout: slide.dataset.slideLayout || null,
      status: slide.dataset.status || null,
      title: slide.querySelector('h1, h2, h3, .slide-title')?.textContent.trim().replace(/\s+/g, ' ') || '',
    })),
    go(page) {
      current = clamp(Number(page) - 1);
      render(true);
    },
    setMotion(mode) {
      if (motionModes.includes(mode)) applyMotion(mode);
    },
  });

  applyMotion();
  render();
  const initialView = new URLSearchParams(location.search).get('view');
  if (initialView === 'grid' || initialView === 'strip') toggleOverview(initialView, true);
  toggleHelp(false);
})();
