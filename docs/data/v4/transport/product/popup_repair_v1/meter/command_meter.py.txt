"""Meter one owned argv; sampled RSS enforcement and identity-safe cleanup."""
from __future__ import annotations
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

INTERVAL, GRACE = 0.05, 1.0
LIBC = ctypes.CDLL(None, use_errno=True)

def pidfd_call(name, *args):
    result = getattr(LIBC, name)(*args)
    if result < 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))
    return result

def process_stat(pid):
    raw = Path(f"/proc/{pid}/stat").read_text()
    end = raw.rfind(")")
    fields = raw[end + 2:].split()
    return {"pid": pid, "ppid": int(fields[1]), "name": raw[raw.find("(") + 1:end],
            "state": fields[0], "start_ticks": int(fields[19]),
            "rss_bytes": int(fields[21]) * os.sysconf("SC_PAGE_SIZE")}

def process_table():
    table = {}
    for path in Path("/proc").iterdir():
        if path.name.isdecimal():
            try:
                table[int(path.name)] = process_stat(int(path.name))
            except (OSError, ValueError, IndexError):
                pass
    return table

def identity_state(identity):
    try:
        current = process_stat(identity[0])
    except (FileNotFoundError, ProcessLookupError):
        return "absent"
    except (OSError, ValueError, IndexError):
        return "unknown"
    if current["start_ticks"] != identity[1]:
        return "pid_reused"
    return "zombie_terminated" if current["state"] == "Z" else "live"

def discover(table, owned):
    found = {pid for pid, start in owned if pid in table and table[pid]["start_ticks"] == start}
    while True:
        added = False
        for pid, item in table.items():
            if pid in found or item["ppid"] not in found:
                continue
            try:
                parent, current = process_stat(item["ppid"]), process_stat(pid)
                if (parent["start_ticks"] != table[item["ppid"]]["start_ticks"]
                        or current["start_ticks"] != item["start_ticks"] or current["ppid"] != item["ppid"]):
                    continue
            except (OSError, ValueError, IndexError):
                continue
            owned[(pid, item["start_ticks"])] = dict(item)
            found.add(pid)
            added = True
        if not added:
            return

def send_owned(identity, signum):
    receipt = {"pid": identity[0], "start_ticks": identity[1], "signal": signum}
    try:
        fd = pidfd_call("pidfd_open", identity[0], 0)
        try:
            state = identity_state(identity)
            if state == "live":
                pidfd_call("pidfd_send_signal", fd, signum, None, 0)
                state = "sent"
            receipt["status"] = state
        finally:
            os.close(fd)
    except ProcessLookupError:
        receipt["status"] = "absent"
    except OSError as error:
        receipt.update(status="signal_error", errno=error.errno)
    return receipt

def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

def run_command(argv, output_dir, *, rss_limit_bytes=4 * 1024**3):
    if (not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv)
            or type(rss_limit_bytes) is not int or rss_limit_bytes <= 0):
        raise ValueError("Explicit nonempty argv and positive RSS limit required")
    if not all(hasattr(LIBC, name) for name in ("pidfd_open", "pidfd_send_signal")):
        raise RuntimeError("Linux pidfd support is required for identity-safe cleanup")
    output = Path(output_dir)
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    record = {"format": "owned_command_meter.v1", "argv": argv, "exit_code": None,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "started_at": datetime.now(timezone.utc).isoformat(),
              "rss_limit_bytes": rss_limit_bytes, "sample_interval_seconds": INTERVAL,
              "sampled_peak_aggregate_rss_bytes": 0, "samples": 0,
              "inherited_cpu_affinity": sorted(os.sched_getaffinity(0)),
              "max_observed_affinity_count": 0, "signals": [], "stop_reason": "command_exit",
              "ownership_scope": "Observed PID/start-matched descendants; unobserved detached descendants are not certified.",
              "cpu_scope": "RUSAGE_CHILDREN delta after waiting; excludes CPU of descendants not reaped through the command.",
              "stdout": "stdout.log", "stderr": "stderr.log"}
    save(output / "started.json", record)
    owned, child = {}, None
    started, before = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)
    def sample():
        table = process_table()
        discover(table, owned)
        rss = 0
        for identity, original in owned.items():
            current = table.get(identity[0])
            if current is None or current["start_ticks"] != identity[1]:
                continue
            rss += current["rss_bytes"]
            try:
                affinity = sorted(os.sched_getaffinity(identity[0]))
                original["last_cpu_affinity"] = affinity
                record["max_observed_affinity_count"] = max(record["max_observed_affinity_count"], len(affinity))
            except OSError:
                pass
        record["samples"] += 1
        record["sampled_peak_aggregate_rss_bytes"] = max(record["sampled_peak_aggregate_rss_bytes"], rss)
        record["exit_code"] = child.poll()
        return rss
    try:
        with (output / "stdout.log").open("xb") as stdout, (output / "stderr.log").open("xb") as stderr:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     shell=False, start_new_session=True)
            root = process_stat(child.pid)
            owned[(child.pid, root["start_ticks"])] = root
            save(output / "spawned.json", root)
            while True:
                tick = time.monotonic()
                rss = sample()
                if rss > rss_limit_bytes:
                    record["stop_reason"] = "rss_limit"
                    break
                if record["exit_code"] is not None:
                    break
                time.sleep(max(0, INTERVAL - (time.monotonic() - tick)))
    except BaseException as error:
        record.update(stop_reason="meter_error", error_type=type(error).__name__)
    finally:
        if child is not None:
            for signum in (signal.SIGTERM, signal.SIGKILL):
                for identity in reversed(list(owned)):
                    if identity_state(identity) in {"live", "unknown"}:
                        record["signals"].append(send_owned(identity, signum))
                deadline = time.monotonic() + GRACE
                while time.monotonic() < deadline:
                    tick = time.monotonic()
                    sample()
                    if all(identity_state(item) not in {"live", "unknown"} for item in owned):
                        break
                    time.sleep(max(0, INTERVAL - (time.monotonic() - tick)))
                if all(identity_state(item) not in {"live", "unknown"} for item in owned):
                    break
            record["exit_code"] = child.poll()
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record.update(wall_seconds=round(time.monotonic() - started, 6),
                      rss_limit_exceeded=record["sampled_peak_aggregate_rss_bytes"] > rss_limit_bytes,
                      child_rusage_cpu_seconds=round(after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, 6),
                      completed_at=datetime.now(timezone.utc).isoformat(),
                      owned_processes=[{**item, "terminal_state": identity_state(identity)} for identity, item in owned.items()])
        record["terminal_ownership_verified"] = bool(owned) and all(
            item["terminal_state"] in {"absent", "pid_reused", "zombie_terminated"} for item in record["owned_processes"])
        record["status"] = ("TERMINAL" if record["exit_code"] is not None and record["terminal_ownership_verified"]
                            else "UNKNOWN")
        save(output / "result.json", record)
    return record

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rss-limit-bytes", type=int, default=4 * 1024**3)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    def interrupted(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    result = run_command(args.command[1:] if args.command[:1] == ["--"] else args.command,
                         args.output_dir, rss_limit_bytes=args.rss_limit_bytes)
    print(json.dumps(result))
    raise SystemExit(result["exit_code"] if result["status"] == "TERMINAL" and not result["rss_limit_exceeded"]
                     and result["stop_reason"] == "command_exit"
                     and result["exit_code"] >= 0 else 2)
if __name__ == "__main__":
    main()
