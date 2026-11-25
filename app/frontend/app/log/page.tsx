"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, Lock, RefreshCw, ScrollText, ShieldAlert, ShieldCheck, Trash2, UserX, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, Empty, PageHeader, Stat } from "@/components/ui";
import { api, type LogItem } from "@/lib/api";
import { when } from "@/lib/format";

const tone = (r: string) => (r === "granted" || r === "ok" ? "ok" : r === "denied" ? "bad" : r === "locked" ? "warn" : "neutral") as "ok" | "bad" | "warn" | "neutral";

export default function LogPage() {
  const [items, setItems] = useState<LogItem[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [zoom, setZoom] = useState<LogItem | null>(null);
  const [filter, setFilter] = useState<"all" | "extract" | "denied">("all");

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.logs(); setItems(r.items); setStats(r.stats); } catch { /* backend offline: shell shows status */ } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); const id = setInterval(load, 8000); return () => clearInterval(id); }, [load]);

  const shown = items.filter((i) => filter === "all" || (filter === "extract" ? i.action === "extract" : i.result === "denied"));
  const intruders = items.filter((i) => i.photo).length;

  return (
    <div>
      <PageHeader icon={<ScrollText className="h-6 w-6" />} title="Security Log" subtitle="Every enrolment, hide and unlock attempt is recorded server-side. Failed face attempts store an intruder snapshot; three failures lock the vault temporarily."
        right={<div className="flex gap-2">
          <Button variant="ghost" onClick={load} loading={loading}><RefreshCw className="h-4 w-4" /> Refresh</Button>
          <Button variant="ghost" onClick={async () => { if (confirm("Clear the whole security log?")) { await api.clearLogs(); load(); } }}><Trash2 className="h-4 w-4" /> Clear</Button>
        </div>} />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Access granted" value={stats.granted || 0} tone="ok" icon={<ShieldCheck className="h-4 w-4" />} />
        <Stat label="Access denied" value={stats.denied || 0} tone="bad" icon={<ShieldAlert className="h-4 w-4" />} />
        <Stat label="Lockout hits" value={stats.locked || 0} tone="warn" icon={<Lock className="h-4 w-4" />} />
        <Stat label="Intruder photos" value={intruders} tone="violet" icon={<Camera className="h-4 w-4" />} />
      </div>

      <Card title="Attempts" icon={<ScrollText className="h-4 w-4" />} action={
        <div className="flex gap-1 text-xs">
          {(["all", "extract", "denied"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`rounded-lg px-3 py-1.5 capitalize transition ${filter === f ? "bg-brand-400/15 text-brand-300" : "text-slate-600 hover:text-slate-500"}`}>{f}</button>
          ))}
        </div>}>
        {shown.length === 0 ? (
          <Empty icon={<ScrollText className="h-8 w-8" />} title="No events yet">Hide or extract something to see entries here.</Empty>
        ) : (
          <div className="-mx-2 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-wider text-slate-600">
                  <th className="px-3 py-2 font-medium">Time</th><th className="px-3 py-2 font-medium">Action</th><th className="px-3 py-2 font-medium">Result</th>
                  <th className="px-3 py-2 font-medium">Reason</th><th className="px-3 py-2 font-medium">Score</th><th className="px-3 py-2 font-medium">Intruder</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence initial={false}>
                  {shown.map((i) => (
                    <motion.tr key={i.id} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="border-t border-slate-200 align-middle hover:bg-slate-100">
                      <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-slate-500">{when(i.ts)}</td>
                      <td className="px-3 py-3 text-slate-500">{i.action}{i.method ? <span className="text-slate-600"> · {i.method}</span> : null}</td>
                      <td className="px-3 py-3"><Badge tone={tone(i.result)}>{i.result}</Badge></td>
                      <td className="max-w-xs px-3 py-3 text-slate-500">{i.reason}{i.matched_label ? <span className="text-ok-400"> ({i.matched_label})</span> : null}</td>
                      <td className="px-3 py-3 font-mono text-xs text-slate-500">{i.score != null ? i.score.toFixed(3) : "—"}</td>
                      <td className="px-3 py-3">
                        {i.photo ? (
                          <button onClick={() => setZoom(i)} className="block overflow-hidden rounded-lg border border-bad-400/40 transition hover:scale-105">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={api.logPhotoUrl(i.id)} alt="intruder" className="h-12 w-16 object-cover" />
                          </button>
                        ) : <span className="text-slate-500">—</span>}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <AnimatePresence>
        {zoom && (
          <motion.div className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setZoom(null)}>
            <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }} className="card max-w-xl p-4" onClick={(e) => e.stopPropagation()}>
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-bad-400"><UserX className="h-4 w-4" /> Intruder capture · {when(zoom.ts)}</div>
                <button aria-label="Close" onClick={() => setZoom(null)} className="rounded-lg p-1 text-slate-500 hover:bg-slate-100"><X className="h-4 w-4" /></button>
              </div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={api.logPhotoUrl(zoom.id)} alt="intruder" className="w-full -scale-x-100 rounded-xl" />
              <p className="mt-3 text-sm text-slate-500">{zoom.reason}</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
