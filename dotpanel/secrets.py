"""dotpanel.secrets — scoped secrets API.

Every call must state intent: a specific `--key`, a specific
`--backend`/`--variant`, or the narrow `--scope llm` carve-out for
IDE/.bashrc inheritance. The threat model and rationale live in the
substrate-managed secrets design notes.

Subcommands:

    secrets init [--keygen | --recipient <pubkey-path>] [--force]
    secrets list [--scope <name>] [--names-only]
    secrets edit
    secrets run --key NAME [--key NAME...] -- cmd args...
    secrets run --backend <provider> [--variant <name>] -- cmd args...
    secrets export --scope llm [--shell {bash,zsh,fish}]
    secrets rotate-key [--add-recipient <pubkey-path>]
    secrets help

Exit codes (per design doc):
    0   ok
    2   usage / missing key / unknown backend variant / pre-flight refusal
    3   bundle missing-or-unreadable / age key not found / age binary not found
    4   bundle write failed

The bundle is a tar.gz wrapped in age encryption (matches v4 format).
Decrypt-edit-encrypt happens through a tmpfs-backed scratch dir
(`/dev/shm` on Linux, falling back to `/tmp`) with mode 0600 files.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .config import (
    BackendVariant,
    SchemaError,
    SubstrateConfig,
    SubstrateNotFound,
    find_substrate,
)


# Provider → base_url env var resolver table (IC-SG-3). Lowercase match.
PROVIDER_BASE_URL_ENV = {
    "claude": "ANTHROPIC_BASE_URL",
    "codex": "OPENAI_BASE_URL",
    "kimi": "ANTHROPIC_BASE_URL",
}

VALID_SHELLS = ("bash", "zsh", "fish")

DEFAULT_AGE_KEY_PATH = "~/.config/age/key.txt"


class SecretsError(Exception):
    """Raised inside secrets handlers. Carries the exit code per the contract."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# --- Helpers --------------------------------------------------------------

def _refuse_under_xtrace() -> None:
    """v4 behavior: refuse to run when bash xtrace is on (set -x would print
    decrypted values). The bash shim guarded this; in Python we approximate
    by checking the parent shell's flags via $SHELLOPTS. Most pythons inherit
    a clean env from the shim, so this is informational/defensive."""
    opts = os.environ.get("SHELLOPTS", "")
    if "xtrace" in opts.split(":"):
        print(
            "secrets: refusing to run under xtrace (set -x leaks secrets)",
            file=sys.stderr,
        )
        raise SecretsError("xtrace refused", exit_code=2)


def _age_binary() -> str:
    age = shutil.which("age")
    if not age:
        raise SecretsError(
            "age binary not found in $PATH. Install with `apt install age` or "
            "`brew install age`, then retry.",
            exit_code=3,
        )
    return age


def _age_keygen_binary() -> str:
    keygen = shutil.which("age-keygen")
    if not keygen:
        raise SecretsError(
            "age-keygen binary not found in $PATH. Install with `apt install "
            "age` or `brew install age`, then retry.",
            exit_code=3,
        )
    return keygen


def _resolve_age_key() -> Path:
    """Return the path to the age private key. v4 looked at the macOS
    keychain first; v5 keeps things simple: $HOME/.config/age/key.txt
    is the only source of truth here. Operators on macOS can symlink it.
    """
    candidate = Path(os.path.expanduser(DEFAULT_AGE_KEY_PATH))
    if candidate.is_file():
        return candidate
    raise SecretsError(
        f"age key not found at {candidate}. Run `dotpanel secrets init "
        "--keygen` to create one, or copy your existing key.txt to "
        f"{candidate} (mode 0600).",
        exit_code=3,
    )


def _scratch_dir(prefix: str) -> Path:
    """Allocate a private scratch dir.

    Prefer `/dev/shm` (tmpfs) when writable; otherwise fall back to
    `tempfile.mkdtemp`. Permissions 0700.
    """
    for base in (Path("/dev/shm"), None):
        if base is not None:
            if not (base.exists() and os.access(base, os.W_OK)):
                continue
            base_str = str(base)
        else:
            base_str = None
        try:
            d = Path(tempfile.mkdtemp(prefix=prefix, dir=base_str))
            d.chmod(0o700)
            return d
        except OSError:
            continue
    raise SecretsError("could not allocate scratch directory", exit_code=4)


