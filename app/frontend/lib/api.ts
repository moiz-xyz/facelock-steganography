/**
 * Typed client for the FaceLock Stego FastAPI backend.
 * Every security decision is made server-side; this module only moves data.
 */
// Without NEXT_PUBLIC_API_URL: over HTTPS (scripts/https_proxy.js) the API is on the same origin; over plain
// HTTP it is port 8000 on the host the page was opened from (works on the LAN too).
function defaultApiUrl(): string {
  if (typeof window === "undefined") return "http://localhost:8000";
  const { protocol, hostname, origin } = window.location;
  return protocol === "https:" ? origin : `${protocol}//${hostname}:8000`;
}
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || defaultApiUrl()).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status: number, public body?: unknown) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }
  const ct = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof body === "object" && body && "detail" in body ? String((body as { detail: unknown }).detail) : res.statusText;
    throw new ApiError(detail, res.status, body);
  }
  return body as T;
}

const post = <T,>(path: string, form?: FormData) => request<T>(path, { method: "POST", body: form });

// ----------------------------------------------------------------- types
export interface Health {
  status: string; face_engine: string; face_threshold: number; liveness: string; liveness_required: boolean;
  enroll_samples: number; max_authorized_faces: number; max_failures: number; lockout_seconds: number; profiles: number;
}
export interface Profile {
  id: string; label: string; engine: string; created_at: string;
  quality: { samples: number; min_pair_similarity: number; mean_pair_similarity: number; mean_detection_score: number };
}
export interface Metrics {
  psnr: number | null; mse: number; ssim: number; changed_pixels: number; changed_channel_values: number;
  total_pixels: number; max_abs_diff: number;
}
export interface HideResult {
  job_id: string; vault_id: string; width: number; height: number; capacity_bytes: number; embedded_bytes: number;
  usage_pct: number; payload: { kind: "text" | "file"; size: number; name: string }; embed_seconds: number;
  vault_seconds: number; metrics: Metrics; authorized: string[]; password_fallback: boolean; warnings: string[];
  stego_name: string; vault_name: string;
}
export interface Capacity { width: number; height: number; format: string; capacity_bytes: number; has_alpha: boolean }
export interface Challenge { challenge_id: string; type: "blink_twice" | "turn_left" | "turn_right"; instruction: string; ttl: number }
export interface LockStatus { locked: boolean; failures: number; remaining_s: number; max_failures: number }
export interface Liveness {
  passed: boolean; reason: string; challenge: string; blinks: number; turn_peak: number; frames: number; face_frames: number;
  ear_baseline: number; yaw_baseline: number; ear_series: (number | null)[]; yaw_series: (number | null)[]; blink_series?: (number | null)[]; blink_baseline?: number;
}
export interface Secret {
  kind: "text" | "file"; size: number; name: string; mime: string; text?: string; data_b64?: string; extract_seconds: number;
}
export interface UnlockResult {
  granted: boolean; reason: string; secret?: Secret; matched_label?: string; liveness?: Liveness; threshold?: number;
  best_similarity?: number; scores?: { label: string; similarity: number }[]; lock?: LockStatus; total_seconds?: number;
  challenge?: string; consistency_min?: number | null;
}
export interface VaultInfo { vault_id: string; created_at: string; face_slots: number; password_fallback: boolean; lock: LockStatus }
export interface Analysis {
  job_id: string; meta: Partial<HideResult> & { width: number; height: number }; metrics: Metrics;
  per_channel: { channel: string; psnr: number | null; changed: number }[];
  cover: string; stego: string; heatmap: string;
  histogram: { v: number; coverR: number; stegoR: number; coverG: number; stegoG: number; coverB: number; stegoB: number }[];
}
export interface AttackResult {
  fill: number; payload_bytes: number; width: number; height: number;
  series: { pct: number; cover: number; sequential: number; random: number }[];
  summary: Record<"cover" | "sequential" | "random", { mean_p: number; max_p: number; flagged_prefix_pct: number; flagged_any: boolean }>;
  psnr: { sequential: number; random: number };
  lsb_planes: Record<"cover" | "sequential" | "random", string>;
}
export interface LogItem {
  id: number; ts: string; action: string; method: string | null; vault_id: string | null; result: string;
  reason: string | null; score: number | null; matched_label: string | null; client: string | null; photo: string | null;
}
export interface DemoIndex { covers: string[]; pair: { password: string; cover: string; note: string } | null }

