"""Recording engine: runs gst-launch-1.0 for screen video and system audio into one MKV file.

Screen comes from a PipeWire node chosen through the ScreenCast portal (portal.py).
System audio comes from the default output's monitor source. Stop sends SIGINT, which
with gst-launch's -e flag writes an end-of-stream, so the MKV file is finalised.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from screen_recorder_buffed.portal import ScreenStream

GST_BINARY = "gst-launch-1.0"
STOP_TIMEOUT_S = 15.0


def output_file_name(started_at: datetime) -> str:
    """MKV name from the local start time, e.g. 2026-11-02_14-30-05.mkv (content-model.md)."""
    return started_at.strftime("%Y-%m-%d_%H-%M-%S") + ".mkv"


def build_gst_args(
    stream: ScreenStream,
    audio_monitor: str,
    output_path: Path,
) -> list[str]:
    """The gst-launch-1.0 arguments: screen and system audio muxed into one Matroska file."""
    return [
        GST_BINARY,
        "-e",
        # Muxer and file first, so both branches can link to 'mux'.
        "matroskamux", "name=mux", "!",
        "filesink", f"location={output_path}",
        # Screen video from the portal's PipeWire node.
        "pipewiresrc", f"fd={stream.fd}", f"path={stream.node_id}", "do-timestamp=true", "!",
        "queue", "!",
        "videoconvert", "!",
        "x264enc", "speed-preset=veryfast", "key-int-max=60", "!",
        "h264parse", "!",
        "queue", "!",
        "mux.",
        # System audio: the default output's monitor, i.e. what the meeting plays.
        "pulsesrc", f"device={audio_monitor}", "!",
        "queue", "!",
        "audioconvert", "!",
        "audioresample", "!",
        "opusenc", "!",
        "mux.",
    ]


def log_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "screen-recorder-buffed" / "logs"


def default_audio_monitor() -> str | None:
    """The default output's monitor source name, or None if it cannot be found."""
    try:
        result = subprocess.run(
            ["pactl", "get-default-sink"], capture_output=True, text=True, timeout=5, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sink = result.stdout.strip()
    return f"{sink}.monitor" if sink else None


@dataclass
class RunningRecording:
    process: subprocess.Popen
    output_path: Path
    started_at: datetime
    started_monotonic: float
    stream: ScreenStream

    def elapsed(self) -> float:
        return time.monotonic() - self.started_monotonic

    def file_size(self) -> int:
        try:
            return self.output_path.stat().st_size
        except OSError:
            return 0


class Recorder:
    def start(self, stream: ScreenStream, audio_monitor: str, output_dir: Path) -> RunningRecording:
        started_at = datetime.now()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_file_name(started_at)
        args = build_gst_args(stream, audio_monitor, output_path)
        # Log to a file, not a pipe: an unread pipe can fill up and stall a long recording.
        log_path = log_dir() / (started_at.strftime("%Y-%m-%d_%H-%M-%S") + ".log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                args,
                pass_fds=(stream.fd,),
                stdout=subprocess.DEVNULL,
                stderr=log,
            )
        # The child has its own copy of the descriptor now; drop ours.
        os.close(stream.fd)
        return RunningRecording(
            process=process,
            output_path=output_path,
            started_at=started_at,
            started_monotonic=time.monotonic(),
            stream=stream,
        )

    def stop(self, recording: RunningRecording) -> int | None:
        """Ask the pipeline to finish the file, and wait. Returns the exit code, or None if killed."""
        if recording.process.poll() is None:
            recording.process.send_signal(signal.SIGINT)
            try:
                return recording.process.wait(timeout=STOP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                recording.process.kill()
                recording.process.wait()
                return None
        return recording.process.returncode
