#!/usr/bin/env python3
"""
flow — Gitflow local seguro con Conventional Commits estricto.

Uso:
  flow init
  flow status
  flow feature start <nombre> | flow feature finish
  flow release start <X.Y.Z>  | flow release finish
  flow hotfix  start <X.Y.Z>  | flow hotfix  finish
  flow commit  [-m "tipo(scope): asunto"]
  flow save    [-m "mensaje wip"]
  flow undo
  flow discard <archivo|all>  [--yes]
  flow backup
  flow restore
  flow log
"""
import sys, os, re, subprocess, json
from datetime import datetime, timezone

# ────────────────────────────────────────────── helpers git

def git(*args, check=True, capture=True):
    r = subprocess.run(["git"] + list(args),
                       capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise FlowError((r.stderr or r.stdout).strip())
    return r.stdout.strip() if capture else None

def git_ok(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True)
    return r.returncode == 0

def current_branch():
    return git("rev-parse", "--abbrev-ref", "HEAD")

def branch_exists(name):
    return git_ok("show-ref", "--verify", "--quiet", f"refs/heads/{name}")

def is_repo():
    return git_ok("rev-parse", "--is-inside-work-tree")

def is_clean():
    return git("status", "--porcelain") == ""

def require_repo():
    if not is_repo():
        raise FlowError("No es un repositorio git. Corre 'flow init' primero.")

def require_clean(msg="Tienes cambios sin guardar. Usa 'flow save' o 'flow commit' antes."):
    if not is_clean():
        raise FlowError(msg)

def tag_exists(name):
    return git_ok("rev-parse", "--verify", f"refs/tags/{name}")

def now_tag():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

# ────────────────────────────────────────────── Conventional Commits

TYPES = {"feat","fix","chore","docs","refactor","test","perf","build","ci","style","revert"}
CC_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s(?P<desc>.+)$")

def validate_cc(msg):
    """Devuelve (ok, error_str)."""
    first = msg.strip().splitlines()[0] if msg.strip() else ""
    m = CC_RE.match(first)
    if not m:
        return False, (
            "Formato invalido. Debe ser: tipo(scope): asunto en minusculas\n"
            f"  Tipos validos: {', '.join(sorted(TYPES))}\n"
            f"  Ejemplo:  feat(auth): agrega login con email\n"
            f"  Recibido: {first!r}"
        )
    if m.group("type") not in TYPES:
        return False, (
            f"Tipo '{m.group('type')}' no reconocido.\n"
            f"  Tipos validos: {', '.join(sorted(TYPES))}"
        )
    return True, ""

# ────────────────────────────────────────────── backups

def create_backup(label="backup"):
    tag = f"flow-backup/{label}-{now_tag()}"
    git("tag", tag)
    return tag

# ────────────────────────────────────────────── error

class FlowError(Exception):
    pass

# ────────────────────────────────────────────── comandos

def cmd_init(args):
    cwd = os.getcwd()
    fresh = not is_repo()
    if fresh:
        git("init", capture=False, check=False)
        print("[flow] Repositorio git inicializado.")

    # asegurar main
    if not branch_exists("main"):
        if git("log", "--oneline", "-1", check=False) == "":
            # repo vacio: necesita un commit inicial
            readme = os.path.join(cwd, "README.md")
            if not os.path.exists(readme):
                with open(readme, "w") as f:
                    f.write("# Proyecto\n")
                git("add", "README.md")
            git("commit", "-m", "chore: commit inicial")
        git("branch", "-M", "main", check=False)
        print("[flow] Rama 'main' lista.")
    else:
        git("checkout", "main")

    # asegurar develop
    if not branch_exists("develop"):
        git("checkout", "-b", "develop")
        print("[flow] Rama 'develop' creada desde main.")
    else:
        print("[flow] Rama 'develop' ya existe.")

    # guardar config Gitflow
    git("config", "flow.initialized", "true")
    git("config", "flow.main", "main")
    git("config", "flow.develop", "develop")

    print("\n[flow] Gitflow inicializado.")
    print("  main    → produccion / tags de release")
    print("  develop → integracion continua")
    print("\n  Siguientes pasos:")
    print("    flow feature start <nombre>")
    print("    flow status")


def cmd_status(args):
    require_repo()
    branch = current_branch()
    clean = is_clean()

    # determinar rol de la rama
    if branch == "main":
        role = "produccion"
        next_step = "flow hotfix start <X.Y.Z>  o  espera un release"
    elif branch == "develop":
        role = "integracion"
        next_step = "flow feature start <nombre>  o  flow release start <X.Y.Z>"
    elif branch.startswith("feature/"):
        role = f"feature → develop"
        next_step = "flow commit -m '...'  |  flow feature finish"
    elif branch.startswith("release/"):
        role = f"release → main + develop"
        next_step = "flow commit -m '...'  |  flow release finish"
    elif branch.startswith("hotfix/"):
        role = f"hotfix → main + develop"
        next_step = "flow commit -m '...'  |  flow hotfix finish"
    else:
        role = "rama personalizada"
        next_step = "flow commit -m '...'"

    # diff summary
    staged = git("diff", "--cached", "--stat", check=False) or ""
    unstaged = git("diff", "--stat", check=False) or ""
    last = git("log", "--oneline", "-3", check=False) or "(sin commits)"

    print(f"\nRama : {branch}  [{role}]")
    print(f"Estado: {'limpio' if clean else 'cambios pendientes'}")
    if not clean:
        if staged.strip():
            n = len([l for l in staged.strip().splitlines() if "|" in l])
            print(f"  Preparados  : {n} archivo(s)")
        if unstaged.strip():
            n = len([l for l in unstaged.strip().splitlines() if "|" in l])
            print(f"  Sin preparar: {n} archivo(s)")
    print(f"\nUltimos commits:")
    for l in last.splitlines():
        print(f"  {l}")
    print(f"\nSiguiente: {next_step}")
    print()


def cmd_feature(args):
    require_repo()
    if not args:
        raise FlowError("Uso: flow feature start <nombre>  |  flow feature finish")
    sub = args[0]
    if sub == "start":
        if len(args) < 2:
            raise FlowError("Uso: flow feature start <nombre>")
        name = args[1]
        branch = f"feature/{name}"
        if branch_exists(branch):
            raise FlowError(f"La rama '{branch}' ya existe.")
        _stash_if_dirty("feature start")
        git("checkout", "develop")
        git("checkout", "-b", branch)
        print(f"[flow] Rama '{branch}' creada desde develop.")
        print(f"  Cuando termines: flow feature finish")
    elif sub == "finish":
        branch = current_branch()
        if not branch.startswith("feature/"):
            raise FlowError(f"No estas en una rama feature (estas en '{branch}').")
        require_clean()
        backup = create_backup(branch.replace("/", "-"))
        print(f"[flow] Backup: {backup}")
        git("checkout", "develop")
        git("merge", "--no-ff", branch, "-m", f"feat: merge {branch} into develop")
        git("branch", "-d", branch)
        print(f"[flow] '{branch}' mergeada a develop y eliminada.")
    else:
        raise FlowError(f"Subcomando desconocido: '{sub}'. Usa 'start' o 'finish'.")


def cmd_release(args):
    require_repo()
    if not args:
        raise FlowError("Uso: flow release start <X.Y.Z>  |  flow release finish")
    sub = args[0]
    if sub == "start":
        if len(args) < 2:
            raise FlowError("Uso: flow release start <X.Y.Z>")
        ver = args[1]
        _validate_semver(ver)
        branch = f"release/{ver}"
        if branch_exists(branch):
            raise FlowError(f"La rama '{branch}' ya existe.")
        _stash_if_dirty("release start")
        git("checkout", "develop")
        git("checkout", "-b", branch)
        _bump_version(ver)
        print(f"[flow] Rama '{branch}' creada desde develop.")
        print(f"  Haz los ajustes finales y luego: flow release finish")
    elif sub == "finish":
        branch = current_branch()
        if not branch.startswith("release/"):
            raise FlowError(f"No estas en una rama release (estas en '{branch}').")
        ver = branch.split("/", 1)[1]
        require_clean()
        backup = create_backup(branch.replace("/", "-"))
        print(f"[flow] Backup: {backup}")
        tag = f"v{ver}"
        if tag_exists(tag):
            raise FlowError(f"El tag '{tag}' ya existe.")
        # merge a main
        git("checkout", "main")
        git("merge", "--no-ff", branch, "-m", f"chore(release): merge {branch} into main")
        git("tag", "-a", tag, "-m", f"Release {tag}")
        # merge a develop
        git("checkout", "develop")
        git("merge", "--no-ff", branch, "-m", f"chore(release): merge {branch} into develop")
        git("branch", "-d", branch)
        print(f"[flow] Release {tag}: mergeada a main + develop, tag creado, rama eliminada.")
    else:
        raise FlowError(f"Subcomando desconocido: '{sub}'.")


def cmd_hotfix(args):
    require_repo()
    if not args:
        raise FlowError("Uso: flow hotfix start <X.Y.Z>  |  flow hotfix finish")
    sub = args[0]
    if sub == "start":
        if len(args) < 2:
            raise FlowError("Uso: flow hotfix start <X.Y.Z>")
        ver = args[1]
        _validate_semver(ver)
        branch = f"hotfix/{ver}"
        if branch_exists(branch):
            raise FlowError(f"La rama '{branch}' ya existe.")
        _stash_if_dirty("hotfix start")
        git("checkout", "main")
        git("checkout", "-b", branch)
        _bump_version(ver)
        print(f"[flow] Rama '{branch}' creada desde main.")
        print(f"  Aplica el parche y luego: flow hotfix finish")
    elif sub == "finish":
        branch = current_branch()
        if not branch.startswith("hotfix/"):
            raise FlowError(f"No estas en una rama hotfix (estas en '{branch}').")
        ver = branch.split("/", 1)[1]
        require_clean()
        backup = create_backup(branch.replace("/", "-"))
        print(f"[flow] Backup: {backup}")
        tag = f"v{ver}"
        if tag_exists(tag):
            raise FlowError(f"El tag '{tag}' ya existe.")
        git("checkout", "main")
        git("merge", "--no-ff", branch, "-m", f"fix(hotfix): merge {branch} into main")
        git("tag", "-a", tag, "-m", f"Hotfix {tag}")
        git("checkout", "develop")
        git("merge", "--no-ff", branch, "-m", f"fix(hotfix): merge {branch} into develop")
        git("branch", "-d", branch)
        print(f"[flow] Hotfix {tag}: mergeado a main + develop, tag creado, rama eliminada.")
    else:
        raise FlowError(f"Subcomando desconocido: '{sub}'.")


def cmd_commit(args):
    require_repo()
    msg = _extract_m(args)
    if not msg:
        # modo interactivo: pedir mensaje
        print("Mensaje de commit (formato: tipo(scope): asunto):")
        print(f"  Tipos: {', '.join(sorted(TYPES))}")
        try:
            msg = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            raise FlowError("Commit cancelado.")
    ok, err = validate_cc(msg)
    if not ok:
        raise FlowError(f"Commit rechazado — Conventional Commits:\n  {err}")
    # agregar todo lo que este sin stagear (opcional: solo lo staged si ya hay algo)
    staged = git("diff", "--cached", "--name-only", check=False)
    if not staged:
        git("add", "-A")
    result = subprocess.run(["git", "commit", "-m", msg],
                            capture_output=False, text=True)
    if result.returncode != 0:
        raise FlowError("Commit fallido.")


def cmd_save(args):
    require_repo()
    msg = _extract_m(args) or "wip: checkpoint"
    git("add", "-A")
    result = subprocess.run(["git", "commit", "-m", msg],
                            capture_output=False, text=True)
    if result.returncode != 0:
        raise FlowError("Save fallido (puede que no haya cambios).")


def cmd_undo(args):
    require_repo()
    last = git("log", "--oneline", "-1", check=False)
    if not last:
        raise FlowError("No hay commits que deshacer.")
    backup = create_backup("pre-undo")
    print(f"[flow] Backup creado: {backup}")
    print(f"[flow] Deshaciendo: {last}")
    git("reset", "HEAD~1")
    print("[flow] Ultimo commit deshecho. Los cambios siguen en el directorio de trabajo.")


def cmd_discard(args):
    require_repo()
    if not args:
        raise FlowError("Uso: flow discard <archivo|all> [--yes]")
    target = args[0]
    confirmed = "--yes" in args
    if not confirmed:
        scope = "TODOS los cambios" if target == "all" else f"los cambios en '{target}'"
        print(f"[flow] ATENCION: se van a descartar {scope}.")
        print("  Esto crea un stash de respaldo. Continuar? (escribe 'si' para confirmar)")
        try:
            resp = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = ""
        if resp not in ("si", "yes", "s", "y"):
            print("[flow] Cancelado.")
            return
    # snapshot a stash
    stash_ok = git_ok("stash", "push", "-u", "-m", f"flow-discard-backup-{now_tag()}")
    if not stash_ok:
        print("[flow] No habia cambios que descartar.")
        return
    if target != "all":
        # restaurar todo excepto el archivo objetivo
        git("stash", "pop")
        git("checkout", "--", target)
        print(f"[flow] Cambios en '{target}' descartados. Stash de respaldo creado.")
    else:
        print("[flow] Todos los cambios descartados. Respaldo en stash (usa 'git stash pop' para recuperar).")


def cmd_backup(args):
    require_repo()
    label = args[0] if args else "manual"
    tag = create_backup(label)
    print(f"[flow] Backup creado: {tag}")


def cmd_restore(args):
    require_repo()
    tags = git("tag", "--list", "flow-backup/*", check=False).splitlines()
    if not tags:
        print("[flow] No hay backups disponibles.")
        return
    if not args:
        print("[flow] Backups disponibles:")
        for i, t in enumerate(sorted(tags)):
            print(f"  {i+1}. {t}")
        print("\nUsa: flow restore <nombre-del-tag>  (copia el tag completo de arriba)")
        return
    target = args[0]
    if target not in tags:
        raise FlowError(f"Backup '{target}' no encontrado. Usa 'flow restore' para ver la lista.")
    backup = create_backup("pre-restore")
    print(f"[flow] Backup actual creado: {backup}")
    git("checkout", target)
    print(f"[flow] Restaurado a {target}.")
    print("  Nota: estas en modo 'detached HEAD'. Crea una rama si quieres continuar trabajando:")
    print("  git checkout -b mi-rama-recuperada")


def cmd_log(args):
    require_repo()
    subprocess.run(["git", "log", "--oneline", "--graph", "--decorate", "--all", "-20"],
                   capture_output=False)

# ────────────────────────────────────────────── helpers internos

def _extract_m(args):
    if "-m" in args:
        i = args.index("-m")
        return args[i + 1] if len(args) > i + 1 else None
    return None

def _stash_if_dirty(context):
    if not is_clean():
        label = f"flow-autostash-{context}-{now_tag()}"
        git("stash", "push", "-u", "-m", label)
        print(f"[flow] Cambios guardados en stash: {label}")

def _validate_semver(ver):
    if not re.match(r"^\d+\.\d+\.\d+$", ver):
        raise FlowError(f"Version '{ver}' invalida. Usa formato X.Y.Z (ej: 1.2.3)")

def _bump_version(ver):
    for fname in ("VERSION", "version.txt"):
        p = os.path.join(os.getcwd(), fname)
        if os.path.exists(p):
            with open(p, "w") as f:
                f.write(ver + "\n")
            git("add", fname)
            git("commit", "-m", f"chore(release): bump version to {ver}")
            print(f"[flow] {fname} actualizado a {ver}")
            return

# ────────────────────────────────────────────── dispatch

COMMANDS = {
    "init":    cmd_init,
    "status":  cmd_status,
    "feature": cmd_feature,
    "release": cmd_release,
    "hotfix":  cmd_hotfix,
    "commit":  cmd_commit,
    "save":    cmd_save,
    "undo":    cmd_undo,
    "discard": cmd_discard,
    "backup":  cmd_backup,
    "restore": cmd_restore,
    "log":     cmd_log,
}

HELP = """
Uso: flow <comando> [opciones]

Comandos:
  init                         Inicializa Gitflow en el repo actual
  status                       Estado: rama, rol, cambios, siguientes pasos
  feature start <nombre>       Nueva feature desde develop
  feature finish               Mergea la feature a develop
  release start <X.Y.Z>        Nueva release desde develop
  release finish               Mergea a main + develop, crea tag
  hotfix  start <X.Y.Z>        Nuevo hotfix desde main
  hotfix  finish               Mergea a main + develop, crea tag
  commit  [-m "tipo: asunto"]  Commit con validacion Conventional Commits
  save    [-m "mensaje"]       Checkpoint WIP rapido
  undo                         Deshace el ultimo commit (conserva cambios)
  discard <archivo|all>        Descarta cambios (pide confirmacion)
  backup  [etiqueta]           Crea snapshot de seguridad manual
  restore [tag]                Lista o restaura backups
  log                          Historial en grafo

Conventional Commits (obligatorio en 'flow commit'):
  formato: tipo(scope): asunto
  tipos:   feat fix chore docs refactor test perf build ci style revert
"""

def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP)
        return
    cmd = argv[0]
    rest = argv[1:]
    if cmd not in COMMANDS:
        print(f"[flow] Comando desconocido: '{cmd}'. Usa 'flow --help'.")
        sys.exit(1)
    try:
        COMMANDS[cmd](rest)
    except FlowError as e:
        print(f"\n[flow] Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[flow] Cancelado.")
        sys.exit(0)

if __name__ == "__main__":
    main()
