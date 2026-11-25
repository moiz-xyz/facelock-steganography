"use client";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { CameraOff, Loader2 } from "lucide-react";
import type { ReactNode, RefObject } from "react";
import type { CamState } from "@/lib/camera";

/** Mirrored webcam preview with a face guide oval and an optional overlay. */
export function CameraView({ videoRef, state, error, overlay, scanning, tone = "brand" }: {
  videoRef: RefObject<HTMLVideoElement>; state: CamState; error?: string; overlay?: ReactNode; scanning?: boolean;
  tone?: "brand" | "ok" | "bad";
}) {
  const ring = { brand: "border-brand-400/70", ok: "border-ok-400", bad: "border-bad-400" }[tone];
  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl border border-slate-200 bg-ink-950">
      <video ref={videoRef} playsInline muted className={clsx("h-full w-full -scale-x-100 object-cover transition", state !== "ready" && "opacity-0")} />
      {state === "ready" && (
        <>
          <div className={clsx("pointer-events-none absolute left-1/2 top-1/2 h-[72%] w-[46%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-2 border-dashed transition", ring)} />
          {scanning && (
            <motion.div className="pointer-events-none absolute inset-x-0 h-24 bg-gradient-to-b from-transparent via-brand-400/25 to-transparent"
              initial={{ top: "-20%" }} animate={{ top: "100%" }} transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }} />
          )}
          {["left-3 top-3 border-l-2 border-t-2", "right-3 top-3 border-r-2 border-t-2", "left-3 bottom-3 border-l-2 border-b-2", "right-3 bottom-3 border-r-2 border-b-2"].map((c) => (
            <span key={c} className={clsx("pointer-events-none absolute h-6 w-6 rounded-sm border-brand-300/80", c)} />
          ))}
        </>
      )}
      {state !== "ready" && (
        <div className="absolute inset-0 grid place-items-center text-sm text-slate-500">
          {state === "starting" ? (
            <div className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Starting camera…</div>
          ) : state === "error" ? (
            <div className="flex max-w-xs flex-col items-center gap-2 text-center text-bad-400"><CameraOff className="h-8 w-8" />{error}</div>
          ) : (
            <div className="flex flex-col items-center gap-2"><CameraOff className="h-8 w-8 text-slate-500" />Camera is off</div>
          )}
        </div>
      )}
      <AnimatePresence>{overlay}</AnimatePresence>
    </div>
  );
}
