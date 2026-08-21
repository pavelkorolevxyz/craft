const links = [...document.querySelectorAll('.system-links a')];
const sections = links
  .map((link) => document.querySelector(link.hash))
  .filter(Boolean);

if (links.length && sections.length) {
  let currentId;
  const setCurrent = (id) => {
    if (id === currentId) return;
    currentId = id;

    let currentLink;
    for (const link of links) {
      if (link.hash === `#${id}`) {
        link.setAttribute('aria-current', 'true');
        currentLink = link;
      } else {
        link.removeAttribute('aria-current');
      }
    }

    if (currentLink && matchMedia('(max-width: 900px)').matches) {
      const container = currentLink.parentElement;
      const left = currentLink.offsetLeft - (container.clientWidth - currentLink.offsetWidth) / 2;
      container.scrollTo({
        left,
        behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
      });
    }
  };

  const updateCurrent = () => {
    const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
    if (atBottom) {
      setCurrent(sections.at(-1).id);
      return;
    }

    const threshold = window.scrollY + Math.min(180, window.innerHeight * 0.3);
    let current = sections[0];
    for (const section of sections) {
      if (section.offsetTop <= threshold) current = section;
      else break;
    }
    setCurrent(current.id);
  };

  let scheduled = false;
  let navigationTarget = null;
  let navigationTimer;

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

  links.forEach((link) => link.addEventListener('click', () => {
    navigationTarget = link.hash.slice(1);
    clearTimeout(navigationTimer);
    setCurrent(navigationTarget);
  }));
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', scheduleUpdate);
  updateCurrent();
}
