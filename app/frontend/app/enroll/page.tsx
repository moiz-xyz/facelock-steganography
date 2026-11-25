"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, CheckCircle2, RotateCcw, ScanFace, Trash2, UserRound, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { CameraView } from "@/components/CameraView";
import { Alert, Badge, Button, Card, Empty, PageHeader, ProgressRing } from "@/components/ui";
import { api, ApiError, type Profile } from "@/lib/api";
import { useWebcam } from "@/lib/camera";
import { when } from "@/lib/format";

const POSES = [
  "Look straight at the camera",
  "Turn your head slightly left",
  "Turn your head slightly right",
  "Lift your chin a little",
  "Look straight again, relaxed",
];

export default function EnrollPage() {
  const cam = useWebcam();
  const [name, setName] = useState("");
  const [samples, setSamples] = useState<{ blob: Blob; url: string }[]>([]);
  const [count, setCount] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState<Profile | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);

  const load = useCallback(() => api.profiles().then(setProfiles).catch(() => undefined), []);
  useEffect(() => { load(); }, [load]);

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  async function guidedCapture() {
    setError(""); setDone(null); setRunning(true);
    const got: { blob: Blob; url: string }[] = [];
    setSamples([]);
    try {
      for (let i = 0; i < POSES.length; i++) {
        for (let c = 3; c > 0; c--) { setCount(c); await sleep(i === 0 ? 700 : 450); }
        setCount(0);
        const blob = await cam.capture(0.92);
        got.push({ blob, url: URL.createObjectURL(blob) });
        setSamples([...got]);
        await sleep(250);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCount(null); setRunning(false);
    }
  }

  async function save() {
    setBusy(true); setError("");
    try {
      const p = await api.enroll(name, samples.map((s) => s.blob));
      setDone(p); setSamples([]); setName(""); load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally { setBusy(false); }
  }

  const step = Math.min(samples.length, POSES.length - 1);
  return (
    <div>
      <PageHeader icon={<ScanFace className="h-6 w-6" />} title="Enroll Face" subtitle="Capture five guided samples. The server turns them into one averaged face embedding and stores it encrypted on this device; no photo is kept." />
      <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        <Card title="Camera" icon={<Camera className="h-4 w-4" />} action={cam.state === "ready"
          ? <Button variant="ghost" onClick={cam.stop}>Stop camera</Button>
          : <Button variant="outline" onClick={cam.start} loading={cam.state === "starting"}>Start camera</Button>}>
          <CameraView videoRef={cam.videoRef} state={cam.state} error={cam.error} scanning={running}
            overlay={count !== null && (
              <motion.div key={`c${count}-${samples.length}`} initial={{ opacity: 0, scale: 1.4 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 grid place-items-center bg-black/20">
                {count > 0 ? <span className="text-7xl font-bold text-white drop-shadow-lg">{count}</span>
                  : <motion.div initial={{ opacity: 0.9 }} animate={{ opacity: 0 }} transition={{ duration: 0.4 }} className="absolute inset-0 bg-white" />}
              </motion.div>
            )} />
          <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div>
              <div className="label">Step {running ? step + 1 : samples.length >= 5 ? 5 : 1} of 5</div>
              <div className="mt-0.5 text-sm font-medium text-slate-900">{samples.length >= 5 && !running ? "All samples captured" : POSES[step]}</div>
            </div>
            <Button onClick={guidedCapture} disabled={cam.state !== "ready" || running} loading={running}>
              {samples.length ? <><RotateCcw className="h-4 w-4" /> Retake</> : <><Camera className="h-4 w-4" /> Start guided capture</>}
            </Button>
          </div>
        </Card>

        <div className="space-y-6">
          <Card title="Capture progress" icon={<UserRound className="h-4 w-4" />}>
            <div className="flex items-center gap-6">
              <ProgressRing value={samples.length / 5} size={132}>
                <div className="text-center">
                  <div className="font-mono text-3xl font-semibold text-slate-900">{samples.length}<span className="text-slate-600">/5</span></div>
                  <div className="text-[11px] text-slate-600">samples</div>
                </div>
              </ProgressRing>
              <div className="grid flex-1 grid-cols-5 gap-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="aspect-square overflow-hidden rounded-lg border border-slate-200 bg-ink-950">
                    <AnimatePresence>
                      {samples[i] && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <motion.img initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} src={samples[i].url} alt={`sample ${i + 1}`} className="h-full w-full -scale-x-100 object-cover" />
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-5 space-y-3">
              <input className="input" placeholder="Name for this profile (e.g. Ayesha)" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} />
              <Button className="w-full" onClick={save} disabled={samples.length < 5 || !name.trim() || running} loading={busy}>
                <CheckCircle2 className="h-4 w-4" /> Save face profile
              </Button>
              {error && <Alert tone="bad">{error}</Alert>}
              {done && (
                <Alert tone="ok">
                  <b>{done.label}</b> enrolled. Sample consistency {(done.quality.mean_pair_similarity * 100).toFixed(1)}% (min {(done.quality.min_pair_similarity * 100).toFixed(1)}%).
                </Alert>
              )}
            </div>
          </Card>

          <Card title="Enrolled profiles" icon={<Users className="h-4 w-4" />} action={<Badge tone="info">{profiles.length} stored</Badge>}>
            {profiles.length === 0 ? (
              <Empty icon={<Users className="h-8 w-8" />} title="No faces enrolled yet">Enroll at least one face to lock secrets with it.</Empty>
            ) : (
              <ul className="space-y-2">
                {profiles.map((p) => (
                  <motion.li layout key={p.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-brand-400/30 to-violet-500/30 text-sm font-semibold text-slate-900">{p.label[0]?.toUpperCase()}</div>
                      <div>
                        <div className="text-sm font-medium text-slate-900">{p.label}</div>
                        <div className="text-[11px] text-slate-600">{when(p.created_at)} · {p.engine.toUpperCase()} · consistency {(p.quality.mean_pair_similarity * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                    <button aria-label={`Delete ${p.label}`} className="rounded-lg p-2 text-slate-600 transition hover:bg-bad-400/10 hover:text-bad-400"
                      onClick={async () => { if (confirm(`Delete profile ${p.label}? Vaults already created keep working.`)) { await api.deleteProfile(p.id); load(); } }}>
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </motion.li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