def _decrypt_bundle(bundle: Path, key: Path) -> bytes:
    """Run `age -d -i <key> <bundle>` and return the decrypted bytes."""
    if not bundle.is_file():
        raise SecretsError(f"bundle missing: {bundle}", exit_code=3)
    try:
        result = subprocess.run(
            [_age_binary(), "-d", "-i", str(key), str(bundle)],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise SecretsError(f"age invocation failed: {exc}", exit_code=3) from exc
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise SecretsError(
            f"age decrypt failed (exit {result.returncode}): {stderr or '<no stderr>'}",
            exit_code=3,
        )
    return result.stdout


def _encrypt_bundle(plaintext: bytes, pubkey_path: Path, bundle: Path) -> None:
    """Run `age -R <pubkey> > <bundle>` with atomic move."""
    if not pubkey_path.is_file():
        raise SecretsError(f"pubkey missing: {pubkey_path}", exit_code=3)
    tmp_path = bundle.with_suffix(bundle.suffix + ".tmp")
    try:
        with tmp_path.open("wb") as out:
            result = subprocess.run(
                [_age_binary(), "-R", str(pubkey_path)],
                input=plaintext,
                stdout=out,
                stderr=subprocess.PIPE,
                check=False,
            )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise SecretsError(
                f"age encrypt failed (exit {result.returncode}): "
                f"{stderr or '<no stderr>'}",
                exit_code=4,
            )
        tmp_path.chmod(0o600)
        os.replace(tmp_path, bundle)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _is_tar_gz(payload: bytes) -> bool:
    return payload[:2] == b"\x1f\x8b"


def _unpack_to_dir(bundle: Path, key: Path) -> Path:
    """Decrypt + untar bundle into a fresh scratch dir. Returns that dir.

    Caller is responsible for `shutil.rmtree` when finished.
    """
    plaintext = _decrypt_bundle(bundle, key)
    scratch = _scratch_dir("dotpanel-secrets-")
    if _is_tar_gz(plaintext):
        raw = scratch / ".bundle.tar.gz"
        raw.write_bytes(plaintext)
        raw.chmod(0o600)
        try:
            with tarfile.open(raw, mode="r:gz") as tf:
                tf.extractall(scratch, filter="data")
        except (tarfile.TarError, OSError) as exc:
            shutil.rmtree(scratch, ignore_errors=True)
            raise SecretsError(f"bundle unpack failed: {exc}", exit_code=3) from exc
        try:
            raw.unlink()
        except OSError:
            pass
        env_file = scratch / "env"
        if not env_file.exists():
            # Empty bundles are legal; create the file so callers don't crash.
            env_file.write_text("", encoding="utf-8")
            env_file.chmod(0o600)
    else:
        # Legacy plain-text format (pre-tar). Treat the whole payload as env.
        env_file = scratch / "env"
        env_file.write_bytes(plaintext)
        env_file.chmod(0o600)
    return scratch


def _pack_and_encrypt(scratch: Path, pubkey_path: Path, bundle: Path) -> None:
    """Re-pack the scratch dir contents as tar.gz, re-encrypt, atomic-replace."""
    members = [p for p in scratch.iterdir() if not p.name.startswith(".bundle")]
    if not members:
        # Empty bundle. Pack an empty tarfile.
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmpf:
            tmp_archive = Path(tmpf.name)
        try:
            with tarfile.open(tmp_archive, mode="w:gz") as tf:
                pass
            plaintext = tmp_archive.read_bytes()
        finally:
            try:
                tmp_archive.unlink()
            except OSError:
                pass
    else:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmpf:
            tmp_archive = Path(tmpf.name)
        try:
            with tarfile.open(tmp_archive, mode="w:gz") as tf:
                for member in members:
                    tf.add(member, arcname=member.name)
            plaintext = tmp_archive.read_bytes()
        finally:
            try:
                tmp_archive.unlink()
            except OSError:
                pass
    _encrypt_bundle(plaintext, pubkey_path, bundle)


def _parse_env_file(env_path: Path) -> list[tuple[str, str]]:
    """Read KEY=VALUE pairs from the env file. Preserves insertion order.

    Lines beginning with `#` or empty lines are skipped. Lines without `=`
    are silently ignored (matches v4 behavior).
    """
    if not env_path.exists():
        return []
    entries: list[tuple[str, str]] = []
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        entries.append((key.strip(), value))
    return entries


def _env_names(env_path: Path) -> list[str]:
    return [k for k, _ in _parse_env_file(env_path)]


def _env_value(env_path: Path, key: str) -> str | None:
    for k, v in _parse_env_file(env_path):
        if k == key:
            return v
    return None


def _matches_any(name: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, pat) for pat in patterns)


