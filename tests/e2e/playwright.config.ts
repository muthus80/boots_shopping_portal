import { defineConfig, devices } from '@playwright/test'

const BE_PORT = process.env.BE_PORT || '8000'
const FE_PORT = process.env.FE_PORT || '3000'
const PROJECT_ROOT = process.env.PROJECT_ROOT || '../..'
const PYTHON_BIN = process.env.PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3')

export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 60_000,
  reporter: [
    ['html', { open: 'never', outputFolder: '../../playwright-report' }],
    ['json', { outputFile: '../../playwright-results.json' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.BASE_URL || `http://localhost:${FE_PORT}`,
    // Always record the full session — trace (step-by-step DOM/network
    // replay in the Playwright trace viewer) + video — so every E2E run
    // produces a human-watchable recording captured into the qa_evidence
    // artifact, not just on failure.
    trace: 'on',
    screenshot: 'on',
    video: 'on',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: `${PYTHON_BIN} -m uvicorn app.main:app --port ${BE_PORT} --host 0.0.0.0`,
      // Gate on the TCP port accepting connections, NOT an HTTP health
      // path: the app may mount /health under a version prefix (e.g.
      // /api/v1/health), so a hardcoded health URL is fragile. Port
      // readiness is true as soon as uvicorn binds — robust for any app.
      port: Number(BE_PORT),
      cwd: PROJECT_ROOT,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      // Inherit the full parent env, then override just what we need.
      // Playwright's `env:` block on a webServer is REPLACE-mode, not
      // merge-mode: writing `env: { DATABASE_URL: ... }` strips PATH,
      // interpreter-locator vars, HOME, and every other inherited var,
      // leaving the command with no way to locate its runtime or its
      // dependencies. Spread first, override second.
      env: { ...process.env, DATABASE_URL: process.env.DATABASE_URL || '' },
    },
    {
      command: `npm run dev -- --port ${FE_PORT}`,
      port: Number(FE_PORT),
      cwd: `${PROJECT_ROOT}/frontend`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      // Point the SPA at the ephemeral backend port Playwright
      // chose for THIS run. Without this the bundle falls back
      // to the hardcoded http://localhost:8000 baked into
      // frontend/src/api/client.ts at build time, which under
      // the test runner is empty / a different DB.
      // Same spread-and-override pattern as backend (see comment
      // above): keeps PATH / HOME / npm's cache dir intact so
      // `npm run dev` can find node + resolve its dep graph.
      env: { ...process.env, VITE_API_URL: `http://localhost:${BE_PORT}` },
    },
  ],
})
