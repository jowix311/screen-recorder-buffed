"""Speech-to-text worker. Runs under the separate Python 3.12 environment that has faster-whisper.

It imports only the standard library and faster_whisper, so it can run under the
transcriber's own interpreter. The app calls it as a subprocess (transcribe.py).

Usage: python transcribe_worker.py MODEL_SIZE AUDIO_PATH LANGUAGE
Prints one JSON list of [start_seconds, end_seconds, text] on stdout.
Exits 1 with a message on stderr if anything fails.
"""

from __future__ import annotations

import json
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: transcribe_worker.py MODEL_SIZE AUDIO_PATH LANGUAGE", file=sys.stderr)
        return 2
    model_size, audio_path, language = argv

    from faster_whisper import WhisperModel

    # CPU for now: GPU use needs NVIDIA CUDA libraries that are not installed.
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,  # skip silence instead of inventing text for it
        beam_size=5,
    )
    rows = [[segment.start, segment.end, segment.text] for segment in segments]
    json.dump(rows, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as error:  # noqa: BLE001 - report any failure to the caller
        print(f"transcription failed: {error}", file=sys.stderr)
        sys.exit(1)
