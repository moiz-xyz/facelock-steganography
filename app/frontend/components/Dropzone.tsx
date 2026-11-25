"use client";
import clsx from "clsx";
import { motion } from "framer-motion";
import { UploadCloud } from "lucide-react";
import { useRef, useState, type ReactNode } from "react";

/** Drag-and-drop file picker with keyboard/click fallback. */
export function Dropzone({ onFile, accept, label, hint, children, compact }: {
  onFile: (f: File) => void; accept?: string; label: string; hint?: string; children?: ReactNode; compact?: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <motion.div
      whileHover={{ scale: 1.005 }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      onClick={() => input.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
      className={clsx(
        "group relative flex cursor-pointer flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed text-center transition",
        compact ? "px-4 py-6" : "px-6 py-10",
        over ? "border-brand-400 bg-brand-400/10" : "border-slate-200 bg-slate-50 hover:border-brand-400/50 hover:bg-slate-100",
      )}
    >
      <input ref={input} type="file" accept={accept} className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
      {children ?? (
        <>
          <div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-400/10 text-brand-300 transition group-hover:scale-110">
            <UploadCloud className="h-6 w-6" />
          </div>
          <div className="text-sm font-medium text-slate-700">{label}</div>
          {hint && <div className="mt-1 text-xs text-slate-600">{hint}</div>}
        </>
      )}
    </motion.div>
  );
}
