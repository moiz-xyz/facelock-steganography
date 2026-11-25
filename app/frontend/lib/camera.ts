"use client";
/**
 * Webcam helpers. Frames are captured UN-MIRRORED (exactly what the camera sees),
 * because the server's head-turn check assumes raw camera geometry. Only the
 * on-screen <video> preview is mirrored with CSS so it feels like a mirror.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export type CamState = "idle" | "starting" | "ready" | "error";

export function useWebcam() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CamState>("idle");
  const [error, setError] = useState<string>("");

  const start = useCallback(async () => {
    if (streamRef.current) return;
    setState("starting");
    setError("");
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("This browser does not support camera access (use http://localhost or HTTPS).");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }
      setState("ready");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg.includes("Permission") || msg.includes("NotAllowed") ? "Camera permission was denied." : msg);
      setState("error");
    }
  }, []);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setState("idle");
  }, []);

  useEffect(() => stop, [stop]);

  /** Grab one JPEG frame (un-mirrored). */
  const capture = useCallback(async (quality = 0.85): Promise<Blob> => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) throw new Error("Camera is not ready");
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext("2d")!.drawImage(v, 0, 0);
    return new Promise((resolve, reject) =>
      c.toBlob((b) => (b ? resolve(b) : reject(new Error("capture failed"))), "image/jpeg", quality),
    );
  }, []);

  /** Record a burst of frames at a fixed rate; onTick reports progress 0..1. */
  const burst = useCallback(
    async (seconds: number, fps: number, onTick?: (p: number) => void): Promise<Blob[]> => {
      const n = Math.round(seconds * fps);
      const frames: Blob[] = [];
      const t0 = performance.now();
      for (let i = 0; i < n; i++) {
        const due = t0 + (i * 1000) / fps;
        const wait = due - performance.now();
        if (wait > 0) await new Promise((r) => setTimeout(r, wait));
        frames.push(await capture(0.8));
        onTick?.((i + 1) / n);
      }
      return frames;
    },
    [capture],
  );

  return { videoRef, state, error, start, stop, capture, burst };
}
