// Simplified network and signal glyphs for the architecture slides, drawn as SVG and rasterized to PNG.
// Each export resolves to { data, aspect } where aspect = width / height of the drawing.

const sharp = require("sharp");

const GRAY = { front: "#D9D9D9", top: "#EDEDED", side: "#B8B8B8", line: "#404040" };
const REDT = { front: "#EDB8B8", top: "#F6D8D8", side: "#D48A8A", line: "#7A0000" };
const RED = "#A00000", BLUE = "#1F4E79", DARK = "#404040", LIGHT = "#A6A6A6";

async function render(svgBody, w, h) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w * 4}" height="${h * 4}" viewBox="0 0 ${w} ${h}">${svgBody}</svg>`;
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return { data: "image/png;base64," + buf.toString("base64"), aspect: w / h };
}

function cuboid(x, y, w, h, d, c, extra = "") {
  return `
    <polygon points="${x},${y} ${x + d},${y - d} ${x + w + d},${y - d} ${x + w},${y}" fill="${c.top}" stroke="${c.line}" stroke-width="1.2"/>
    <polygon points="${x + w},${y} ${x + w + d},${y - d} ${x + w + d},${y + h - d} ${x + w},${y + h}" fill="${c.side}" stroke="${c.line}" stroke-width="1.2"/>
    <rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${c.front}" stroke="${c.line}" stroke-width="1.2"/>${extra}`;
}

function arrow(x1, y, x2, color = DARK) {
  return `<line x1="${x1}" y1="${y}" x2="${x2 - 5}" y2="${y}" stroke="${color}" stroke-width="1.6"/>
    <polygon points="${x2},${y} ${x2 - 7},${y - 4} ${x2 - 7},${y + 4}" fill="${color}"/>`;
}

function lockGlyph(x, y, s = 1) {
  return `<g transform="translate(${x},${y}) scale(${s})">
    <path d="M6 14 V9 a8 8 0 0 1 16 0 V14" fill="none" stroke="${RED}" stroke-width="3"/>
    <rect x="2" y="14" width="24" height="18" rx="3" fill="${RED}"/>
    <circle cx="14" cy="22" r="3" fill="#FFFFFF"/></g>`;
}

// Deterministic pseudo-noise: sum of sines.
function noise(t, seed) {
  return Math.sin(2 * Math.PI * (7 + seed) * t + seed) * 0.5 + Math.sin(2 * Math.PI * (13 + 2 * seed) * t + 2 * seed) * 0.3
    + Math.sin(2 * Math.PI * (23 + seed) * t + 3 * seed) * 0.2;
}
function erp(t) {        // biphasic, lateralization-like shape
  return -0.8 * Math.exp(-(((t - 0.25) / 0.08) ** 2)) + 1.0 * Math.exp(-(((t - 0.55) / 0.09) ** 2));
}
function path(fn, x0, w, y0, amp, n = 80) {
  let d = "";
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    d += `${i ? "L" : "M"}${(x0 + t * w).toFixed(1)} ${(y0 - amp * fn(t)).toFixed(1)} `;
  }
  return d;
}

// ---------- signals ----------
exports.traces = async (kind) => {
  const W = 200, H = 110;
  let body = "";
  if (kind === "group") {
    for (let i = 0; i < 4; i++) {
      body += `<path d="${path((t) => noise(t, i + 1) + 0.6 * erp(t), 6, W - 12, 18 + i * 25, 9)}" fill="none" stroke="${DARK}" stroke-width="1.6"/>`;
    }
  } else if (kind === "single") {
    body += `<path d="${path((t) => noise(t, 3) * 1.3 + 0.4 * erp(t), 6, W - 12, H / 2, 28)}" fill="none" stroke="${DARK}" stroke-width="2"/>`;
  } else if (kind === "average") {
    for (let i = 0; i < 3; i++) {
      body += `<path d="${path((t) => noise(t, i + 2) + 0.6 * erp(t), 6, W - 12, H / 2, 22)}" fill="none" stroke="${LIGHT}" stroke-width="1.2" opacity="0.8"/>`;
    }
    body += `<path d="${path(erp, 6, W - 12, H / 2, 32)}" fill="none" stroke="${RED}" stroke-width="3.2"/>`;
  } else if (kind === "recon") {
    body += `<path d="${path(erp, 6, W - 12, H / 2, 32)}" fill="none" stroke="${LIGHT}" stroke-width="2.2" stroke-dasharray="6 4"/>`;
    body += `<path d="${path((t) => 0.85 * erp(t) + 0.08 * noise(t, 5), 6, W - 12, H / 2, 32)}" fill="none" stroke="${RED}" stroke-width="3"/>`;
  }
  return render(body, W, H);
};

