/* ============================================================
   media.js: video playback and prewarming of nearby pages. It runs
   after deck.js, when the slides are already expanded into reveal
   steps.

   data-media sets the video role:
   demo     (default) starts from the beginning when the slide opens;
   scene    background of a shared scene. It keeps its position across
            pages with the same data-scene, hidden copies do not play;
   manual   never starts on its own, the video keeps its controls.

   Options: loop, data-playback-rate="1.5", data-rewind (after the end
   the video rewinds fast and starts again, data-rewind-ms sets the
   rewind length), data-sound (keep the sound on autoplay).

   Rules:
   - only the video on the open page plays, hidden ones stay paused.
     On a phone every playing video holds a hardware decoder;
   - between states of one slide and between pages of one scene the
     video keeps its position instead of starting over;
   - printing, a hidden tab and motion turned off pause the video and
     cancel the rewind;
   - a rejected play() is not silent. The manager retries after layout
     and on the next viewer gesture, and a blocked video gets controls.

   Prewarming: .deck[data-prewarm-images] (3 pages by default) and
   .deck[data-prewarm-videos] (1 page) set the radius. Beyond
   data-release-videos (4 pages) the manager releases a loaded video,
   so a long pass through the deck does not pile up decoders and
   memory. With data saver on, videos are not prewarmed.
   ============================================================ */

