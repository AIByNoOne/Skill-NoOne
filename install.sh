#!/usr/bin/env bash
# Instalador local de session-report.
# Uso:
#   ./install.sh                  -> CLI global + skill de Claude Code
#   ./install.sh --project DIR    -> ademas instala wrappers de Copilot/Antigravity/Bob en ese repo
#   ./install.sh --claude-hook    -> instala tambien el hook SessionEnd de Claude Code
#   ./install.sh --all --project DIR
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DST="${HOME}/.local/bin"
CLAUDE_SKILL="${HOME}/.claude/skills/session-report"
PROJECT=""
DO_HOOK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --claude-hook) DO_HOOK=1; shift ;;
    --all) DO_HOOK=1; shift ;;
    *) echo "Opcion desconocida: $1"; exit 1 ;;
  esac
done

echo "== session-report :: instalacion =="
echo "Kit: $KIT"

# 1) CLI global -------------------------------------------------------------
mkdir -p "$BIN_DST"
cat > "$BIN_DST/session-report" <<EOF
#!/usr/bin/env bash
exec python3 "$KIT/bin/report.py" "\$@"
EOF
chmod +x "$BIN_DST/session-report"
echo "[ok] CLI -> $BIN_DST/session-report"
case ":$PATH:" in
  *":$BIN_DST:"*) ;;
  *) echo "    (anade $BIN_DST a tu PATH: export PATH=\"$BIN_DST:\$PATH\")" ;;
esac

# 2) Claude Code skill ------------------------------------------------------
mkdir -p "$CLAUDE_SKILL"
cp "$KIT/bin/report.py" "$CLAUDE_SKILL/report.py"
cp "$KIT/claude-code/SKILL.md" "$CLAUDE_SKILL/SKILL.md"
echo "[ok] Claude Code skill -> $CLAUDE_SKILL"

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
exists = any(
    h.get("command") == cmd
    for blk in se for h in blk.get("hooks", [])
)
if not exists:
    se.append({"hooks": [{"type": "command", "command": cmd}]})
    json.dump(data, open(p, "w"), indent=2)
    print("[ok] hook SessionEnd anadido a", p)
else:
    print("[skip] hook SessionEnd ya existia")
PY
fi

# 3) Wrappers por proyecto (Copilot / Antigravity / Bob) --------------------
if [ -n "$PROJECT" ]; then
  PROJECT="$(cd "$PROJECT" && pwd)"
  echo "== Proyecto: $PROJECT =="
  cp "$KIT/AGENTS.md" "$PROJECT/AGENTS.md"
  echo "[ok] AGENTS.md -> $PROJECT/AGENTS.md (Copilot/Antigravity/Bob)"
  mkdir -p "$PROJECT/.github/prompts"
  cp "$KIT/github-copilot/session-report.prompt.md" "$PROJECT/.github/prompts/"
  echo "[ok] Copilot prompt -> $PROJECT/.github/prompts/session-report.prompt.md"
  mkdir -p "$PROJECT/.antigravity"
  cp "$KIT/antigravity/session-report.md" "$PROJECT/.antigravity/"
  echo "[ok] Antigravity -> $PROJECT/.antigravity/session-report.md"
  echo "[i ] IBM Bob: usa el AGENTS.md de la raiz, o copia ibm-bob/session-report.md"
  echo "     a la convencion de tu version de Bob."
fi

echo "== Listo. Prueba:  session-report --daily  =="
