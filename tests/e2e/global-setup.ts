// tests/e2e/global-setup.ts
import { execSync } from 'child_process'
export default async function globalSetup() {
  const py = process.env.PYTHON_BIN || 'python3'
  try {
    execSync(`${py} tests/fixtures/seed.py`, { cwd: process.env.PROJECT_ROOT || '../..', env: process.env, stdio: 'inherit' })
  } catch (e) {
    console.warn('[global-setup] seed failed (non-fatal):', String(e))
  }
}