# --- Substrate / paths --------------------------------------------------

@dataclass
class SecretsContext:
    config: SubstrateConfig
    bundle_path: Path
    pubkey_path: Path

    @property
    def llm_scope(self) -> list[str]:
        return list(self.config.secrets.llm_scope)


def _load_context(*, require_bundle: bool = True) -> SecretsContext:
    try:
        cfg = find_substrate()
    except SubstrateNotFound as exc:
        raise SecretsError(f"substrate config not found: {exc}", exit_code=2) from exc
    try:
        bundle_path = cfg.path_for("secret_bundle")
        pubkey_path = cfg.path_for("secret_pubkey")
    except SchemaError as exc:
        raise SecretsError(str(exc), exit_code=2) from exc
    if require_bundle and not bundle_path.is_file():
        raise SecretsError(
            f"bundle missing at {bundle_path}. Run `dotpanel secrets init` "
            "to create one.",
            exit_code=3,
        )
    return SecretsContext(config=cfg, bundle_path=bundle_path, pubkey_path=pubkey_path)


# --- list ---------------------------------------------------------------

def cmd_list(scope: str | None, names_only: bool) -> int:
    ctx = _load_context()
    key = _resolve_age_key()
    scratch = _unpack_to_dir(ctx.bundle_path, key)
    try:
        env_path = scratch / "env"
        names = sorted(_env_names(env_path))
        if scope:
            patterns = _scope_patterns(ctx, scope)
            names = [n for n in names if _matches_any(n, patterns)]
        if names_only:
            for name in names:
                print(name)
            return 0
        print("# env vars:")
        for name in names:
            print(name)
        keys_dir = scratch / "keys"
        if keys_dir.is_dir():
            print("# keys:")
            for f in sorted(p.name for p in keys_dir.iterdir() if p.is_file()):
                print(f)
        configs_dir = scratch / "configs"
        if configs_dir.is_dir():
            print("# configs:")
            for f in sorted(
                str(p.relative_to(configs_dir))
                for p in configs_dir.rglob("*")
                if p.is_file()
            ):
                print(f)
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _scope_patterns(ctx: SecretsContext, scope: str) -> list[str]:
    if scope == "llm":
        return ctx.llm_scope
    # Future scopes are operator-additive; design says only `llm` exists in v5.
    raise SecretsError(
        f"unknown scope: {scope!r}. v5 defines only 'llm'.",
        exit_code=2,
    )


# --- edit ---------------------------------------------------------------

def cmd_edit() -> int:
    ctx = _load_context()
    key = _resolve_age_key()
    scratch = _unpack_to_dir(ctx.bundle_path, key)
    try:
        env_path = scratch / "env"
        if not env_path.exists():
            env_path.write_text("", encoding="utf-8")
        env_path.chmod(0o600)
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
        rc = subprocess.run(shlex.split(editor) + [str(env_path)], check=False).returncode
        if rc != 0:
            print(f"WARN  editor exited {rc}; re-packing anyway", file=sys.stderr)
        _pack_and_encrypt(scratch, ctx.pubkey_path, ctx.bundle_path)
        print("OK  secrets re-encrypted")
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# --- run ----------------------------------------------------------------

