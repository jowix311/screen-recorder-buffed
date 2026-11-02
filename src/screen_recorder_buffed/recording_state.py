"""Recording control state machine. Rules: site-contract.md §2 and §3, content-model.md (Recording control).

Pure logic with no Qt or capture code, so it can be tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

STALL_SECONDS = 5.0  # capture error: no new data for this long (content-model.md)

MSG_PRIVACY = "Accept privacy in Settings to record"
MSG_KEY = "Add a Claude API key in Settings to record"
MSG_LANGUAGE = "Select a spoken language to record"
MSG_RETRY = "Wait for the retry to finish before recording"
MSG_NO_SOURCE = "No screen or system-audio source found"
MSG_CAPTURE_ERROR = "Capture stopped. The partial recording is being processed."
MSG_STOP_FAILED = "The recording could not be finished cleanly."


class State(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    STOPPING = "stopping"
    PROCESSING = "processing"


@dataclass(frozen=True)
class StartInputs:
    privacy_accepted: bool
    has_key: bool
    language_selected: bool
    retry_running: bool


def start_blockers(inputs: StartInputs) -> list[str]:
    """Messages shown under the button, one per unmet condition, in the spec's order."""
    messages: list[str] = []
    if not inputs.privacy_accepted:
        messages.append(MSG_PRIVACY)
    if not inputs.has_key:
        messages.append(MSG_KEY)
    if not inputs.language_selected:
        messages.append(MSG_LANGUAGE)
    if inputs.retry_running:
        messages.append(MSG_RETRY)
    return messages


def can_start(inputs: StartInputs) -> bool:
    return not start_blockers(inputs)


def format_elapsed(seconds: float) -> str:
    """Elapsed time as hh:mm:ss (content-model.md, Recording control)."""
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def is_stalled(last_data_at: float, now: float) -> bool:
    """True when the capture source has delivered nothing for STALL_SECONDS."""
    return now - last_data_at >= STALL_SECONDS


@dataclass
class RecordingControl:
    """The Recording control state, with the transitions from site-contract.md §2."""

    state: State = State.IDLE
    messages: list[str] = field(default_factory=list)

    # What the button and indicators show in each state (site-contract.md §2 table).
    def button_label(self) -> str:
        return {
            State.IDLE: "Start recording",
            State.RECORDING: "Stop recording",
            State.STOPPING: "Stopping…",
            State.PROCESSING: "Processing…",
        }[self.state]

    def button_enabled(self, inputs: StartInputs) -> bool:
        if self.state is State.IDLE:
            return can_start(inputs)
        return self.state is State.RECORDING

    def timer_visible(self) -> bool:
        return self.state in (State.RECORDING, State.STOPPING)

    def indicator_visible(self) -> bool:
        return self.state in (State.RECORDING, State.STOPPING)

    def library_status(self) -> str:
        """Status shown in the library row (content-model.md, Recording library)."""
        return "recording" if self.state is State.RECORDING else "processing"

    # Transitions. Each returns True when the transition happened.

    def request_start(self, inputs: StartInputs, source_available: bool = True) -> bool:
        if self.state is not State.IDLE:
            return False
        if not can_start(inputs):
            self.messages = start_blockers(inputs)
            return False
        if not source_available:
            self.messages = [MSG_NO_SOURCE]
            return False
        self.messages = []
        self.state = State.RECORDING
        return True

    def request_stop(self) -> bool:
        """Stop button or Ctrl+Shift+R while recording."""
        if self.state is not State.RECORDING:
            return False
        self.state = State.STOPPING
        return True

    def on_capture_error(self) -> bool:
        if self.state is not State.RECORDING:
            return False
        self.state = State.STOPPING
        self.messages = [MSG_CAPTURE_ERROR]
        return True

    def on_file_finalised(self) -> bool:
        if self.state is not State.STOPPING:
            return False
        self.state = State.PROCESSING
        return True

    def on_processing_done(self) -> bool:
        """Processing ended with status 'ready' or 'failed'; the state returns to idle."""
        if self.state is not State.PROCESSING:
            return False
        self.state = State.IDLE
        return True