// ----------------------------------------------------------------- calls
export const api = {
  health: () => request<Health>("/api/health"),
  profiles: () => request<Profile[]>("/api/profiles"),
  deleteProfile: (id: string) => request(`/api/profiles/${id}`, { method: "DELETE" }),
  enroll(label: string, samples: Blob[]) {
    const f = new FormData();
    f.append("label", label);
    samples.forEach((s, i) => f.append("samples", s, `sample_${i}.jpg`));
    return post<Profile>("/api/enroll", f);
  },
  capacity(cover: Blob) {
    const f = new FormData();
    f.append("cover", cover, (cover as File).name || "cover.png");
    return post<Capacity>("/api/capacity", f);
  },
  hide(p: { cover: Blob; message?: string; file?: File | null; profileIds: string[]; password?: string }) {
    const f = new FormData();
    f.append("cover", p.cover, (p.cover as File).name || "cover.png");
    if (p.file) f.append("secret_file", p.file, p.file.name);
    else if (p.message) f.append("message", p.message);
    f.append("profile_ids", p.profileIds.join(","));
    if (p.password) f.append("password", p.password);
    return post<HideResult>("/api/hide", f);
  },
  jobUrl: (jobId: string, kind: "stego" | "vault" | "cover") => `${API_URL}/api/jobs/${jobId}/${kind}`,
  challenge: () => post<Challenge>("/api/challenge"),
  inspectVault(vault: Blob) {
    const f = new FormData();
    f.append("vault_file", vault, "secret.vault");
    return post<VaultInfo>("/api/vault/inspect", f);
  },
  extractFace(stego: Blob, vault: Blob, challengeId: string, frames: Blob[]) {
    const f = new FormData();
    f.append("stego_image", stego, "stego.png");
    f.append("vault_file", vault, "secret.vault");
    f.append("challenge_id", challengeId);
    frames.forEach((b, i) => f.append("frames", b, `f${i}.jpg`));
    return post<UnlockResult>("/api/extract/face", f);
  },
  extractPassword(stego: Blob, vault: Blob, password: string) {
    const f = new FormData();
    f.append("stego_image", stego, "stego.png");
    f.append("vault_file", vault, "secret.vault");
    f.append("password", password);
    return post<UnlockResult>("/api/extract/password", f);
  },
  analyze: (jobId: string) => request<Analysis>(`/api/analyze/${jobId}`),
  analyzeUpload(cover: Blob, stego: Blob) {
    const f = new FormData();
    f.append("cover", cover, "cover.png");
    f.append("stego_image", stego, "stego.png");
    return post<Analysis>("/api/analyze/upload", f);
  },
  bitplaneUrl: (jobId: string, which: "cover" | "stego", channel: number, bit: number) =>
    `${API_URL}/api/bitplane/${jobId}?which=${which}&channel=${channel}&bit=${bit}`,
  attack(p: { fill: number; cover?: File | null; sample?: string }) {
    const f = new FormData();
    f.append("fill", String(p.fill));
    if (p.cover) f.append("cover", p.cover, p.cover.name);
    else if (p.sample) f.append("sample", p.sample);
    return post<AttackResult>("/api/attack", f);
  },
  logs: () => request<{ items: LogItem[]; stats: Record<string, number> }>("/api/logs"),
  clearLogs: () => request("/api/logs", { method: "DELETE" }),
  logPhotoUrl: (id: number) => `${API_URL}/api/logs/${id}/photo`,
  demo: () => request<DemoIndex>("/api/demo"),
  demoCoverUrl: (name: string) => `${API_URL}/api/demo/covers/${encodeURIComponent(name)}`,
  demoPairUrl: (kind: "stego" | "vault" | "cover") => `${API_URL}/api/demo/pair/${kind}`,
};

export async function fetchAsFile(url: string, name: string, type?: string): Promise<File> {
  const r = await fetch(url);
  if (!r.ok) throw new ApiError(`Could not load ${name}`, r.status);
  const b = await r.blob();
  return new File([b], name, { type: type || b.type });
}
