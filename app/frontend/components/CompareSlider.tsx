"use client";
import { MoveHorizontal } from "lucide-react";
import { useRef, useState } from "react";

/** Before/after image comparison with a draggable divider. */
export function CompareSlider({ before, after, labels = ["Original", "Stego"] }: { before: string; after: string; labels?: [string, string] }) {
  const [pos, setPos] = useState(50);
  const box = useRef<HTMLDivElement>(null);
  const move = (clientX: number) => {
    const r = box.current?.getBoundingClientRect();
    if (r) setPos(Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100)));
  };
  return (
    <div
      ref={box}
      className="relative w-full cursor-ew-resize select-none overflow-hidden rounded-xl border border-slate-200"
      onPointerDown={(e) => { (e.target as HTMLElement).setPointerCapture(e.pointerId); move(e.clientX); }}
      onPointerMove={(e) => e.buttons === 1 && move(e.clientX)}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={after} alt={labels[1]} className="block w-full" draggable={false} />
      <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={before} alt={labels[0]} className="block w-full" draggable={false} />
      </div>
      <div className="absolute inset-y-0 w-0.5 bg-white/90 shadow-[0_0_12px_rgba(255,255,255,.6)]" style={{ left: `${pos}%` }}>
        <div className="absolute left-1/2 top-1/2 grid h-9 w-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-white text-slate-900 shadow-lg ring-1 ring-slate-300">
          <MoveHorizontal className="h-4 w-4" />
        </div>
      </div>
      <span className="absolute left-3 top-3 rounded-md bg-black/60 px-2 py-1 text-xs font-medium text-white">{labels[0]}</span>
      <span className="absolute right-3 top-3 rounded-md bg-black/60 px-2 py-1 text-xs font-medium text-white">{labels[1]}</span>
    </div>
  );
}
