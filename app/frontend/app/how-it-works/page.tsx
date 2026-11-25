"use client";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, ChevronLeft, ChevronRight, Eye, Fingerprint, ImageIcon, KeyRound, Lock, Pause, Play, ScanFace, Shuffle, Unlock } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { PageHeader } from "@/components/ui";

/** The LSB idea in one animation: a pixel's colour values before and after embedding. */
function LsbDemo() {
  const [phase, setPhase] = useState(0);
  useEffect(() => { const id = setInterval(() => setPhase((p) => (p + 1) % 2), 2200); return () => clearInterval(id); }, []);
  const before = [154, 201, 87];
  const bits = [1, 0, 0];
  const after = before.map((v, i) => (v & 0xfe) | bits[i]);
  const vals = phase ? after : before;
  return (
    <div className="flex flex-col items-center gap-6 md:flex-row md:justify-center">
      <motion.div className="h-28 w-28 rounded-2xl ring-1 ring-slate-200" animate={{ backgroundColor: `rgb(${vals.join(",")})` }} />
      <div className="space-y-2 font-mono text-sm">
        {["R", "G", "B"].map((c, i) => {
          const bin = vals[i].toString(2).padStart(8, "0");
          return (
            <div key={c} className="flex items-center gap-3">
              <span className="w-4 text-slate-600">{c}</span>
              <span className="w-10 text-right text-slate-500">{vals[i]}</span>
              <span className="tracking-[.25em] text-slate-500">{bin.slice(0, 7)}</span>
              <motion.span key={`${phase}${i}`} initial={{ scale: 1.6, color: "#0891b2" }} animate={{ scale: 1, color: phase && before[i] !== after[i] ? "#34d399" : "#0891b2" }}
                className="-ml-2 rounded bg-brand-400/15 px-1 font-bold">{bin[7]}</motion.span>
            </div>
          );
        })}
      </div>
      <div className="max-w-xs text-sm text-slate-500">
        Hiding the bits <span className="font-mono text-brand-300">{bits.join(" ")}</span> changes each value by at most 1, a difference no human eye can see.
        <div className="mt-2 text-xs text-slate-600">{phase ? "After embedding" : "Before embedding"}</div>
      </div>
    </div>
  );
}

const STEPS: { icon: typeof Lock; title: string; tag: string; body: string; visual: ReactNode }[] = [
  {
    icon: ScanFace, title: "Enroll your face", tag: "Biometrics",
    body: "Five webcam samples are turned into 128-dimensional face embeddings by OpenCV's SFace network. They are averaged into one template and stored encrypted with this device's key. No photo is kept.",
    visual: <div className="grid grid-cols-8 gap-1">{Array.from({ length: 64 }).map((_, i) => <motion.div key={i} className="h-5 rounded-sm bg-violet-400" initial={{ opacity: 0.1 }} animate={{ opacity: [0.15, Math.abs(Math.sin(i * 1.7)), 0.15] }} transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.02 }} />)}</div>,
  },
  {
    icon: Lock, title: "Encrypt the secret", tag: "AES-256-GCM",
    body: "A fresh random 256-bit Data Encryption Key (DEK) encrypts your message with AES-GCM, which also adds a 16-byte authentication tag so any tampering is detected.",
    visual: <div className="font-mono text-xs leading-relaxed text-brand-300">{"Meet at 9 → 8f3a c19e 02d7 ff41 9b0c e6a2 77d1 3e90 …"}</div>,
  },
  {
    icon: Shuffle, title: "Scatter bits over random pixels", tag: "Keyed random LSB",
    body: "A seed derived from the DEK drives an AES-CTR keystream that ranks every colour channel. The bits go into the least significant bit of the top-ranked slots, spread uniformly over the image.",
    visual: <div className="grid grid-cols-12 gap-1">{Array.from({ length: 96 }).map((_, i) => <motion.div key={i} className="aspect-square rounded-[3px]" animate={{ backgroundColor: [(i * 37) % 7 === 0 ? "#0891b2" : "#e2e8f0", "#e2e8f0", (i * 53) % 9 === 0 ? "#0891b2" : "#e2e8f0"] }} transition={{ duration: 3, repeat: Infinity }} />)}</div>,
  },
  {
    icon: Fingerprint, title: "Seal the Face Vault", tag: ".vault file",
    body: "The DEK is NOT stored in the image. It is wrapped once per authorised face with a key derived from that face template and the device key (plus an optional Argon2id password slot). The vault is bound to the exact stego pixels.",
    visual: <div className="flex items-center gap-3 text-sm"><span className="chip border-violet-400/30 bg-violet-500/10 text-violet-400">DEK</span>→<span className="chip border-slate-200 text-slate-500">wrap(face₁)</span><span className="chip border-slate-200 text-slate-500">wrap(face₂)</span><span className="chip border-slate-200 text-slate-500">wrap(password)</span></div>,
  },
  {
    icon: Eye, title: "Prove you are alive", tag: "Liveness",
    body: "The server reads ~50 frames with MediaPipe's 478-point face mesh. It needs real blinks (eye aspect ratio dips) and the random challenge it issued, e.g. a head turn to the left. A photo or a phone screen cannot respond.",
    visual: (
      <motion.div className="w-full" initial={{ clipPath: "inset(0 100% 0 0)" }} animate={{ clipPath: "inset(0 0% 0 0)" }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
        <svg viewBox="0 0 300 80" className="w-full"><path d="M0 30 L60 30 L70 70 L80 30 L170 30 L180 72 L190 30 L300 30" fill="none" stroke="#0891b2" strokeWidth="3" /></svg>
      </motion.div>
    ),
  },
  {
    icon: Unlock, title: "Match and unlock", tag: "Server-side",
    body: "Your live embedding must reach cosine similarity ≥ 0.40 with an authorised template, and stay consistent across the scan. Only then does the server unwrap the DEK, read the random pixels and decrypt. Three failures lock the vault.",
    visual: <motion.div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-ok-400 text-ink-950" animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 1.6, repeat: Infinity }}><KeyRound className="h-8 w-8" /></motion.div>,
  },
];