def _resolve_backend_variant(
    ctx: SecretsContext, backend: str, variant: str | None
) -> tuple[str, BackendVariant]:
    providers = ctx.config.backends.providers
    if backend not in providers:
        raise SecretsError(
            f"unknown backend: {backend!r}. Configured: "
            f"{', '.join(sorted(providers)) or '(none)'}",
            exit_code=2,
        )
    provider = providers[backend]
    name = variant or provider.default
    if name not in provider.variants:
        raise SecretsError(
            f"unknown backend variant: {backend}.{name}",
            exit_code=2,
        )
    return name, provider.variants[name]


def _backend_env(
    ctx: SecretsContext, backend: str, variant_name: str, variant: BackendVariant, secret_value: str
) -> dict[str, str]:
    """Compose the env dict that should be exposed to the child process.

    Per design doc IC-SG-3:
      - `variant.env_alias` (default `variant.key`) gets the decrypted value.
      - `<PROVIDER>_BASE_URL` (per resolver table) gets `variant.base_url`.
      - Every `variant.extra_env` entry is exported as-is.
      - DOTPANEL_MODEL = `variant.model`
      - DOTPANEL_PROMPT_OVERLAY = `variant.prompt_overlay` (resolved to abspath).
    """
    env: dict[str, str] = {}
    alias = variant.env_alias or variant.key
    env[alias] = secret_value
    if variant.base_url:
        base_var = PROVIDER_BASE_URL_ENV.get(backend.lower(), f"{backend.upper()}_BASE_URL")
        env[base_var] = variant.base_url
    for k, v in variant.extra_env.items():
        env[k] = v
    if variant.model:
        env["DOTPANEL_MODEL"] = variant.model
    if variant.prompt_overlay:
        overlay = ctx.config.root / variant.prompt_overlay
        env["DOTPANEL_PROMPT_OVERLAY"] = str(overlay)
    return env


def cmd_run(
    keys: list[str],
    backend: str | None,
    variant: str | None,
    cmd: list[str],
) -> int:
    if not cmd:
        raise SecretsError(
            "no command given. Usage: dotpanel secrets run --key X -- cmd args...",
            exit_code=2,
        )
    if bool(keys) == bool(backend):
        raise SecretsError(
            "must pass exactly one of: --key NAME [--key ...]  OR  --backend X "
            "[--variant Y]",
            exit_code=2,
        )

    ctx = _load_context()
    age_key = _resolve_age_key()
    scratch = _unpack_to_dir(ctx.bundle_path, age_key)
    try:
        env_path = scratch / "env"
        child_env = os.environ.copy()
        if keys:
            for k in keys:
                value = _env_value(env_path, k)
                if value is None:
                    raise SecretsError(
                        f"secret {k!r} not in bundle. List with "
                        "`dotpanel secrets list`.",
                        exit_code=2,
                    )
                child_env[k] = value
        else:
            assert backend is not None
            variant_name, variant_def = _resolve_backend_variant(ctx, backend, variant)
            secret_value = _env_value(env_path, variant_def.key)
            if secret_value is None:
                raise SecretsError(
                    f"backend {backend}.{variant_name} references secret "
                    f"{variant_def.key!r} which is not in bundle.",
                    exit_code=2,
                )
            additions = _backend_env(ctx, backend, variant_name, variant_def, secret_value)
            child_env.update(additions)
        # `exec` semantics: we need the scratch to survive long enough for
        # the child to read its env, but since we've already copied values
        # into child_env, the scratch can go right before exec.
        shutil.rmtree(scratch, ignore_errors=True)
        scratch = None  # type: ignore[assignment]
        os.execvpe(cmd[0], cmd, child_env)
        # Unreachable, but linters appreciate it.
        return 0
    finally:
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)


# --- export -------------------------------------------------------------

