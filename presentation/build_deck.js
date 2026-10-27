// Mid-term defense deck, slides 1-5 (sample).
// Usage: NODE_PATH=<dir with pptxgenjs, react, react-dom, react-icons, sharp> node build_deck.js [out.pptx] [apply_theme.js]

const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const md = require("react-icons/md");

const OUT = process.argv[2] || path.join(__dirname, "midterm_defense_sample.pptx");
const APPLY_THEME = process.argv[3];

// ---------- Theme ----------
const HEX = {
  ink: "1B2B30", deep: "12343B", tint: "EEF3F3", white: "FFFFFF",
  teal: "2E6F73", rust: "C8553D", sage: "8AA6A3", gold: "D9A441",
  slate: "5B6770", mist: "A3C4BC",
};
const THEME = {
  name: "Mid-term Defense",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: HEX.ink, lt1: HEX.white, dk2: HEX.deep, lt2: HEX.tint,
    accent1: HEX.teal, accent2: HEX.rust, accent3: HEX.sage,
    accent4: HEX.gold, accent5: HEX.slate, accent6: HEX.mist,
    hlink: HEX.teal, folHlink: HEX.slate,
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Mid-term Thesis Defense";
const C = pres.SchemeColor;
const W = 13.333, M = 0.6, CW = W - 2 * M;

// ---------- Layouts ----------
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: HEX.deep },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: M, y: 1.55, w: 7.2, h: 0.4,
      fontSize: 14, bold: true, color: C.accent6, charSpacing: 3, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.05, w: 7.4, h: 2.1,
      fontSize: 36, bold: true, color: C.background1, align: "left", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: M, y: 4.25, w: 7.2, h: 0.6,
      fontSize: 20, italic: true, color: C.accent6, valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: M, y: 5.45, w: 7.2, h: 0.9,
      fontSize: 14, color: C.background1, valign: "top", margin: 0 }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.white },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.38, w: 8, h: 0.3,
      fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.7, w: CW, h: 0.7,
      fontSize: 30, bold: true, color: C.text2, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: "Mid-term Thesis Defense", options: { x: M, y: 7.02, w: 6, h: 0.3,
      fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.02, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
});