// Antisymmetric (left and right hemisphere opposite) or symmetric (same) stream.
exports.hemiTraces = async (kind) => {
  const W = 200, H = 90;
  const s = kind === "anti" ? -1 : 1;
  const body = `
    <path d="${path(erp, 6, W - 12, H / 2, 30)}" fill="none" stroke="${RED}" stroke-width="2.8"/>
    <path d="${path((t) => s * erp(t) * 0.92, 6, W - 12, H / 2, 30)}" fill="none" stroke="${BLUE}" stroke-width="2.8" ${kind === "sym" ? 'stroke-dasharray="7 4"' : ""}/>
    <line x1="6" y1="${H / 2}" x2="${W - 6}" y2="${H / 2}" stroke="${LIGHT}" stroke-width="1"/>`;
  return render(body, W, H);
};

// ---------- networks ----------
// EEGNet: temporal conv -> depthwise spatial conv -> separable conv (three blocks of shrinking size).
exports.eegnet = async ({ tint = false, lock = false } = {}) => {
  const W = 250, H = 110, c = tint ? REDT : GRAY;
  let body = cuboid(8, 22, 20, 80, 14, c) + cuboid(34, 22, 6, 80, 14, c)       // temporal filter bank
    + arrow(58, 62, 84)
    + cuboid(88, 34, 34, 56, 12, c)
    + arrow(140, 62, 164)
    + cuboid(168, 46, 40, 34, 10, c);
  if (lock) body += lockGlyph(214, 4, 1.05);
  return render(body, W, H);
};

// Fully connected classifier head.
exports.fc = async () => {
  const W = 130, H = 110, ins = [15, 38, 61, 84], outs = [35, 70];
  let body = "";
  ins.forEach((y) => outs.forEach((o) => { body += `<line x1="22" y1="${y + 6}" x2="104" y2="${o + 6}" stroke="${LIGHT}" stroke-width="1.2"/>`; }));
  ins.forEach((y) => { body += `<circle cx="22" cy="${y + 6}" r="8" fill="#D9D9D9" stroke="${DARK}" stroke-width="1.4"/>`; });
  outs.forEach((y, i) => { body += `<circle cx="104" cy="${y + 6}" r="10" fill="${i ? "#C9D6E3" : "#EDB8B8"}" stroke="${DARK}" stroke-width="1.4"/>`; });
  return render(body, W, H);
};

// Linear ERP decoder: virtual sources -> upsampled time courses -> channels (expanding).
exports.decoder = async () => {
  const W = 200, H = 90;
  let body = `<polygon points="10,32 190,6 190,84 10,58" fill="#F2F2F2" stroke="${DARK}" stroke-width="1.6" stroke-dasharray="6 4"/>`;
  for (let i = 1; i < 6; i++) {
    const x = 10 + i * 30, top = 32 - (26 * i) / 6, bot = 58 + (26 * i) / 6;
    body += `<line x1="${x}" y1="${top + 2}" x2="${x}" y2="${bot - 2}" stroke="${LIGHT}" stroke-width="1"/>`;
  }
  return render(body, W, H);
};

// Small MLP (router).
exports.mlp = async () => {
  const W = 150, H = 100, layers = [[20, 50, 80], [12, 37, 63, 88], [30, 70]], xs = [20, 75, 130];
  let body = "";
  for (let l = 0; l < 2; l++) layers[l].forEach((a) => layers[l + 1].forEach((b) => {
    body += `<line x1="${xs[l]}" y1="${a}" x2="${xs[l + 1]}" y2="${b}" stroke="#D48A8A" stroke-width="1.1"/>`;
  }));
  layers.forEach((ys, l) => ys.forEach((y) => {
    body += `<circle cx="${xs[l]}" cy="${y}" r="8" fill="${l === 2 ? RED : "#F6D8D8"}" stroke="${RED}" stroke-width="1.4"/>`;
  }));
  return render(body, W, H);
};

