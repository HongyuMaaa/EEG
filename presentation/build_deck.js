// Mid-term defense deck (sample: opening, Part 1 and the start of Part 2).
// Conventional academic style: red title banner, outline slides between parts,
// figures/tables with a text column, references at the bottom.
// Usage: NODE_PATH=<dir with pptxgenjs> node build_deck.js [out.pptx] [apply_theme.js]

const path = require("path");
const pptxgen = require("pptxgenjs");

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

  // ===== 3. Background: paradigm =====
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTIONS[0] });
    s.addText(sectionTitle(0), { placeholder: "title" });

    // (a) stimulus layout
    screen(s, "Screen", 0.6, 1.65, 3.6, 2.4, null);
    text(s, "Caption a", "(a) Miniature stimuli flank the fixation point", {
      x: 0.6, y: 4.15, w: 3.6, h: 0.35, fontSize: 14, align: "center" });

    // (b) the two classes are the order of the two lateral stimuli
    const bx = 4.55;
    text(s, "Caption b head", "(b) One trial = one stimulus pair", {
      x: bx, y: 1.6, w: 3.6, h: 0.35, fontSize: 14, align: "center" });
    [["Class 0:  left → right", "L", "R"], ["Class 1:  right → left", "R", "L"]].forEach(([lbl, a, b], i) => {
      const y = 2.05 + i * 1.25;
      screen(s, `Class ${i} first`, bx + 0.15, y, 1.2, 0.8, a);
      arrowRight(s, `Class ${i} arrow`, bx + 1.45, y + 0.4, 0.55);
      screen(s, `Class ${i} second`, bx + 2.1, y, 1.2, 0.8, b);
      text(s, `Class ${i} label`, lbl, { x: bx + 0.15, y: y + 0.85, w: 3.15, h: 0.3, fontSize: 14,
        align: "center", valign: "middle" });
    });

    text(s, "Dataset", [
      { text: "Dataset: ", options: { bold: true } },
      { text: "28 subjects × 6 sessions × 480 trials; 21 parieto-occipital channels, 200 Hz; " +
        "stimulus pairs presented every 200 ms" },
    ], { x: 0.6, y: 4.85, w: 7.5, h: 0.8, fontSize: 16 });

    // Right text column
    const items = [
      ["Visual BCIs", "High speed, but large flashing stimuli cause visual fatigue"],
      ["Miniature lateral stimuli [1]", "Small and unobtrusive, so more comfortable to use"],
      ["Cost", "Very weak response: class difference ≈ 1 µV"],
      ["Task", "Decode the stimulus order (left→right vs right→left) from a single trial"],
    ];
    text(s, "Background points", items.flatMap(([h, d], i) => [
      { text: h, options: { bold: true, breakLine: true } },
      { text: d, options: { breakLine: i < items.length - 1 } },
      ...(i < items.length - 1 ? [{ text: " ", options: { fontSize: 8, breakLine: true } }] : []),
    ]), { x: 8.45, y: 1.65, w: 4.5, h: 4.6, fontSize: 18 });

    reference(s, "[1] M. Xu et al. A Brain–Computer Interface Based on Miniature-Event-Related Potentials " +
      "Induced by Very Small Lateral Visual Stimuli. IEEE Trans. Biomed. Eng., 2018.");
    s.addNotes("~45 s. Visual BCIs are fast, but large flashing stimuli are tiring. Miniature lateral stimuli are " +
      "comfortable, but the response is tiny. Each trial is a pair of stimuli; the task is to decode whether it went " +
      "left→right or right→left from a single trial. (One sentence on the topic change, if needed.)");
  }

  // ===== 4. Background: observations =====
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: SECTIONS[0] });
    s.addText(sectionTitle(0), { placeholder: "title" });

    const t = [50, 70, 90, 110, 130, 150, 170, 190, 210, 230, 250, 270, 290, 310, 330];
    const v = [-0.01, -0.03, -0.44, -0.76, -0.38, 0.04, 0.12, 0.65, 1.01, 0.32, -0.30, -0.42, -0.39, -0.18, 0.02];
    s.addChart(pres.charts.LINE, [{ name: "Lateralization", labels: t.map(String), values: v }], {
      objectName: "Lateralization chart", x: 0.45, y: 1.45, w: 7.6, h: 4.6,
      chartColors: [HEX.red], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 6,
      showLegend: false, showTitle: true, title: "Grand-average lateralization (n = 28)",
      titleFontSize: 16, titleColor: HEX.black, titleFontFace: "+mn-lt",
      showCatAxisTitle: true, catAxisTitle: "Time after pair onset (ms)",
      showValAxisTitle: true, valAxisTitle: "Amplitude (µV)",
      catAxisTitleFontSize: 14, valAxisTitleFontSize: 14, catAxisTitleColor: HEX.black, valAxisTitleColor: HEX.black,
      catAxisLabelColor: HEX.black, valAxisLabelColor: HEX.black, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12,
      catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
      catAxisTitleFontFace: "+mn-lt", valAxisTitleFontFace: "+mn-lt",
      valAxisMinVal: -1, valAxisMaxVal: 1.2, valAxisMajorUnit: 0.5, valAxisLabelFormatCode: "0.0",
      valGridLine: { color: "D9D9D9", size: 0.5 }, catGridLine: { style: "none" }, catAxisLabelPos: "low",
    });
    text(s, "Chart note", "Class difference (left→right − right→left) of the hemispheric difference, " +
      "averaged over 9 mirror channel pairs", { x: 0.6, y: 6.1, w: 7.4, h: 0.6, fontSize: 12, color: C.accent3 });

    const obs = [
      ["1. Very weak effect", "Class difference ≈ 1 µV"],
      ["2. Time-varying lateralization", "Sign reverses: −0.76 µV at 110 ms, +1.01 µV at 210 ms"],
      ["3. Overlapping responses", "Pairs every 200 ms, so each epoch also contains the next trials"],
      ["4. Inter-subject heterogeneity", "Mirror-symmetry correlation −0.64 to 0.75; peak latency 105–245 ms"],
    ];
    text(s, "Observations", obs.flatMap(([h, d], i) => [
      { text: h, options: { bold: true, breakLine: true } },
      { text: d, options: { breakLine: i < obs.length - 1 } },
      ...(i < obs.length - 1 ? [{ text: " ", options: { fontSize: 8, breakLine: true } }] : []),
    ]), { x: 8.45, y: 1.65, w: 4.5, h: 4.6, fontSize: 18 });

    s.addNotes("~40 s. Exploratory analysis of the class-averaged ERPs: the effect is about 1 µV and changes sign " +
      "between ~110 and ~210 ms, matching the stimulus order. Responses to neighbouring trials overlap, and " +
      "subjects differ strongly in symmetry and latency.");
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
