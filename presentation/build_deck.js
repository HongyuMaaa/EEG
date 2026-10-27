// Mid-term defense deck (sample: opening, Part 1 and the start of Part 2).
// Conventional academic style: red title banner, outline slides between parts,
// figures/tables with a text column, references at the bottom.
// Usage: NODE_PATH=<dir with pptxgenjs> node build_deck.js [out.pptx] [apply_theme.js]

const path = require("path");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");

const OUT = process.argv[2] || path.join(__dirname, "midterm_defense_sample.pptx");
const APPLY_THEME = process.argv[3];

// ---------- Theme ----------
// Change RED to your university's colour; everything else follows it.
const HEX = {
  red: "A00000", black: "000000", white: "FFFFFF", gray: "7F7F7F",
  light: "F2F2F2", rule: "BFBFBF", dark: "262626",
};
const THEME = {
  name: "Thesis Defense",
  headFontFace: "Times New Roman",
  bodyFontFace: "Times New Roman",
  colors: {
    dk1: HEX.black, lt1: HEX.white, dk2: HEX.red, lt2: HEX.light,
    accent1: HEX.red, accent2: HEX.dark, accent3: HEX.gray,
    accent4: HEX.rule, accent5: "595959", accent6: "C00000",
    hlink: HEX.red, folHlink: HEX.gray,
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Mid-term Thesis Defense";
const C = pres.SchemeColor;
const W = 13.333;

// Logo slot (top right) and bottom rule, shared by all layouts.
const logoSlot = () => [
  { rect: { x: 10.35, y: 0.3, w: 2.6, h: 0.8, fill: { color: HEX.white },
    line: { color: HEX.rule, width: 0.75, dashType: "dash" } } },
  { text: { text: "[University logo]", options: { x: 10.35, y: 0.3, w: 2.6, h: 0.8,
    fontSize: 12, color: C.accent3, align: "center", valign: "middle" } } },
];
const bottomRule = { rect: { x: 0, y: 7.42, w: W, h: 0.08, fill: { color: HEX.red }, line: { type: "none" } } };
const slideNo = { x: 12.35, y: 6.98, w: 0.65, h: 0.35, fontSize: 14, color: C.text1, align: "right" };

// ---------- Layouts ----------
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: HEX.white },
  objects: [
    ...logoSlot(), bottomRule,
    { placeholder: { options: { name: "title", type: "title", x: 0.9, y: 1.8, w: 11.5, h: 2.0,
      fontSize: 36, bold: true, color: C.accent1, align: "center", valign: "middle", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: 2.5, y: 4.55, w: 8.3, h: 1.6,
      fontSize: 20, color: C.text1, align: "center", valign: "top", margin: 0 }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "OUTLINE",
  background: { color: HEX.white },
  objects: [
    ...logoSlot(), bottomRule,
    { rect: { x: 0, y: 0, w: 4.1, h: 7.42, fill: { color: HEX.red }, line: { type: "none" } } },
    { text: { text: "Outline", options: { x: 0.3, y: 3.0, w: 3.5, h: 1.0, fontSize: 40, bold: true,
      color: C.background1, align: "center", valign: "middle" } } },
  ],
  slideNumber: slideNo,
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.white },
  margin: [0.4, 0.35, 0.6, 0.35],
  objects: [
    ...logoSlot(), bottomRule,
    { rect: { x: 0.35, y: 0.3, w: 9.0, h: 0.82, fill: { color: HEX.red }, line: { type: "none" },
      shadow: { type: "outer", angle: 90, blur: 4, offset: 2, color: "000000", opacity: 0.35 } } },
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 8.75, h: 0.82,
      fontSize: 28, bold: true, color: C.background1, align: "left", valign: "middle", margin: 0 }, text: "" } },
  ],
  slideNumber: slideNo,
});

// ---------- Helpers ----------
const SECTIONS = [
  "Research Background and Objectives",
  "Research Progress and Stage Achievements",
  "Next-stage Research Plan",
  "Project Schedule",
];
const sectionTitle = (i) => `${i + 1} ${SECTIONS[i]}`;

function outlineSlide(active, notes) {
  const s = pres.addSlide({ masterName: "OUTLINE", sectionTitle: SECTIONS[active] });
  s.addText(SECTIONS.map((t, i) => ({ text: t, options: {
    bullet: true, color: i === active ? HEX.red : HEX.black, breakLine: i < SECTIONS.length - 1 } })), {
    objectName: "Outline list", x: 4.8, y: 2.1, w: 7.8, h: 3.2, fontSize: 26, valign: "middle",
    paraSpaceAfter: 18, margin: 0, isTextBox: true });
  s.addNotes(notes);
}

