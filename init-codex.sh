#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
codex_dir="$project_root/.codex"
global_auth="$HOME/.codex/auth.json"
project_auth="$codex_dir/auth.json"

mkdir -p "$codex_dir"

if [[ -f "$global_auth" ]]; then
    ln -sf "$global_auth" "$project_auth"
    echo "Shared global Codex auth credentials."
else
    echo "Global auth was not found. Run 'codex login' in AgentWorkspaces."
fi

scp usl:~/AgentWorkspaces/codex-controller/.codex/config.toml "$codex_dir/config.toml"
echo "Fetched Codex config from usl."