(() => {
  const deck = document.querySelector('.deck');
  const slidesRoot = deck?.querySelector('.slides');
  if (!slidesRoot || !window.craftDeck) return;

  const pages = [...slidesRoot.querySelectorAll(':scope > .slide')];
  const videos = [...slidesRoot.querySelectorAll('video')];
  const images = [...slidesRoot.querySelectorAll('img')];

  const number = (value, fallback) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
  };
  const connection = navigator.connection;
  const saveData = Boolean(connection?.saveData) || /(^|-)2g$/.test(connection?.effectiveType || '');
  const imageRadius = number(deck.dataset.prewarmImages, saveData ? 1 : 3);
  const videoRadius = saveData ? 0 : number(deck.dataset.prewarmVideos, 1);
  const releaseRadius = Math.max(videoRadius + 1, number(deck.dataset.releaseVideos, 4));

  const pageOf = (element) => element.closest('.slide');
  const indexOf = (element) => pages.indexOf(pageOf(element));
  const role = (video) => (['demo', 'scene', 'manual'].includes(video.dataset.media) ? video.dataset.media : video.dataset.scene ? 'scene' : 'demo');

  // The same recording on nearby pages: copies of one slide across
  // reveal steps, or an explicit shared scene.
  const identity = new Map();
  videos.forEach((video) => {
    const page = pageOf(video);
    const position = [...page.querySelectorAll('video')].indexOf(video);
    identity.set(video, video.dataset.scene ? `scene:${video.dataset.scene}` : `${page.dataset.key}:${position}`);
  });

  let printing = false;
  const addedControls = new WeakSet();
  const rewinds = new Map();
  const lastTime = new Map();

  function rate(video) {
    return number(video.dataset.playbackRate, 1) || 1;
  }

  function applyRate(video) {
    const value = rate(video);
    video.defaultPlaybackRate = value;
    if (video.playbackRate !== value) video.playbackRate = value;
  }

  videos.forEach((video) => {
    // The manager decides on autoplay, otherwise hidden copies start on their own.
    video.autoplay = false;
    video.removeAttribute('autoplay');
    video.playsInline = true;
    if (!('sound' in video.dataset)) {
      video.muted = true;
      video.defaultMuted = true;
    }
    if (role(video) === 'manual') video.controls = true;
    if ('rewind' in video.dataset) video.loop = false;
    applyRate(video);
    // Some browsers reset the rate to the default on load() and on loop.
    // Set it again on every start.
    video.addEventListener('loadedmetadata', () => applyRate(video));
    video.addEventListener('play', () => applyRate(video));
    video.addEventListener('ended', () => {
      if ('rewind' in video.dataset) startRewind(video);
    });
    video.addEventListener('timeupdate', () => {
      if (!video.paused) lastTime.set(identity.get(video), video.currentTime);
    });
  });

  const motionActive = () => window.craftDeck.motion.active;
  const isActive = (video) => pageOf(video)?.hasAttribute('data-active') ?? false;
  const canPlay = () => !printing && !document.hidden && motionActive();

  function stopRewind(video) {
    const frame = rewinds.get(video);
    if (frame) cancelAnimationFrame(frame);
    rewinds.delete(video);
    pageOf(video)?.classList.remove('is-rewinding');
  }

  function startRewind(video) {
    if (!isActive(video) || !canPlay()) return;
    const total = number(video.dataset.rewindMs, 900);
    const from = video.duration || video.currentTime;
    const startedAt = performance.now();
    pageOf(video).classList.add('is-rewinding');
    const step = (now) => {
      if (!isActive(video) || !canPlay()) {
        stopRewind(video);
        return;
      }
      const progress = total === 0 ? 1 : Math.min(1, (now - startedAt) / total);
      const eased = 1 - (1 - progress) ** 3;
      video.currentTime = from * (1 - eased);
      if (progress < 1) {
        rewinds.set(video, requestAnimationFrame(step));
      } else {
        stopRewind(video);
        video.currentTime = 0;
        play(video);
      }
    };
    rewinds.set(video, requestAnimationFrame(step));
  }

  function markBlocked(video, blocked) {
    video.toggleAttribute('data-media-blocked', blocked);
    if (blocked && !video.controls) {
      video.controls = true;
      addedControls.add(video);
    } else if (!blocked && addedControls.has(video) && role(video) !== 'manual') {
      video.controls = false;
      addedControls.delete(video);
    }
  }

  function play(video) {
    restore(video);
    applyRate(video);
    const attempt = video.play();
    if (!attempt) return;
    attempt.then(() => markBlocked(video, false)).catch((error) => {
      // AbortError means the video was already paused when the page closed.
      if (error?.name !== 'AbortError' && isActive(video) && canPlay() && role(video) !== 'scene') markBlocked(video, true);
    });
  }

  function pause(video) {
    stopRewind(video);
    if (!video.paused) video.pause();
  }

  // The previously open page. The new copy takes its position from there.
  let previousPage = null;

  function enter(page) {
    const incoming = [...page.querySelectorAll('video')];
    for (const video of incoming) {
      if (role(video) === 'manual') continue;
      const key = identity.get(video);
      const predecessor = previousPage && [...previousPage.querySelectorAll('video')].find((item) => identity.get(item) === key);
      try {
        if (predecessor && predecessor.readyState > 0) {
          video.currentTime = predecessor.currentTime;
        } else if (role(video) === 'scene' && lastTime.has(key)) {
          video.currentTime = lastTime.get(key);
        } else {
          video.currentTime = 0;
        }
      } catch {
        // The position is not available yet, so the video starts from the beginning.
      }
    }
  }

  function sync() {
    for (const video of videos) {
      if (!isActive(video) || !canPlay()) {
        pause(video);
        continue;
      }
      if (role(video) === 'manual') continue;
      if (video.paused && !rewinds.has(video)) play(video);
    }
    if (!motionActive()) {
      // With motion off the video does not start on its own, but the viewer
      // can start it. A scene background needs no controls, it is decoration.
      videos.filter((video) => isActive(video) && role(video) !== 'scene').forEach((video) => markBlocked(video, true));
    }
  }

  function retry() {
    if (!canPlay()) return;
    for (const video of videos) {
      if (isActive(video) && video.paused && role(video) !== 'manual' && !rewinds.has(video)) play(video);
    }
  }

  function syncLater() {
    sync();
    requestAnimationFrame(retry);
    setTimeout(retry, 400);
  }

  // ---------- prewarming and release ----------

  const warmedImages = new WeakSet();

  function release(video) {
    if (isActive(video) || !video.paused || video.hasAttribute('data-media-released')) return;
    if (video.readyState === 0 && video.networkState !== HTMLMediaElement.NETWORK_LOADING) return;
    const sources = [video, ...video.querySelectorAll('source')];
    sources.forEach((element) => {
      const value = element.getAttribute('src');
      if (value) {
        element.dataset.mediaSrc = value;
        element.removeAttribute('src');
      }
    });
    video.setAttribute('data-media-released', '');
    video.preload = 'none';
    video.load();
  }

  function restore(video) {
    if (!video.hasAttribute('data-media-released')) return;
    [video, ...video.querySelectorAll('source')].forEach((element) => {
      if (element.dataset.mediaSrc) {
        element.setAttribute('src', element.dataset.mediaSrc);
        delete element.dataset.mediaSrc;
      }
    });
    video.removeAttribute('data-media-released');
    video.load();
  }

  function warmVideo(video) {
    if (!video.paused) return;
    restore(video);
    if (video.preload !== 'auto') {
      video.preload = 'auto';
      if (video.readyState < HTMLMediaElement.HAVE_FUTURE_DATA) video.load();
    }
  }

  function warmImage(image) {
    if (warmedImages.has(image)) return;
    warmedImages.add(image);
    image.loading = 'eager';
    image.decode?.().catch(() => {});
  }

  function prewarm(current) {
    const reach = Math.max(imageRadius, releaseRadius);
    // Nearest pages first. On a slow network the next slide gets
    // bandwidth before a distant one.
    for (let distance = 0; distance <= reach; distance += 1) {
      for (const index of distance ? [current + distance, current - distance] : [current]) {
        const page = pages[index];
        if (!page) continue;
        if (distance <= imageRadius) page.querySelectorAll('img').forEach(warmImage);
        if (distance <= videoRadius) page.querySelectorAll('video').forEach(warmVideo);
      }
    }
    videos.forEach((video) => {
      if (Math.abs(indexOf(video) - current) > releaseRadius) release(video);
    });
  }

  // A contained frame gets its own aspect ratio so the border follows it
  // instead of staying wider. See .frame > .media-contain in the theme.
  function fit(element) {
    const width = element.naturalWidth || element.videoWidth;
    const height = element.naturalHeight || element.videoHeight;
    if (width && height) element.style.setProperty('--media-ratio', String(width / height));
  }
  slidesRoot.querySelectorAll('.frame > .media-contain').forEach((element) => {
    fit(element);
    element.addEventListener(element.tagName === 'VIDEO' ? 'loadedmetadata' : 'load', () => fit(element));
  });
  // The wipe uses the aspect ratio of its first frame for the whole area.
  slidesRoot.querySelectorAll('.wipe').forEach((wipe) => {
    const first = wipe.querySelector('.wipe-before');
    if (!first) return;
    const apply = () => {
      const width = first.naturalWidth || first.videoWidth;
      const height = first.naturalHeight || first.videoHeight;
      if (width && height) wipe.style.setProperty('--media-ratio', String(width / height));
    };
    apply();
    first.addEventListener(first.tagName === 'VIDEO' ? 'loadedmetadata' : 'load', apply);
  });

  // Distant videos do not download on page load.
  const initial = pages.findIndex((page) => page.hasAttribute('data-active'));
  videos.forEach((video) => {
    if (Math.abs(indexOf(video) - initial) > videoRadius) video.preload = 'none';
  });
  images.forEach((image) => {
    if (Math.abs(indexOf(image) - initial) > imageRadius && !image.hasAttribute('loading')) image.loading = 'lazy';
  });

  addEventListener('craft-slidechange', (event) => {
    const page = event.detail.slide;
    enter(page);
    previousPage = page;
    prewarm(pages.indexOf(page));
    syncLater();
  });
  addEventListener('craft-motionchange', syncLater);
  for (const type of ['touchend', 'pointerup', 'click', 'keydown']) {
    document.addEventListener(type, retry, { capture: true, passive: true });
  }
  document.addEventListener('visibilitychange', sync);
  addEventListener('beforeprint', () => { printing = true; sync(); });
  addEventListener('afterprint', () => { printing = false; syncLater(); });

  window.craftMedia = Object.freeze({
    radius: { images: imageRadius, videos: videoRadius, release: releaseRadius },
    state: () => videos.map((video) => ({
      page: indexOf(video) + 1,
      identity: identity.get(video),
      role: role(video),
      active: isActive(video),
      paused: video.paused,
      currentTime: video.currentTime,
      duration: Number.isFinite(video.duration) ? video.duration : null,
      loop: video.loop || 'rewind' in video.dataset,
      playbackRate: video.playbackRate,
      expectedRate: rate(video),
      readyState: video.readyState,
      released: video.hasAttribute('data-media-released'),
      blocked: video.hasAttribute('data-media-blocked'),
      poster: Boolean(video.getAttribute('poster')),
    })),
  });

  if (initial >= 0) {
    previousPage = pages[initial];
    enter(pages[initial]);
    prewarm(initial);
  }
  syncLater();
})();
