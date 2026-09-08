import { execSync } from "node:child_process";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Defaults to the host-local backend; docker-compose overrides this to the
// "api" service name since the dev server proxies from inside its container.
const apiTarget = process.env.VITE_API_PROXY_TARGET || "http://localhost:8000";

/**
 * CI passes the deployed SHA in VITE_COMMIT; fall back to the working tree so a
 * locally built bundle still says which commit it is rather than "unknown".
 *
 * Anything already in process.env outranks .env files in Vite, so this has to
 * check the .env files too — assigning the fallback unconditionally would
 * silently shadow a VITE_COMMIT the developer set in .env.local.
 */
function resolveCommit(mode: string): void {
  if (process.env.VITE_COMMIT) return;
  if (loadEnv(mode, process.cwd(), "VITE_").VITE_COMMIT) return;
  const git = (args: string) =>
    execSync(`git ${args}`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  try {
    // Marked dirty for the same reason as the backend: a local bundle built on
    // top of uncommitted edits isn't the commit it would otherwise claim to be.
    const dirty = git("status --porcelain") ? "-dirty" : "";
    process.env.VITE_COMMIT = git("rev-parse HEAD") + dirty;
  } catch {
    // No git available (a source tarball, say) — the UI shows "unknown".
  }
}

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  resolveCommit(mode);
  return {
    // GitHub Pages serves this as a project page at /bgai/, not the domain root;
    // the dev server still needs to run at "/" so the proxy below keeps working.
    base: command === "build" ? "/bgai/" : "/",
    plugins: [react(), tailwindcss()],
    server: {
      host: true,
      // See VITE_USE_POLLING in docker-compose.yml: bind-mounted source across
      // the colima/Docker Desktop VM boundary doesn't deliver native fs events.
      watch: process.env.VITE_USE_POLLING ? { usePolling: true } : undefined,
      proxy: {
        "/game": apiTarget,
        "/engines": apiTarget,
        "/engine": apiTarget,
        "/version": apiTarget,
      },
    },
  };
});
