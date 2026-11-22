"""Windows ACL and current-user DPAPI adapter."""
import argparse
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile

def native(action, path, data=""):
    shell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    try:
        reply = subprocess.run(
            [str(shell), "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
             "RemoteSigned", "-File", str(Path(__file__).with_suffix(".ps1")), action, str(path)],
            input=data, text=True, capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Windows private security helper unavailable") from exc
    if reply.returncode:
        raise ValueError(f"Windows private security verification failed ({action})")
    return reply.stdout

def reject_reparse(path):
    if not re.fullmatch(r"[A-Za-z]:", path.drive) or any(":" in part for part in path.parts[1:]):
        raise ValueError("private storage requires a local drive path without alternate streams")
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("private storage cannot traverse a Windows reparse point")

def directory(path, create):
    if create and not path.exists():
        if not path.parent.is_dir():
            raise ValueError("parent of Windows private directory must already exist")
        native("create", path)
    else:
        native("directory", path)

def file(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
        or info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError("Windows private file must be a single-link regular file")
    native("file", path)

def credential_path(value, create=False):
    from private_store import private_path
    path = private_path(value, create)
    if path.suffix.lower() != ".dpapi":
        raise ValueError("Windows credential file must use .dpapi")
    return path

def rotate(value):
    path = credential_path(value, True)
    blob = native("protect", path, secrets.token_hex(32))
    if not blob or len(blob) > 16384:
        raise ValueError("invalid protected credential")
    fd, temporary = tempfile.mkstemp(prefix=".credential-", dir=path.parent)
    staged = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        file(staged)
        os.replace(staged, path)
        file(path)
    finally:
        staged.unlink(missing_ok=True)

def configured_token():
    path = os.getenv("SOURCE_HUB_TOKEN_FILE")
    if not path:
        return os.getenv("SOURCE_HUB_INTAKE_TOKEN")
    if os.name != "nt" or os.getenv("SOURCE_HUB_INTAKE_TOKEN") is not None:
        raise ValueError("configure exactly one supported intake credential")
    path = credential_path(path)
    with path.open(encoding="ascii") as blob:
        data = blob.read(16385)
    if not data or len(data) > 16384:
        raise ValueError("invalid protected credential")
    token = native("unprotect", path, data)
    if not re.fullmatch(r"[a-f0-9]{64}", token):
        raise ValueError("invalid protected credential")
    return token

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate or rotate a Windows DPAPI intake credential")
    parser.add_argument("action", choices=("rotate",))
    parser.add_argument("path")
    args = parser.parse_args()
    try:
        if os.name != "nt":
            raise ValueError("Windows required")
        rotate(args.path)
        print("Protected credential replaced. Restart the intake to activate it.")
    except (ValueError, OSError):
        parser.exit(1, "Windows credential rotation failed.\n")
