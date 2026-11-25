/**
 * FaceLock Stego presentation (15 slides, 16:9) built with pptxgenjs.
 *   node build_ppt.js ppt_data.json out.pptx
 * Numbers come from ppt_data.json (written by scripts/build_ppt.py from the real benchmark results).
 */
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const lu = require("react-icons/lu");

const [, , dataPath, outPath] = process.argv;
const D = JSON.parse(fs.readFileSync(dataPath, "utf8"));
const ROOT = D.root;
const C = D.cfg;
const fig = (p) => path.join(ROOT, "docs", "figures", p);
const MEMBERS = C.group_members && C.group_members.length ? C.group_members : [{ name: C.student_name, roll_no: C.roll_no }];
const FOOTER = MEMBERS.length > 1 ? `Group: ${MEMBERS.map((m) => m.name.split(" ")[0]).join(", ")}` : C.student_name;

// ------------------------------------------------------------------ theme
const THEME = {
  name: "FaceLock Cipher",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B1220", lt1: "FFFFFF", dk2: "1C2A44", lt2: "EEF3F8",
    accent1: "0E9FBF", accent2: "F59E0B", accent3: "10B981", accent4: "E11D48", accent5: "6D5BD0", accent6: "64748B",
    hlink: "0E9FBF", folHlink: "6D5BD0",
  },
};
const HEX = { navy: "0B1220", ink: "1C2A44", teal: "0E9FBF", amber: "F59E0B", green: "10B981", red: "E11D48", violet: "6D5BD0", slate: "64748B", mist: "EEF3F8", line: "D5DEE8", orange: "EB6834", aqua: "1BAF7A" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = `${C.project_title}: ${C.project_subtitle}`;
pres.author = MEMBERS.map((m) => m.name).join(", ");
pres.company = C.university.replace(/&/g, "&amp;");
const S = pres.SchemeColor;
// debugging aid: ONLY_SLIDE=k builds just slide k (others become no-ops)
if (process.env.ONLY_SLIDE) {
  const orig = pres.addSlide.bind(pres);
  let k = 0;
  const noop = new Proxy({}, { get: () => () => noop });
  pres.addSlide = (o) => (++k === Number(process.env.ONLY_SLIDE) ? orig(o) : noop);
}

// pptxgenjs cannot write theme colours, so write the colour scheme into theme1.xml ourselves
async function applyTheme(file, theme) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const order = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
  const scheme = `<a:clrScheme name="${esc(theme.name)}">` + order.map((k) => `<a:${k}><a:srgbClr val="${theme.colors[k]}"/></a:${k}>`).join("") + "</a:clrScheme>";
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/theme\/theme\d+\.xml$/.test(n))) {
    let x = await zip.file(name).async("string");
    x = x.replace(/<a:clrScheme[\s\S]*?<\/a:clrScheme>/, scheme).replace(/(<a:theme [^>]*name=")[^"]*"/, `$1${esc(theme.name)}"`);
    zip.file(name, x);
  }
  const out = new JSZip();
  for (const [n, f] of Object.entries(zip.files)) if (!f.dir) out.file(n, await f.async("nodebuffer"), { createFolders: false });
  fs.writeFileSync(file, await out.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

// ------------------------------------------------------------------ icons
async function icon(name, color = "#FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(lu[name], { color, size, strokeWidth: 2 }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "DARK",
  background: { color: HEX.navy },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: "FFFFFF" },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontFace: "Arial", fontSize: 32, bold: true, color: HEX.navy, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: `${C.project_title}  ·  ${FOOTER}`, options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: HEX.slate, fontFace: "Calibri", margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: HEX.slate, fontFace: "Calibri", align: "right" },
});

let n = 0;
function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  n++;
  return s;
}
const txt = (s, text, o) => s.addText(text, { isTextBox: true, fontFace: "Calibri", color: HEX.ink, margin: 0, ...o });

function card(s, x, y, w, h, fill = HEX.mist, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.12, objectName: name });
}
async function iconBadge(s, name, x, y, d = 0.62, bg = HEX.teal) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg } });
  s.addImage({ data: await icon(name), x: x + d * 0.22, y: y + d * 0.22, w: d * 0.56, h: d * 0.56 });
}

(async () => {
  // ================================================================ 1 Title
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
  // pixel grid motif (LSB plane) on the right
  for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++) {
    const on = (r * 7 + c * 13) % 11 === 0;
    const shade = ["13213A", "182A47", "1D3354", "223B60"][(r + c) % 4];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.3 + c * 0.47, y: 1.0 + r * 0.47, w: 0.4, h: 0.4, rectRadius: 0.05, fill: { color: on ? HEX.teal : shade }, line: { color: on ? HEX.teal : shade } });
  }
  txt(s, "INFORMATION SECURITY · FINAL YEAR PROJECT", { x: 0.7, y: 1.0, w: 7.2, h: 0.4, fontSize: 13, bold: true, color: HEX.teal, charSpacing: 2 });
  txt(s, C.project_title, { x: 0.7, y: 1.55, w: 7.4, h: 1.2, fontSize: 54, bold: true, color: "FFFFFF", fontFace: "Arial" });
  txt(s, C.project_subtitle, { x: 0.7, y: 2.75, w: 7.2, h: 0.9, fontSize: 22, color: "C7D2E2" });
  txt(s, "GROUP MEMBERS", { x: 0.7, y: 3.85, w: 7.2, h: 0.3, fontSize: 12, bold: true, color: HEX.teal, charSpacing: 2 });
  txt(s, MEMBERS.map((m, i) => ({ text: `${m.name}   ${m.roll_no}`, options: { bold: true, color: "FFFFFF", breakLine: i < MEMBERS.length - 1 } })),
    { x: 0.7, y: 4.2, w: 7.2, h: 1.45, fontSize: 17, paraSpaceAfter: 3, valign: "top" });
  txt(s, [
    { text: `${C.department}  ·  ${C.university}`, options: { color: "AFC0D6", breakLine: true } },
    { text: `Supervisor: ${C.supervisor}  ·  ${C.submission_date}`, options: { color: "AFC0D6" } },
  ], { x: 0.7, y: 5.8, w: 7.4, h: 0.7, fontSize: 14, valign: "top" });
  txt(s, "Hide secrets in plain sight. Unlock them with your face.", { x: 8.3, y: 5.5, w: 4.3, h: 0.8, fontSize: 14, italic: true, color: "C7D2E2" });
  s.addNotes(`Good morning. We are ${MEMBERS.map((m) => m.name).join(", ")}, and our project is ${C.project_title}: a system that hides encrypted messages inside ordinary images, and only lets a registered person extract them after a live face check. The squares on the right represent the least-significant-bit plane of an image; the highlighted ones carry hidden bits. In the next 15 minutes I will cover the problem, the design, a live demo and real measured results.`);

  // ================================================================ 2 Agenda
  pres.addSection({ title: "Background" });
  s = content("Agenda", "Background");
  const agenda = [["LuBookOpen", "Background", "Cryptography, steganography, biometrics"], ["LuTarget", "Problem & objectives", "Why existing tools fall short"],
    ["LuBinary", "How LSB works", "One bit per colour channel"], ["LuLayers", "System design", "Architecture, workflows, Face Vault"],
    ["LuMonitor", "Build & live demo", "FastAPI + Next.js web app"], ["LuGauge", "Results & limits", "Measured quality, security, future work"]];
  for (let i = 0; i < 6; i++) {
    const x = 0.6 + (i % 3) * 4.1, y = 1.6 + Math.floor(i / 3) * 2.55;
    card(s, x, y, 3.8, 2.25);
    await iconBadge(s, agenda[i][0], x + 0.3, y + 0.3);
    txt(s, `0${i + 1}`, { x: x + 2.9, y: y + 0.3, w: 0.6, h: 0.5, fontSize: 18, bold: true, color: HEX.slate, align: "right" });
    txt(s, agenda[i][1], { x: x + 0.3, y: y + 1.05, w: 3.3, h: 0.5, fontSize: 20, bold: true, color: HEX.navy });
    txt(s, agenda[i][2], { x: x + 0.3, y: y + 1.55, w: 3.3, h: 0.5, fontSize: 14, color: HEX.slate });
  }
  s.addNotes("Here is the plan: background and problem, the core idea of least-significant-bit hiding, the design of the system with its Face Vault, the implementation with a live demo, and finally measured results, limitations and future work.");

  // ================================================================ 3 Intro
  s = content("Three locks, three different jobs", "Background");
  const intro = [["LuLock", HEX.teal, "Cryptography", "Hides the MEANING", "Ciphertext looks random, so it is obviously secret.", "AES-256-GCM"],
    ["LuEyeOff", HEX.violet, "Steganography", "Hides the EXISTENCE", "The carrier looks like an ordinary photo.", "Keyed random LSB"],
    ["LuScanFace", HEX.green, "Biometrics", "Proves WHO is present", "Access is tied to a live person, not a password.", "SFace + liveness"]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.6, 3.8, 4.6);
    await iconBadge(s, intro[i][0], x + 0.3, 1.9, 0.8, intro[i][1]);
    txt(s, intro[i][2], { x: x + 0.3, y: 2.95, w: 3.3, h: 0.5, fontSize: 22, bold: true, color: HEX.navy });
    txt(s, intro[i][3], { x: x + 0.3, y: 3.5, w: 3.3, h: 0.4, fontSize: 14, bold: true, color: intro[i][1], charSpacing: 1 });
    txt(s, intro[i][4], { x: x + 0.3, y: 4.0, w: 3.3, h: 1.0, fontSize: 15, color: HEX.ink, valign: "top" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.3, y: 5.35, w: 3.2, h: 0.5, rectRadius: 0.1, fill: { color: "FFFFFF" }, line: { color: HEX.line } });
    txt(s, `In this project: ${intro[i][5]}`, { x: x + 0.3, y: 5.35, w: 3.2, h: 0.5, fontSize: 13, color: HEX.ink, align: "center", valign: "middle" });
  }
  txt(s, "FaceLock Stego combines all three so that each covers the others' weaknesses.", { x: 0.6, y: 6.4, w: 12, h: 0.4, fontSize: 15, italic: true, color: HEX.slate });
  s.addNotes("Cryptography hides what a message says, but the ciphertext itself attracts attention. Steganography hides that a message exists at all, but if it is detected and not encrypted, it can be read. Biometrics proves who is in front of the camera. The project layers all three: encryption for confidentiality, steganography for deniability, and the face for access control.");

  // ================================================================ 4 Problem
  s = content("Problem statement", "Background");
  const probs = [["LuShuffle", "Sequential embedding", "Most tools write bits from the first pixel, which the chi-square attack detects and reads."],
    ["LuKeyRound", "Key travels with the image", "Passwords or seeds are stored in, or derived from, the image itself."],
    ["LuUsers", "Shared passwords", "Anyone who learns the password gets the secret; nothing ties it to a person."],
    ["LuTimer", "No throttling or audit", "Unlimited guesses, no record of who tried, no evidence of intruders."]];
  for (let i = 0; i < 4; i++) {
    const y = 1.55 + i * 1.22;
    await iconBadge(s, probs[i][0], 0.7, y + 0.1, 0.7, HEX.red);
    txt(s, probs[i][1], { x: 1.65, y, w: 5.6, h: 0.45, fontSize: 19, bold: true, color: HEX.navy });
    txt(s, probs[i][2], { x: 1.65, y: y + 0.45, w: 5.6, h: 0.65, fontSize: 14, color: HEX.slate, valign: "top" });
  }
  card(s, 7.8, 1.55, 4.9, 4.75, HEX.navy);
  txt(s, "The question", { x: 8.15, y: 1.85, w: 4.2, h: 0.4, fontSize: 14, bold: true, color: HEX.teal, charSpacing: 1 });
  txt(s, "How can a secret hidden in an ordinary image be recovered only by an authorised person who is physically present, without degrading the image?",
    { x: 8.15, y: 2.35, w: 4.2, h: 3.6, fontSize: 22, color: "FFFFFF", valign: "top", fontFace: "Arial" });
  s.addNotes("Four weaknesses motivated the project. Sequential embedding is easily detected. Keys often travel with the image. A shared password says nothing about who is using it. And there is no protection against guessing and no audit trail. So the question is: can we make a hidden secret recoverable only by an authorised, physically present person, while keeping the image visually unchanged?");

  // ================================================================ 5 Objectives
  s = content("Objectives", "Background");
  const objs = [["LuShuffle", "Random LSB embedding", "Key-selected pixel positions with an authenticated 38-byte header"],
    ["LuLock", "Strong encryption", "Fresh AES-256-GCM key per secret, never stored in the image"],
    ["LuFingerprint", "Face Vault", "Key wrapped for up to 3 enrolled faces + Argon2id backup password"],
    ["LuEye", "Live verification", "Server-side blink detection + random head-turn challenge"],
    ["LuShieldCheck", "Brute-force defence", "Audit log, intruder photos, lockout after 3 failures"],
    ["LuGauge", "Measured evaluation", `${D.images} images × 5 payloads: PSNR, SSIM, speed, steganalysis`]];
  for (let i = 0; i < 6; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.5 + Math.floor(i / 2) * 1.75;
    card(s, x, y, 5.9, 1.5);
    await iconBadge(s, objs[i][0], x + 0.3, y + 0.42, 0.66);
    txt(s, objs[i][1], { x: x + 1.2, y: y + 0.25, w: 4.5, h: 0.45, fontSize: 19, bold: true, color: HEX.navy });
    txt(s, objs[i][2], { x: x + 1.2, y: y + 0.72, w: 4.5, h: 0.6, fontSize: 14, color: HEX.slate, valign: "top" });
  }
  s.addNotes("Six objectives: random-position LSB embedding; AES-256-GCM encryption with a key that never touches the image; a Face Vault for up to three people with a password fallback; server-side liveness; brute-force protection with logging and intruder photos; and a real, measured evaluation on a public dataset.");

  // ================================================================ 6 LSB
  pres.addSection({ title: "Design" });
  s = content("How LSB steganography works", "Design");
  s.addImage({ path: fig("diagrams/fig_lsb_example.png"), x: 0.6, y: 1.5, w: 7.8, h: 7.8 * 0.383 });
  card(s, 8.8, 1.5, 3.9, 4.9);
  txt(s, "±1", { x: 9.1, y: 1.75, w: 3.3, h: 1.0, fontSize: 60, bold: true, color: HEX.teal, fontFace: "Arial" });
  txt(s, "maximum change per colour value (out of 255)", { x: 9.1, y: 2.8, w: 3.3, h: 0.6, fontSize: 14, color: HEX.slate });
  txt(s, "3 bits", { x: 9.1, y: 3.6, w: 3.3, h: 0.8, fontSize: 40, bold: true, color: HEX.violet, fontFace: "Arial" });
  txt(s, "hidden per pixel (R, G, B): a 768×512 photo holds 144 KB", { x: 9.1, y: 4.4, w: 3.3, h: 0.8, fontSize: 14, color: HEX.slate });
  txt(s, "The eye cannot see a 1-level change, but statistics can: so we encrypt first and scatter the bits randomly.", { x: 0.6, y: 5.0, w: 7.8, h: 1.0, fontSize: 16, color: HEX.ink });
  s.addNotes("Each pixel has red, green and blue values from 0 to 255. LSB steganography overwrites only the last bit of each value with one secret bit. In the example, six secret bits change four values by exactly one level; two values already had the right bit and are untouched. A one-level change is invisible. A 768 by 512 photo can hold about 144 kilobytes this way. The catch is that naive LSB leaves a statistical fingerprint, which is why we encrypt first and scatter the bits.");

  // ================================================================ 7 Literature
  s = content("Existing techniques compared", "Design");
  const rows = [["Technique", "Domain", "Capacity", "Survives JPEG", "Detectability", "Complexity"],
    ["Sequential LSB", "Spatial", "Very high", "No", "High", "Very low"],
    ["Random-order LSB (ours)", "Spatial", "Very high", "No", "Low below 50 % load", "Low"],
    ["DCT (JSteg, F5, OutGuess)", "Frequency", "Low-medium", "Yes", "Medium", "Medium"],
    ["DWT sub-band embedding", "Wavelet", "Medium", "Partly", "Medium", "Medium-high"],
    ["Adaptive (HUGO, S-UNIWARD)", "Spatial/JPEG", "Medium", "Variant", "Very low", "High"]];
  s.addTable(rows.map((r, i) => r.map((c) => ({ text: c, options: {
    bold: i === 0 || (i === 2), color: i === 0 ? "FFFFFF" : HEX.ink, fill: { color: i === 0 ? HEX.navy : i === 2 ? "DDF3F8" : (i % 2 ? "FFFFFF" : HEX.mist) } } }))),
  { x: 0.6, y: 1.55, w: 12.1, colW: [3.2, 1.7, 1.6, 1.7, 2.3, 1.6], fontSize: 15, fontFace: "Calibri", border: { type: "solid", pt: 0.75, color: HEX.line }, rowH: 0.55, valign: "middle" });
  txt(s, "Why LSB? Highest capacity and clearest to explain. Security comes from the cryptography, not from hiding the algorithm (Kerckhoffs' principle).",
    { x: 0.6, y: 5.3, w: 12.1, h: 0.8, fontSize: 16, color: HEX.ink });
  s.addNotes("The literature offers spatial, frequency and adaptive methods. DCT methods survive JPEG but carry less. Adaptive methods are the hardest to detect but complex. I chose LSB for capacity and clarity, and improved its main weakness with random ordering. Importantly, confidentiality does not depend on keeping the method secret: it comes from AES-GCM.");

  // ================================================================ 8 Overview
  s = content("Proposed system: three layers of protection", "Design");
  const lay = [["LuImage", HEX.slate, "Image alone", "Looks like an ordinary photo. Bits sit at secret random positions and are AES-encrypted.", "Nothing to read"],
    ["LuFileKey", HEX.violet, "Image + vault", "The key is wrapped inside the vault, sealed with this device's key.", "Still locked"],
    ["LuScanFace", HEX.green, "Image + vault + face", "Liveness and face match pass on the server, then the key is released.", "ACCESS GRANTED"]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.15;
    card(s, x, 1.7, 3.75, 4.2);
    await iconBadge(s, lay[i][0], x + 0.3, 2.0, 0.8, lay[i][1]);
    txt(s, lay[i][2], { x: x + 0.3, y: 3.0, w: 3.2, h: 0.5, fontSize: 20, bold: true, color: HEX.navy });
    txt(s, lay[i][3], { x: x + 0.3, y: 3.55, w: 3.2, h: 1.3, fontSize: 15, color: HEX.ink, valign: "top" });
    txt(s, lay[i][4], { x: x + 0.3, y: 5.1, w: 3.2, h: 0.5, fontSize: 16, bold: true, color: lay[i][1] });
    if (i < 2) s.addImage({ data: await icon("LuArrowRight", "#64748B"), x: x + 3.8, y: 3.6, w: 0.32, h: 0.32 });
  }
  txt(s, "Plus: up to 3 authorised people · Argon2id backup password · lockout after 3 failures · intruder photos", { x: 0.6, y: 6.2, w: 12.1, h: 0.4, fontSize: 15, color: HEX.slate });
  s.addNotes("The design has three layers. The image alone reveals nothing: the data is encrypted and scattered at secret positions. Even with the vault file, the key is sealed with this device's key and released only after the server verifies a live, authorised face. Up to three people can be authorised, and there is a hashed backup password, a lockout and intruder photos.");

  // ================================================================ 9 Architecture
  s = content("System architecture", "Design");
  s.addImage({ path: fig("diagrams/fig_architecture.png"), x: 1.85, y: 1.3, w: 9.6, h: 9.6 * 0.584 });
  s.addNotes("The browser is a thin Next.js client: it captures files and camera frames. FastAPI receives requests, and one service class makes every security decision on the server, calling focused modules for cryptography, LSB, the vault, face recognition, liveness and the security log. State such as the device key, encrypted face profiles and the audit database stays on the owner's device.");

  // ================================================================ 10 Workflows
  s = content("Hide and extract workflows", "Design");
  const flow = async (y, label, color, steps) => {
    txt(s, label, { x: 0.6, y: y - 0.55, w: 4, h: 0.45, fontSize: 18, bold: true, color });
    const w = 12.1 / steps.length - 0.25;
    for (let i = 0; i < steps.length; i++) {
      const x = 0.6 + i * (w + 0.25);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 1.5, rectRadius: 0.12, fill: { color: i === steps.length - 1 ? color : HEX.mist }, line: { color } });
      s.addImage({ data: await icon(steps[i][0], i === steps.length - 1 ? "#FFFFFF" : "#" + color), x: x + 0.15, y: y + 0.18, w: 0.4, h: 0.4 });
      txt(s, steps[i][1], { x: x + 0.15, y: y + 0.65, w: w - 0.3, h: 0.75, fontSize: 13, bold: true, color: i === steps.length - 1 ? "FFFFFF" : HEX.navy, valign: "top" });
    }
  };
  await flow(1.95, "Hide", HEX.teal, [["LuImage", "Cover image + secret"], ["LuKeyRound", "Random 256-bit key"], ["LuLock", "AES-256-GCM encrypt"], ["LuShuffle", "Keyed random positions"], ["LuBinary", "Write LSBs, save PNG"], ["LuFileKey", "stego.png + .vault"]]);
  await flow(4.55, "Extract", HEX.green, [["LuTimer", "Lockout + image check"], ["LuCamera", "Random challenge, 5 s video"], ["LuEye", "Blinks + head turn"], ["LuScanFace", "Face match ≥ 0.40"], ["LuKeyRound", "Unwrap key"], ["LuShieldCheck", "Decrypt + verify"]]);
  txt(s, "Any failed check: ACCESS DENIED, intruder photo, failure count +1 (3 = lockout)", { x: 0.6, y: 6.3, w: 12.1, h: 0.4, fontSize: 14, color: HEX.red, bold: true });
  s.addNotes("Hiding: generate a random key, encrypt with AES-GCM, derive a seed from the key to choose random positions, write the bits and output two files. Extracting runs checks in a deliberate order: lockout and image binding first, then a random challenge recorded as a five-second video, liveness, face match, and only then is the key unwrapped and the message decrypted and integrity-checked. Any failure is logged with a photo.");

  // ================================================================ 11 Security features
  s = content("Security features", "Design");
  const sec = [["LuShuffle", HEX.teal, "Random pixel selection", "AES-CTR keystream ranks every R, G, B slot; positions are never stored and depend on the key."],
    ["LuLock", HEX.violet, "AES-256-GCM", "Fresh key per secret; header authenticated as AAD; any modified bit is detected."],
    ["LuFingerprint", HEX.amber, "Face Vault", "Key wrapped per face slot; vault bound to the stego pixels by SHA-256; Argon2id password slot."],
    ["LuEye", HEX.green, "Liveness", "Eye aspect ratio blinks + random challenge; static photos and wrong responses fail."]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.5 + Math.floor(i / 2) * 2.15;
    card(s, x, y, 5.9, 1.9);
    await iconBadge(s, sec[i][0], x + 0.3, y + 0.35, 0.72, sec[i][1]);
    txt(s, sec[i][2], { x: x + 1.25, y: y + 0.28, w: 4.4, h: 0.45, fontSize: 19, bold: true, color: HEX.navy });
    txt(s, sec[i][3], { x: x + 1.25, y: y + 0.75, w: 4.4, h: 1.0, fontSize: 14, color: HEX.ink, valign: "top" });
  }
  card(s, 0.6, 5.85, 12.05, 0.75, HEX.navy);
  txt(s, "Also: 3 failures → temporary lockout  ·  intruder photo on every failed face attempt  ·  every decision made server-side", { x: 0.9, y: 5.85, w: 11.5, h: 0.75, fontSize: 15, color: "FFFFFF", valign: "middle" });
  s.addNotes("Four core mechanisms. Random positions driven by the key, so an attacker does not know where to look. AES-256-GCM, which also authenticates, so tampering is detected. The Face Vault, which keeps the key out of the image and binds itself to the exact stego pixels. And liveness: blink detection with the eye aspect ratio plus a random challenge. On top, lockout and intruder photos, and nothing is trusted from the browser.");

  // ================================================================ 12 Implementation
  pres.addSection({ title: "Implementation" });
  s = content("Implementation and user interface", "Implementation");
  const stack = ["FastAPI · Python 3.12", "OpenCV YuNet + SFace", "MediaPipe Face Landmarker", "cryptography · argon2", "Next.js 14 · TypeScript", "Tailwind · Framer Motion · Recharts", "SQLite audit log", `${D.tests} pytest + ${D.ui} browser checks`];
  stack.forEach((t, i) => {
    const y = 1.5 + i * 0.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 3.6, h: 0.48, rectRadius: 0.1, fill: { color: i < 4 ? "DDF3F8" : "ECE9FB" }, line: { color: i < 4 ? "DDF3F8" : "ECE9FB" } });
    txt(s, t, { x: 0.75, y, w: 3.4, h: 0.48, fontSize: 13, color: HEX.navy, valign: "middle" });
  });
  s.addImage({ path: fig("screenshots/06_access_granted.png"), x: 4.5, y: 1.45, w: 4.1, h: 4.1 * (2036 / 2160), sizing: { type: "crop", w: 4.1, h: 3.86 } });
  s.addImage({ path: fig("screenshots/04_hide_result.png"), x: 8.75, y: 1.45, w: 4.0, h: 2.0, sizing: { type: "crop", w: 4.0, h: 2.0 } });
  s.addImage({ path: fig("screenshots/12_attack_lab.png"), x: 8.75, y: 3.6, w: 4.0, h: 1.75, sizing: { type: "crop", w: 4.0, h: 1.75 } });
  txt(s, "Extract: ACCESS GRANTED with the server's liveness signal", { x: 4.5, y: 5.4, w: 4.1, h: 0.4, fontSize: 11, color: HEX.slate });
  txt(s, "Hide Data and Attack Lab pages (real screenshots)", { x: 8.75, y: 5.4, w: 4.0, h: 0.4, fontSize: 11, color: HEX.slate });
  txt(s, "8 pages: Home · Enroll · Hide · Extract · Analysis · Security Log · Attack Lab · How It Works. Demo Mode preloads samples so the demo never fails.", { x: 4.5, y: 5.9, w: 8.25, h: 0.7, fontSize: 14, color: HEX.ink });
  s.addNotes("The backend is Python FastAPI with OpenCV's YuNet and SFace models, which install on Windows without compiling anything, and MediaPipe for the 478-point face mesh. The frontend is Next.js with TypeScript. These are real screenshots from the automated browser test: access granted with the liveness signal, the hide page and the attack lab. [LIVE DEMO: enrol, hide, extract, then show a photo attack being denied.]");

  // ================================================================ 13 Results
  pres.addSection({ title: "Results" });
  s = content("Results: invisible, recoverable and harder to detect", "Results");
  const stats = [[`${D.ok_runs}/${D.ok_runs}`, "fitting payloads recovered bit-exactly", HEX.green], [`${D.min_psnr} dB`, "worst-case PSNR (all > 40 dB)", HEX.teal],
    [`${D.live.correct}/${D.live.trials}`, "correct liveness decisions incl. photo attacks", HEX.violet]];
  stats.forEach(([v, l, col], i) => {
    const x = 0.6 + i * 4.1;
    txt(s, v, { x, y: 1.35, w: 3.9, h: 0.75, fontSize: 36, bold: true, color: col, fontFace: "Arial" });
    txt(s, l, { x, y: 2.05, w: 3.9, h: 0.4, fontSize: 13, color: HEX.slate });
  });
  const axis = { catAxisLabelColor: "475569", valAxisLabelColor: "475569", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
    valGridLine: { color: "E2E8F0", size: 0.75 }, catGridLine: { style: "none" }, titleFontFace: "+mj-lt", titleFontSize: 14, titleColor: "0B1220", dataLabelFontFace: "+mn-lt", dataLabelFontSize: 11, dataLabelColor: "1C2A44" };
  s.addChart(pres.charts.BAR, [{ name: "Mean PSNR (dB)", labels: D.psnr.map((p) => p.payload), values: D.psnr.map((p) => p.mean) }], {
    x: 0.6, y: 2.65, w: 5.9, h: 3.95, barDir: "col", chartColors: [HEX.teal], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
    showTitle: true, title: `Mean PSNR by payload (${D.images} images)`, showLegend: false, valAxisMinVal: 0, valAxisMaxVal: 90, ...axis });
  s.addChart(pres.charts.BAR, [{ name: "Sequential LSB", labels: D.stega.map((x) => x.fill), values: D.stega.map((x) => x.seq) },
    { name: "FaceLock random LSB", labels: D.stega.map((x) => x.fill), values: D.stega.map((x) => x.rnd) }], {
    x: 6.75, y: 2.65, w: 5.95, h: 3.95, barDir: "col", barGrouping: "clustered", chartColors: [HEX.orange, HEX.aqua], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
    showTitle: true, title: "% of image flagged by chi-square attack, by payload", showLegend: true, legendPos: "b", legendFontFace: "+mn-lt", legendFontSize: 12, valAxisMinVal: 0, valAxisMaxVal: 100, ...axis });
  s.addNotes(`All numbers are from real runs on ${D.images} images and five payloads. Every one of the ${D.ok_runs} embeddings that fitted was recovered exactly; ${D.cap_fail} oversize runs were correctly rejected. PSNR stays far above the 40 dB visibility threshold, the worst case is ${D.min_psnr} dB, and SSIM never drops below ${D.min_ssim}. On the right, the chi-square attack: at 50 percent payload it flags ${D.stega[2].seq} percent of the image for sequential LSB but only ${D.stega[2].rnd} percent for our random LSB. At 100 percent both are detected, which I will come back to in limitations. Liveness made the right decision in all ${D.live.trials} synthetic trials. A 10 KB secret in a 768 by 512 image embeds in about ${D.kodak10_embed} ms.`);

  // ================================================================ 14 Limitations
  pres.addSection({ title: "Closing" });
  s = content("Limitations and future work", "Closing");
  card(s, 0.6, 1.5, 5.9, 5.1, "FDECEF");
  txt(s, "Honest limitations", { x: 0.9, y: 1.7, w: 5.3, h: 0.5, fontSize: 20, bold: true, color: HEX.red });
  txt(s, [
    { text: "Face check is a server policy gate, not a cryptographic binding (device key + vault would bypass it)", options: { bullet: true, breakLine: true } },
    { text: "Vault opens by face only on the owner's device", options: { bullet: true, breakLine: true } },
    { text: "JPEG, resizing or cropping destroys the payload (detected, not silent)", options: { bullet: true, breakLine: true } },
    { text: "At full capacity any LSB replacement is detectable", options: { bullet: true, breakLine: true } },
    { text: "Liveness stops photos, not real-time deepfakes or masks; tested on synthetic faces", options: { bullet: true } },
  ], { x: 0.9, y: 2.3, w: 5.3, h: 4.1, fontSize: 15, color: HEX.ink, paraSpaceAfter: 8, valign: "top" });
  card(s, 6.8, 1.5, 5.9, 5.1, "E3F6EF");
  txt(s, "Future work", { x: 7.1, y: 1.7, w: 5.3, h: 0.5, fontSize: 20, bold: true, color: "0F7A55" });
  txt(s, [
    { text: "Fuzzy extractor: derive the key from the face itself, no stored template", options: { bullet: true, breakLine: true } },
    { text: "DCT / DWT embedding with error correction to survive compression", options: { bullet: true, breakLine: true } },
    { text: "Adaptive embedding (LSB matching, STC) against RS / ML steganalysis", options: { bullet: true, breakLine: true } },
    { text: "Multi-biometric or face + hardware key", options: { bullet: true, breakLine: true } },
    { text: "Passive anti-spoofing and a user study with real volunteers", options: { bullet: true } },
  ], { x: 7.1, y: 2.3, w: 5.3, h: 4.1, fontSize: 15, color: HEX.ink, paraSpaceAfter: 8, valign: "top" });
  s.addNotes("I want to be clear about the limits. The face check is enforced by the server; someone with both the device key and the vault could bypass it, so a fuzzy extractor that derives the key from the face is the most important next step. LSB is fragile by design, and at full capacity it is detectable regardless of ordering. Liveness defeats photos and replays, not deepfakes, and my face results use synthetic faces, so a real user study is needed.");

  // ================================================================ 15 Conclusion
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Closing" });
  txt(s, "Conclusion", { x: 0.7, y: 0.6, w: 8, h: 0.9, fontSize: 40, bold: true, color: "FFFFFF", fontFace: "Arial" });
  const concl = [["LuLock", "Confidential", "AES-256-GCM with a key that never touches the image"],
    ["LuEyeOff", "Invisible", `PSNR ≥ ${D.min_psnr} dB, SSIM ≥ ${D.min_ssim}; chi-square flags ${D.stega[2].rnd}% at 50% load`],
    ["LuScanFace", "Personal", "Only a live, enrolled face (or backup password) releases the key"],
    ["LuShieldCheck", "Accountable", "Lockout, audit log and intruder photos; all checks server-side"]];
  for (let i = 0; i < 4; i++) {
    const y = 1.75 + i * 1.12;
    await iconBadge(s, concl[i][0], 0.7, y, 0.7, HEX.teal);
    txt(s, concl[i][1], { x: 1.65, y: y - 0.02, w: 6.5, h: 0.42, fontSize: 20, bold: true, color: "FFFFFF" });
    txt(s, concl[i][2], { x: 1.65, y: y + 0.4, w: 6.5, h: 0.4, fontSize: 14, color: "AFC0D6" });
  }
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.9, y: 1.75, w: 3.8, h: 3.9, rectRadius: 0.2, fill: { color: "13213A" }, line: { color: HEX.teal, width: 1.5 } });
  s.addImage({ data: await icon("LuHelpCircle", "#0E9FBF"), x: 10.2, y: 2.2, w: 1.2, h: 1.2 });
  txt(s, "Questions?", { x: 8.9, y: 3.6, w: 3.8, h: 0.7, fontSize: 30, bold: true, color: "FFFFFF", align: "center" });
  txt(s, "Thank you", { x: 8.9, y: 4.3, w: 3.8, h: 0.5, fontSize: 16, color: "AFC0D6", align: "center" });
  txt(s, `${MEMBERS.map((m) => `${m.name} (${m.roll_no})`).join("  ·  ")}  ·  Supervisor: ${C.supervisor}`, { x: 0.7, y: 6.6, w: 12, h: 0.4, fontSize: 12, color: "8094B0" });
  s.addNotes("To conclude: FaceLock Stego keeps a secret confidential with AES-GCM, invisible with random LSB embedding, personal through a live face check, and accountable through logging and lockout. Every result I showed was measured on the dataset in the repository. Thank you, I am happy to take questions.");

  await pres.writeFile({ fileName: outPath });
  if (!process.env.NO_THEME) await applyTheme(outPath, THEME);
  // remove folder entries from the ZIP (some cloud editors reject them)
  console.log("wrote", outPath);
})().catch((e) => { console.error(e); process.exit(1); });
