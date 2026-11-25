"use client";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity, Check, Download, EyeOff, FileText, FileUp, ImageIcon, KeyRound, Lock, Shuffle, Sparkles, Type, Users, Vault, X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Dropzone } from "@/components/Dropzone";
import { Alert, Badge, Button, Card, PageHeader, Stat, Tabs, Toggle } from "@/components/ui";
import { api, ApiError, fetchAsFile, type HideResult, type Profile } from "@/lib/api";
import { rememberJob, useDemo } from "@/lib/demo";
import { bytes, capacityOf, db, packedSize } from "@/lib/format";

const STEPS = [
  { icon: Lock, label: "Encrypting with AES-256-GCM" },
  { icon: Shuffle, label: "Selecting key-driven random pixels" },
  { icon: Sparkles, label: "Embedding bits into LSBs" },
  { icon: Vault, label: "Sealing the Face Vault" },
];

function CapacityMeter({ used, cap }: { used: number; cap: number }) {
  const pct = cap ? (used / cap) * 100 : 0;
  const tone = pct > 100 ? "bg-bad-400" : pct > 60 ? "bg-warn-400" : "bg-gradient-to-r from-brand-500 to-brand-300";
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="label">Capacity</span>
        <span className={clsx("font-mono text-sm", pct > 100 ? "text-bad-400" : "text-slate-500")}>{bytes(used)} / {bytes(cap)} · {pct.toFixed(pct < 1 ? 2 : 1)}%</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-ink-950 ring-1 ring-white/5">
        <motion.div className={clsx("h-full rounded-full", tone)} animate={{ width: `${Math.min(100, Math.max(pct, used ? 0.8 : 0))}%` }} transition={{ type: "spring", stiffness: 80, damping: 18 }} />
      </div>
      <div className="mt-1.5 text-[11px] text-slate-600">
        {pct > 100 ? "Payload too large for this image: use a bigger cover or a smaller secret." : "Estimate before compression; 1 bit per R, G and B value. Under ~50% keeps statistical traces low."}
      </div>
    </div>
  );
}

