#!/usr/bin/env bash
# Instalador de Skill-NoOne (session-report + git-flow).
# Uso:
#   ./install.sh                        CLI + skills de Claude Code
#   ./install.sh --project DIR          + wrappers Copilot/Antigravity/Bob en el repo
#   ./install.sh --claude-hook          + hook SessionEnd automatico de Claude Code
#   ./install.sh --all --project DIR    todo lo anterior
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DST="${HOME}/.local/bin"
CLAUDE_SKILLS="${HOME}/.claude/skills"
PROJECT=""
DO_HOOK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project)    PROJECT="$2"; shift 2 ;;
    --claude-hook) DO_HOOK=1; shift ;;
    --all)        DO_HOOK=1; shift ;;
    *) echo "Opcion desconocida: $1"; exit 1 ;;
  esac
done

mkdir -p "$BIN_DST"

echo "== Skill-NoOne :: instalacion =="
echo "Kit: $KIT"

# ── 1) session-report ──────────────────────────────────────────────────────
SR_SKILL="${CLAUDE_SKILLS}/session-report"
mkdir -p "$SR_SKILL"
cp "$KIT/session-report/bin/report.py" "$SR_SKILL/report.py"
cp "$KIT/session-report/claude-code/SKILL.md" "$SR_SKILL/SKILL.md"

cat > "$BIN_DST/session-report" <<EOF
#!/usr/bin/env bash
exec python3 "$KIT/session-report/bin/report.py" "\$@"
EOF
chmod +x "$BIN_DST/session-report"
echo "[ok] session-report CLI -> $BIN_DST/session-report"
echo "[ok] session-report Claude skill -> $SR_SKILL"

if [ "$DO_HOOK" = "1" ]; then
  python3 - "$HOME/.claude/settings.json" <<'PY'
import json, os, sys
p = sys.argv[1]
data = {}
if os.path.exists(p):
    try: data = json.load(open(p))
    except Exception: data = {}
hooks = data.setdefault("hooks", {})
se = hooks.setdefault("SessionEnd", [])
cmd = "python3 ~/.claude/skills/session-report/report.py --stdin-hook"
exists = any(h.get("command") == cmd for blk in se for h in blk.get("hooks", []))
if not exists:
    se.append({"hooks": [{"type": "command", "command": cmd}]})
    json.dump(data, open(p, "w"), indent=2)
    print("[ok] hook SessionEnd anadido a", p)
else:
    print("[skip] hook SessionEnd ya existia")
PY
fi

# ── 2) git-flow ────────────────────────────────────────────────────────────
GF_SKILL="${CLAUDE_SKILLS}/git-flow"
mkdir -p "$GF_SKILL"
cp "$KIT/git-flow/bin/flow.py" "$GF_SKILL/flow.py"
cp "$KIT/git-flow/claude-code/SKILL.md" "$GF_SKILL/SKILL.md"

cat > "$BIN_DST/flow" <<EOF
#!/usr/bin/env bash
exec python3 "$KIT/git-flow/bin/flow.py" "\$@"
EOF
chmod +x "$BIN_DST/flow"
echo "[ok] git-flow CLI -> $BIN_DST/flow"
echo "[ok] git-flow Claude skill -> $GF_SKILL"

# ── 3) Wrappers por proyecto ────────────────────────────────────────────────
if [ -n "$PROJECT" ]; then
  PROJECT="$(cd "$PROJECT" && pwd)"
  echo "== Proyecto: $PROJECT =="
  cp "$KIT/AGENTS.md" "$PROJECT/AGENTS.md"
  mkdir -p "$PROJECT/.github/prompts"
  cp "$KIT/session-report/github-copilot/session-report.prompt.md" "$PROJECT/.github/prompts/"
  cp "$KIT/git-flow/github-copilot/git-flow.prompt.md"             "$PROJECT/.github/prompts/"
  mkdir -p "$PROJECT/.antigravity"
  cp "$KIT/session-report/antigravity/session-report.md" "$PROJECT/.antigravity/"
  cp "$KIT/git-flow/antigravity/git-flow.md"             "$PROJECT/.antigravity/"
  echo "[ok] AGENTS.md y wrappers instalados en $PROJECT"
  echo "[i ] IBM Bob: usa el AGENTS.md de la raiz del proyecto."
fi

case ":$PATH:" in
  *":$BIN_DST:"*) ;;
  *) echo ""; echo "  IMPORTANTE: anade $BIN_DST a tu PATH:"; echo "  export PATH=\"$BIN_DST:\$PATH\"" ;;
esac

echo ""
echo "== Listo. Prueba: flow status  |  session-report --daily =="
