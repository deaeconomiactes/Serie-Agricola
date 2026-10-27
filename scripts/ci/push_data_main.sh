#!/usr/bin/env bash
# Rebase onto the current main; retry one push only when main actually advanced.
set -euo pipefail
if [ "${GITHUB_ACTIONS:-false}" = true ] && [ "${GITHUB_REF:-}" != refs/heads/main ]; then
  echo '::error::La publicación productiva requiere refs/heads/main.'
  exit 1
fi

git fetch origin main
for attempt in 1 2; do
  remote_before=$(git rev-parse refs/remotes/origin/main)
  if ! git -c rebase.autoStash=false -c rerere.enabled=false rebase origin/main; then
    if [ -d "$(git rev-parse --git-path rebase-merge)" ] || [ -d "$(git rev-parse --git-path rebase-apply)" ]; then
      if ! git rebase --abort; then
        echo '::error::No se pudo abortar el rebase. Conservar artifacts y revisar manualmente.'
        exit 1
      fi
    fi
    echo '::error::Rebase fallido/conflictivo: abortado sin resolver ni forzar. Conservar artifacts.'
    exit 1
  fi
  if git push origin HEAD:main; then
    echo "[PUBLISH] Push a main exitoso; intento $attempt/2."
    exit 0
  fi
  if [ "$attempt" -eq 2 ]; then
    echo '::error::Push rechazado tras un único retry; no se fuerza la publicación.'
    exit 1
  fi
  git fetch origin main
  remote_after=$(git rev-parse refs/remotes/origin/main)
  if [ "$remote_before" = "$remote_after" ] || ! git merge-base --is-ancestor "$remote_before" "$remote_after"; then
    echo '::error::Push rechazado sin avance compatible de main; no reintentar ni forzar.'
    exit 1
  fi
  echo '[PUBLISH] Main avanzó durante el push; un único retry con rebase.'
done