export default function HowItWorks() {
  const [i, setI] = useState(0);
  const [auto, setAuto] = useState(true);
  useEffect(() => { if (!auto) return; const id = setInterval(() => setI((x) => (x + 1) % STEPS.length), 5000); return () => clearInterval(id); }, [auto]);
  const S = STEPS[i];
  return (
    <div>
      <PageHeader icon={<BookOpen className="h-6 w-6" />} title="How It Works" subtitle="From your face to a hidden, encrypted, liveness-protected secret in six steps." />

      <div className="card mb-8 p-6"><div className="label mb-5 text-center">The core idea: least significant bit (LSB)</div><LsbDemo /></div>

      <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-1">
        {STEPS.map((s, k) => (
          <button key={s.title} onClick={() => { setI(k); setAuto(false); }} className={clsx("flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2 text-sm transition", k === i ? "border-brand-400/50 bg-brand-400/10 text-slate-900" : "border-slate-200 text-slate-600 hover:text-slate-500")}>
            <span className={clsx("grid h-6 w-6 place-items-center rounded-full text-xs font-semibold", k <= i ? "bg-brand-400 text-ink-950" : "bg-ink-700")}>{k + 1}</span>
            <span className="hidden sm:inline">{s.title}</span>
          </button>
        ))}
      </div>

      <div className="card relative overflow-hidden p-8">
        <div className="absolute inset-x-0 top-0 h-1 bg-ink-800"><motion.div className="h-full bg-brand-400" animate={{ width: `${((i + 1) / STEPS.length) * 100}%` }} /></div>
        <AnimatePresence mode="wait">
          <motion.div key={i} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.35 }} className="grid items-center gap-8 md:grid-cols-2">
            <div>
              <div className="chip mb-4 border-brand-400/30 bg-brand-400/10 text-brand-300"><S.icon className="h-3.5 w-3.5" /> {S.tag}</div>
              <h2 className="text-2xl font-semibold text-slate-900 md:text-3xl">{i + 1}. {S.title}</h2>
              <p className="mt-4 leading-relaxed text-slate-500">{S.body}</p>
            </div>
            <div className="grid min-h-[180px] place-items-center rounded-2xl border border-slate-200 bg-slate-50 p-6">{S.visual}</div>
          </motion.div>
        </AnimatePresence>
        <div className="mt-8 flex items-center justify-between">
          <button onClick={() => { setI((i - 1 + STEPS.length) % STEPS.length); setAuto(false); }} className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-100"><ChevronLeft className="h-4 w-4" /> Back</button>
          <button onClick={() => setAuto(!auto)} className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs text-slate-600 hover:bg-slate-100">{auto ? <><Pause className="h-3.5 w-3.5" /> Auto-play on</> : <><Play className="h-3.5 w-3.5" /> Auto-play off</>}</button>
          <button onClick={() => { setI((i + 1) % STEPS.length); setAuto(false); }} className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-100">Next <ChevronRight className="h-4 w-4" /></button>
        </div>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {[
          [ImageIcon, "Image alone", "Statistically noisy LSBs, no key, no positions → nothing to read."],
          [Fingerprint, "Vault alone", "Encrypted with the device key; useless without the stego image."],
          [ScanFace, "Photo of the owner", "Fails liveness: no blinks, cannot follow a random challenge."],
        ].map(([Icon, t, d]) => {
          const I = Icon as typeof Lock;
          return <div key={t as string} className="card p-5"><I className="mb-3 h-5 w-5 text-brand-300" /><div className="font-semibold text-slate-900">{t as string}</div><p className="mt-1 text-sm text-slate-500">{d as string}</p></div>;
        })}
      </div>
    </div>
  );
}