def cmd_export(scope: str, shell: str) -> int:
    if scope != "llm":
        raise SecretsError(
            "v5 removed bulk `secrets export`. Only `dotpanel secrets export "
            "--scope llm` is supported.\n"
            "Migration: for one-off keys, use `dotpanel secrets run --key X -- "
            "cmd`. For backend launchers, use `--backend X --variant Y`. See "
            "design doc 'Scoped Secrets API > Bulk export removed'.",
            exit_code=2,
        )
    ctx = _load_context()
    if not ctx.llm_scope:
        print(
            "INFO  no [secrets] llm_scope patterns configured; emitting nothing",
            file=sys.stderr,
        )
        return 0
    age_key = _resolve_age_key()
    scratch = _unpack_to_dir(ctx.bundle_path, age_key)
    try:
        env_path = scratch / "env"
        emitted = 0
        for name, value in _parse_env_file(env_path):
            if not _matches_any(name, ctx.llm_scope):
                continue
            line = _render_export_line(name, value, shell)
            print(line)
            emitted += 1
        if emitted == 0:
            print("INFO  no llm-scoped keys in bundle", file=sys.stderr)
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _render_export_line(name: str, value: str, shell: str) -> str:
    quoted = shlex.quote(value)
    if shell == "fish":
        return f"set -gx {name} {quoted}"
    # bash and zsh share `export NAME=value`.
    return f"export {name}={quoted}"


# --- init ---------------------------------------------------------------