function reference(slide, text) {
  slide.addText(text, { objectName: "Reference", x: 0.35, y: 6.95, w: 11.6, h: 0.4,
    fontSize: 12, color: C.accent3, valign: "bottom", margin: 0, isTextBox: true });
}

function text(slide, name, runs, opts) {
  slide.addText(runs, { objectName: name, color: C.text1, margin: 0, valign: "top", isTextBox: true, ...opts });
}

function arrowDown(slide, name, x, y, h) {
  slide.addShape(pres.shapes.LINE, { objectName: name, x, y, w: 0, h,
    line: { color: HEX.black, width: 1.5, endArrowType: "triangle" } });
}

function arrowRight(slide, name, x, y, w) {
  slide.addShape(pres.shapes.LINE, { objectName: name, x, y, w, h: 0,
    line: { color: HEX.black, width: 1.25, endArrowType: "triangle" } });
}

// Mini stimulus screen: dark rectangle, fixation cross, optional lit stimulus on one side.
function screen(slide, name, x, y, w, h, lit) {
  slide.addShape(pres.shapes.RECTANGLE, { objectName: name, x, y, w, h,
    fill: { color: HEX.dark }, line: { type: "none" } });
  const fs = Math.max(10, Math.round(h * 22));
  slide.addText("+", { objectName: name + " fixation", x: x + w / 2 - 0.2, y: y + h / 2 - 0.2, w: 0.4, h: 0.4,
    fontSize: fs, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
  const sq = Math.max(0.06, h * 0.07), off = w * 0.17;
  ["L", "R"].forEach((side) => {
    if (lit && lit !== side) return;
    const cx = side === "L" ? x + w / 2 - off - sq : x + w / 2 + off;
    slide.addShape(pres.shapes.RECTANGLE, { objectName: `${name} ${side} stimulus`, x: cx, y: y + h / 2 - sq / 2,
      w: sq, h: sq, fill: { color: HEX.white }, line: { type: "none" } });
  });
}

// Schematic workspace (table, robotic arm, two objects) as a PNG, 16:10.
async function workspaceScene() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 800 500">
    <rect width="800" height="500" fill="#F4F4F4"/>
    <rect y="360" width="800" height="140" fill="#E3E3E3"/>
    <line x1="0" y1="360" x2="800" y2="360" stroke="#BFBFBF" stroke-width="3"/>
    <path d="M250 360 L350 360 L335 328 L265 328 Z" fill="#595959"/>
    <line x1="300" y1="330" x2="380" y2="190" stroke="#8C8C8C" stroke-width="24" stroke-linecap="round"/>
    <line x1="380" y1="190" x2="500" y2="255" stroke="#8C8C8C" stroke-width="20" stroke-linecap="round"/>
    <circle cx="300" cy="330" r="17" fill="#404040"/><circle cx="380" cy="190" r="16" fill="#404040"/>
    <circle cx="500" cy="255" r="13" fill="#404040"/>
    <line x1="492" y1="266" x2="484" y2="302" stroke="#404040" stroke-width="7" stroke-linecap="round"/>
    <line x1="508" y1="266" x2="516" y2="302" stroke="#404040" stroke-width="7" stroke-linecap="round"/>
    <rect x="478" y="315" width="44" height="44" fill="#A00000"/>
    <rect x="610" y="300" width="42" height="60" rx="4" fill="#7F7F7F"/>
  </svg>`;
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// Booktabs-style table cell: rules only where asked.
function cell(textVal, { top = 0, bottom = 0, bold = false, color = HEX.black, align = "left", fontSize = 16 } = {}) {
  const b = (pt) => (pt ? { type: "solid", pt, color: HEX.black } : { type: "none" });
  return { text: textVal, options: { bold, color, align, fontSize, valign: "middle",
    border: [b(top), { type: "none" }, b(bottom), { type: "none" }] } };
}

(async () => {
  // ===== 1. Title =====
  pres.addSection({ title: "Opening" });
  {
    const s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Opening" });
    s.addText("Decoding Miniature Asymmetric Visual Evoked Potentials with EEGNet-Based Methods",
      { placeholder: "title" });
    s.addText([
      { text: "[Your Name]", options: { breakLine: true } },
      { text: "Supervisor: [Supervisor Name]", options: { breakLine: true } },
      { text: "[Date]" },
    ], { placeholder: "meta", paraSpaceAfter: 8 });
    s.addNotes("~10 s. Greet the committee and state the thesis title.");
  }

  // ===== 2. Outline =====
  pres.addSection({ title: SECTIONS[0] });
  outlineSlide(0, "~5 s. Four parts: background and objectives, progress, next-stage plan, schedule.");

  // ===== 3. Background: visual BCI paradigms =====
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTIONS[0] });
    s.addText(sectionTitle(0), { placeholder: "title" });

    // Three panels: the same robotic-arm workspace seen through each paradigm's stimulus layout.
    const pw = 3.95, ph = 2.47, gap = 0.2, py = 1.72;
    const pxs = [0, 1, 2].map((i) => 0.55 + i * (pw + gap));
    const scene = await workspaceScene();
    const heads = ["(a) SSVEP [1]", "(b) Oddball (P300) [2]", "(c) aVEP [3]"];
    pxs.forEach((px, i) => {
      text(s, `Panel ${i} head`, heads[i], { x: px, y: 1.27, w: pw, h: 0.4, fontSize: 16, bold: true,
        align: "center", valign: "middle" });
      s.addImage({ objectName: `Panel ${i} scene`, data: scene, x: px, y: py, w: pw, h: ph,
        altText: "Schematic workspace: robotic arm and objects on a table" });
    });

    // (a) SSVEP: 12 large targets, each flickering at its own frequency
    {
      const px = pxs[0], cw = 0.72, ch = 0.56, gx = (pw - 4 * cw) / 5, gy = (ph - 3 * ch) / 4;
      for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++) {
        const f = (8 + 0.5 * (r * 4 + c)).toFixed(1);
        s.addText(`${f} Hz`, { objectName: `SSVEP target ${r * 4 + c}`, shape: pres.shapes.RECTANGLE,
          x: px + gx + c * (cw + gx), y: py + gy + r * (ch + gy), w: cw, h: ch,
          fill: { color: HEX.white }, line: { color: "A6A6A6", width: 0.75 },
          fontSize: 11, color: C.text1, align: "center", valign: "middle", margin: 0 });
      }
    }

    // (b) Oddball: 6 x 6 symbol matrix, one row intensified
    {
      const mx = pxs[1] + 0.35, mw = pw - 0.7, my = py + 0.12, mh = ph - 0.24;
      s.addShape(pres.shapes.RECTANGLE, { objectName: "P300 matrix bg", x: mx, y: my, w: mw, h: mh,
        fill: { color: "1A1A1A" }, line: { type: "none" } });
      const sym = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789_";
      const cw = mw / 6, ch = mh / 6, flash = 2;
      s.addShape(pres.shapes.RECTANGLE, { objectName: "P300 flashed row", x: mx, y: my + flash * ch, w: mw, h: ch,
        fill: { color: "595959" }, line: { type: "none" } });
      for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) {
        s.addText(sym[r * 6 + c], { objectName: `P300 cell ${r * 6 + c}`, x: mx + c * cw, y: my + r * ch, w: cw, h: ch,
          fontSize: 13, bold: r === flash, color: r === flash ? HEX.white : "8C8C8C",
          align: "center", valign: "middle", margin: 0, isTextBox: true });
      }
    }

    // (c) aVEP: small command labels with miniature lateral stimuli; the scene stays visible
    {
      const px = pxs[2], cmds = ["↑", "↓", "←", "→", "Grasp"];
      const cw = (pw - 0.3) / cmds.length, y = py + ph - 0.32;
      cmds.forEach((cmd, i) => {
        const x = px + 0.15 + i * cw;
        text(s, `aVEP command ${i}`, cmd, { x, y, w: cw, h: 0.24, fontSize: 11, align: "center", valign: "middle" });
        const half = cmd.length > 1 ? 0.2 : 0.07, sq = 0.05;
        [x + cw / 2 - half - 0.04 - sq, x + cw / 2 + half + 0.04].forEach((sx, j) =>
          s.addShape(pres.shapes.RECTANGLE, { objectName: `aVEP stimulus ${i}${j ? "R" : "L"}`,
            x: sx, y: y + 0.12 - sq / 2, w: sq, h: sq, fill: { color: HEX.red }, line: { type: "none" } }));
      });
    }

    // Panel captions: what the stimuli are, and the visual burden
    const caps = [
      ["Large flickering targets, one frequency each", "High visual burden: view largely occluded", HEX.red],
      ["Flashing rows / columns of a symbol matrix", "High visual burden: view largely occluded", HEX.red],
      ["Miniature stimuli beside each command", "Low visual burden: environment stays visible", "1E7B34"],
    ];
    pxs.forEach((px, i) => text(s, `Panel ${i} caption`, [
      { text: caps[i][0], options: { breakLine: true } },
      { text: caps[i][1], options: { bold: true, color: caps[i][2] } },
    ], { x: px, y: py + ph + 0.06, w: pw, h: 0.62, fontSize: 14, align: "center" }));

    // Bottom left: how aVEP encodes a command bit (this thesis decodes it)
    const by = 4.98, bh = 1.47;
    s.addShape(pres.shapes.RECTANGLE, { objectName: "Coding panel", x: 0.55, y: by, w: 6.0, h: bh,
      fill: { color: HEX.light }, line: { type: "none" } });
    text(s, "Coding head", "aVEP coding [3]: stimulus order = code", { x: 0.75, y: by + 0.1, w: 5.6, h: 0.35, fontSize: 16, bold: true });
    [["L", "R", "= code 0"], ["R", "L", "= code 1"]].forEach(([a, b, lbl], i) => {
      const x = 0.75 + i * 2.95, y = by + 0.45;
      screen(s, `Code ${i} first`, x, y, 0.6, 0.4, a);
      arrowRight(s, `Code ${i} arrow`, x + 0.65, y + 0.2, 0.3);
      screen(s, `Code ${i} second`, x + 1.0, y, 0.6, 0.4, b);
      text(s, `Code ${i} label`, lbl, { x: x + 1.7, y, w: 1.2, h: 0.4, fontSize: 14, valign: "middle" });
    });
    text(s, "Coding task", "Task: decode each pair (one every 200 ms) from single-trial EEG", {
      x: 0.75, y: by + 1.1, w: 5.6, h: 0.3, fontSize: 14, italic: true });

    // Bottom right: application
    s.addShape(pres.shapes.RECTANGLE, { objectName: "Application panel", x: 6.75, y: by, w: 6.0, h: bh,
      fill: { color: HEX.light }, line: { type: "none" } });
    text(s, "Application", [
      { text: "Application", options: { bold: true, breakLine: true } },
      { text: "Robotic arms, unmanned vehicles: the user must keep watching the environment while issuing commands",
        options: { breakLine: true } },
      { text: "→ Chapter 3: online aVEP-based robotic arm", options: { bold: true, color: C.accent1 } },
    ], { x: 6.95, y: by + 0.1, w: 5.6, h: bh - 0.2, fontSize: 16, paraSpaceAfter: 2 });

    s.addText([
      { text: "[1] X. Chen et al., PNAS, 2015.   [2] L. A. Farwell, E. Donchin, Electroencephalogr. Clin. " +
        "Neurophysiol., 1988.", options: { breakLine: true } },
      { text: "[3] M. Xu et al., IEEE Trans. Biomed. Eng., 2018.   Panels (a)–(c) are schematic illustrations." },
    ], { objectName: "Reference", x: 0.35, y: 6.55, w: 11.9, h: 0.8, fontSize: 12, color: C.accent3,
      valign: "bottom", margin: 0, isTextBox: true });

    s.addNotes("~50 s. Traditional visual BCIs use large stimuli: SSVEP needs big flickering targets, the P300 " +
      "speller a flashing symbol matrix. Both cover most of the view, so the user cannot watch the robot or the " +
      "road. aVEP uses tiny stimuli beside each command: a left→right pair is code 0, right→left code 1. The scene " +
      "stays visible, which is what device control needs; this is the goal of Chapter 3. The cost is a very weak " +
      "signal, shown next.");
  }

  // ===== 4. Background: two challenges, measured data =====
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTIONS[0] });
    s.addText(sectionTitle(0), { placeholder: "title" });

    const fw = 6.1, fh = 3.75, fy = 1.75, xs = [0.45, 6.8];
    const fig = (f) => path.join(__dirname, "figures", f);
    [["Challenge 1: Low single-trial SNR", "slide4_snr.png",
      "Measured single trials (grey) vs. class averages, all 28 subjects"],
     ["Challenge 2: High inter-subject variability", "slide4_variability.png",
      "Measured class averages of four example subjects and per-subject statistics"]]
      .forEach(([head, file, alt], i) => {
        text(s, `Challenge ${i + 1} head`, head, { x: xs[i], y: 1.27, w: fw, h: 0.42, fontSize: 18, bold: true,
          color: C.accent1, align: "center", valign: "middle" });
        s.addImage({ objectName: `Challenge ${i + 1} figure`, path: fig(file), x: xs[i], y: fy, w: fw, h: fh,
          altText: alt });
      });

    text(s, "Challenge 1 text", [
      { text: "Single trials fluctuate by about ±10 µV (SD 3.3 µV), while the class difference peaks at only ≈ 1 µV",
        options: { breakLine: true } },
      { text: "→ The task-related ERP is buried in background EEG", options: { bold: true } },
    ], { x: xs[0] + 0.15, y: fy + fh + 0.1, w: fw - 0.3, h: 0.85, fontSize: 15 });
    text(s, "Challenge 2 text", [
      { text: "Mirror-symmetry r: −0.65 to 0.86;  peak latency: 150–300 ms;  peak amplitude: 0.3–3.9 µV",
        options: { breakLine: true } },
      { text: "→ Waveform, timing and lateralization differ across subjects", options: { bold: true } },
    ], { x: xs[1] + 0.15, y: fy + fh + 0.1, w: fw - 0.3, h: 0.85, fontSize: 15 });

    s.addText("All waveforms are measured data (28 subjects; 1–30 Hz, common average reference). Signal: left − right " +
      "hemisphere, mean of 9 mirror channel pairs. r: correlation of the class-0 pattern with the sign-flipped class-1 " +
      "pattern (9 pairs × time; mirror rule gives r = 1). Peak latency: largest class difference within 80–300 ms.", {
      objectName: "Reference", x: 0.35, y: 6.5, w: 11.9, h: 0.85, fontSize: 11, color: C.accent3,
      valign: "bottom", margin: 0, isTextBox: true });

    s.addNotes("~45 s. Left: grey lines are real single trials; red and blue are the class averages, black dashed " +
      "their difference. Single trials swing by about ten microvolts, the class difference is about one, so a " +
      "single trial carries very little of the signal. Responses to neighbouring pairs also overlap, since pairs " +
      "come every 200 ms. Right: four real subjects. Sub18 follows the mirror rule, Sub22 peaks early, Sub17 is " +
      "inverted, Sub05 barely responds. Across 28 subjects r ranges from −0.65 to 0.86 and the peak from 150 to " +
      "300 ms, so a model trained on some subjects transfers poorly to others.");
  }

  // ===== 5. Objectives =====
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTIONS[0] });
    s.addText(sectionTitle(0), { placeholder: "title" });

    const hdr = { bottom: 1, bold: true, fontSize: 18 };
    const rows = [
      [cell("", { ...hdr, top: 1.5 }), cell("Current limitation", { ...hdr, top: 1.5 }),
        cell("Research focus", { ...hdr, top: 1.5 })],
      [cell("① Chapter 1: Low single-trial SNR"),
        cell("Weak (≈ 1 µV), overlapping responses; single trials are unreliable"),
        cell("Distil the recoverable ERP from multi-trial averages (RED)")],
      [cell("② Chapter 2: Inter-subject variability"),
        cell("Symmetry and latency differ by subject; cross-subject accuracy drops"),
        cell("Physiology-routed mixture of experts (LR-MoE)")],
      [cell("③ Chapter 3: Offline-only validation", { bottom: 1.5 }),
        cell("Decoders are evaluated offline only", { bottom: 1.5 }),
        cell("Online EEG-based brain-controlled robotic arm", { bottom: 1.5 })],
    ];
    s.addTable(rows, { objectName: "Objectives table", x: 0.6, y: 1.75, w: 12.1, colW: [3.9, 4.2, 4.0],
      rowH: [0.6, 1.05, 1.05, 1.05], fontFace: THEME.bodyFontFace, margin: [4, 8, 4, 8] });

    text(s, "Research line", "Single-trial decoding  →  Cross-subject generalization  →  Online application", {
      x: 0.6, y: 6.05, w: 12.1, h: 0.45, fontSize: 20, bold: true, align: "center", valign: "middle", color: C.accent1 });

    s.addNotes("~30 s. The observations give two decoding problems, and the thesis adds an application: " +
      "Chapter 1 targets single-trial SNR, Chapter 2 cross-subject variability, Chapter 3 the online system.");
  }

  // ===== 6. Outline =====
  pres.addSection({ title: SECTIONS[1] });
  outlineSlide(1, "~3 s.");

  // ===== 7. Progress: pipeline and baselines =====
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTIONS[1] });
    s.addText(sectionTitle(1), { placeholder: "title" });

    text(s, "Lead", "Completed: a verified preprocessing pipeline, leakage-free evaluation and two baselines.", {
      x: 0.6, y: 1.35, w: 12.1, h: 0.4, fontSize: 18 });

    // Left: pipeline flow
    const px = 0.6, pw = 4.3, py = 1.95;
    text(s, "Pipeline head", "Preprocessing pipeline", { x: px, y: py, w: pw, h: 0.4, fontSize: 18,
      bold: true, align: "center" });
    s.addShape(pres.shapes.RECTANGLE, { objectName: "Pipeline panel", x: px, y: py + 0.45, w: pw, h: 4.1,
      fill: { color: HEX.light }, line: { type: "none" } });
    const steps = ["Raw EEG: 21 channels, 200 Hz", "Band-pass 1–30 Hz (zero-phase FIR)",
      "Bad-channel interpolation + CAR", "Epoch 0.05–0.34 s after pair onset",
      "Session- / subject-wise splits (no leakage)"];
    steps.forEach((st, i) => {
      const y = py + 0.6 + i * 0.8;
      text(s, `Pipeline step ${i}`, st, { x: px + 0.1, y, w: pw - 0.2, h: 0.4, fontSize: 16,
        align: "center", valign: "middle" });
      if (i < steps.length - 1) arrowDown(s, `Pipeline arrow ${i}`, px + pw / 2, y + 0.42, 0.34);
    });

    // Right: baseline table
    const tx = 5.4, tw = 7.35;
    text(s, "Table caption", [
      { text: "Table 1. ", options: { bold: true } },
      { text: "Single-trial accuracy (%), mean ± std over 28 subjects (chance 50%)" },
    ], { x: tx, y: py, w: tw, h: 0.65, fontSize: 14 });
    const H = { bottom: 1, bold: true, align: "center", top: 1.5 };
    const best = { bold: true, color: HEX.red, align: "center" };
    const ctr = { align: "center" };
    s.addTable([
      [cell("Method", { ...H, align: "left" }), cell("Within-subject", H), cell("Pooled", H), cell("LOSO", H)],
      [cell("DCPM [1]"), cell("72.57 ± 9.34", ctr), cell("63.21 ± 6.76", ctr), cell("60.34 ± 7.31", ctr)],
      [cell("EEGNet [2]", { bottom: 1.5 }), cell("74.40 ± 8.46", { ...best, bottom: 1.5 }),
        cell("66.73 ± 8.59", { ...best, bottom: 1.5 }), cell("62.26 ± 7.88", { ...best, bottom: 1.5 })],
    ], { objectName: "Baseline table", x: tx, y: py + 0.7, w: tw, colW: [1.6, 2.05, 1.85, 1.85],
      rowH: [0.5, 0.5, 0.5], fontFace: THEME.bodyFontFace, margin: [4, 6, 4, 6] });

    text(s, "Protocols", [
      { text: "Within-subject: ", options: { bold: true } },
      { text: "leave-one-session-out, per subject", options: { breakLine: true } },
      { text: "Pooled: ", options: { bold: true } },
      { text: "all subjects, leave-one-session-out", options: { breakLine: true } },
      { text: "LOSO: ", options: { bold: true } },
      { text: "leave-one-subject-out (cross-subject)" },
    ], { x: tx, y: py + 2.4, w: tw, h: 1.1, fontSize: 16, paraSpaceAfter: 4 });

    text(s, "Finding", "Finding: accuracy drops by ≈ 12 points from within-subject to cross-subject, " +
      "which motivates Chapters 1 and 2.", { x: tx, y: py + 3.7, w: tw, h: 0.8, fontSize: 18, color: C.accent1 });

    reference(s, "[1] Xu et al., IEEE TBME, 2018.   [2] V. J. Lawhern et al. EEGNet: a compact convolutional " +
      "neural network for EEG-based brain–computer interfaces. J. Neural Eng., 2018.");
    s.addNotes("~50 s. Completed so far: a verified, reproducible preprocessing pipeline and three leakage-free " +
      "protocols. EEGNet is the stronger baseline: 74.4 % within subjects but 62.3 % across subjects, about 12 " +
      "points lower. Chapter 1 targets single-trial accuracy, Chapter 2 the cross-subject drop.");
  }

  await pres.writeFile({ fileName: OUT });
  if (APPLY_THEME) {
    const { applyTheme } = require(APPLY_THEME);
    await applyTheme(OUT, THEME);
  }
  console.log("Wrote " + OUT);
})();
