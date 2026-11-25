"use client";
import clsx from "clsx";
import { Activity, BarChart3, Flame, Gauge, ImageIcon, Layers, Loader2, Microscope, Upload } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CompareSlider } from "@/components/CompareSlider";
import { Dropzone } from "@/components/Dropzone";
import { Alert, Badge, Button, Card, Empty, PageHeader, Stat, Tabs } from "@/components/ui";
import { api, ApiError, fetchAsFile, type Analysis } from "@/lib/api";
import { recentJobs, rememberJob, useDemo, type RecentJob } from "@/lib/demo";
import { db } from "@/lib/format";

const tip = { contentStyle: { background: "#ffffff", border: "1px solid #e2e8f0", color: "#0f172a", borderRadius: 12, fontSize: 12 } };

function BitPlanes({ jobId }: { jobId: string }) {
  const [ch, setCh] = useState(0);
  const [bit, setBit] = useState(0);
  return (
    <Card title="LSB bit-plane viewer" icon={<Layers className="h-4 w-4" />}
      action={<Tabs value={String(ch)} onChange={(v) => setCh(Number(v))} items={[{ value: "0", label: "R" }, { value: "1", label: "G" }, { value: "2", label: "B" }]} />}>
      <div className="mb-4 flex items-center gap-4">
        <span className="label w-16">Bit {bit}</span>
        <input type="range" min={0} max={7} value={bit} onChange={(e) => setBit(Number(e.target.value))} className="flex-1" aria-label="bit plane" />
        <span className="font-mono text-xs text-slate-600">{bit === 0 ? "LSB (carries data)" : bit === 7 ? "MSB" : ""}</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {(["cover", "stego"] as const).map((w) => (
          <figure key={w}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={api.bitplaneUrl(jobId, w, ch, bit)} alt={`${w} bit plane`} className="pixelated w-full rounded-xl border border-slate-200" />
            <figcaption className="mt-2 text-center text-xs text-slate-500">{w === "cover" ? "Original" : "Stego"} · {"RGB"[ch]} channel · bit {bit}</figcaption>
          </figure>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-600">Higher bit planes are identical: only bit 0 is ever modified. Random embedding makes the stego LSB plane look like noise, with no visible block of data.</p>
    </Card>
  );
}

function AnalysisView() {
  const params = useSearchParams();
  const { demo } = useDemo();
  const [jobId, setJobId] = useState<string>(params.get("job") || "");
  const [data, setData] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<RecentJob[]>([]);
  const [hCh, setHCh] = useState<"R" | "G" | "B">("R");
  const [upCover, setUpCover] = useState<File | null>(null);
  const [upStego, setUpStego] = useState<File | null>(null);

  useEffect(() => { setRecent(recentJobs()); if (!jobId) { const r = recentJobs()[0]; if (r) setJobId(r.job_id); } }, [jobId]);

  const load = useCallback(async (id: string) => {
    if (!id) return;
    setLoading(true); setError("");
    try { setData(await api.analyze(id)); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); setData(null); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(jobId); }, [jobId, load]);

  async function uploadPair(c: File, s: File) {
    setLoading(true); setError("");
    try {
      const a = await api.analyzeUpload(c, s);
      rememberJob({ job_id: a.job_id, name: `${c.name} vs ${s.name}`, ts: Date.now(), psnr: a.metrics.psnr });
      setJobId(a.job_id); setData(a); setRecent(recentJobs());
    } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); } finally { setLoading(false); }
  }

  async function demoPair() {
    const [c, s] = await Promise.all([fetchAsFile(api.demoPairUrl("cover"), "demo_cover.png"), fetchAsFile(api.demoPairUrl("stego"), "demo_stego.png")]);
    uploadPair(c, s);
  }

  const m = data?.metrics;
  const hist = data?.histogram.map((h) => ({ v: h.v, cover: h[`cover${hCh}`], stego: h[`stego${hCh}`] }));
  const color = { R: "#fb7185", G: "#34d399", B: "#60a5fa" }[hCh];

  return (
    <div>
      <PageHeader icon={<Activity className="h-6 w-6" />} title="Analysis Dashboard" subtitle="Measure how invisible the embedding is: PSNR, MSE and SSIM, a pixel-difference heatmap, the LSB bit planes and the colour histograms."
        right={
          <div className="flex flex-wrap items-center gap-2">
            {recent.length > 0 && (
              <select className="input w-auto py-2" value={jobId} onChange={(e) => setJobId(e.target.value)} aria-label="Recent jobs">
                {recent.map((r) => <option key={r.job_id} value={r.job_id}>{r.name.slice(0, 32)} · {r.psnr ? r.psnr.toFixed(1) + " dB" : ""}</option>)}
              </select>
            )}
            {demo && <Button variant="outline" onClick={demoPair}>Analyse demo pair</Button>}
          </div>
        } />

      {!data && !loading && (
        <Card title="Compare any cover / stego pair" icon={<Upload className="h-4 w-4" />}>
          <div className="grid gap-4 md:grid-cols-2">
            <Dropzone compact onFile={setUpCover} accept="image/*" label={upCover ? upCover.name : "Original cover image"} />
            <Dropzone compact onFile={setUpStego} accept="image/png" label={upStego ? upStego.name : "Stego image (.png)"} />
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button disabled={!upCover || !upStego} onClick={() => upCover && upStego && uploadPair(upCover, upStego)}><Microscope className="h-4 w-4" /> Analyse</Button>
            <span className="text-xs text-slate-600">Or hide a secret first: results open here automatically.</span>
          </div>
          {error && <div className="mt-4"><Alert tone="bad">{error}</Alert></div>}
        </Card>
      )}
      {loading && <div className="flex items-center justify-center gap-2 py-24 text-slate-500"><Loader2 className="h-5 w-5 animate-spin" /> Analysing…</div>}

      {data && m && !loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="PSNR" value={db(m.psnr)} hint="> 40 dB is imperceptible" tone="ok" icon={<Gauge className="h-4 w-4" />} />
            <Stat label="MSE" value={m.mse.toFixed(5)} hint="mean squared error" tone="brand" icon={<BarChart3 className="h-4 w-4" />} />
            <Stat label="SSIM" value={m.ssim.toFixed(5)} hint="1.0 = structurally identical" tone="violet" icon={<Layers className="h-4 w-4" />} />
            <Stat label="Pixels touched" value={`${((m.changed_pixels / m.total_pixels) * 100).toFixed(2)}%`} hint={`${m.changed_pixels.toLocaleString()} px · max ±${m.max_abs_diff}`} tone="warn" icon={<Flame className="h-4 w-4" />} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Original vs stego (drag the slider)" icon={<ImageIcon className="h-4 w-4" />} action={<Badge>{data.meta.width} × {data.meta.height}</Badge>}>
              <CompareSlider before={data.cover} after={data.stego} />
              <p className="mt-3 text-xs text-slate-600">The two images are visually indistinguishable: every channel value differs by at most 1.</p>
            </Card>
            <Card title="Difference heatmap (changed LSBs per pixel)" icon={<Flame className="h-4 w-4" />}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={data.heatmap} alt="difference heatmap" className="pixelated w-full rounded-xl border border-slate-200" />
              <div className="mt-3 flex items-center gap-3 text-xs text-slate-500">
                <span>0</span>
                <div className="h-2 flex-1 rounded-full" style={{ background: "linear-gradient(90deg,#000004,#781c6d,#ed6925,#fcffa4)" }} />
                <span>3 channels changed</span>
              </div>
              <p className="mt-2 text-xs text-slate-600">Changed pixels are drawn 3×3 so they are visible; the background is the dimmed cover. No region is concentrated: the key spreads bits uniformly.</p>
            </Card>
          </div>

          <BitPlanes jobId={data.job_id} />

          <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
            <Card title="Colour histogram" icon={<BarChart3 className="h-4 w-4" />} action={<Tabs value={hCh} onChange={setHCh} items={[{ value: "R", label: "R" }, { value: "G", label: "G" }, { value: "B", label: "B" }]} />}>
              <div className="h-64">
                <ResponsiveContainer>
                  <AreaChart data={hist} margin={{ left: -10, right: 8 }}>
                    <CartesianGrid stroke="rgba(15,23,42,.08)" />
                    <XAxis dataKey="v" tick={{ fill: "#64748b", fontSize: 10 }} interval={31} />
                    <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                    <Tooltip {...tip} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Area type="step" dataKey="cover" name="Original" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.15} animationDuration={500} />
                    <Area type="step" dataKey="stego" name="Stego" stroke={color} fill={color} fillOpacity={0.25} animationDuration={500} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="Per-channel impact" icon={<Activity className="h-4 w-4" />}>
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={data.per_channel} margin={{ left: -10 }}>
                    <CartesianGrid stroke="rgba(15,23,42,.08)" />
                    <XAxis dataKey="channel" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                    <Tooltip {...tip} />
                    <Bar dataKey="changed" name="Values changed" radius={[6, 6, 0, 0]} fill="#38d4ef" animationDuration={500} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-center text-xs">
                {data.per_channel.map((c) => <div key={c.channel} className={clsx("rounded-lg bg-slate-50 py-2")}><div className="text-slate-600">{c.channel}</div><div className="font-mono text-slate-700">{db(c.psnr)}</div></div>)}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AnalysisPage() {
  return <Suspense fallback={null}><AnalysisView /></Suspense>;
}
