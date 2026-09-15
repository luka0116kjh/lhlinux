"""Run one explicit command with bounded private logs and a short summary."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time


def positive(value):
    number = int(value)
    if not 1 <= number <= 1073741824:
        raise argparse.ArgumentTypeError("expected an integer from 1 to 1073741824")
    return number


def terminate(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def preview(path, limit=2048):
    with path.open("rb") as stream:
        size = path.stat().st_size
        stream.seek(max(0, size - limit))
        data = stream.read(limit)
    text = data.decode("utf-8", errors="replace")
    text = "".join(c for c in text if c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) < 160))
    # Bound line count as well as bytes, without discarding the saved full log.
    lines = text.splitlines()
    return ("[tail preview]\n" if size > limit or len(lines) > 30 else "") + "\n".join(lines[-30:])


def execute(args):
    cwd = args.cwd.resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("--cwd must be a directory")
    os.umask(0o077)
    args.log_dir.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=args.log_dir)).resolve()
    paths = {name: folder / (name + ".log") for name in ("stdout", "stderr")}
    result = {
        "schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(),
        "cwd": str(cwd), "executable": args.command[0],
        "argv": args.command if args.record_command else None,
        "log_directory": str(folder), "timeout_seconds": args.timeout,
        "max_output_bytes": args.max_output_bytes, "bytes_saved": {name: 0 for name in paths},
        "stop_reason": "completed", "exit_code": None,
    }
    process = None
    start = time.monotonic()
    previous = {}

    def interrupted(signum, frame):
        result["stop_reason"] = "signal"
        result["exit_code"] = 128 + signum
        raise KeyboardInterrupt

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.signal(signum, interrupted)
    try:
        with paths["stdout"].open("wb") as stdout, paths["stderr"].open("wb") as stderr:
            files = {"stdout": stdout, "stderr": stderr}
            try:
                process = subprocess.Popen(args.command, cwd=cwd, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           start_new_session=True)
            except OSError as error:
                result["stop_reason"] = "launch_error"
                result["exit_code"] = 127 if isinstance(error, FileNotFoundError) else 126
                result["error"] = str(error)
            if process is not None:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
                    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
                    while selector.get_map():
                        remaining = args.timeout - (time.monotonic() - start)
                        if remaining <= 0:
                            result.update(stop_reason="timeout", exit_code=124)
                            break
                        exceeded = False
                        for key, _ in selector.select(min(remaining, 0.1)):
                            chunk = os.read(key.fileobj.fileno(), 65536)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            room = args.max_output_bytes - sum(result["bytes_saved"].values())
                            kept = chunk[:room]
                            files[key.data].write(kept)
                            result["bytes_saved"][key.data] += len(kept)
                            if len(chunk) > room:
                                result.update(stop_reason="output_limit", exit_code=125)
                                exceeded = True
                                break
                        if exceeded:
                            break
                    if result["exit_code"] is None:
                        try:
                            code = process.wait(timeout=max(0.001, args.timeout - (time.monotonic() - start)))
                            result["exit_code"] = code if code >= 0 else 128 - code
                        except subprocess.TimeoutExpired:
                            result.update(stop_reason="timeout", exit_code=124)
    except KeyboardInterrupt:
        result.update(stop_reason="signal", exit_code=result["exit_code"] or 130)
    finally:
        terminate(process)
        if process is not None:
            process.stdout.close()
            process.stderr.close()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        result["elapsed_seconds"] = round(time.monotonic() - start, 6)
        (folder / "result.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
    return result, paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--log-dir", type=Path, default=Path.home() / "lab/results/runs")
    parser.add_argument("--timeout", type=positive, default=300)
    parser.add_argument("--max-output-bytes", type=positive, default=16 * 1024 * 1024)
    parser.add_argument("--record-command", action="store_true", help="also save command arguments in the private result")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command[:1] == ["--"]:
        args.command.pop(0)
    if not args.command:
        parser.error("expected -- executable [arguments]")
    if args.timeout > 86400:
        parser.error("--timeout must be at most 86400 seconds")
    try:
        result, paths = execute(args)
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            print(f"[lhlinux] exit={result['exit_code']} reason={result['stop_reason']} elapsed={result['elapsed_seconds']:.3f}s")
            print("Logs: " + json.dumps(result["log_directory"]))
            for name, path in paths.items():
                print(f"\n--- {name}: {result['bytes_saved'][name]} bytes saved ---")
                print(preview(path))
        return result["exit_code"]
    except (OSError, ValueError) as error:
        print("[lhlinux] " + ascii(str(error)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
