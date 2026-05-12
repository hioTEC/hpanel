"""dotpanel.install — pinned-download tool installer.

Reads pin metadata from the substrate's `install_pins` path (sourced as bash
to populate `PIN_<tool>_<field>` plain variables).

    dotpanel install <tool>              one named tool
    dotpanel install all                 install every tool in pins file
    dotpanel install --list              show known pins

- SHA-256 verification is mandatory; mismatch -> exit 2 + delete temp file.
- `DOTPANEL_INSTALL_ALLOW_UNPINNED=1` opt-in for first-pin bootstrap.
- Output to `~/.local/bin`.
- Exit codes: 0 ok; 2 sha mismatch / unknown tool / usage error;
  4 download failed.

Single-arch only. The pins file is treated as opaque bash; we extract
`PIN_*_{url,sha256,handler,src}` assignments without executing arbitrary
side effects.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import SchemaError, find_substrate, SubstrateNotFound


LOCAL_BIN_DEFAULT = "~/.local/bin"

# Tools that need post-download unpacking. Map: tool-name -> handler symbol.
# Handler symbols are resolved in _post_install. We keep this list explicit
# rather than guessing from URL/extension because v4 install-tools made the
# choice explicit per-tool too.
_POST_INSTALL_HANDLERS = {
    "code": "vscode_cli_tarball",
}

# Tools handled by an out-of-band installer (e.g. devtunnel via npm). The
# install verb refuses `curl | bash` and refers the operator to the manual
# instructions baked into v4 install-tools; we preserve that refusal here.
_NPM_TOOLS = {"devtunnel"}

# Handlers for tools that don't download from URL+SHA. Each handler reads a
# substrate-relative `src` path declared in install-pins.sh and applies its
# install action (e.g. `tic -x` for terminfo). dotpanel ships the mechanism;
# the substrate owns what to install and where the source lives.
_BUNDLED_HANDLERS = {"terminfo"}


@dataclass(frozen=True)
class Pin:
    name: str
    url: str = ""
    sha256: str = ""
    handler: str = ""  # if set, dispatches to a bundled handler instead of URL+SHA
    src: str = ""     # substrate-relative path to bundled source

    @property
    def is_pinned(self) -> bool:
        return bool(self.url) and bool(self.sha256)

    @property
    def is_bundled(self) -> bool:
        return bool(self.handler)


class InstallError(Exception):
    """Anything that should turn into a non-zero exit code from `cmd_install`."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# --- pins file parser -----------------------------------------------------

_PIN_ASSIGN_RE = re.compile(
    r"""^\s*
        PIN_(?P<tool>[A-Za-z0-9_]+)_(?P<field>url|sha256|handler|src)
        \s*=\s*
        (?:
            "(?P<dq>[^"]*)"     # double-quoted
            |
            '(?P<sq>[^']*)'     # single-quoted
            |
            (?P<bare>\S+)       # bare token
        )
        \s*$
    """,
    re.VERBOSE,
)


def parse_pins_file(text: str) -> dict[str, Pin]:
    """Extract Pin entries from install-pins.sh.

    Lines parsed:
        PIN_<tool>_url="https://..."         # URL+SHA download (binary)
        PIN_<tool>_sha256="..."
        PIN_<tool>_handler="<name>"          # bundled tool dispatched to handler
        PIN_<tool>_src="path/relative/..."   # substrate-relative source for bundled

    Comments and shebangs are ignored. Multiple assignments for the same
    tool are merged. Empty values are kept (Pin.is_pinned reports false).
    """
    fields: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _PIN_ASSIGN_RE.match(line)
        if not m:
            continue
        tool = m.group("tool")
        field = m.group("field")
        value = m.group("dq") if m.group("dq") is not None else (
            m.group("sq") if m.group("sq") is not None else m.group("bare") or ""
        )
        fields.setdefault(tool, {})[field] = value
    return {
        tool: Pin(
            name=tool,
            url=info.get("url", ""),
            sha256=info.get("sha256", ""),
            handler=info.get("handler", ""),
            src=info.get("src", ""),
        )
        for tool, info in fields.items()
    }


# --- download / verify ----------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path, *, timeout: int = 180) -> None:
    """Stream `url` to `dest`. Raises InstallError on network failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "dotpanel-install/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as fh:
                shutil.copyfileobj(resp, fh)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise InstallError(f"download failed for {url}: {exc}", exit_code=4) from exc


def _unpinned_allowed() -> bool:
    """True if either the v5 canonical or v4 legacy env-var opt-in is set."""
    for var in ("DOTPANEL_INSTALL_ALLOW_UNPINNED", "INSTALL_TOOLS_ALLOW_UNPINNED"):
        if os.environ.get(var) == "1":
            return True
    return False


def _fetch_pinned(pin: Pin, dest: Path) -> None:
    """Download `pin.url` to `dest`, verify SHA-256. Raises InstallError on mismatch."""
    _download(pin.url, dest)
    actual = _sha256_file(dest)
    if actual != pin.sha256:
        try:
            dest.unlink()
        except OSError:
            pass
        raise InstallError(
            f"SHA-256 mismatch for {pin.name}\n"
            f"  expected: {pin.sha256}\n"
            f"  actual:   {actual}",
            exit_code=2,
        )


def _print_pin_hint(name: str, file_path: Path) -> None:
    """Print a hint matching v4 install-tools' `_print_pin_hint`."""
    sha = _sha256_file(file_path)
    print(
        f"\nTo pin {name}, set these in install-pins.sh:\n"
        f'    PIN_{name}_url="<the URL you downloaded from>"\n'
        f'    PIN_{name}_sha256="{sha}"\n',
        file=sys.stderr,
    )


