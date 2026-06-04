#!/usr/bin/env python3
"""
memory-agent setup helper — verifica instalacion de engram y estado del MCP.
Uso: python3 setup.py [--check | --install-instructions | --backup]
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
DB_PATH = Path.home() / ".engram" / "engram.db"


def check_binary():
    path = shutil.which("engram")
    if path:
        try:
            result = subprocess.run(["engram", "version"], capture_output=True, text=True, timeout=5)
            version = result.stdout.strip() or result.stderr.strip()
            print(f"[ok] engram binary: {path}")
            print(f"     version: {version}")
            return True
        except Exception as e:
            print(f"[warn] engram encontrado en {path} pero no responde: {e}")
            return False
    print("[error] engram no esta instalado o no esta en el PATH.")
    return False


def check_database():
    if DB_PATH.exists():
        size_kb = DB_PATH.stat().st_size // 1024
        print(f"[ok] base de datos: {DB_PATH} ({size_kb} KB)")
        return True
    print(f"[info] base de datos no encontrada en {DB_PATH}")
    print("       se crea automaticamente al usar engram por primera vez.")
    return False


def check_plugin():
    settings = {}
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH) as f:
            settings = json.load(f)
    if "engram" in settings.get("mcpServers", {}):
        print("[ok] MCP engram configurado en settings.json")
        return True
    print("[warn] plugin engram no detectado en Claude Code.")
    print("       ejecuta: claude plugin marketplace add Gentleman-Programming/engram")
    print("                claude plugin install engram")
    return False


def check_all():
    print("=== memory-agent :: estado de engram ===\n")
    binary_ok = check_binary()
    print()
    db_ok = check_database()
    print()
    plugin_ok = check_plugin()
    print()
    if binary_ok and plugin_ok:
        print("[ok] memory-agent listo para usar.")
    elif not binary_ok:
        print("[action] instalar engram primero (--install-instructions).")
    else:
        print("[action] configurar el plugin en Claude Code.")
    return binary_ok and plugin_ok


def install_instructions():
    print("=== Instrucciones de instalacion ===\n")
    print("1. Instalar el binario engram:")
    print("   macOS:  brew install gentleman-programming/tap/engram")
    print("   otros:  https://github.com/Gentleman-Programming/engram/blob/main/docs/INSTALLATION.md\n")
    print("2. Configurar en tu agente:")
    print("   Claude Code:    claude plugin marketplace add Gentleman-Programming/engram")
    print("                   claude plugin install engram")
    print("   Codex:          engram setup codex")
    print("   Gemini CLI:     engram setup gemini-cli")
    print("   VS Code:        code --add-mcp '{\"name\":\"engram\",\"command\":\"engram\",\"args\":[\"mcp\"]}'")
    print("   Antigravity:    config manual en ~/.gemini/antigravity/mcp_config.json")
    print("   Bob/generico:   config manual MCP stdio\n")
    print("3. Verificar:   python3 setup.py --check")
    print("4. TUI:         engram tui\n")
    print("Repo: https://github.com/Gentleman-Programming/engram")


def backup():
    if not DB_PATH.exists():
        print("[error] no hay base de datos para respaldar.")
        sys.exit(1)
    import shutil as sh
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = DB_PATH.parent / f"engram.db.bak.{ts}"
    sh.copy2(DB_PATH, dst)
    size_kb = dst.stat().st_size // 1024
    print(f"[ok] backup creado: {dst} ({size_kb} KB)")


def main():
    parser = argparse.ArgumentParser(description="memory-agent setup helper")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--install-instructions", action="store_true")
    parser.add_argument("--backup", action="store_true")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check_all() else 1)
    elif args.install_instructions:
        install_instructions()
    elif args.backup:
        backup()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