def cmd_init(keygen: bool, recipient: Path | None, force: bool) -> int:
    if keygen and recipient:
        raise SecretsError(
            "pass either --keygen OR --recipient <pubkey-path>, not both.",
            exit_code=2,
        )
    if not (keygen or recipient):
        raise SecretsError(
            "must pass one of: --keygen, --recipient <pubkey-path>",
            exit_code=2,
        )
    ctx = _load_context(require_bundle=False)
    if ctx.bundle_path.exists():
        raise SecretsError(
            f"bundle already exists at {ctx.bundle_path}; use `secrets edit` "
            "to modify",
            exit_code=2,
        )

    age_key_path = Path(os.path.expanduser(DEFAULT_AGE_KEY_PATH))
    if keygen:
        if age_key_path.exists():
            raise SecretsError(
                f"age key already exists at {age_key_path}; pass --recipient "
                "<pubkey> to reuse it",
                exit_code=2,
            )
        age_key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        age_key_path.parent.chmod(0o700)
        keygen_bin = _age_keygen_binary()
        result = subprocess.run(
            [keygen_bin, "-o", str(age_key_path)],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise SecretsError(
                f"age-keygen failed: {stderr or '<no stderr>'}",
                exit_code=4,
            )
        age_key_path.chmod(0o600)
        # Extract the pubkey from the just-created private key.
        with age_key_path.open("rb") as keyfile:
            pub_result = subprocess.run(
                [keygen_bin, "-y"],
                stdin=keyfile,
                check=False,
                capture_output=True,
            )
        if pub_result.returncode != 0:
            stderr = pub_result.stderr.decode("utf-8", errors="replace").strip()
            raise SecretsError(
                f"age-keygen -y failed: {stderr or '<no stderr>'}",
                exit_code=4,
            )
        pubkey_text = pub_result.stdout.decode("utf-8").strip()
        if not pubkey_text.startswith("age1"):
            raise SecretsError(
                "age-keygen -y produced no usable pubkey",
                exit_code=4,
            )
        ctx.pubkey_path.parent.mkdir(parents=True, exist_ok=True)
        ctx.pubkey_path.write_text(pubkey_text + "\n", encoding="utf-8")
        ctx.pubkey_path.chmod(0o600)
    else:
        assert recipient is not None
        src = recipient.expanduser().resolve()
        if not src.is_file():
            raise SecretsError(f"pubkey not found: {src}", exit_code=2)
        pubkey_text = src.read_text(encoding="utf-8").strip()
        if not pubkey_text.startswith("age1"):
            raise SecretsError(
                f"pubkey at {src} does not look like an age public line (must "
                "start with 'age1')",
                exit_code=2,
            )
        if ctx.pubkey_path.exists() and not force:
            existing = ctx.pubkey_path.read_text(encoding="utf-8").strip()
            if existing != pubkey_text:
                raise SecretsError(
                    f"pubkey at {ctx.pubkey_path} differs from {src}; pass "
                    "--force to overwrite.",
                    exit_code=2,
                )
        ctx.pubkey_path.parent.mkdir(parents=True, exist_ok=True)
        ctx.pubkey_path.write_text(pubkey_text + "\n", encoding="utf-8")
        ctx.pubkey_path.chmod(0o600)

    # Create empty bundle
    scratch = _scratch_dir("dotpanel-init-")
    try:
        (scratch / "env").write_text("", encoding="utf-8")
        (scratch / "env").chmod(0o600)
        ctx.bundle_path.parent.mkdir(parents=True, exist_ok=True)
        _pack_and_encrypt(scratch, ctx.pubkey_path, ctx.bundle_path)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    print(f"OK  age key:    {age_key_path}")
    print(f"OK  recipient:  {ctx.pubkey_path}")
    print(f"OK  bundle:     {ctx.bundle_path} (empty)")
    print("Next: dotpanel secrets edit  (add KEY=value lines)")
    return 0


# --- rotate-key ---------------------------------------------------------

def cmd_rotate_key(add_recipient: Path | None) -> int:
    ctx = _load_context()
    age_key = _resolve_age_key()
    # Decrypt with the current key, then re-encrypt with the (possibly
    # extended) pubkey file.
    plaintext = _decrypt_bundle(ctx.bundle_path, age_key)
    if add_recipient is not None:
        added = add_recipient.expanduser().resolve()
        if not added.is_file():
            raise SecretsError(f"pubkey not found: {added}", exit_code=2)
        line = added.read_text(encoding="utf-8").strip()
        if not line.startswith("age1"):
            raise SecretsError(
                f"pubkey at {added} does not start with age1", exit_code=2
            )
        existing = ctx.pubkey_path.read_text(encoding="utf-8").splitlines()
        if line not in existing:
            existing.append(line)
            ctx.pubkey_path.write_text("\n".join(existing) + "\n", encoding="utf-8")
            ctx.pubkey_path.chmod(0o600)
            print(f"OK  added recipient: {line}")
    _encrypt_bundle(plaintext, ctx.pubkey_path, ctx.bundle_path)
    print(
        "OK  bundle re-encrypted.\n"
        "WARN  in-flight processes hold stale env (H3). Restart any "
        "consumer that loaded keys at startup (claw --serve, vscode-server, "
        "tmux sessions, sourced .bashrc shells).",
        file=sys.stderr,
    )
    print("OK  rotate-key done")
    return 0


# --- argparse + main ----------------------------------------------------

def _parse_run_args(rest: list[str]) -> tuple[list[str], str | None, str | None, list[str]]:
    """Manual argparse for `secrets run` because `--key NAME [--key NAME...] -- cmd`
    is awkward to express in argparse without `--`.

    Returns (keys, backend, variant, cmd).
    """
    keys: list[str] = []
    backend: str | None = None
    variant: str | None = None
    cmd: list[str] = []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--":
            cmd = rest[i + 1:]
            return keys, backend, variant, cmd
        if a == "--key":
            if i + 1 >= len(rest):
                raise SecretsError("--key requires an argument", exit_code=2)
            keys.append(rest[i + 1])
            i += 2
            continue
        if a == "--backend":
            if i + 1 >= len(rest):
                raise SecretsError("--backend requires an argument", exit_code=2)
            backend = rest[i + 1]
            i += 2
            continue
        if a == "--variant":
            if i + 1 >= len(rest):
                raise SecretsError("--variant requires an argument", exit_code=2)
            variant = rest[i + 1]
            i += 2
            continue
        if a.startswith("--"):
            raise SecretsError(f"unknown flag for run: {a}", exit_code=2)
        # Plain word with no preceding `--` is a bug — keep strict.
        raise SecretsError(
            "expected `--` before the command. "
            "Usage: dotpanel secrets run --key X -- cmd args...",
            exit_code=2,
        )
    return keys, backend, variant, cmd


def _print_help() -> int:
    print(
        "Usage:\n"
        "  dotpanel secrets init [--keygen | --recipient <pubkey-path>] [--force]\n"
        "  dotpanel secrets list [--scope llm] [--names-only]\n"
        "  dotpanel secrets edit\n"
        "  dotpanel secrets run --key NAME [--key NAME ...] -- cmd args...\n"
        "  dotpanel secrets run --backend <provider> [--variant <name>] -- cmd ...\n"
        "  dotpanel secrets export --scope llm [--shell bash|zsh|fish]\n"
        "  dotpanel secrets rotate-key [--add-recipient <pubkey-path>]\n"
        "  dotpanel secrets help\n",
    )
    return 0


def build_secrets_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="secrets_cmd", required=False)

    init_p = sub.add_parser("init", help="bootstrap an empty bundle")
    init_p.add_argument("--keygen", action="store_true",
                        help="generate a new age key at ~/.config/age/key.txt")
    init_p.add_argument("--recipient", type=Path, default=None,
                        help="use an existing age pubkey instead of generating one")
    init_p.add_argument("--force", action="store_true",
                        help="overwrite differing pubkey at the configured path")

    list_p = sub.add_parser("list", help="list key names in the bundle")
    list_p.add_argument("--scope", default=None, choices=("llm",),
                        help="restrict to a configured scope (currently only 'llm')")
    list_p.add_argument("--names-only", action="store_true", dest="names_only",
                        help="emit one name per line, no headers (H7 strip workflow)")

    sub.add_parser("edit", help="decrypt bundle to a tmpfs file, $EDITOR, re-encrypt")

    run_p = sub.add_parser("run", help="exec a command with selected secrets injected")
    # We collect everything as REMAINDER and parse manually because argparse
    # doesn't model `--key X --key Y -- cmd args...` cleanly.
    run_p.add_argument("rest", nargs=argparse.REMAINDER,
                       help="--key NAME ... or --backend X --variant Y, then -- and the command")

    export_p = sub.add_parser("export", help="emit eval-able export lines for a scope")
    export_p.add_argument("--scope", required=True, choices=("llm",),
                          help="ONLY --scope llm is supported (no bulk decrypt)")
    export_p.add_argument("--shell", default="bash", choices=VALID_SHELLS,
                          help="output dialect (bash/zsh share syntax)")

    rotate_p = sub.add_parser("rotate-key", help="re-encrypt bundle to current pubkey file")
    rotate_p.add_argument("--add-recipient", type=Path, default=None,
                          help="append a pubkey to .secrets.pub before re-encrypting")

    sub.add_parser("help", help="show usage")