# --- post-install handlers ------------------------------------------------

def _install_bundled(pin: Pin) -> Path:
    """Install a tool whose source ships in the substrate.

    The Pin must declare `handler` (handler name) and `src` (substrate-relative
    path to the source). dotpanel provides the install mechanism; the substrate
    declares what + where via install-pins.sh.
    """
    if pin.handler not in _BUNDLED_HANDLERS:
        raise InstallError(
            f"{pin.name}: unknown handler {pin.handler!r}. "
            f"Known handlers: {', '.join(sorted(_BUNDLED_HANDLERS))}",
            exit_code=2,
        )
    if not pin.src:
        raise InstallError(
            f"{pin.name}: handler {pin.handler!r} requires PIN_{pin.name}_src",
            exit_code=2,
        )

    try:
        substrate = find_substrate()
    except SubstrateNotFound as exc:
        raise InstallError(
            f"{pin.name}: substrate not found (need substrate to resolve "
            f"`src` path): {exc}",
            exit_code=2,
        ) from exc
    src = substrate.root / pin.src
    if not src.is_file():
        raise InstallError(
            f"{pin.name}: source missing at {src}",
            exit_code=2,
        )

    if pin.handler == "terminfo":
        tic = shutil.which("tic")
        if not tic:
            raise InstallError(
                f"{pin.name}: `tic` not found. Install ncurses-bin (Debian/Ubuntu) "
                "or ncurses (RHEL) first, then re-run.",
                exit_code=2,
            )
        import subprocess
        terminfo_dir = Path(os.path.expanduser("~/.terminfo"))
        terminfo_dir.mkdir(parents=True, exist_ok=True)
        rc = subprocess.run(
            [tic, "-x", "-o", str(terminfo_dir), str(src)],
            check=False,
        ).returncode
        if rc != 0:
            raise InstallError(f"{pin.name}: tic exited {rc}", exit_code=4)
        # tic infers the installed-entry path from the .src header; we report
        # the terminfo dir generically since handlers may install multiple entries.
        return terminfo_dir

    raise InstallError(f"{pin.name}: handler {pin.handler!r} not implemented", exit_code=2)


def _post_install(name: str, downloaded: Path, local_bin: Path) -> Path:
    """Run any post-install unpacking. Returns the final installed path.

    For tools without special handling, this just `chmod +x`s the file.
    """
    handler = _POST_INSTALL_HANDLERS.get(name)
    if handler == "vscode_cli_tarball":
        # vscode CLI ships as `<tmp>/<extracted>/code` (single file named
        # `code` after unpacking). Mirrors v4 install-tools cmd_code.
        target = local_bin / "code"
        with tempfile.TemporaryDirectory(prefix=f"dotpanel-{name}-") as td:
            tdir = Path(td)
            with tarfile.open(downloaded, mode="r:gz") as tf:
                # Python 3.12 deprecation: filter='data' avoids extracting outside td
                tf.extractall(tdir, filter="data")
            extracted = tdir / "code"
            if not extracted.is_file():
                # vscode tarball sometimes nests under a versioned dir
                for candidate in tdir.rglob("code"):
                    if candidate.is_file() and os.access(candidate, os.X_OK | os.R_OK):
                        extracted = candidate
                        break
            if not extracted.is_file():
                raise InstallError(
                    f"{name}: unpacked archive did not contain expected 'code' binary",
                    exit_code=4,
                )
            shutil.move(str(extracted), target)
        target.chmod(0o755)
        return target

    # Default: rename downloaded into local_bin/<name>, chmod +x
    target = local_bin / name
    if downloaded != target:
        shutil.move(str(downloaded), target)
    target.chmod(0o755)
    return target


# --- per-tool installers --------------------------------------------------