// ---------- Helpers ----------
async function icon(Comp, hex, px = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + hex, size: px }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// Decorative multi-channel EEG-like traces for the title slide.
async function eegTraces() {
  const w = 1200, h = 1000, rows = 7;
  let paths = "";
  for (let r = 0; r < rows; r++) {
    const y0 = 90 + r * 135;
    let d = "";
    for (let x = 0; x <= w; x += 4) {
      const t = x / w;
      const y = y0
        + 18 * Math.sin(2 * Math.PI * (9 + r) * t + r)
        + 10 * Math.sin(2 * Math.PI * (23 + 2 * r) * t + 2 * r)
        + 6 * Math.sin(2 * Math.PI * (47 + r) * t)
        - 42 * Math.exp(-Math.pow((t - 0.45 - 0.02 * r) / 0.025, 2)) * (r % 2 ? 1 : -0.8);
      d += (x === 0 ? "M" : "L") + x + " " + y.toFixed(1) + " ";
    }
    const col = r === 3 ? "#" + HEX.rust : "#" + HEX.mist;
    const op = r === 3 ? 0.95 : 0.45;
    paths += `<path d="${d}" fill="none" stroke="${col}" stroke-width="${r === 3 ? 5 : 3}" stroke-opacity="${op}"/>`;
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${paths}</svg>`;
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

function card(slide, name, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    objectName: name, x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { type: "none" },
  });
}

function pill(slide, name, text, x, y, w, fill, color) {
  slide.addText(text, {
    objectName: name, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.13,
    x, y, w, h: 0.28, fill: { color: fill }, color, fontSize: 10, bold: true,
    align: "center", valign: "middle", margin: 0, charSpacing: 1,
  });
}

function arrow(slide, name, x, y1, y2) {
  slide.addShape(pres.shapes.LINE, {
    objectName: name, x, y: y1, w: 0, h: y2 - y1,
    line: { color: HEX.sage, width: 2, endArrowType: "triangle" },
  });
}

// Dark callout: label + sentence on a rounded card.
function callout(slide, name, label, text, x, y, w, h, fontSize) {
  card(slide, name + " bg", x, y, w, h, HEX.deep);
  slide.addText([
    { text: label + "   ", options: { bold: true, color: C.accent6 } },
    { text },
  ], { objectName: name, x: x + 0.3, y, w: w - 0.6, h, fontSize, color: C.background1,
    valign: "middle", margin: 0, isTextBox: true });
}

(async () => {
  const ic = {
    fatigue: await icon(md.MdVisibilityOff, HEX.white),
    focus: await icon(md.MdCenterFocusStrong, HEX.white),
    signal: await icon(md.MdShowChart, HEX.white),
    check: await icon(md.MdCheckCircle, HEX.teal),
  };

  // ===== Slide 1: Title =====
  pres.addSection({ title: "Opening" });
  {
    const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
    s.addImage({ objectName: "EEG traces", data: await eegTraces(), x: 8.45, y: 1.1, w: 4.5, h: 3.75,
      altText: "Decorative multi-channel EEG traces" });
    s.addText("MID-TERM THESIS DEFENSE", { placeholder: "kicker" });
    s.addText("Decoding Miniature Asymmetric Visual Evoked Potentials with EEGNet-Based Methods",
      { placeholder: "title" });
    s.addText("Toward an online EEG-based brain-controlled robotic arm", { placeholder: "subtitle" });
    s.addText([
      { text: "[Your Name]", options: { bold: true, breakLine: true } },
      { text: "Supervisor: [Supervisor Name]   ·   [School / Department]   ·   [Date]" },
    ], { placeholder: "meta" });
    s.addNotes("~10 s. Greet the committee; state the title and that this is the mid-term report.");
  }

  // ===== Slide 2: Background & motivation =====
  pres.addSection({ title: "Background" });
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Background" });
    s.addText("01  RESEARCH BACKGROUND", { placeholder: "kicker" });
    s.addText("Miniature Visual Stimuli: Comfortable but Hard to Decode", { placeholder: "title" });

    // Left: paradigm schematic
    const px = M, py = 1.7, pw = 5.9, ph = 3.85;
    card(s, "Paradigm panel", px, py, pw, ph, HEX.tint);
    s.addText("Paradigm (Xu et al., IEEE TBME 2018)", { objectName: "Paradigm heading",
      x: px + 0.3, y: py + 0.2, w: pw - 0.6, h: 0.35, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });

    // Screen with fixation cross and two tiny lateral stimuli
    const sx = px + 0.3, sy = py + 0.75, sw = 2.3, sh = 1.5;
    s.addShape(pres.shapes.RECTANGLE, { objectName: "Screen", x: sx, y: sy, w: sw, h: sh,
      fill: { color: HEX.ink }, line: { type: "none" } });
    s.addText("+", { objectName: "Fixation", x: sx + sw / 2 - 0.2, y: sy + sh / 2 - 0.22, w: 0.4, h: 0.4,
      fontSize: 20, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addShape(pres.shapes.RECTANGLE, { objectName: "Left stimulus", x: sx + sw / 2 - 0.42, y: sy + sh / 2 - 0.05,
      w: 0.1, h: 0.1, fill: { color: HEX.teal }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { objectName: "Right stimulus", x: sx + sw / 2 + 0.32, y: sy + sh / 2 - 0.05,
      w: 0.1, h: 0.1, fill: { color: HEX.rust }, line: { type: "none" } });
    s.addText("Tiny stimuli flank the fixation point", { objectName: "Screen caption",
      x: sx, y: sy + sh + 0.08, w: sw, h: 0.3, fontSize: 11, color: C.accent5, margin: 0, isTextBox: true });

    // Two classes = stimulus order
    const cx = sx + sw + 0.3, cw = pw - (cx - px) - 0.3;
    const rows = [
      { y: sy + 0.05, label: "Class 0", order: [["L", HEX.teal], ["R", HEX.rust]], txt: "left → right" },
      { y: sy + 0.85, label: "Class 1", order: [["R", HEX.rust], ["L", HEX.teal]], txt: "right → left" },
    ];
    rows.forEach((r, i) => {
      s.addText(r.label, { objectName: `Class ${i} label`, x: cx, y: r.y, w: cw, h: 0.28,
        fontSize: 12, bold: true, color: C.text2, margin: 0, isTextBox: true });
      r.order.forEach(([t, col], j) => {
        s.addText(t, { objectName: `Class ${i} step ${j}`, shape: pres.shapes.OVAL,
          x: cx + j * 0.85, y: r.y + 0.32, w: 0.36, h: 0.36, fill: { color: col },
          color: C.background1, fontSize: 12, bold: true, align: "center", valign: "middle", margin: 0 });
      });
      s.addShape(pres.shapes.LINE, { objectName: `Class ${i} arrow`, x: cx + 0.42, y: r.y + 0.5, w: 0.37, h: 0,
        line: { color: HEX.slate, width: 1.5, endArrowType: "triangle" } });
      s.addText(r.txt, { objectName: `Class ${i} order`, x: cx + 1.3, y: r.y + 0.32, w: cw - 1.3, h: 0.36,
        fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    });

    s.addText([
      { text: "One trial = one stimulus pair, presented every 200 ms", options: { bullet: true, breakLine: true } },
      { text: "28 subjects × 6 sessions × 480 trials; 21 channels", options: { bullet: true } },
    ], { objectName: "Paradigm facts", x: px + 0.3, y: py + 2.75, w: pw - 0.6, h: 0.9,
      fontSize: 14, color: C.text1, paraSpaceAfter: 4, margin: 0, valign: "top", isTextBox: true });

    // Right: motivation rows
    const rx = 6.9, rw = W - M - rx;
    const items = [
      [ic.fatigue, C.accent5, "Conventional VEP-based BCIs", "Large, intense flashing stimuli cause visual fatigue and discomfort"],
      [ic.focus, C.accent1, "Miniature lateral stimuli", "Small stimuli beside fixation: more comfortable and less intrusive"],
      [ic.signal, C.accent2, "The price: a very weak signal", "Class difference ≈ 1 µV, so single-trial decoding is hard"],
    ];
    items.forEach(([img, col, head, desc], i) => {
      const y = 1.75 + i * 1.3;
      s.addShape(pres.shapes.OVAL, { objectName: `Motivation icon bg ${i}`, x: rx, y, w: 0.7, h: 0.7,
        fill: { color: col }, line: { type: "none" } });
      s.addImage({ objectName: `Motivation icon ${i}`, data: img, x: rx + 0.15, y: y + 0.15, w: 0.4, h: 0.4,
        altText: head });
      s.addText(head, { objectName: `Motivation head ${i}`, x: rx + 0.95, y: y - 0.02, w: rw - 0.95, h: 0.36,
        fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });
      s.addText(desc, { objectName: `Motivation text ${i}`, x: rx + 0.95, y: y + 0.36, w: rw - 0.95, h: 0.6,
        fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true });
    });

    // Research question
    callout(s, "Research question", "Research question",
      "How can the stimulus order be decoded reliably from a single trial, within and across subjects?",
      M, 5.85, CW, 0.8, 16);

    s.addNotes("~50 s. Visual BCIs are fast but large flashing stimuli are tiring. Miniature lateral stimuli are comfortable, " +
      "but the response is tiny. Task: decide whether a stimulus pair went left→right or right→left from one trial. " +
      "(One sentence on the topic change, if needed.)");
  }

  // ===== Slide 3: Observations & challenges =====
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Background" });
    s.addText("02  KEY OBSERVATIONS", { placeholder: "kicker" });
    s.addText("A Weak, Time-Varying and Subject-Specific Signal", { placeholder: "title" });

    const t = [50, 70, 90, 110, 130, 150, 170, 190, 210, 230, 250, 270, 290, 310, 330];
    const v = [-0.01, -0.03, -0.44, -0.76, -0.38, 0.04, 0.12, 0.65, 1.01, 0.32, -0.30, -0.42, -0.39, -0.18, 0.02];
    s.addChart(pres.charts.LINE, [{ name: "Class difference", labels: t.map(String), values: v }], {
      objectName: "Lateralization chart", x: M, y: 1.65, w: 6.9, h: 3.7,
      chartColors: [HEX.teal], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 6,
      showLegend: false, showTitle: true, title: "Lateralization: left→right minus right→left (n = 28)",
      titleFontSize: 13, titleColor: HEX.deep, titleFontFace: "+mn-lt",
      catAxisTitle: "Time after pair onset (ms)", showCatAxisTitle: true,
      valAxisTitle: "µV", showValAxisTitle: true,
      catAxisTitleFontSize: 11, valAxisTitleFontSize: 11, catAxisTitleColor: HEX.slate, valAxisTitleColor: HEX.slate,
      catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate, catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
      catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisTitleFontFace: "+mn-lt", valAxisTitleFontFace: "+mn-lt",
      valAxisMinVal: -1, valAxisMaxVal: 1.2, valAxisMajorUnit: 0.5, valAxisLabelFormatCode: "0.0",
      valGridLine: { color: "DDE5E5", size: 0.5 }, catGridLine: { style: "none" },
      catAxisLabelPos: "low",
    });

    // Stat callouts under the chart
    [["−0.76 µV", "at 110 ms", HEX.teal], ["+1.01 µV", "at 210 ms", HEX.rust], ["Sign flip", "encodes stimulus order", HEX.deep]]
      .forEach(([big, small, col], i) => {
        const x = M + i * 2.37, w = 2.16;
        card(s, `Stat card ${i}`, x, 5.55, w, 1.1, HEX.tint);
        s.addText(big, { objectName: `Stat value ${i}`, x: x + 0.2, y: 5.62, w: w - 0.4, h: 0.5,
          fontSize: 24, bold: true, color: col, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
        s.addText(small, { objectName: `Stat label ${i}`, x: x + 0.2, y: 6.12, w: w - 0.4, h: 0.4,
          fontSize: 12, color: C.accent5, margin: 0, isTextBox: true });
      });

    // Challenge cards
    const rx = 7.95, rw = W - M - rx;
    const ch = [
      { y: 1.65, h: 2.4, tag: "CHALLENGE 1", head: "Low single-trial SNR", col: HEX.teal, pts: [
        "Effect ≈ 1 µV, buried in background EEG",
        "Lateralization reverses sign within 100 ms",
        "Pairs every 200 ms: responses overlap",
      ] },
      { y: 4.25, h: 2.4, tag: "CHALLENGE 2", head: "Inter-subject variability", col: HEX.rust, pts: [
        "Mirror-symmetry correlation: −0.64 to 0.75",
        "Peak latency ranges from 105 to 245 ms",
        "Some subjects encode it in the hemispheric sum",
      ] },
    ];
    ch.forEach((c, i) => {
      card(s, `Challenge card ${i + 1}`, rx, c.y, rw, c.h, HEX.tint);
      pill(s, `Challenge tag ${i + 1}`, c.tag, rx + 0.3, c.y + 0.22, 1.35, c.col, C.background1);
      s.addText(c.head, { objectName: `Challenge head ${i + 1}`, x: rx + 0.3, y: c.y + 0.6, w: rw - 0.6, h: 0.4,
        fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
      s.addText(c.pts.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < c.pts.length - 1 } })), {
        objectName: `Challenge points ${i + 1}`, x: rx + 0.3, y: c.y + 1.05, w: rw - 0.5, h: c.h - 1.15,
        fontSize: 14, color: C.text1, paraSpaceAfter: 4, valign: "top", margin: 0, isTextBox: true });
    });

    s.addNotes("~45 s. Exploratory analysis of the grand average: the class difference is about 1 µV and flips sign " +
      "between ~110 ms and ~210 ms, matching the stimulus order. Trials overlap. And subjects differ strongly in symmetry " +
      "and latency. Observations 1-3 give Challenge 1, observation 4 gives Challenge 2.");
  }

  // ===== Slide 4: Research framework =====
  pres.addSection({ title: "Framework" });
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Framework" });
    s.addText("03  RESEARCH FRAMEWORK", { placeholder: "kicker" });
    s.addText("Two Challenges, Three Chapters", { placeholder: "title" });

    const gap = 0.45, cw2 = (CW - gap) / 2, x1 = M, x2 = M + cw2 + gap;
    // Row 1: challenges
    [[x1, "Challenge 1", "Low single-trial SNR", HEX.teal], [x2, "Challenge 2", "Inter-subject variability", HEX.rust]]
      .forEach(([x, tag, txt, col], i) => {
        card(s, `Framework challenge ${i + 1}`, x, 1.6, cw2, 0.72, HEX.tint);
        pill(s, `Framework challenge tag ${i + 1}`, tag.toUpperCase(), x + 0.3, 1.82, 1.35, col, C.background1);
        s.addText(txt, { objectName: `Framework challenge text ${i + 1}`, x: x + 1.9, y: 1.6, w: cw2 - 2.1, h: 0.72,
          fontSize: 16, bold: true, color: C.text2, valign: "middle", margin: 0, isTextBox: true });
        arrow(s, `Framework arrow down ${i + 1}`, x + cw2 / 2, 2.38, 2.72);
      });

    // Row 2: chapters 1 and 2
    const chs = [
      [x1, "CHAPTER 1", "RED: Recoverable-ERP Distillation",
        "Multi-trial averages as training-only privileged information; the student learns only what one trial can recover",
        "Within-subject"],
      [x2, "CHAPTER 2", "LR-MoE: Lateralization-Routed Mixture-of-Experts",
        "Experts organised by hemispheric symmetry and latency; a physiological router selects them per trial",
        "Cross-subject (LOSO)"],
    ];
    chs.forEach(([x, tag, head, desc, scope], i) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { objectName: `Chapter ${i + 1} card`, x, y: 2.78, w: cw2, h: 1.85,
        rectRadius: 0.08, fill: { color: HEX.white }, line: { color: HEX.sage, width: 1.25 } });
      s.addText(tag, { objectName: `Chapter ${i + 1} tag`, x: x + 0.3, y: 2.95, w: 1.5, h: 0.28,
        fontSize: 11, bold: true, color: C.accent1, charSpacing: 2, margin: 0, isTextBox: true });
      pill(s, `Chapter ${i + 1} status`, "DESIGNED", x + cw2 - 1.35, 2.95, 1.05, HEX.gold, C.text1);
      s.addText(head, { objectName: `Chapter ${i + 1} head`, x: x + 0.3, y: 3.27, w: cw2 - 0.6, h: 0.38,
        fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true });
      s.addText(desc, { objectName: `Chapter ${i + 1} desc`, x: x + 0.3, y: 3.68, w: cw2 - 0.6, h: 0.6,
        fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true });
      s.addText(scope, { objectName: `Chapter ${i + 1} scope`, x: x + 0.3, y: 4.28, w: cw2 - 0.6, h: 0.28,
        fontSize: 12, italic: true, color: C.accent5, margin: 0, isTextBox: true });
      arrow(s, `Chapter ${i + 1} arrow`, x + cw2 / 2, 4.68, 5.02);
    });

    // Row 3: chapter 3
    card(s, "Chapter 3 card", M, 5.08, CW, 0.82, HEX.deep);
    s.addText("CHAPTER 3", { objectName: "Chapter 3 tag", x: M + 0.3, y: 5.08, w: 1.5, h: 0.82,
      fontSize: 11, bold: true, color: C.accent6, charSpacing: 2, valign: "middle", margin: 0, isTextBox: true });
    s.addText("Online EEG-based brain-controlled robotic arm, built on the proposed decoders", {
      objectName: "Chapter 3 text", x: M + 1.9, y: 5.08, w: CW - 3.5, h: 0.82,
      fontSize: 16, bold: true, color: C.background1, valign: "middle", margin: 0, isTextBox: true });
    pill(s, "Chapter 3 status", "PLANNED", W - M - 1.35, 5.35, 1.05, HEX.mist, C.text1);

    // Foundation
    card(s, "Foundation card", M, 6.1, CW, 0.6, HEX.tint);
    pill(s, "Foundation status", "COMPLETED", M + 0.3, 6.26, 1.2, HEX.teal, C.background1);
    s.addText([
      { text: "Foundation:  ", options: { bold: true, color: C.text2 } },
      { text: "verified preprocessing pipeline  ·  leakage-free evaluation protocols  ·  EEGNet & DCPM baselines" },
    ], { objectName: "Foundation text", x: M + 1.75, y: 6.1, w: CW - 2.0, h: 0.6,
      fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true });

    s.addNotes("~25 s. Each challenge gets one chapter: RED for single-trial SNR within a subject, LR-MoE for " +
      "cross-subject variability. Chapter 3 puts the decoders into an online robotic-arm system. " +
      "All of it rests on the shared pipeline and baselines, which are done.");
  }

  // ===== Slide 5: Completed - pipeline & baselines =====
  pres.addSection({ title: "Completed Work" });
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Completed Work" });
    s.addText("04  WORK COMPLETED", { placeholder: "kicker" });
    s.addText("Data Pipeline and Baseline Benchmarks", { placeholder: "title" });

    // Stat grid
    const stats = [["80,640", "single trials (28 × 6 × 480)"], ["21", "parieto-occipital channels"],
      ["3", "leakage-free protocols"], ["2", "baselines: EEGNet, DCPM"]];
    const gw = 2.05, gh = 1.2, gg = 0.25;
    stats.forEach(([big, small], i) => {
      const x = M + (i % 2) * (gw + gg), y = 1.65 + Math.floor(i / 2) * (gh + gg);
      card(s, `Data stat ${i}`, x, y, gw, gh, HEX.tint);
      s.addText(big, { objectName: `Data stat value ${i}`, x: x + 0.2, y: y + 0.12, w: gw - 0.4, h: 0.55,
        fontSize: 30, bold: true, color: C.accent1, fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
      s.addText(small, { objectName: `Data stat label ${i}`, x: x + 0.2, y: y + 0.68, w: gw - 0.3, h: 0.45,
        fontSize: 12, color: C.accent5, valign: "top", margin: 0, isTextBox: true });
    });

    // Checklist
    const checks = ["Event parsing and codebook verified", "Preprocessing reproducible bit-for-bit",
      "Whole sessions / subjects held out"];
    checks.forEach((txt, i) => {
      const y = 4.62 + i * 0.5;
      s.addImage({ objectName: `Check icon ${i}`, data: ic.check, x: M, y: y + 0.04, w: 0.3, h: 0.3, altText: "Done" });
      s.addText(txt, { objectName: `Check text ${i}`, x: M + 0.42, y, w: 4.0, h: 0.38,
        fontSize: 14, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    });

    // Baseline chart
    const cx = 5.35, cw = W - M - cx;
    s.addChart(pres.charts.BAR, [
      { name: "EEGNet", labels: ["Within-subject", "Pooled", "Cross-subject (LOSO)"], values: [74.4, 66.7, 62.3] },
      { name: "DCPM", labels: ["Within-subject", "Pooled", "Cross-subject (LOSO)"], values: [72.6, 63.2, 60.3] },
    ], {
      objectName: "Baseline chart", x: cx, y: 1.6, w: cw, h: 4.15, barDir: "col", barGapWidthPct: 60,
      chartColors: [HEX.teal, HEX.sage],
      showTitle: true, title: "Single-trial accuracy (%), mean of 28 subjects  ·  chance = 50%", titleFontSize: 13,
      titleColor: HEX.deep, titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", dataLabelFontSize: 11,
      dataLabelColor: HEX.ink, dataLabelFontFace: "+mn-lt",
      showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.slate, legendFontFace: "+mn-lt",
      valAxisMinVal: 50, valAxisMaxVal: 80, valAxisMajorUnit: 10,
      valAxisTitle: "Accuracy (%)", showValAxisTitle: true, valAxisTitleFontSize: 10,
      valAxisTitleColor: HEX.slate, valAxisTitleFontFace: "+mn-lt",
      catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
      catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
      valGridLine: { color: "DDE5E5", size: 0.5 }, catGridLine: { style: "none" },
    });

    callout(s, "Baseline takeaway", "Takeaway",
      "EEGNet reaches 74% within subjects but drops 12 points across subjects: room for Ch. 1 and Ch. 2",
      cx, 5.95, cw, 0.75, 14);

    s.addNotes("~50 s. Completed so far: a verified, reproducible preprocessing pipeline and three leakage-free protocols. " +
      "Baselines, seed 0: EEGNet 74.4 / 66.7 / 62.3 %, DCPM 72.6 / 63.2 / 60.3 % (within / pooled / LOSO). " +
      "Single-trial accuracy is limited and falls about 12 points across subjects, which is what Chapters 1 and 2 address.");
  }

  await pres.writeFile({ fileName: OUT });
  if (APPLY_THEME) {
    const { applyTheme } = require(APPLY_THEME);
    await applyTheme(OUT, THEME);
  }
  console.log("Wrote " + OUT);
})();
