"use client";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import {
  Camera, Copy, Download, Eye, FileCheck2, ImageIcon, KeyRound, Loader2, Lock, RotateCcw, ScanFace, ShieldAlert, ShieldCheck, Timer, Vault,
} from "lucide-react";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CameraView } from "@/components/CameraView";
import { Dropzone } from "@/components/Dropzone";
import { Alert, Badge, Button, Card, PageHeader, Tabs } from "@/components/ui";
import { api, ApiError, fetchAsFile, type Challenge, type LockStatus, type UnlockResult, type VaultInfo } from "@/lib/api";
import { useWebcam } from "@/lib/camera";
import { useDemo } from "@/lib/demo";
import { b64ToBlob, bytes, downloadBlob } from "@/lib/format";

type Phase = "idle" | "prepare" | "challenge" | "verifying" | "done";
const SCAN_SECONDS = 5;
const FPS = 15;

function FilePill({ icon, file, label, onFile, accept }: { icon: React.ReactNode; file: File | null; label: string; onFile: (f: File) => void; accept: string }) {
  return (
    <Dropzone compact onFile={onFile} accept={accept} label={label}>
      <div className="flex w-full items-center gap-3 text-left">
        <div className={clsx("grid h-10 w-10 shrink-0 place-items-center rounded-xl", file ? "bg-ok-400/15 text-ok-400" : "bg-brand-400/10 text-brand-300")}>{file ? <FileCheck2 className="h-5 w-5" /> : icon}</div>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-slate-900">{file ? file.name : label}</div>
          <div className="text-xs text-slate-600">{file ? bytes(file.size) : "drop or click"}</div>
        </div>
      </div>
    </Dropzone>
  );
}