export default function HidePage() {
  const { demo } = useDemo();
  const [cover, setCover] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);
  const [mode, setMode] = useState<"text" | "file">("text");
  const [message, setMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [usePw, setUsePw] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(-1);
  const [result, setResult] = useState<HideResult | null>(null);
  const [error, setError] = useState("");
  const [demoCovers, setDemoCovers] = useState<string[]>([]);

  useEffect(() => { api.profiles().then((p) => { setProfiles(p); if (p.length === 1) setSelected([p[0].id]); }).catch(() => undefined); }, []);
  useEffect(() => { if (demo) api.demo().then((d) => setDemoCovers(d.covers)).catch(() => undefined); }, [demo]);

  function pickCover(f: File) {
    setCover(f); setResult(null); setError("");
    const url = URL.createObjectURL(f);
    setPreview(url);
    const img = new Image();
    img.onload = () => setDims({ w: img.naturalWidth, h: img.naturalHeight });
    img.src = url;
  }

  const cap = dims ? capacityOf(dims.w, dims.h) : 0;
  const need = useMemo(() => {
    if (mode === "text") return message ? packedSize(new TextEncoder().encode(message).length) : 0;
    return file ? packedSize(file.size, file.name, file.type || "application/octet-stream") : 0;
  }, [mode, message, file]);
  const isJpeg = cover && /jpe?g|webp/i.test(cover.type + cover.name);
  const canHide = cover && need > 0 && (selected.length > 0 || (usePw && password.length >= 8)) && !busy;

  async function run() {
    if (!cover) return;
    setBusy(true); setError(""); setResult(null); setStep(0);
    const ticker = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 550);
    try {
      const r = await api.hide({ cover, message: mode === "text" ? message : undefined, file: mode === "file" ? file : null, profileIds: selected, password: usePw ? password : undefined });
      clearInterval(ticker);
      setStep(STEPS.length);
      await new Promise((res) => setTimeout(res, 400));
      setResult(r);
      rememberJob({ job_id: r.job_id, name: cover.name, ts: Date.now(), psnr: r.metrics.psnr });
    } catch (e) {
      clearInterval(ticker);
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false); setStep(-1);
    }
  }

  return (
    <div>
      <PageHeader icon={<EyeOff className="h-6 w-6" />} title="Hide Data" subtitle="Choose a cover image and a secret. FaceLock encrypts it, scatters the bits over random pixels and gives you a PNG plus a Face Vault file." />
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-6">
          <Card title="1 · Cover image" icon={<ImageIcon className="h-4 w-4" />} action={cover && <button onClick={() => { setCover(null); setPreview(""); setDims(null); setResult(null); }} className="text-xs text-slate-600 hover:text-slate-500">Clear</button>}>
            {!cover ? (
              <Dropzone onFile={pickCover} accept="image/png,image/jpeg,image/bmp,image/webp" label="Drop a cover image or click to browse" hint="PNG recommended · output is always lossless PNG" />
            ) : (
              <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preview} alt="cover" className="aspect-square w-full rounded-xl border border-slate-200 object-cover" />
                <div className="space-y-3">
                  <div className="truncate text-sm font-medium text-slate-900">{cover.name}</div>
                  <div className="flex flex-wrap gap-2">
                    {dims && <Badge>{dims.w} × {dims.h}px</Badge>}
                    <Badge>{bytes(cover.size)}</Badge>
                    <Badge tone={isJpeg ? "warn" : "ok"}>{isJpeg ? "JPG input" : "Lossless input"}</Badge>
                  </div>
                  <CapacityMeter used={need} cap={cap} />
                </div>
              </div>
            )}
            {isJpeg && <div className="mt-4"><Alert tone="warn">JPG covers are accepted but the output is saved as <b>PNG</b>. Never re-save or send the stego image as JPG: lossy compression destroys the hidden bits.</Alert></div>}
            {demo && demoCovers.length > 0 && (
              <div className="mt-4">
                <div className="label mb-2">Demo samples</div>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {demoCovers.map((c) => (
                    <button key={c} onClick={async () => pickCover(await fetchAsFile(api.demoCoverUrl(c), c, "image/png"))} className="shrink-0 overflow-hidden rounded-lg border border-slate-200 transition hover:border-brand-400/60">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={api.demoCoverUrl(c)} alt={c} className="h-16 w-20 object-cover" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card title="2 · Secret" icon={<FileText className="h-4 w-4" />} action={<Tabs value={mode} onChange={setMode} items={[{ value: "text", label: "Text", icon: <Type className="h-3.5 w-3.5" /> }, { value: "file", label: "File", icon: <FileUp className="h-3.5 w-3.5" /> }]} />}>
            {mode === "text" ? (
              <div>
                <textarea className="input min-h-[150px] resize-y font-mono" placeholder="Type the secret message…" value={message} onChange={(e) => setMessage(e.target.value)} />
                <div className="mt-2 flex justify-between text-[11px] text-slate-600">
                  <span>{message.length} characters</span>
                  {demo && <button className="text-brand-300 hover:underline" onClick={() => setMessage("Launch codes rotate at 06:00 UTC.\nNew passphrase: violet-anchor-1729\nDestroy after reading.")}>Fill sample message</button>}
                </div>
              </div>
            ) : file ? (
              <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="flex items-center gap-3"><FileText className="h-5 w-5 text-brand-300" /><div><div className="text-sm text-slate-900">{file.name}</div><div className="text-xs text-slate-600">{bytes(file.size)} · {file.type || "binary"}</div></div></div>
                <button aria-label="Remove file" onClick={() => setFile(null)} className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100"><X className="h-4 w-4" /></button>
              </div>
            ) : (
              <Dropzone compact onFile={setFile} label="Drop any file (PDF, ZIP, DOCX…)" hint="It will be compressed (when useful) and encrypted" />
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="3 · Who can unlock it" icon={<Users className="h-4 w-4" />} action={<Badge tone="info">{selected.length}/3 selected</Badge>}>
            {profiles.length === 0 ? (
              <Alert tone="info">No faces enrolled yet. <Link href="/enroll" className="font-semibold text-brand-300 underline">Enroll a face</Link> or use a backup password only.</Alert>
            ) : (
              <div className="flex flex-wrap gap-2">
                {profiles.map((p) => {
                  const on = selected.includes(p.id);
                  return (
                    <button key={p.id} onClick={() => setSelected(on ? selected.filter((x) => x !== p.id) : selected.length < 3 ? [...selected, p.id] : selected)}
                      className={clsx("flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition", on ? "border-brand-400/60 bg-brand-400/15 text-slate-900" : "border-slate-200 text-slate-500 hover:border-slate-400")}>
                      <span className={clsx("grid h-5 w-5 place-items-center rounded-full text-[10px]", on ? "bg-brand-400 text-ink-950" : "bg-ink-700")}>{on ? <Check className="h-3 w-3" /> : p.label[0]}</span>
                      {p.label}
                    </button>
                  );
                })}
              </div>
            )}
            <div className="mt-5 border-t border-slate-200 pt-4">
              <Toggle checked={usePw} onChange={setUsePw} label={<span className="flex items-center gap-1.5"><KeyRound className="h-4 w-4 text-slate-500" /> Backup password (Argon2id)</span>} />
              <AnimatePresence>
                {usePw && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                    <input type="password" className="input mt-3" placeholder="At least 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} />
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink-950">
                      <div className={clsx("h-full transition-all", password.length >= 14 ? "bg-ok-400" : password.length >= 8 ? "bg-warn-400" : "bg-bad-400")} style={{ width: `${Math.min(100, password.length * 7)}%` }} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </Card>

          <Card>
            <Button className="w-full py-3.5 text-base" disabled={!canHide || need > cap} onClick={run} loading={busy}>
              <EyeOff className="h-5 w-5" /> Hide secret in image
            </Button>
            <AnimatePresence>
              {busy && (
                <motion.ul initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="mt-4 space-y-2 overflow-hidden">
                  {STEPS.map(({ icon: Icon, label }, i) => (
                    <li key={label} className={clsx("flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition", i < step ? "text-ok-400" : i === step ? "bg-brand-400/10 text-brand-300" : "text-slate-500")}>
                      {i < step ? <Check className="h-4 w-4" /> : <Icon className={clsx("h-4 w-4", i === step && "animate-pulse")} />}
                      {label}
                    </li>
                  ))}
                </motion.ul>
              )}
            </AnimatePresence>
            {error && <div className="mt-4"><Alert tone="bad">{error}</Alert></div>}
          </Card>

          <AnimatePresence>
            {result && (
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card overflow-hidden border-ok-400/25 p-6">
                <div className="flex items-center gap-3">
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring" }} className="grid h-10 w-10 place-items-center rounded-full bg-ok-400/15 text-ok-400"><Check className="h-5 w-5" /></motion.div>
                  <div>
                    <div className="font-semibold text-slate-900">Secret hidden successfully</div>
                    <div className="text-xs text-slate-600">{bytes(result.embedded_bytes)} embedded · {result.usage_pct.toFixed(2)}% of capacity · {(result.embed_seconds * 1000).toFixed(0)} ms</div>
                  </div>
                </div>
                <div className="mt-5 grid grid-cols-2 gap-3">
                  <Stat label="PSNR" value={db(result.metrics.psnr)} tone="ok" />
                  <Stat label="SSIM" value={result.metrics.ssim.toFixed(5)} tone="brand" />
                </div>
                {result.warnings.map((w) => <div key={w} className="mt-4"><Alert tone="warn">{w}</Alert></div>)}
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <a href={api.jobUrl(result.job_id, "stego")} download className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-500 to-brand-400 px-4 py-3 text-sm font-semibold text-ink-950"><Download className="h-4 w-4" /> Stego image (.png)</a>
                  <a href={api.jobUrl(result.job_id, "vault")} download className="inline-flex items-center justify-center gap-2 rounded-xl border border-violet-400/40 bg-violet-500/10 px-4 py-3 text-sm font-semibold text-violet-400"><Vault className="h-4 w-4" /> Face Vault (.vault)</a>
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-slate-600">Keep the vault separate from the image (e.g. on your own device). Authorised: {result.authorized.join(", ") || "none"}{result.password_fallback ? " + backup password" : ""}.</p>
                <Link href={`/analysis?job=${result.job_id}`} className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-brand-300 hover:underline"><Activity className="h-4 w-4" /> Open in Analysis Dashboard</Link>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
