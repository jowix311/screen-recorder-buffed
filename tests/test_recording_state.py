"""Slice 2 state rules: site-contract.md §2 and §3, content-model.md (Recording control).

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from screen_recorder_buffed.recording_state import (
    MSG_CAPTURE_ERROR,
    MSG_KEY,
    MSG_LANGUAGE,
    MSG_NO_SOURCE,
    MSG_PRIVACY,
    MSG_RETRY,
    RecordingControl,
    StartInputs,
    State,
    format_elapsed,
    is_stalled,
    start_blockers,
)

READY = StartInputs(privacy_accepted=True, has_key=True, language_selected=True, retry_running=False)


class StartConditionTests(unittest.TestCase):
    def test_all_conditions_met_means_no_blockers(self) -> None:
        self.assertEqual(start_blockers(READY), [])

    def test_blockers_are_listed_privacy_first(self) -> None:
        inputs = StartInputs(False, False, False, True)
        self.assertEqual(start_blockers(inputs), [MSG_PRIVACY, MSG_KEY, MSG_LANGUAGE, MSG_RETRY])

    def test_single_unmet_condition_gives_its_message(self) -> None:
        self.assertEqual(start_blockers(replace(READY, privacy_accepted=False)), [MSG_PRIVACY])
        self.assertEqual(start_blockers(replace(READY, has_key=False)), [MSG_KEY])
        self.assertEqual(start_blockers(replace(READY, language_selected=False)), [MSG_LANGUAGE])
        self.assertEqual(start_blockers(replace(READY, retry_running=True)), [MSG_RETRY])


class TransitionTests(unittest.TestCase):
    def test_start_moves_idle_to_recording(self) -> None:
        control = RecordingControl()
        self.assertTrue(control.request_start(READY))
        self.assertEqual(control.state, State.RECORDING)

    def test_start_is_refused_with_messages_when_blocked(self) -> None:
        control = RecordingControl()
        blocked = replace(READY, privacy_accepted=False)
        self.assertFalse(control.request_start(blocked))
        self.assertEqual(control.state, State.IDLE)
        self.assertEqual(control.messages, [MSG_PRIVACY])

    def test_missing_source_refuses_start_with_message(self) -> None:
        control = RecordingControl()
        self.assertFalse(control.request_start(READY, source_available=False))
        self.assertEqual(control.state, State.IDLE)
        self.assertEqual(control.messages, [MSG_NO_SOURCE])

    def test_full_cycle_returns_to_idle(self) -> None:
        control = RecordingControl()
        control.request_start(READY)
        self.assertTrue(control.request_stop())
        self.assertEqual(control.state, State.STOPPING)
        self.assertTrue(control.on_file_finalised())
        self.assertEqual(control.state, State.PROCESSING)
        self.assertTrue(control.on_processing_done())
        self.assertEqual(control.state, State.IDLE)

    def test_capture_error_stops_and_shows_message(self) -> None:
        control = RecordingControl()
        control.request_start(READY)
        self.assertTrue(control.on_capture_error())
        self.assertEqual(control.state, State.STOPPING)
        self.assertEqual(control.messages, [MSG_CAPTURE_ERROR])

    def test_out_of_order_transitions_are_refused(self) -> None:
        control = RecordingControl()
        self.assertFalse(control.request_stop())
        self.assertFalse(control.on_capture_error())
        self.assertFalse(control.on_file_finalised())
        self.assertFalse(control.on_processing_done())
        self.assertEqual(control.state, State.IDLE)

    def test_cannot_start_while_not_idle(self) -> None:
        control = RecordingControl()
        control.request_start(READY)
        self.assertFalse(control.request_start(READY))
        control.request_stop()
        self.assertFalse(control.request_start(READY))


class ScreenStateTests(unittest.TestCase):
    """The table in site-contract.md §2."""

    def test_button_labels(self) -> None:
        expected = {
            State.IDLE: "Start recording",
            State.RECORDING: "Stop recording",
            State.STOPPING: "Stopping…",
            State.PROCESSING: "Processing…",
        }
        for state, label in expected.items():
            control = RecordingControl(state=state)
            self.assertEqual(control.button_label(), label)

    def test_stop_is_enabled_only_while_recording(self) -> None:
        self.assertTrue(RecordingControl(State.RECORDING).button_enabled(READY))
        self.assertFalse(RecordingControl(State.STOPPING).button_enabled(READY))
        self.assertFalse(RecordingControl(State.PROCESSING).button_enabled(READY))

    def test_start_enabled_only_when_conditions_hold(self) -> None:
        self.assertTrue(RecordingControl(State.IDLE).button_enabled(READY))
        self.assertFalse(RecordingControl(State.IDLE).button_enabled(replace(READY, has_key=False)))

    def test_timer_and_indicator_visible_while_recording_or_stopping(self) -> None:
        for state in State:
            control = RecordingControl(state=state)
            visible = state in (State.RECORDING, State.STOPPING)
            self.assertEqual(control.timer_visible(), visible, state)
            self.assertEqual(control.indicator_visible(), visible, state)

    def test_library_status_mapping(self) -> None:
        self.assertEqual(RecordingControl(State.RECORDING).library_status(), "recording")
        self.assertEqual(RecordingControl(State.STOPPING).library_status(), "processing")
        self.assertEqual(RecordingControl(State.PROCESSING).library_status(), "processing")


class CaptureStallTests(unittest.TestCase):
    def test_no_data_for_five_seconds_is_a_stall(self) -> None:
        self.assertFalse(is_stalled(last_data_at=100.0, now=104.9))
        self.assertTrue(is_stalled(last_data_at=100.0, now=105.0))

    def test_fresh_data_is_not_a_stall(self) -> None:
        self.assertFalse(is_stalled(last_data_at=100.0, now=100.1))


class ElapsedFormatTests(unittest.TestCase):
    def test_format_is_hh_mm_ss(self) -> None:
        self.assertEqual(format_elapsed(0), "00:00:00")
        self.assertEqual(format_elapsed(59.9), "00:00:59")
        self.assertEqual(format_elapsed(3725), "01:02:05")

    def test_negative_clamps_to_zero(self) -> None:
        self.assertEqual(format_elapsed(-3), "00:00:00")


if __name__ == "__main__":
    unittest.main()
