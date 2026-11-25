"use client";
import clsx from "clsx";
import { motion } from "framer-motion";
import { Bug, FlaskConical, Info, Play, Radar, Shuffle, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Dropzone } from "@/components/Dropzone";
import { Alert, Badge, Button, Card, PageHeader } from "@/components/ui";
import { api, ApiError, type AttackResult } from "@/lib/api";
import { bytes } from "@/lib/format";

export default function AttackLab() {
  const [samples, setSamples] = useState<string[]>([]);
  const [sample, setSample] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fill, setFill] = useState(0.5);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<AttackResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { api.demo().then((d) => { setSamples(d.covers); setSample(d.covers.find((c) => c.includes("kodim23")) || d.covers[0] || ""); }).catch(() => undefined); }, []);

  async function run() {
    setBusy(true); setError("");
    try { setRes(await api.attack({ fill, cover: file, sample })); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); } finally { setBusy(false); }
  }

  const s = res?.summary;
  return (
    <div>
      <PageHeader icon={<FlaskConical className="h-6 w-6" />} title="Attack Lab" subtitle="Play the attacker. The chi-square steganalysis attack (Westfeld & Pfitzmann) scans the image top-to-bottom and estimates the probability that LSBs were overwritten. Compare naive sequential LSB with FaceLock's keyed random LSB." />

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card title="Experiment" icon={<Radar className="h-4 w-4" />}>
          <div className="label mb-2">Cover image</div>
          <div className="grid grid-cols-4 gap-2">
            {samples.map((c) => (
              <button key={c} onClick={() => { setSample(c); setFile(null); }} className={clsx("overflow-hidden rounded-lg border-2 transition", sample === c && !file ? "border-brand-400" : "border-transparent opacity-70 hover:opacity-100")}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={api.demoCoverUrl(c)} alt={c} className="aspect-square w-full object-cover" />
              </button>
            ))}
          </div>
          <div className="mt-3">
            <Dropzone compact onFile={setFile} accept="image/*" label={file ? file.name : "…or upload your own"} />
          </div>
          <div className="mt-5">
            <div className="flex items-baseline justify-between">
              <span className="label">Payload size</span>
              <span className="font-mono text-sm text-brand-300">{Math.round(fill * 100)}% of capacity</span>
            </div>
            <input type="range" min={0.05} max={1} step={0.05} value={fill} onChange={(e) => setFill(Number(e.target.value))} className="mt-2 w-full" aria-label="payload fill" />
          </div>
          <Button className="mt-5 w-full" onClick={run} loading={busy} disabled={!sample && !file}><Play className="h-4 w-4" /> Run chi-square attack</Button>
          {error && <div className="mt-3"><Alert tone="bad">{error}</Alert></div>}
          <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
            <div className="mb-1 flex items-center gap-1.5 font-semibold text-slate-500"><Info className="h-3.5 w-3.5" /> Reading the chart</div>
            p ≈ 1 means the attacker is confident that the scanned region carries hidden data. Sequential LSB gives itself away exactly where the message sits; random LSB spreads the same bits thinly across the whole image.
          </div>
        </Card>

        <div className="space-y-6">
          {!res ? (
            <Card><div className="grid place-items-center py-24 text-center text-slate-600"><Bug className="mb-3 h-10 w-10" />Pick a cover and run the attack.</div></Card>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-3">
                {([
                  ["cover", "Clean cover", "text-slate-500"],
                  ["sequential", "Sequential LSB", "text-bad-400"],
                  ["random", "FaceLock random LSB", "text-ok-400"],
                ] as const).map(([k, label, c]) => (
                  <motion.div key={k} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
                    <div className="label">{label}</div>
                    <div className={clsx("mt-2 font-mono text-2xl font-semibold", c)}>{s![k].flagged_prefix_pct}%</div>
                    <div className="text-xs text-slate-600">of image flagged (p ≥ 0.95)</div>
                    <div className="mt-2 text-xs text-slate-500">mean p = {s![k].mean_p.toFixed(3)}</div>
                  </motion.div>
                ))}
              </div>
              <Card title="Chi-square attack: embedding probability vs. portion of image scanned" icon={<Radar className="h-4 w-4" />}
                action={<Badge>{res.width}×{res.height} · {bytes(res.payload_bytes)} payload</Badge>}>
                <div className="h-72">
                  <ResponsiveContainer>
                    <LineChart data={res.series} margin={{ left: -10, right: 10 }}>
                      <CartesianGrid stroke="rgba(15,23,42,.08)" />
                      <XAxis dataKey="pct" tick={{ fill: "#64748b", fontSize: 10 }} unit="%" />
                      <YAxis domain={[0, 1]} tick={{ fill: "#64748b", fontSize: 10 }} />
                      <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", color: "#0f172a", borderRadius: 12, fontSize: 12 }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <ReferenceLine x={Math.round(res.fill * 100)} stroke="#fbbf24" strokeDasharray="4 4" label={{ value: "payload end (sequential)", fill: "#fbbf24", fontSize: 10, position: "insideTopRight" }} />
                      <Line type="monotone" dataKey="sequential" name="Sequential LSB" stroke="#fb7185" strokeWidth={2.5} dot={false} animationDuration={500} />
                      <Line type="monotone" dataKey="random" name="FaceLock random LSB" stroke="#34d399" strokeWidth={2.5} dot={false} animationDuration={500} />
                      <Line type="monotone" dataKey="cover" name="Clean cover" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="5 4" dot={false} animationDuration={500} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card title="What the attacker sees in the red-channel LSB plane" icon={<Shuffle className="h-4 w-4" />}>
                <div className="grid gap-4 sm:grid-cols-3">
                  {(["cover", "sequential", "random"] as const).map((k) => (
                    <figure key={k}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={res.lsb_planes[k]} alt={k} className="pixelated w-full rounded-xl border border-slate-200" />
                      <figcaption className="mt-2 text-center text-xs capitalize text-slate-500">{k === "random" ? "FaceLock (random)" : k}</figcaption>
                    </figure>
                  ))}
                </div>
                <p className="mt-3 text-xs text-slate-600">
                  {res.fill >= 0.9
                    ? "At ~100% capacity every LSB is overwritten, so any LSB-replacement scheme becomes detectable. Keep payloads small."
                    : "Sequential embedding leaves a visible noisy band at the top. Random embedding has no boundary to find."}
                </p>
              </Card>
              <Alert tone="info">Honest note: random positions hide <i>where</i> the data is, which defeats this sequential chi-square scan at low/medium payloads. Stronger detectors (RS analysis, SPA, machine-learning steganalysis) can still estimate the payload of any LSB-replacement scheme.</Alert>
            </>
          )}
        </div>
      </div>
      {!samples.length && <div className="mt-6"><Alert tone="warn"><Upload className="mr-1 inline h-4 w-4" /> No demo samples found. Run <code>scripts/make_demo_assets.py</code> or upload an image.</Alert></div>}
    </div>
  );
}
