"use client";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity, BookOpen, EyeOff, FlaskConical, Home, KeyRound, Menu, ScanFace, ScrollText, ShieldCheck, X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { api, type Health } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { Toggle } from "./ui";

export const NAV = [
  { href: "/", label: "Home", icon: Home },
  { href: "/enroll", label: "Enroll Face", icon: ScanFace },
  { href: "/hide", label: "Hide Data", icon: EyeOff },
  { href: "/extract", label: "Extract Data", icon: KeyRound },
  { href: "/analysis", label: "Analysis", icon: Activity },
  { href: "/log", label: "Security Log", icon: ScrollText },
  { href: "/attack-lab", label: "Attack Lab", icon: FlaskConical },
  { href: "/how-it-works", label: "How It Works", icon: BookOpen },
];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-brand-400 to-violet-500 text-ink-950 shadow-glow">
        <ShieldCheck className="h-5 w-5" strokeWidth={2.5} />
      </div>
      <div className="leading-tight">
        <div className="font-semibold tracking-tight text-slate-900">FaceLock Stego</div>
        <div className="text-[11px] text-slate-600">Biometric steganography</div>
      </div>
    </Link>
  );
}

function Status() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let alive = true;
    const tick = () => api.health().then((x) => { if (alive) { setH(x); setErr(false); } }).catch(() => alive && setErr(true));
    tick();
    const id = setInterval(tick, 10000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
      <div className="flex items-center gap-2">
        <span className={clsx("h-2 w-2 rounded-full", err ? "bg-bad-400" : h ? "bg-ok-400 shadow-[0_0_8px] shadow-ok-400" : "bg-warn-400")} />
        <span className="font-medium text-slate-500">{err ? "Backend offline" : h ? "Backend online" : "Connecting…"}</span>
      </div>
      {h && (
        <div className="mt-2 space-y-0.5 text-slate-600">
          <div>Face engine: <span className="text-slate-500">{h.face_engine.toUpperCase()}</span></div>
          <div>Liveness: <span className="text-slate-500">MediaPipe EAR + challenge</span></div>
          <div>Enrolled faces: <span className="text-slate-500">{h.profiles}</span></div>
        </div>
      )}
    </div>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const path = usePathname();
  return (
    <nav className="space-y-1">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? path === "/" : path.startsWith(href);
        return (
          <Link key={href} href={href} onClick={onNavigate}
            className={clsx("relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
              active ? "text-slate-900" : "text-slate-500 hover:bg-slate-100 hover:text-slate-700")}>
            {active && <motion.span layoutId="nav-active" className="absolute inset-0 rounded-xl border border-brand-400/20 bg-gradient-to-r from-brand-400/15 to-transparent" />}
            <Icon className={clsx("relative h-4 w-4", active && "text-brand-300")} />
            <span className="relative">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { demo, setDemo } = useDemo();
  const [open, setOpen] = useState(false);
  const side = (
    <div className="flex h-full flex-col gap-6 p-5">
      <Logo />
      <NavLinks onNavigate={() => setOpen(false)} />
      <div className="mt-auto space-y-3">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <Toggle checked={demo} onChange={setDemo} label={<span className="font-medium">Demo Mode</span>} />
          <p className="mt-2 text-[11px] leading-relaxed text-slate-600">Preloads sample covers and a password-protected demo pair.</p>
        </div>
        <Status />
      </div>
    </div>
  );
  return (
    <div className="bg-aurora min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-slate-50 backdrop-blur-xl lg:block">{side}</aside>
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-ink-950/80 px-4 py-3 backdrop-blur-xl lg:hidden">
        <Logo />
        <button aria-label="Open menu" onClick={() => setOpen(true)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><Menu className="h-5 w-5" /></button>
      </header>
      <AnimatePresence>
        {open && (
          <>
            <motion.div className="fixed inset-0 z-40 bg-black/60 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} />
            <motion.aside className="fixed inset-y-0 left-0 z-50 w-72 border-r border-slate-200 bg-ink-950 lg:hidden" initial={{ x: -300 }} animate={{ x: 0 }} exit={{ x: -300 }} transition={{ type: "spring", damping: 26 }}>
              <button aria-label="Close menu" onClick={() => setOpen(false)} className="absolute right-3 top-4 rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
              {side}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
      <main className="lg:pl-64">
        {demo && (
          <div className="border-b border-warn-400/20 bg-warn-400/[.06] px-6 py-2 text-center text-xs font-medium text-warn-400">
            Demo Mode is on: sample images and the demo pair are one click away.
          </div>
        )}
        <div className="mx-auto max-w-7xl px-4 py-8 md:px-8 md:py-10">{children}</div>
      </main>
    </div>
  );
}
