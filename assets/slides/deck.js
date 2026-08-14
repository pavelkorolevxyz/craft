/* ============================================================
   deck.js — навигация по колоде. Общая для всех тем.

   Каждый .frag становится отдельным состоянием слайда. Состояния
   разворачиваются в самостоятельные страницы при загрузке, поэтому
   у каждого есть свой номер, hash, плитка в обзоре и страница в PDF.

   ← → Space PgUp PgDn  переход
   Кликер назад/вперёд  переход
   Home / End           первый / последний
   G                    обзор сеткой
   L                    обзор лентой
   F                    полный экран
   H / ?                показать или скрыть справку
   ============================================================ */

(() => {
  const deck = document.querySelector('.deck');
  if (!deck) return;

  const slidesRoot = deck.querySelector('.slides');
  const sourceSlides = [...slidesRoot.querySelectorAll(':scope > .slide')];

  // Автор пишет каждый смысловой слайд один раз. Для показа создаём
  // страницу с одним дополнительным раскрытым .frag на каждом шаге.
  sourceSlides.forEach((source, sourceIndex) => {
    const fragmentCount = source.querySelectorAll('.frag').length;
    const pages = document.createDocumentFragment();

    for (let step = 0; step <= fragmentCount; step += 1) {
      const page = source.cloneNode(true);
      const fragments = [...page.querySelectorAll('.frag')];

      fragments.forEach((fragment, index) => {
        const shown = index < step;
        fragment.toggleAttribute('data-shown', shown);
        if (shown) fragment.removeAttribute('aria-hidden');
        else fragment.setAttribute('aria-hidden', 'true');
      });

      page.dataset.source = sourceIndex + 1;
      page.dataset.step = step;
      page.dataset.steps = fragmentCount;
      pages.append(page);
    }

    source.replaceWith(pages);
  });

  const slides = [...slidesRoot.querySelectorAll(':scope > .slide')];
  const helpPanel = document.querySelector('.help-panel');
  const helpReveal = document.querySelector('.help-reveal');
  const helpRevealZone = document.querySelector('.help-reveal-zone');
  const helpPage = helpPanel?.querySelector('.help-page');
  const previousButton = helpPanel?.querySelector('[data-deck-go="-1"]');
  const nextButton = helpPanel?.querySelector('[data-deck-go="1"]');
  const stripButton = helpPanel?.querySelector('[data-deck-action="strip"]');
  const total = slides.length;
  const pad = (n) => String(n).padStart(2, '0');

  slides.forEach((slide, index) => {
    slide.dataset.index = index + 1;
    const page = pad(index + 1);
    const number = slide.querySelector('.slide-number');
    if (number) number.innerHTML = `${page}<span>/ ${total}</span>`;
  });

  const clamp = (n) => Math.max(0, Math.min(total - 1, n));
  const pageFromHash = () => {
    const page = parseInt(location.hash.slice(1), 10);
    return Number.isFinite(page) ? clamp(page - 1) : 0;
  };
  let current = pageFromHash();

  function render(scroll = false) {
    slides.forEach((slide, index) => {
      slide.toggleAttribute('data-active', index === current);
    });

    if (helpPage) helpPage.textContent = `${pad(current + 1)} / ${total}`;
    if (previousButton) previousButton.disabled = current === 0;
    if (nextButton) nextButton.disabled = current === total - 1;
    history.replaceState(null, '', `#${current + 1}`);

    if (scroll && (deck.dataset.mode === 'grid' || deck.dataset.mode === 'strip')) {
      slides[current].scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }

    document.title = document.title.replace(/^\d+ · /, '');
  }

  function go(delta) {
    const next = clamp(current + delta);
    if (next === current) return;
    current = next;
    render(true);
  }

  function toggleOverview(mode, force) {
    const on = force ?? deck.dataset.mode !== mode;
    if (on) deck.dataset.mode = mode;
    else delete deck.dataset.mode;
    document.body.style.overflow = on ? 'auto' : 'hidden';
    if (on) slides[current].scrollIntoView({ block: 'center', inline: 'center' });
    syncStripButton();
  }

  const toggleGrid = (force) => toggleOverview('grid', force);

  function syncStripButton() {
    if (!stripButton) return;
    const direction = deck.dataset.stripDirection || 'vertical';
    stripButton.dataset.direction = direction;
    if (deck.dataset.mode !== 'strip') {
      stripButton.setAttribute('aria-label', 'Обзор слайдов лентой');
      return;
    }
    const nextDirection = direction === 'vertical' ? 'горизонтальную' : 'вертикальную';
    stripButton.setAttribute('aria-label', `Переключить ленту на ${nextDirection}`);
  }

  function toggleStrip() {
    if (deck.dataset.mode !== 'strip') {
      deck.dataset.stripDirection ||= 'vertical';
      toggleOverview('strip', true);
    } else {
      deck.dataset.stripDirection = deck.dataset.stripDirection === 'horizontal'
        ? 'vertical'
        : 'horizontal';
      slides[current].scrollIntoView({ block: 'center', inline: 'center' });
    }
    syncStripButton();
  }

  let lastMousePosition = null;

  function updateHelpReveal(clientX, clientY) {
    if (!helpRevealZone || !helpPanel?.hidden) return;
    const inZone = clientX >= window.innerWidth - 112
      && clientY >= window.innerHeight - 96;
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

    // Некоторые кликеры представляются браузеру как Alt + ←/→,
    // другие — как отдельные кнопки BrowserBack/BrowserForward.
    if (event.altKey) {
      if (event.key === 'ArrowRight') {
        event.preventDefault(); go(1);
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault(); go(-1);
      }
      return;
    }

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
      case 'g': case 'G': case 'п': case 'П':
        event.preventDefault(); toggleGrid(); break;
      case 'l': case 'L': case 'д': case 'Д':
        event.preventDefault(); toggleStrip(); break;
      case 'f': case 'F': case 'а': case 'А':
        event.preventDefault();
        document.fullscreenElement
          ? document.exitFullscreen()
          : document.documentElement.requestFullscreen();
        break;
      case 'h': case 'H': case 'р': case 'Р': case '?':
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

    // Как в обычных приложениях для презентаций: клик по свободному
    // месту листает вперёд, но ссылки, элементы управления и выделение текста работают сами.
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) return;
    if (!event.target.closest('a, button, input, select, textarea')) go(1);
  });

  // Часть кликеров определяется как мышь с боковыми кнопками.
  // Кнопка 3 — назад, кнопка 4 — вперёд.
  deck.addEventListener('pointerdown', (event) => {
    if (event.button !== 3 && event.button !== 4) return;
    event.preventDefault();
    go(event.button === 4 ? 1 : -1);
  });
  deck.addEventListener('auxclick', (event) => {
    if (event.button === 3 || event.button === 4) event.preventDefault();
  });

  // Колесо вниз листает вперёд, вверх — назад. Серия инерционных
  // событий тачпада считается одним жестом, чтобы не проскочить слайды.
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

  window.addEventListener('hashchange', () => {
    const next = pageFromHash();
    if (next !== current) {
      current = next;
      render(true);
    }
  });

  render();
  const initialView = new URLSearchParams(location.search).get('view');
  if (initialView === 'grid' || initialView === 'strip') toggleOverview(initialView, true);
  toggleHelp(false);
})();
