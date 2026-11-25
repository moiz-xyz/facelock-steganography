#!/usr/bin/env node
/**
 * HTTPS front door for LAN demos (the browser allows the camera only on HTTPS or localhost).
 *   node scripts/https_proxy.js            -> https://<lan-ip>:3443
 * /api/* goes to the FastAPI backend (:8000), everything else to Next.js (:3100).
 * Uses a self-signed certificate from scripts/.certs (created by the run step if missing).
 * Env: HTTPS_PORT (3443), FRONT_PORT (3100), API_PORT (8000).
 */
const fs = require("fs");
const http = require("http");
const https = require("https");
const path = require("path");

const CERT_DIR = path.join(__dirname, ".certs");
const PORT = Number(process.env.HTTPS_PORT || 3443);
const FRONT = Number(process.env.FRONT_PORT || 3100);
const API = Number(process.env.API_PORT || 8000);

const server = https.createServer(
  { key: fs.readFileSync(path.join(CERT_DIR, "key.pem")), cert: fs.readFileSync(path.join(CERT_DIR, "cert.pem")) },
  (req, res) => {
    const port = req.url.startsWith("/api") ? API : FRONT;
    const headers = { ...req.headers, "x-forwarded-proto": "https", "x-forwarded-host": req.headers.host || "" };
    const up = http.request({ host: "127.0.0.1", port, path: req.url, method: req.method, headers }, (r) => {
      res.writeHead(r.statusCode || 502, r.headers);
      r.pipe(res);
    });
    up.on("error", (e) => {
      if (!res.headersSent) res.writeHead(502, { "content-type": "text/plain" });
      res.end(`Upstream :${port} unreachable: ${e.message}`);
    });
    req.pipe(up);
  },
);

server.listen(PORT, "0.0.0.0", () => console.log(`HTTPS proxy on https://0.0.0.0:${PORT} -> api :${API}, web :${FRONT}`));