function LivenessChart({ r }: { r: UnlockResult }) {
  const l = r.liveness;
  if (!l) return null;
  const data = l.ear_series.map((e, i) => ({ t: (i / FPS).toFixed(1), ear: e, yaw: l.yaw_series[i], blink: l.blink_series?.[i] ?? null }));
  return (
    <div className="h-44">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="rgba(15,23,42,.08)" />
          <XAxis dataKey="t" tick={{ fill: "#64748b", fontSize: 10 }} interval={FPS - 1} />
          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} domain={[0, 1]} />
          <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", color: "#0f172a", borderRadius: 12, fontSize: 12 }} />
          <ReferenceLine y={l.ear_baseline * 0.62} stroke="#fbbf24" strokeDasharray="4 4" />
          <Line type="monotone" dataKey="ear" name="Eye aspect ratio" stroke="#38d4ef" strokeWidth={2} dot={false} connectNulls animationDuration={500} />
          <Line type="monotone" dataKey="yaw" name="Nose position (yaw)" stroke="#a78bfa" strokeWidth={2} dot={false} connectNulls animationDuration={500} />
          <Line type="monotone" dataKey="blink" name="Blink score (MediaPipe)" stroke="#fbbf24" strokeWidth={1.5} dot={false} connectNulls animationDuration={500} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function ExtractPage() {
  const { demo } = useDemo();
  const cam = useWebcam();
  const [stego, setStego] = useState<File | null>(null);
  const [vault, setVault] = useState<File | null>(null);
  const [info, setInfo] = useState<VaultInfo | null>(null);
  const [method, setMethod] = useState<"face" | "password">("face");
  const [password, setPassword] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<UnlockResult | null>(null);
  const [lock, setLock] = useState<LockStatus | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demoPw, setDemoPw] = useState("");

  useEffect(() => {
    if (!vault) { setInfo(null); return; }
    api.inspectVault(vault).then((v) => { setInfo(v); setLock(v.lock.locked ? v.lock : null); if (!v.face_slots) setMethod("password"); })
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [vault]);

  useEffect(() => {
    if (!lock?.locked) return;
    const id = setInterval(() => setLock((l) => (l && l.remaining_s > 1 ? { ...l, remaining_s: l.remaining_s - 1 } : null)), 1000);
    return () => clearInterval(id);
  }, [lock?.locked]);

  async function loadDemoPair() {
    setError(""); setResult(null);
    const [s, v, d] = await Promise.all([fetchAsFile(api.demoPairUrl("stego"), "demo_stego.png", "image/png"), fetchAsFile(api.demoPairUrl("vault"), "demo.vault"), api.demo()]);
    setStego(s); setVault(v); setMethod("password"); setDemoPw(d.pair?.password || "");
  }

  function handleError(e: unknown) {
    if (e instanceof ApiError && e.status === 423) {
      const b = e.body as { lock?: LockStatus };
      if (b?.lock) setLock(b.lock);
    }
    setError(e instanceof ApiError ? e.message : String(e));
    setPhase("idle");
  }

  async function faceScan() {
    if (!stego || !vault) return;
    setError(""); setResult(null);
    try {
      if (cam.state !== "ready") await cam.start();
      setPhase("prepare");
      await new Promise((r) => setTimeout(r, 1800));
      const ch = await api.challenge();
      setChallenge(ch); setPhase("challenge"); setProgress(0);
      const frames = await cam.burst(SCAN_SECONDS, FPS, setProgress);
      setPhase("verifying");
      const r = await api.extractFace(stego, vault, ch.challenge_id, frames);
      setResult(r); setLock(r.lock?.locked ? r.lock : null); setPhase("done");
    } catch (e) { handleError(e); }
  }

  async function passwordUnlock() {
    if (!stego || !vault) return;
    setBusy(true); setError(""); setResult(null);
    try {
      const r = await api.extractPassword(stego, vault, password);
      setResult(r); setLock(r.lock?.locked ? r.lock : null); setPhase("done");
    } catch (e) { handleError(e); } finally { setBusy(false); }
  }

  const ready = stego && vault && !lock?.locked;
  const secret = result?.secret;
  const attemptsLeft = result?.lock ? Math.max(0, result.lock.max_failures - result.lock.failures) : null;

  return (
    <div>
      <PageHeader icon={<ScanFace className="h-6 w-6" />} title="Extract Data" subtitle="Upload the stego image and its Face Vault, then prove you are a live, authorised person. The server checks liveness and face match before the vault releases the key."
        right={demo && <Button variant="outline" onClick={loadDemoPair}><Vault className="h-4 w-4" /> Load demo pair</Button>} />

      <div className="grid gap-6 lg:grid-cols-[1fr_1.25fr]">
        <div className="space-y-6">
          <Card title="1 · Files" icon={<ImageIcon className="h-4 w-4" />}>
            <div className="space-y-3">
              <FilePill icon={<ImageIcon className="h-5 w-5" />} file={stego} label="Stego image (.png)" onFile={(f) => { setStego(f); setResult(null); }} accept="image/png,image/bmp" />
              <FilePill icon={<Vault className="h-5 w-5" />} file={vault} label="Face Vault (.vault)" onFile={(f) => { setVault(f); setResult(null); }} accept=".vault,application/json" />
            </div>
            {info && (
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge tone="info"><ScanFace className="h-3 w-3" /> {info.face_slots} face slot{info.face_slots === 1 ? "" : "s"}</Badge>
                <Badge tone={info.password_fallback ? "ok" : "neutral"}><KeyRound className="h-3 w-3" /> {info.password_fallback ? "Password fallback" : "No password"}</Badge>
                <Badge><span className="font-mono">{info.vault_id.slice(0, 10)}…</span></Badge>
              </div>
            )}
          </Card>

          <Card title="2 · Verify" icon={<Lock className="h-4 w-4" />} action={<Tabs value={method} onChange={setMethod} items={[{ value: "face", label: "Face", icon: <ScanFace className="h-3.5 w-3.5" /> }, { value: "password", label: "Password", icon: <KeyRound className="h-3.5 w-3.5" /> }]} />}>
            {lock?.locked ? (
              <div className="flex items-center gap-4 rounded-xl border border-bad-400/30 bg-bad-400/[.07] p-4">
                <Timer className="h-8 w-8 text-bad-400" />
                <div>
                  <div className="font-semibold text-bad-400">Temporarily locked</div>
                  <div className="text-sm text-slate-500">Too many failed attempts. Try again in <span className="font-mono font-semibold">{lock.remaining_s}s</span>.</div>
                </div>
              </div>
            ) : method === "face" ? (
              <div className="space-y-3 text-sm text-slate-500">
                <p>You will get a <b className="text-slate-700">random challenge</b> (blink twice or turn your head). Keep your face inside the oval for {SCAN_SECONDS} seconds.</p>
                <Button className="w-full py-3" onClick={faceScan} disabled={!ready || (phase !== "idle" && phase !== "done") || info?.face_slots === 0}
                  loading={phase === "prepare" || phase === "challenge" || phase === "verifying"}>
                  <Camera className="h-4 w-4" /> Start live face scan
                </Button>
                {info && info.face_slots === 0 && <Alert tone="info">This vault has no face slots; use the backup password.</Alert>}
              </div>
            ) : (
              <div className="space-y-3">
                <input type="password" className="input" placeholder="Backup password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ready && passwordUnlock()} />
                {demo && demoPw && <button className="text-xs text-brand-300 hover:underline" onClick={() => setPassword(demoPw)}>Use demo password</button>}
                <Button className="w-full" onClick={passwordUnlock} disabled={!ready || !password} loading={busy}><KeyRound className="h-4 w-4" /> Unlock with password</Button>
              </div>
            )}
            {error && <div className="mt-4"><Alert tone="bad">{error}</Alert></div>}
          </Card>
        </div>

        <div className="space-y-6">
          {method === "face" && (
            <Card title="Live scan" icon={<Eye className="h-4 w-4" />} action={cam.state === "ready" ? <Button variant="ghost" onClick={cam.stop}>Stop camera</Button> : <Button variant="outline" onClick={cam.start} loading={cam.state === "starting"}>Start camera</Button>}>
              <CameraView videoRef={cam.videoRef} state={cam.state} error={cam.error} scanning={phase === "challenge"}
                tone={phase === "done" ? (result?.granted ? "ok" : "bad") : "brand"}
                overlay={
                  phase === "prepare" ? (
                    <motion.div key="prep" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-5 text-center">
                      <div className="text-lg font-semibold text-white">Look straight at the camera…</div>
                    </motion.div>
                  ) : phase === "challenge" && challenge ? (
                    <motion.div key="ch" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 to-transparent p-5">
                      <div className="label text-brand-300">Liveness challenge</div>
                      <div className="mt-1 text-2xl font-bold text-white">{challenge.instruction}</div>
                      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200"><div className="h-full bg-brand-400 transition-all" style={{ width: `${progress * 100}%` }} /></div>
                    </motion.div>
                  ) : phase === "verifying" ? (
                    <motion.div key="ver" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 grid place-items-center bg-slate-50 backdrop-blur-sm">
                      <div className="flex flex-col items-center gap-3 text-brand-300"><Loader2 className="h-10 w-10 animate-spin" /><div className="font-medium">Verifying liveness and identity on the server…</div></div>
                    </motion.div>
                  ) : null
                } />
            </Card>
          )}

          <AnimatePresence mode="wait">
            {result && (
              <motion.div key={result.granted ? "g" : "d"} initial={{ opacity: 0, scale: 0.96, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0 }}
                className={clsx("card overflow-hidden p-0", result.granted ? "border-ok-400/40" : "border-bad-400/40")}>
                <div className={clsx("relative flex items-center gap-5 p-6", result.granted ? "bg-gradient-to-r from-ok-500/25 to-ok-500/5" : "bg-gradient-to-r from-bad-500/25 to-bad-500/5")}>
                  <motion.div initial={{ scale: 0, rotate: -30 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 200, damping: 12 }}
                    className={clsx("grid h-16 w-16 shrink-0 place-items-center rounded-2xl", result.granted ? "bg-ok-400 text-ink-950 shadow-[0_0_40px] shadow-ok-400/50" : "bg-bad-400 text-white shadow-[0_0_40px] shadow-bad-400/50")}>
                    {result.granted ? <ShieldCheck className="h-9 w-9" /> : <ShieldAlert className="h-9 w-9" />}
                  </motion.div>
                  <div>
                    <div className={clsx("text-3xl font-black tracking-tight", result.granted ? "text-ok-400" : "text-bad-400")}>{result.granted ? "ACCESS GRANTED" : "ACCESS DENIED"}</div>
                    <div className="mt-1 text-sm text-slate-700">{result.reason}</div>
                  </div>
                </div>
                <div className="space-y-5 p-6">
                  <div className="flex flex-wrap gap-2">
                    {result.best_similarity != null && <Badge tone={result.granted ? "ok" : "bad"}>Similarity {result.best_similarity.toFixed(3)} / threshold {result.threshold}</Badge>}
                    {result.liveness && <Badge tone={result.liveness.passed ? "ok" : "bad"}>Liveness {result.liveness.passed ? "passed" : "failed"} · {result.liveness.blinks} blink(s)</Badge>}
                    {result.total_seconds != null && <Badge>{result.total_seconds}s server time</Badge>}
                    {!result.granted && attemptsLeft != null && <Badge tone="warn">{result.lock?.locked ? "Locked" : `${attemptsLeft} attempt(s) left`}</Badge>}
                  </div>
                  {secret && (
                    <div className="rounded-xl border border-ok-400/20 bg-slate-50 p-4">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="label text-ok-400">Decrypted {secret.kind}</span>
                        <span className="text-xs text-slate-600">{bytes(secret.size)} · integrity verified (GCM)</span>
                      </div>
                      {secret.kind === "text" ? (
                        <>
                          <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-sm text-slate-800">{secret.text}</pre>
                          <Button variant="ghost" className="mt-3" onClick={() => navigator.clipboard.writeText(secret.text || "")}><Copy className="h-4 w-4" /> Copy</Button>
                        </>
                      ) : (
                        <Button variant="success" onClick={() => downloadBlob(b64ToBlob(secret.data_b64 || "", secret.mime), secret.name)}><Download className="h-4 w-4" /> Download {secret.name}</Button>
                      )}
                    </div>
                  )}
                  {result.liveness && (
                    <div>
                      <div className="label mb-2">Liveness signal (server-side)</div>
                      <LivenessChart r={result} />
                      <p className="text-[11px] text-slate-600">Cyan: eye aspect ratio (dips = blinks). Amber: MediaPipe blink score (peaks = blinks). Violet: nose position (moves with head turns).</p>
                    </div>
                  )}
                  {!result.granted && <Button variant="ghost" onClick={() => { setResult(null); setPhase("idle"); }}><RotateCcw className="h-4 w-4" /> Try again</Button>}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
