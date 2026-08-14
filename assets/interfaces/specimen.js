const links = [...document.querySelectorAll('.system-links a')];
const sections = links
  .map((link) => document.querySelector(link.hash))
  .filter(Boolean);

if (links.length && sections.length) {
  const setCurrent = (id) => {
    for (const link of links) {
      if (link.hash === `#${id}`) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
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
  const scheduleUpdate = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      updateCurrent();
      scheduled = false;
    });
  };

  links.forEach((link) => link.addEventListener('click', () => setCurrent(link.hash.slice(1))));
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', scheduleUpdate);
  updateCurrent();
}
