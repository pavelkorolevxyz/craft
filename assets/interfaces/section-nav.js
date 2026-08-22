(() => {
  const initSectionNav = (container) => {
    const links = [...container.querySelectorAll('a[href^="#"]')];
    const pairs = links
      .map((link) => ({ link, section: document.getElementById(decodeURIComponent(link.hash.slice(1))) }))
      .filter((pair) => pair.section);
    if (!pairs.length) return;

    let currentId;
    let scheduled = false;
    let navigationTarget = null;
    let navigationTimer;

    const revealCurrent = (link) => {
      if (container.scrollWidth <= container.clientWidth) return;
      const left = link.offsetLeft - (container.clientWidth - link.offsetWidth) / 2;
      container.scrollTo({ left, behavior: 'auto' });
    };

    const setCurrent = (id) => {
      if (id === currentId) return;
      currentId = id;
      let currentLink;
      for (const pair of pairs) {
        if (pair.section.id === id) {
          pair.link.setAttribute('aria-current', 'true');
          currentLink = pair.link;
        } else {
          pair.link.removeAttribute('aria-current');
        }
      }
      if (currentLink) revealCurrent(currentLink);
    };

    const updateCurrent = () => {
      if (scrollY + innerHeight >= document.documentElement.scrollHeight - 2) {
        setCurrent(pairs.at(-1).section.id);
        return;
      }
      const threshold = scrollY + Math.min(180, innerHeight * 0.3);
      let current = pairs[0].section;
      for (const pair of pairs) {
        if (pair.section.offsetTop <= threshold) current = pair.section;
        else break;
      }
      setCurrent(current.id);
    };

    const scheduleUpdate = () => {
      if (navigationTarget) {
        clearTimeout(navigationTimer);
        navigationTimer = setTimeout(() => {
          navigationTarget = null;
          updateCurrent();
        }, 120);
        return;
      }
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => {
        updateCurrent();
        scheduled = false;
      });
    };

    for (const pair of pairs) {
      pair.link.addEventListener('click', () => {
        navigationTarget = pair.section.id;
        clearTimeout(navigationTimer);
        setCurrent(navigationTarget);
      });
    }
    addEventListener('scroll', scheduleUpdate, { passive: true });
    addEventListener('resize', scheduleUpdate);
    updateCurrent();
  };

  document.querySelectorAll('[data-section-nav]').forEach(initSectionNav);
})();
