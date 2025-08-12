#!/usr/bin/env bash
# Upgrade an Expo (RN) app to SDK 53 with robust logging and fallbacks.
# Usage: bash upgrade-to-expo53.sh
# Location: run from your Expo app folder (…/marvin/app)

set -Eeuo pipefail

# ---------- Logging ----------
START_TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="expo53_${START_TS}.log"
exec > >(tee -a "$LOG_FILE") 2>&1

say() { printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m✓ %s\033[0m\n" "$*"; }
warn(){ printf "\033[1;33m! %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m✗ %s\033[0m\n" "$*"; }

# ---------- Sanity checks ----------
say "Starting Expo SDK 53 upgrade (log: $LOG_FILE)"
if [[ ! -f package.json ]]; then
  err "No package.json here. Run this script from your app folder (…/marvin/app)."
  exit 1
fi

NODE_V="$(node -v || true)"
NPM_V="$(npm -v || true)"
say "Node: ${NODE_V:-missing}, npm: ${NPM_V:-missing}"
if [[ -z "${NODE_V}" || -z "${NPM_V}" ]]; then
  err "Node/npm not found. Install Node 18+ (recommended 18/20) and retry."
  exit 1
fi

# Force public npm registry for all commands within this script
export NPM_CONFIG_REGISTRY="https://registry.npmjs.org/"
say "Using public npm registry: $(npm config get registry)"

# ---------- Record initial state ----------
say "Recording initial state…"
INIT_EXPO="$(node -e "try{console.log(require('./package.json').dependencies.expo||'')}catch(e){console.log('')}" || true)"
INIT_RN="$(node -e "try{console.log(require('./package.json').dependencies['react-native']||'')}catch(e){console.log('')}" || true)"
INIT_REACT="$(node -e "try{console.log(require('./package.json').dependencies.react||'')}catch(e){console.log('')}" || true)"
echo "BEFORE -> expo: ${INIT_EXPO}, react-native: ${INIT_RN}, react: ${INIT_REACT}"

# Try to capture Expo diagnostics (best-effort)
say "Collecting Expo diagnostics (best-effort)…"
npx --yes @expo/cli@latest diagnostics || true

# ---------- Git checkpoint (if repo) ----------
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  say "Creating git checkpoint commit…"
  git add -A || true
  git commit -m "chore: checkpoint before Expo SDK 53 upgrade [${START_TS}]" || true
  ok "Checkpoint created (or nothing to commit)."
else
  warn "Not in a git repo; continuing without checkpoint."
fi

# ---------- Backups ----------
say "Backing up key files…"
cp -f package.json "package.json.bak.${START_TS}"
[[ -f package-lock.json ]] && cp -f package-lock.json "package-lock.json.bak.${START_TS}"
[[ -f app.json ]] && cp -f app.json "app.json.bak.${START_TS}"
[[ -f app.config.js ]] && cp -f app.config.js "app.config.js.bak.${START_TS}"
ok "Backups written with timestamp ${START_TS}"

# ---------- Remove deprecated packages ----------
say "Removing deprecated expo-permissions if present…"
npm pkg delete dependencies.expo-permissions 2>/dev/null || true
npm pkg delete devDependencies.expo-permissions 2>/dev/null || true
npm uninstall expo-permissions 2>/dev/null || true
ok "Deprecated package cleanup done."

# ---------- Remove stale config keys ----------
if grep -Riq "runInspectorProxy" .; then
  say "Removing stale 'server.runInspectorProxy' from config…"
  # Mac/BSD sed inline edit
  sed -i '' '/runInspectorProxy/d' app.json 2>/dev/null || true
  sed -i '' '/runInspectorProxy/d' app.config.js 2>/dev/null || true
  ok "Removed stale key if it existed."
else
  ok "No 'runInspectorProxy' key found."
fi

# ---------- Ensure Expo dependency is ~53.0.0 ----------
say "Ensuring package.json depends on expo ~53.0.0…"
node - <<'NODE'
const fs = require('fs');
const path = 'package.json';
const pkg = JSON.parse(fs.readFileSync(path, 'utf8'));
pkg.dependencies = pkg.dependencies || {};
pkg.dependencies['expo'] = '~53.0.0';   // pin to SDK 53
fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + '\n');
console.log('package.json updated: expo -> ~53.0.0');
NODE
ok "expo dependency set to ~53.0.0"

# ---------- Align peer deps with Expo CLI helper ----------
say "Aligning Expo peer dependencies (expo install)…"
npx @expo/cli@latest install || {
  warn "expo install reported issues. Continuing to npm install to resolve lockfile…"
}

# ---------- Install / lock dependencies ----------
say "Installing dependencies (npm install)…"
npm install

# ---------- Clear caches to avoid stale SDK resolution ----------
say "Clearing Metro/Watchman caches (best-effort)…"
watchman watch-del-all 2>/dev/null || true
rm -rf "$TMPDIR/metro-*" 2>/dev/null || true
rm -rf "$TMPDIR/haste-map-*" 2>/dev/null || true
rm -rf .expo .expo-shared 2>/dev/null || true

# ---------- Verify final versions ----------
say "Verifying final versions in package.json…"
FINAL_EXPO="$(node -e "try{console.log(require('./package.json').dependencies.expo||'')}catch(e){console.log('')}" || true)"
FINAL_RN="$(node -e "try{console.log(require('./package.json').dependencies['react-native']||'')}catch(e){console.log('')}" || true)"
FINAL_REACT="$(node -e "try{console.log(require('./package.json').dependencies.react||'')}catch(e){console.log('')}" || true)"
echo "AFTER  -> expo: ${FINAL_EXPO}, react-native: ${FINAL_RN}, react: ${FINAL_REACT}"

say "Running expo doctor…"
npx @expo/cli@latest doctor || warn "expo doctor returned non-zero (check above)."

# ---------- Summary & next steps ----------
say "Upgrade attempt complete."
if [[ "${FINAL_EXPO}" == "~53.0.0" || "${FINAL_EXPO}" == 53* || "${FINAL_EXPO}" == "~53"* ]]; then
  ok "Expo dependency now targets SDK 53."
else
  warn "Expo still not set to SDK 53 (found: ${FINAL_EXPO}). Check the log for errors."
fi

cat <<'EOF'

Next steps:
1) Start your backend (on your Mac):
   uvicorn agent.main:app --host 0.0.0.0 --port 8000 --reload

2) Ensure app/.env points to a URL your phone can reach, e.g.:
   HEROKU_URL=http://<YOUR_MAC_IP>:8000
   API_AUTH_KEY=test-secret

3) Start Expo with a clean cache:
   npx @expo/cli@latest start -c

4) Open with Expo Go (SDK 53). If you still see "project uses SDK 49":
   - Make sure THIS app folder was started.
   - Clear caches again: rm -rf .expo .expo-shared && npx @expo/cli@latest start -c
   - Delete the project from Expo Go recents and rescan the fresh QR.

If things broke, you can restore backups:
   mv package.json.bak.${START_TS} package.json
   [ -f package-lock.json.bak.${START_TS} ] && mv package-lock.json.bak.${START_TS} package-lock.json
   [ -f app.json.bak.${START_TS} ] && mv app.json.bak.${START_TS} app.json
   [ -f app.config.js.bak.${START_TS} ] && mv app.config.js.bak.${START_TS} app.config.js
   npm install
EOF

ok "All done. Full log saved to: $LOG_FILE"