// Gate weights: soft top-2 (two experts active, one near zero).
exports.gate = async () => {
  const W = 110, H = 90, hs = [62, 30, 4], cols = [RED, "#D48A8A", "#D9D9D9"];
  let body = `<line x1="8" y1="78" x2="102" y2="78" stroke="${DARK}" stroke-width="1.4"/>`;
  hs.forEach((h, i) => { body += `<rect x="${16 + i * 30}" y="${78 - h}" width="20" height="${h}" fill="${cols[i]}" stroke="${DARK}" stroke-width="1"/>`; });
  return render(body, W, H);
};

// Descriptor features (small bar / waveform readout).
exports.descriptors = async () => {
  const W = 120, H = 90, hs = [40, 64, 28, 52];
  let body = `<line x1="8" y1="80" x2="112" y2="80" stroke="${DARK}" stroke-width="1.4"/>`;
  hs.forEach((h, i) => { body += `<rect x="${14 + i * 25}" y="${80 - h}" width="16" height="${h}" fill="#BFBFBF" stroke="${DARK}" stroke-width="1"/>`; });
  return render(body, W, H);
};

// Top view of the head: posterior electrodes, midline and the mirror operator.
exports.head = async () => {
  const W = 170, H = 170, cx = 85, cy = 88, r = 66;
  let body = `<polygon points="${cx - 10},${cy - r + 2} ${cx},${cy - r - 14} ${cx + 10},${cy - r + 2}" fill="#FFFFFF" stroke="${DARK}" stroke-width="2"/>
    <ellipse cx="${cx - r - 4}" cy="${cy}" rx="6" ry="14" fill="#FFFFFF" stroke="${DARK}" stroke-width="2"/>
    <ellipse cx="${cx + r + 4}" cy="${cy}" rx="6" ry="14" fill="#FFFFFF" stroke="${DARK}" stroke-width="2"/>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="#FFFFFF" stroke="${DARK}" stroke-width="2.2"/>
    <line x1="${cx}" y1="${cy - r}" x2="${cx}" y2="${cy + r}" stroke="${LIGHT}" stroke-width="1.6" stroke-dasharray="5 4"/>`;
  const rows = [[cy + 10, [18, 32, 46]], [cy + 28, [16, 30, 44]], [cy + 46, [14, 28]]];
  rows.forEach(([y, offs]) => {
    offs.forEach((o) => {
      body += `<circle cx="${cx - o}" cy="${y}" r="5" fill="${RED}"/><circle cx="${cx + o}" cy="${y}" r="5" fill="${BLUE}"/>`;
    });
    body += `<circle cx="${cx}" cy="${y}" r="5" fill="${LIGHT}"/>`;
  });
  body += `<path d="M${cx - 34} ${cy - 22} Q ${cx} ${cy - 44} ${cx + 34} ${cy - 22}" fill="none" stroke="${DARK}" stroke-width="2"/>
    <polygon points="${cx - 38},${cy - 18} ${cx - 34},${cy - 28} ${cx - 27},${cy - 20}" fill="${DARK}"/>
    <polygon points="${cx + 38},${cy - 18} ${cx + 34},${cy - 28} ${cx + 27},${cy - 20}" fill="${DARK}"/>`;
  return render(body, W, H);
};

// Shared temporal convolution: a tall bank of temporal kernels.
exports.filterBank = async () => {
  const W = 90, H = 230;
  let body = "";
  for (let i = 0; i < 4; i++) body += cuboid(10 + i * 14, 30 + i * 4, 10, 180 - i * 8, 12, GRAY);
  return render(body, W, H);
};

// Expert module: spatial conv + separable conv (two blocks).
exports.expert = async (tint = false) => {
  const W = 150, H = 80, c = tint ? REDT : GRAY;
  const body = cuboid(8, 18, 34, 54, 10, c) + arrow(56, 45, 80) + cuboid(84, 28, 40, 34, 10, c);
  return render(body, W, H);
};
