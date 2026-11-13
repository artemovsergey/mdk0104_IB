#!/usr/bin/env node
// Скриншоты для учебных материалов: вывод команды или страница по URL.
// Коды возврата: 0 — успех, 1 — ошибка запуска, 2 — в выводе найден секрет.

import { spawnSync } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const SECRET_PATTERNS = [
  /ghp_[A-Za-z0-9]{10,}/,
  /github_pat_[A-Za-z0-9_]{10,}/,
  /Bearer\s+[A-Za-z0-9._-]{10,}/i,
  /password\s*=/i,
];

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) continue;
    const name = key.slice(2);
    const value = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : "true";
    args[name] = value;
    if (value !== "true") i += 1;
  }
  return args;
}

function findSecret(text) {
  for (const pattern of SECRET_PATTERNS) {
    const match = text.match(pattern);
    if (match) return match[0].slice(0, 12) + "…";
  }
  return null;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function parseRoutes(text) {
  const routes = [];
  let current = null;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("- ")) {
      if (current) routes.push(current);
      current = {};
      const rest = line.slice(2);
      const [key, ...tail] = rest.split(":");
      current[key.trim()] = tail.join(":").trim();
      continue;
    }
    if (!current) continue;
    const [key, ...tail] = line.split(":");
    current[key.trim()] = tail.join(":").trim();
  }
  if (current) routes.push(current);
  return routes;
}

function commandHtml(title, output) {
  return `<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; background: #0d1117; }
  body { width: 1600px; height: 900px; box-sizing: border-box; padding: 40px 48px; }
  h1 { margin: 0 0 24px; font: 600 32px/1.2 "JetBrains Mono", monospace; color: #8b949e; }
  pre { margin: 0; font: 28px/1.45 "JetBrains Mono", monospace; color: #e6edf3; white-space: pre-wrap; }
</style></head><body><h1>${escapeHtml(title)}</h1><pre>${escapeHtml(output)}</pre></body></html>`;
}

async function ensureBrowser() {
  // Playwright грузится по требованию: проверка секретов работает и без неё.
  const { chromium } = await import("playwright");
  return chromium.launch({ args: ["--no-sandbox"] });
}

async function shootCommand(getBrowser, command, out, size, scale) {
  const [width, height] = size.split("x").map(Number);
  const result = spawnSync("sh", ["-c", command], { encoding: "utf-8", timeout: 60_000 });
  const output = `${result.stdout || ""}${result.stderr || ""}`.trimEnd();
  const secret = findSecret(output);
  if (secret) {
    console.error(`ERROR: в выводе команды найден секрет (${secret}); снимок не сделан`);
    return 2;
  }
  const text = output || `(команда завершилась с кодом ${result.status})`;
  const browser = await getBrowser();
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: scale });
  await page.setContent(commandHtml(command, text), { waitUntil: "load" });
  mkdirSync(dirname(resolve(out)), { recursive: true });
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width, height } });
  await page.close();
  console.log(out);
  return 0;
}

async function shootUrl(getBrowser, url, out, size, scale) {
  const [width, height] = size.split("x").map(Number);
  const browser = await getBrowser();
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: scale });
  await page.goto(url, { waitUntil: "networkidle", timeout: 60_000 });
  await page.addStyleTag({
    content: "*{animation:none!important;transition:none!important;caret-color:transparent!important}",
  });
  mkdirSync(dirname(resolve(out)), { recursive: true });
  await page.screenshot({ path: out });
  await page.close();
  console.log(out);
  return 0;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const size = args.size || "1600x900";
  const scale = Number(args.scale || 2);
  let browser = null;
  const getBrowser = async () => {
    if (!browser) browser = await ensureBrowser();
    return browser;
  };

  try {
    if (args.routes) {
      const routes = parseRoutes(readFileSync(args.routes, "utf-8"));
      const outDir = args["out-dir"] || "dist/shots";
      for (const route of routes) {
        const name = route.name || `shot-${routes.indexOf(route) + 1}`;
        const out = resolve(outDir, `${name}.png`);
        if (route.command) {
          const code = await shootCommand(getBrowser, route.command, out, size, scale);
          if (code !== 0) return code;
        } else if (route.url) {
          await shootUrl(getBrowser, route.url, out, size, scale);
        }
      }
      return 0;
    }
    if (!args.out) {
      console.error("ERROR: нужен --out или --routes");
      return 1;
    }
    if (args.command) {
      return await shootCommand(getBrowser, args.command, args.out, size, scale);
    }
    if (args.url) {
      return await shootUrl(getBrowser, args.url, args.out, size, scale);
    }
    console.error("ERROR: нужен --url, --command или --routes");
    return 1;
  } finally {
    if (browser) await browser.close();
  }
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
  console.error(`ERROR: ${error.message}`);
  process.exit(1);
});