def _install_one(pin: Pin, local_bin: Path) -> Path:
    """Install one pinned tool. Returns the final installed path.

    Raises InstallError on missing-pin (without opt-in), SHA mismatch, or
    download failure.
    """
    if pin.name in _NPM_TOOLS:
        # devtunnel is npm-only in v4; preserve the refusal.
        if not shutil.which("npm"):
            raise InstallError(
                f"{pin.name}: npm not found. dotpanel install refuses 'curl | bash'.\n"
                "Install Node.js + npm first, then re-run: dotpanel install "
                f"{pin.name}",
                exit_code=2,
            )
        # Install via npm. The v4 script used the global flag.
        import subprocess
        rc = subprocess.run(
            ["npm", "install", "-g", "@devtunnel/cli"],
            check=False,
        ).returncode
        if rc != 0:
            raise InstallError(f"{pin.name}: npm install exited {rc}", exit_code=4)
        return local_bin / pin.name  # nominal path; npm picks the real location

    if not pin.is_pinned:
        if not _unpinned_allowed():
            raise InstallError(
                f"{pin.name} is not pinned (need PIN_{pin.name}_url and "
                f"PIN_{pin.name}_sha256).\n"
                "  Refusing to download unpinned binaries (supply-chain hardening).\n"
                "  Bootstrap a new pin once with:\n"
                f"    DOTPANEL_INSTALL_ALLOW_UNPINNED=1 dotpanel install {pin.name}\n"
                "  Then copy the printed SHA-256 back into install-pins.sh.",
                exit_code=2,
            )
        raise InstallError(
            f"{pin.name}: unpinned and DOTPANEL_INSTALL_ALLOW_UNPINNED=1 but no "
            "fallback URL is known. Resolve by adding `PIN_{name}_url` first.",
            exit_code=2,
        )

    local_bin.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"dotpanel-install-{pin.name}-", delete=False, dir=str(local_bin)
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _fetch_pinned(pin, tmp_path)
        return _post_install(pin.name, tmp_path, local_bin)
    except InstallError:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


# --- command dispatch -----------------------------------------------------

def _load_pins() -> tuple[dict[str, Pin], Path]:
    """Load pins from the substrate's install_pins path.

    Returns (pins, resolved_path). Raises InstallError on missing config /
    missing pins file with concrete remediation.
    """
    try:
        substrate = find_substrate()
    except SubstrateNotFound as exc:
        raise InstallError(f"substrate config not found: {exc}", exit_code=2) from exc

    try:
        pins_path = substrate.path_for("install_pins")
    except SchemaError as exc:
        raise InstallError(str(exc), exit_code=2) from exc

    if not pins_path.is_file():
        raise InstallError(
            f"install-pins file missing: {pins_path}. "
            "Add it to your substrate or update [paths] install_pins.",
            exit_code=3,
        )
    return parse_pins_file(pins_path.read_text(encoding="utf-8")), pins_path


def cmd_install_list() -> int:
    try:
        pins, path = _load_pins()
    except InstallError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    print(f"# pins file: {path}")
    if not pins:
        print("# no pins defined")
        return 0
    width = max(len(name) for name in pins)
    for name in sorted(pins):
        pin = pins[name]
        if pin.is_bundled:
            print(f"  {name.ljust(width)}  handler={pin.handler}  "
                  f"src={pin.src or '(unset)'}")
        else:
            marker = "  " if pin.is_pinned else "* "
            print(f"{marker}{name.ljust(width)}  url={pin.url or '(unset)'}  "
                  f"sha256={pin.sha256 or '(unset)'}")
    if any(not p.is_pinned and not p.is_bundled for p in pins.values()):
        print(
            "\n* = unpinned (will refuse to install without "
            "DOTPANEL_INSTALL_ALLOW_UNPINNED=1).",
            file=sys.stderr,
        )
    return 0


def cmd_install(tool: str) -> int:
    try:
        pins, _ = _load_pins()
    except InstallError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code

    local_bin = Path(os.path.expanduser(LOCAL_BIN_DEFAULT))
    targets: list[str]
    if tool == "all":
        targets = sorted(pins)
        if not targets:
            print("# no pins defined; nothing to install")
            return 0
    else:
        if tool not in pins and tool not in _NPM_TOOLS:
            print(f"FAIL  unknown tool: {tool}", file=sys.stderr)
            print(f"  Known tools: {', '.join(sorted(pins)) or '(none)'}",
                  file=sys.stderr)
            return 2
        targets = [tool]

    last_paths: list[Path] = []
    for name in targets:
        pin = pins.get(name) or Pin(name=name)
        print(f"Installing {name}...")
        try:
            if pin.is_bundled:
                installed = _install_bundled(pin)
            else:
                installed = _install_one(pin, local_bin)
        except InstallError as exc:
            print(f"FAIL  {exc}", file=sys.stderr)
            return exc.exit_code
        last_paths.append(installed)
        print(f"  OK  {installed}")

    if len(last_paths) == 1:
        print(f"OK  installed {targets[0]} -> {last_paths[0]}")
    else:
        print(f"OK  installed {len(last_paths)} tool(s) to {local_bin}")
    return 0


def build_install_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "tool",
        nargs="?",
        default=None,
        help="tool name from install-pins.sh, or 'all' to install every pinned tool",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_pins",
        help="show pin metadata (url + sha256) for every known tool",
    )


def dispatch_install(args: argparse.Namespace) -> int:
    if getattr(args, "list_pins", False):
        return cmd_install_list()
    tool = args.tool
    if not tool:
        print(
            "usage: dotpanel install <tool|all>\n"
            "       dotpanel install --list",
            file=sys.stderr,
        )
        return 2
    return cmd_install(tool)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dotpanel install")
    build_install_parser(parser)
    args = parser.parse_args(argv)
    return dispatch_install(args)


if __name__ == "__main__":
    raise SystemExit(main())