def dispatch_secrets(args: argparse.Namespace) -> int:
    _refuse_under_xtrace()
    sub = args.secrets_cmd
    try:
        if sub is None or sub == "help":
            return _print_help()
        if sub == "init":
            return cmd_init(args.keygen, args.recipient, args.force)
        if sub == "list":
            return cmd_list(args.scope, args.names_only)
        if sub == "edit":
            return cmd_edit()
        if sub == "run":
            keys, backend, variant, cmd = _parse_run_args(list(args.rest))
            return cmd_run(keys, backend, variant, cmd)
        if sub == "export":
            return cmd_export(args.scope, args.shell)
        if sub == "rotate-key":
            return cmd_rotate_key(args.add_recipient)
        raise SecretsError(f"unknown secrets subcommand: {sub}", exit_code=2)
    except SecretsError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code


def main(argv: list[str] | None = None) -> int:
    # `secrets run` swallows the remainder for the child command. Because
    # argparse cannot reliably model a `--key X --backend Y -- cmd args...`
    # subcommand shape, we sniff for `run` and route its tail through the
    # manual parser. Everything else goes through argparse normally.
    if argv and argv[0] == "run":
        try:
            keys, backend, variant, cmd = _parse_run_args(list(argv[1:]))
        except SecretsError as exc:
            print(f"FAIL  {exc}", file=sys.stderr)
            return exc.exit_code
        try:
            _refuse_under_xtrace()
            return cmd_run(keys, backend, variant, cmd)
        except SecretsError as exc:
            print(f"FAIL  {exc}", file=sys.stderr)
            return exc.exit_code

    parser = argparse.ArgumentParser(prog="dotpanel secrets")
    build_secrets_parser(parser)
    args = parser.parse_args(argv)
    return dispatch_secrets(args)


if __name__ == "__main__":
    raise SystemExit(main())
