export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(n < 10240 ? 2 : 1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export function db(v: number | null | undefined): string {
  return v == null ? "∞" : `${v.toFixed(2)} dB`;
}

export function when(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** Rough capacity estimate for the live meter (mirrors backend constants). */
export const HEADER_BYTES = 38 + 16; // stego header + GCM tag
export function packedSize(dataLen: number, name = "", mime = "text/plain; charset=utf-8"): number {
  return 4 + new TextEncoder().encode(name).length + 1 + mime.length + 4 + dataLen;
}
export function capacityOf(w: number, h: number): number {
  return Math.max(0, Math.floor((w * h * 3) / 8) - HEADER_BYTES);
}

export function downloadBlob(data: Blob, name: string) {
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function b64ToBlob(b64: string, mime: string): Blob {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: mime });
}
