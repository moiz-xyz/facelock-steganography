"use client";
/** Demo Mode: preloads sample images / a password-protected demo pair so a live presentation never stalls. */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface DemoCtx { demo: boolean; setDemo: (v: boolean) => void }
const Ctx = createContext<DemoCtx>({ demo: false, setDemo: () => undefined });

export function DemoProvider({ children }: { children: ReactNode }) {
  const [demo, setDemoState] = useState(false);
  useEffect(() => {
    try { setDemoState(localStorage.getItem("facelock.demo") === "1"); } catch { /* private mode */ }
  }, []);
  const setDemo = (v: boolean) => {
    setDemoState(v);
    try { localStorage.setItem("facelock.demo", v ? "1" : "0"); } catch { /* ignore */ }
  };
  return <Ctx.Provider value={{ demo, setDemo }}>{children}</Ctx.Provider>;
}

export const useDemo = () => useContext(Ctx);

/** Remember recent hide jobs so the Analysis page can open them. */
export interface RecentJob { job_id: string; name: string; ts: number; psnr: number | null }
export function rememberJob(j: RecentJob) {
  try {
    const list: RecentJob[] = JSON.parse(localStorage.getItem("facelock.jobs") || "[]");
    localStorage.setItem("facelock.jobs", JSON.stringify([j, ...list.filter((x) => x.job_id !== j.job_id)].slice(0, 10)));
  } catch { /* ignore */ }
}
export function recentJobs(): RecentJob[] {
  try { return JSON.parse(localStorage.getItem("facelock.jobs") || "[]"); } catch { return []; }
}
