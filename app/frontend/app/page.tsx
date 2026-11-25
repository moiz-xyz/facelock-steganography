"use client";
import { motion } from "framer-motion";
import { ArrowRight, Eye, EyeOff, Fingerprint, KeyRound, Lock, ScanFace, Shuffle, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

/** Animated grid of "pixels" whose LSBs flip randomly: the hero visual. */
function PixelField() {
  const N = 14 * 10;
  const [flips, setFlips] = useState<Set<number>>(new Set());
  useEffect(() => {
    const id = setInterval(() => {
      const s = new Set<number>();
      for (let i = 0; i < 18; i++) s.add(Math.floor(Math.random() * N));
      setFlips(s);
    }, 900);
    return () => clearInterval(id);
  }, [N]);
  return (
    <div className="grid grid-cols-[repeat(14,minmax(0,1fr))] gap-1.5">
      {Array.from({ length: N }).map((_, i) => {
        const hue = 190 + ((i * 7) % 80);
        const on = flips.has(i);
        return (
          <motion.div key={i} className="aspect-square rounded-[5px]"
            animate={{ backgroundColor: on ? "rgba(8,145,178,.95)" : `hsla(${hue},65%,${84 + ((i * 13) % 10)}%,1)`, scale: on ? 1.12 : 1 }}
            transition={{ duration: 0.35 }} />
        );
      })}
    </div>
  );
}

const features = [
  { icon: Lock, title: "AES-256-GCM", text: "The secret is encrypted with a fresh random key before it touches a pixel." },
  { icon: Shuffle, title: "Keyed random LSB", text: "Bits are scattered over pseudo-random pixels chosen by a key, never stored in the image." },
  { icon: Fingerprint, title: "Face Vault", text: "The key lives in a separate .vault, wrapped by keys derived from enrolled face templates." },
  { icon: Eye, title: "Live verification", text: "Blink detection (EAR) and a random head-turn challenge defeat printed or on-screen photos." },
];

export default function Home() {
  return (
    <div className="space-y-16">
      <section className="relative grid items-center gap-10 pt-4 lg:grid-cols-[1.1fr_.9fr]">
        <div>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="chip mb-5 border-brand-400/30 bg-brand-400/10 text-brand-300">
            <Sparkles className="h-3.5 w-3.5" /> Information Security · Final Year Project
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
            className="text-4xl font-semibold leading-[1.05] tracking-tight text-slate-900 md:text-6xl">
            Hide secrets in plain sight.<br />
            <span className="bg-gradient-to-r from-brand-300 via-brand-400 to-violet-400 bg-clip-text text-transparent">Unlock them with your face.</span>
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="mt-6 max-w-xl text-lg leading-relaxed text-slate-500">
            FaceLock Stego hides encrypted messages and files inside ordinary PNG images. Only a registered person, verified live in front of the camera, can extract them.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="mt-8 flex flex-wrap gap-3">
            <Link href="/hide" className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-500 to-brand-400 px-6 py-3.5 font-semibold text-ink-950 shadow-glow transition hover:brightness-110">
              <EyeOff className="h-5 w-5" /> Hide a secret <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </Link>
            <Link href="/extract" className="group inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-slate-50 px-6 py-3.5 font-semibold text-slate-900 transition hover:bg-slate-100">
              <KeyRound className="h-5 w-5" /> Extract a secret
            </Link>
            <Link href="/enroll" className="inline-flex items-center gap-2 rounded-xl px-4 py-3.5 font-medium text-slate-500 transition hover:text-slate-900">
              <ScanFace className="h-5 w-5" /> Enroll your face first
            </Link>
          </motion.div>
        </div>
        <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.15 }} className="card relative p-6">
          <div className="mb-4 flex items-center justify-between text-xs text-slate-500">
            <span className="font-mono">cover.png · LSB plane</span>
            <span className="chip border-ok-400/30 bg-ok-400/10 text-ok-400"><ShieldCheck className="h-3 w-3" /> PSNR &gt; 60 dB</span>
          </div>
          <PixelField />
          <div className="mt-5 grid grid-cols-3 gap-3 text-center">
            {[["1 bit", "per colour channel"], ["±1", "max change per value"], ["0", "keys stored in image"]].map(([a, b]) => (
              <div key={b} className="rounded-xl bg-slate-50 p-3">
                <div className="font-mono text-lg font-semibold text-brand-300">{a}</div>
                <div className="text-[11px] text-slate-600">{b}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {features.map(({ icon: Icon, title, text }, i) => (
          <motion.div key={title} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.07 }} className="card group p-6 transition hover:border-brand-400/30">
            <div className="mb-4 grid h-11 w-11 place-items-center rounded-xl bg-brand-400/10 text-brand-300 transition group-hover:scale-110"><Icon className="h-5 w-5" /></div>
            <div className="font-semibold text-slate-900">{title}</div>
            <p className="mt-2 text-sm leading-relaxed text-slate-500">{text}</p>
          </motion.div>
        ))}
      </section>

      <section className="card overflow-hidden p-8">
        <div className="grid gap-8 md:grid-cols-3">
          {[
            ["Image alone", "Looks like a normal photo. Without the key, attackers do not even know which pixels to read.", "text-slate-500"],
            ["Image + vault", "Still locked: the vault releases the key only after a live face match on the owner's device.", "text-brand-300"],
            ["Image + vault + live face", "Access granted. The message is decrypted and its integrity verified by the GCM tag.", "text-ok-400"],
          ].map(([t, d, c], i) => (
            <div key={t} className="relative">
              <div className="font-mono text-xs text-slate-600">0{i + 1}</div>
              <div className={`mt-1 text-lg font-semibold ${c}`}>{t}</div>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{d}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
