#!/usr/bin/env bash
# Publish only the lightweight operational report, preserving concurrent writers.
set -euo pipefail
if [ "${GITHUB_ACTIONS:-false}" = true ] && [ "${GITHUB_REF:-}" != refs/heads/main ]; then
  echo 'changed=false' >> "$GITHUB_OUTPUT"
  echo 'deploy_required=false' >> "$GITHUB_OUTPUT"
  exit 0
fi
file=data/magyp/reports/PRICE_FRESHNESS_STATUS.json
if ! git diff --cached --quiet; then echo 'Unexpected staged files before freshness publication'; exit 1; fi
python -c 'import json; from scripts.magyp.build_price_freshness import validate_report; validate_report(json.load(open("data/magyp/reports/PRICE_FRESHNESS_STATUS.json",encoding="utf-8")))'
git add -- "$file" data/magyp/dashboard/mcba/MCBA_MAGYP_UPDATE_STATUS.json
if git diff --cached --quiet; then
  echo 'changed=false' >> "$GITHUB_OUTPUT"
  echo 'deploy_required=false' >> "$GITHUB_OUTPUT"
  exit 0
fi
git diff --cached --check
python scripts/ci/workflow_status.py plan
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git commit -m 'chore: actualizar estado de fuentes de precios'
header=$(python -c 'import base64,os; print(base64.b64encode(("x-access-token:"+os.environ["GH_TOKEN"]).encode()).decode())')
echo "::add-mask::$header"
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=core.autocrlf
export GIT_CONFIG_VALUE_0=false
export GIT_CONFIG_KEY_1=http.https://github.com/.extraheader
export GIT_CONFIG_VALUE_1="AUTHORIZATION: basic $header"
trap 'unset GH_TOKEN GIT_CONFIG_VALUE_1 header' EXIT
bash scripts/ci/push_data_main.sh
echo 'changed=true' >> "$GITHUB_OUTPUT"
