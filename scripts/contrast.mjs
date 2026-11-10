// Palette check for a deck theme, used by deck_probe.mjs.
//
// PALETTE runs in the page and checks the theme roles the way a design
// system guarantees role pairs: text on its background, white on the
// accent fill, marks and data series against the page, and whether the
// data series stay apart, also for red-green color blindness.

const PAGE_COLOR = String.raw`
  // Any CSS color, oklch and display-p3 included, read back as sRGB by
  // painting one pixel.
  const paint = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
  const parseColor = (value) => {
    if (!value || value === 'transparent') return value === 'transparent' ? { r: 0, g: 0, b: 0, a: 0 } : null;
    paint.clearRect(0, 0, 1, 1);
    paint.fillStyle = '#000';
    paint.fillStyle = value;
    paint.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = paint.getImageData(0, 0, 1, 1).data;
    return { r, g, b, a: a / 255 };
  };`;

export const PALETTE = String.raw`(() => {
  ${PAGE_COLOR}
  // A missing or invalid role makes color fall back to the inherited one,
  // so the probe sits in a wrapper with a color no theme uses.
  const wrapper = document.createElement('b');
  wrapper.style.color = 'rgb(1, 2, 3)';
  const probe = wrapper.appendChild(document.createElement('i'));
  document.body.append(wrapper);
  const role = (name) => {
    probe.style.color = 'var(' + name + ')';
    const value = getComputedStyle(probe).color;
    return value === 'rgb(1, 2, 3)' ? null : parseColor(value);
  };
  const roles = {};
  for (const name of ['--craft-bg', '--craft-surface', '--craft-text', '--craft-text-body', '--craft-muted', '--craft-accent',
    '--craft-accent-mark', '--craft-accent-fill', '--craft-on-accent', '--craft-line-strong',
    '--craft-data-blue', '--craft-data-amber', '--craft-data-green']) roles[name] = role(name);
  wrapper.remove();
  return roles;
})()`;

const channel = (v) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const luminance = ({ r, g, b }) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
const blend = (top, bottom) => ({
  r: top.r * top.a + bottom.r * (1 - top.a),
  g: top.g * top.a + bottom.g * (1 - top.a),
  b: top.b * top.a + bottom.b * (1 - top.a),
  a: 1,
});
const ratio = (fg, bg) => {
  const solid = blend(fg, bg);
  const [l1, l2] = [luminance(solid), luminance(bg)];
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
};

// CIELAB distance between two colors, and the same after a simulation of
// deuteranopia (Machado et al. 2009, full severity, in linear RGB).
const toLab = ({ r, g, b }) => {
  const [lr, lg, lb] = [channel(r), channel(g), channel(b)];
  const x = (0.4124 * lr + 0.3576 * lg + 0.1805 * lb) / 0.95047;
  const y = 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
  const z = (0.0193 * lr + 0.1192 * lg + 0.9505 * lb) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))];
};
const distance = (a, b) => Math.hypot(...toLab(a).map((v, i) => v - toLab(b)[i]));
const deuteranopia = ({ r, g, b }) => {
  const [lr, lg, lb] = [channel(r), channel(g), channel(b)];
  const out = [0.367322 * lr + 0.860646 * lg - 0.227968 * lb, 0.280085 * lr + 0.672501 * lg + 0.047413 * lb, -0.01182 * lr + 0.04294 * lg + 0.968881 * lb];
  const back = (v) => 255 * (Math.max(0, Math.min(1, v)) <= 0.0031308 ? 12.92 * Math.max(0, v) : 1.055 * Math.min(1, v) ** (1 / 2.4) - 0.055);
  return { r: back(out[0]), g: back(out[1]), b: back(out[2]), a: 1 };
};

const PAIRS = [
  ['--craft-text', '--craft-bg', 4.5, 'heading text on the page'],
  ['--craft-text-body', '--craft-bg', 4.5, 'body text on the page'],
  ['--craft-muted', '--craft-bg', 4.5, 'muted labels on the page'],
  ['--craft-accent', '--craft-bg', 4.5, 'accent text on the page'],
  ['--craft-text', '--craft-surface', 4.5, 'text on a panel'],
  ['--craft-on-accent', '--craft-accent-fill', 4.5, 'text on the accent fill'],
  ['--craft-accent-mark', '--craft-bg', 3, 'accent marks on the page'],
  ['--craft-line-strong', '--craft-bg', 3, 'axes and strong lines on the page'],
  ['--craft-data-blue', '--craft-bg', 3, 'data series blue'],
  ['--craft-data-amber', '--craft-bg', 3, 'data series amber'],
  ['--craft-data-green', '--craft-bg', 3, 'data series green'],
];
const SERIES = ['--craft-accent-mark', '--craft-data-blue', '--craft-data-amber', '--craft-data-green'];

// Returns { errors, warnings } as plain messages for one theme.
export function judgePalette(roles, theme) {
  const errors = [];
  const warnings = [];
  const page = roles['--craft-bg'];
  for (const [name, value] of Object.entries(roles)) if (!value) errors.push(`${theme} theme: ${name} is not a color`);
  if (!page) return { errors, warnings };
  const opaque = (name, under) => (roles[name] ? blend(roles[name], under || page) : null);
  for (const [fg, bg, min, label] of PAIRS) {
    const back = opaque(bg);
    if (!roles[fg] || !back) continue;
    const value = ratio(roles[fg], back);
    if (value < min - 0.01) errors.push(`${theme} theme: ${label} is ${value.toFixed(2)}:1, needs ${min}:1 (${fg} on ${bg})`);
  }
  const series = SERIES.filter((name) => roles[name]).map((name) => [name, opaque(name)]);
  for (let i = 0; i < series.length; i += 1) {
    for (let j = i + 1; j < series.length; j += 1) {
      const [a, ca] = series[i];
      const [b, cb] = series[j];
      if (distance(ca, cb) < 15) errors.push(`${theme} theme: ${a} and ${b} are too close to tell apart`);
      else if (distance(deuteranopia(ca), deuteranopia(cb)) < 10) warnings.push(`${theme} theme: ${a} and ${b} merge for red-green color blindness; label the series, do not rely on color`);
    }
  }
  return { errors, warnings };
}
