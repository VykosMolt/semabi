import json
from pathlib import Path
import signal
import subprocess
import sys

import pytest

import command_meter as meter


def run(tmp_path, source, **kwargs):
    return meter.run_command([sys.executable, "-B", "-c", source], tmp_path / "attempt", **kwargs)


def assert_closed(result):
    assert result["status"] == "TERMINAL"
    assert result["terminal_ownership_verified"] is True
    assert result["owned_processes"]
    assert all(meter.identity_state((item["pid"], item["start_ticks"])) != "live"
               for item in result["owned_processes"])


@pytest.mark.parametrize("exit_code", [0, 7])
def test_normal_and_nonzero_exit_preserve_output_and_rusage(tmp_path, exit_code):
    result = run(tmp_path, f"import sys; sum(i*i for i in range(1500000)); print('stdout'); print('stderr',file=sys.stderr); sys.exit({exit_code})")
    assert result["exit_code"] == exit_code
    assert result["stop_reason"] == "command_exit"
    assert result["child_rusage_cpu_seconds"] > 0
    assert result["wall_seconds"] > 0
    assert result["sampled_peak_aggregate_rss_bytes"] > 0
    assert result["max_observed_affinity_count"] == 1
    assert (tmp_path / "attempt/stdout.log").read_text() == "stdout\n"
    assert (tmp_path / "attempt/stderr.log").read_text() == "stderr\n"
    assert json.loads((tmp_path / "attempt/result.json").read_text()) == result
    assert_closed(result)


def test_memory_limit_terminates_the_owned_process(tmp_path):
    result = run(tmp_path, "import time; data=bytearray(64*1024*1024); time.sleep(30)",
                 rss_limit_bytes=24 * 1024**2)
    assert result["stop_reason"] == "rss_limit"
    assert result["rss_limit_exceeded"] is True
    assert result["sampled_peak_aggregate_rss_bytes"] > 24 * 1024**2
    assert result["exit_code"] < 0
    assert result["signals"]
    assert result["wall_seconds"] < 5
    assert_closed(result)


def test_nested_owned_child_is_closed_when_parent_finishes(tmp_path):
    nested = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
    source = ("import subprocess,sys,time; "
              f"child=subprocess.Popen([sys.executable,'-B','-c',{nested!r}]); "
              "print(child.pid,flush=True); time.sleep(0.3)")
    result = run(tmp_path, source)
    assert result["exit_code"] == 0
    assert len(result["owned_processes"]) >= 2
    assert any(item["signal"] == signal.SIGKILL and item["status"] == "sent" for item in result["signals"])
    assert result["wall_seconds"] < 5
    assert_closed(result)


def test_output_directory_is_exclusive_before_launch(tmp_path):
    path = tmp_path / "attempt"
    path.mkdir()
    (path / "keep").write_text("unchanged")
    with pytest.raises(FileExistsError):
        run(tmp_path, "raise RuntimeError('must not execute')")
    assert list(path.iterdir()) == [path / "keep"]
    assert (path / "keep").read_text() == "unchanged"


def test_pid_reuse_identity_is_never_signalled(monkeypatch):
    sent = []
    monkeypatch.setattr(meter, "pidfd_call", lambda name, *args: 91 if name == "pidfd_open" else sent.append(args))
    monkeypatch.setattr(meter.os, "close", lambda fd: None)
    monkeypatch.setattr(meter, "process_stat", lambda pid: {"start_ticks": 456, "state": "S"})
    receipt = meter.send_owned((123, 111), signal.SIGKILL)
    assert receipt["status"] == "pid_reused"
    assert sent == []


def test_cli_executes_literal_argv_and_preserves_child_exit(tmp_path):
    output = tmp_path / "cli"
    completed = subprocess.run([sys.executable, "-B", str(Path(meter.__file__)), "--output-dir", str(output),
                                "--", sys.executable, "-B", "-c",
                                "import sys; print(sys.argv[1]); sys.exit(3)", "$(not-a-shell-command)"],
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 3
    result = json.loads(completed.stdout)
    assert result["exit_code"] == 3
    assert (output / "stdout.log").read_text() == "$(not-a-shell-command)\n"
    assert_closed(result)
