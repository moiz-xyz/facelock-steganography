"use client";
/** Small design-system primitives shared by every page. */
import clsx from "clsx";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function PageHeader({ icon, title, subtitle, right }: { icon: ReactNode; title: string; subtitle: string; right?: ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="flex items-center gap-4">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-400/25 to-violet-500/20 text-brand-300 ring-1 ring-slate-200">
          {icon}
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 md:text-3xl">{title}</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">{subtitle}</p>
        </div>
      </div>
      {right}
    </motion.div>
  );
}

export function Card({ children, className, title, icon, action }: { children: ReactNode; className?: string; title?: string; icon?: ReactNode; action?: ReactNode }) {
  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className={clsx("card p-5 md:p-6", className)}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
            {icon && <span className="text-brand-300">{icon}</span>}
            {title}
          </div>
          {action}
        </div>
      )}
      {children}
    </motion.section>
  );
}

type Variant = "primary" | "ghost" | "danger" | "success" | "outline";
export function Button({ variant = "primary", loading, className, children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  const styles: Record<Variant, string> = {
    primary: "bg-gradient-to-r from-brand-500 to-brand-400 text-ink-950 hover:brightness-110 shadow-glow",
    success: "bg-gradient-to-r from-ok-500 to-ok-400 text-ink-950 hover:brightness-110",
    danger: "bg-bad-500/90 text-white hover:bg-bad-500",
    ghost: "bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200",
    outline: "border border-brand-400/40 text-brand-300 hover:bg-brand-400/10",
  };
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-50",
        styles[variant],
        className,
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "ok" | "bad" | "warn" | "info" | "neutral"; children: ReactNode }) {
  const t = {
    ok: "border-ok-400/30 bg-ok-400/10 text-ok-400",
    bad: "border-bad-400/30 bg-bad-400/10 text-bad-400",
    warn: "border-warn-400/30 bg-warn-400/10 text-warn-400",
    info: "border-brand-400/30 bg-brand-400/10 text-brand-300",
    neutral: "border-slate-200 bg-slate-100 text-slate-500",
  }[tone];
  return <span className={clsx("chip", t)}>{children}</span>;
}

export function Alert({ tone = "info", children }: { tone?: "ok" | "bad" | "warn" | "info"; children: ReactNode }) {
  const map = {
    ok: ["border-ok-400/30 bg-ok-400/[.07] text-ok-400", <CheckCircle2 key="i" className="h-4 w-4 shrink-0" />],
    bad: ["border-bad-400/30 bg-bad-400/[.07] text-bad-400", <XCircle key="i" className="h-4 w-4 shrink-0" />],
    warn: ["border-warn-400/30 bg-warn-400/[.07] text-warn-400", <AlertTriangle key="i" className="h-4 w-4 shrink-0" />],
    info: ["border-brand-400/30 bg-brand-400/[.07] text-brand-300", <Info key="i" className="h-4 w-4 shrink-0" />],
  } as const;
  const [cls, icon] = map[tone];
  return (
    <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className={clsx("flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm", cls)}>
      <span className="mt-0.5">{icon}</span>
      <div className="text-slate-700">{children}</div>
    </motion.div>
  );
}

export function Stat({ label, value, hint, tone = "brand", icon }: { label: string; value: ReactNode; hint?: string; tone?: "brand" | "ok" | "bad" | "violet" | "warn"; icon?: ReactNode }) {
  const c = { brand: "text-brand-300", ok: "text-ok-400", bad: "text-bad-400", violet: "text-violet-400", warn: "text-warn-400" }[tone];
  return (
    <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="card relative overflow-hidden p-5">
      <div className="flex items-center justify-between">
        <span className="label">{label}</span>
        {icon && <span className={clsx("opacity-80", c)}>{icon}</span>}
      </div>
      <div className={clsx("mt-2 font-mono text-2xl font-semibold tracking-tight", c)}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-600">{hint}</div>}
    </motion.div>
  );
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { value: T; label: string; icon?: ReactNode }[] }) {
  return (
    <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1">
      {items.map((it) => (
        <button key={it.value} onClick={() => onChange(it.value)} className={clsx("relative flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-sm font-medium transition", value === it.value ? "text-ink-950" : "text-slate-500 hover:text-slate-700")}>
          {value === it.value && <motion.span layoutId={`tab-${items.map((i) => i.value).join()}`} className="absolute inset-0 rounded-lg bg-brand-400" transition={{ type: "spring", bounce: 0.2, duration: 0.4 }} />}
          <span className="relative flex items-center gap-1.5">{it.icon}{it.label}</span>
        </button>
      ))}
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: ReactNode }) {
  return (
    <button type="button" onClick={() => onChange(!checked)} className="flex items-center gap-3 text-sm text-slate-500">
      <span className={clsx("relative h-6 w-11 rounded-full transition", checked ? "bg-brand-400" : "bg-ink-700")}>
        <motion.span layout className={clsx("absolute top-1 h-4 w-4 rounded-full bg-white shadow", checked ? "left-6" : "left-1")} />
      </span>
      {label}
    </button>
  );
}

export function ProgressRing({ value, size = 160, stroke = 10, children, color = "#38d4ef" }: { value: number; size?: number; stroke?: number; children?: ReactNode; color?: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(15,23,42,.08)" strokeWidth={stroke} fill="none" />
        <motion.circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={c} animate={{ strokeDashoffset: c * (1 - Math.min(1, Math.max(0, value))) }} transition={{ type: "spring", stiffness: 60, damping: 15 }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center">{children}</div>
    </div>
  );
}

export function Empty({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 px-6 py-14 text-center">
      <div className="mb-3 text-slate-600">{icon}</div>
      <div className="font-medium text-slate-500">{title}</div>
      {children && <div className="mt-1 max-w-md text-sm text-slate-600">{children}</div>}
    </div>
  );
}
