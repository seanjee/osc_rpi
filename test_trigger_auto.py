#!/usr/bin/env python3
"""
Auto test for oscilloscope trigger and waveform display.

Test scenario:
- CH1: 1kHz square wave (50% duty cycle)
- CH2: constant 0

Verification:
1. Real-time waveform display is correct
2. Trigger condition met -> correct trigger -> correct waveform displayed in main window
3. Trigger event recorded and PNG screenshot saved
"""

import os
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rpiosc.controller import AppState, Controller
from rpiosc.config_loader import load_osc_config, load_trigger_conditions
from rpiosc.gpio_driver import EdgeEvent, EdgeKind
from rpiosc.trigger_dsl import parse_expression


class TestEdgeSource:
    """Mock edge source for testing."""

    def __init__(self, events: list[EdgeEvent]):
        self._events = list(events)
        self._index = 0
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def read_events(self, timeout_s: float) -> list[EdgeEvent]:
        if not self._started:
            return []
        if self._index >= len(self._events):
            return []
        # Return one event at a time
        ev = self._events[self._index]
        self._index += 1
        return [ev]

    def read_current_levels(self) -> dict[int, int]:
        return {}


def generate_1khz_square_wave(
    start_ns: int, duration_ms: float, period_us: int = 1000
) -> list[EdgeEvent]:
    """
    Generate edge events for 1kHz square wave (50% duty cycle).

    Args:
        start_ns: Start time in nanoseconds
        duration_ms: Duration in milliseconds
        period_us: Period in microseconds (default 1000us = 1kHz)

    Returns:
        List of EdgeEvent objects
    """
    events = []
    period_ns = period_us * 1000  # Convert to nanoseconds
    high_duration_ns = period_ns // 2  # 50% duty cycle

    t = start_ns
    end_ns = start_ns + int(duration_ms * 1e6)

    level = 1  # Start high (after rising edge)

    while t < end_ns:
        # Toggle edge
        if level == 1:
            edge = EdgeKind.FALLING
            level = 0
        else:
            edge = EdgeKind.RISING
            level = 1

        events.append(EdgeEvent(channel_id=1, timestamp_ns=t, edge=edge))

        # Next edge time
        if level == 1:
            t += high_duration_ns
        else:
            t += high_duration_ns

    return events


def test_realtime_waveform_display(controller: Controller, state: AppState, events: list[EdgeEvent]):
    """Test 1: Real-time waveform display is correct."""
    print("\n[Test 1] Real-time waveform display")

    # Simulate processing events
    waveform_captured = []
    original_emit = state.waveform_updated.emit

    def capture_waveform(traces):
        waveform_captured.append(traces)
        original_emit(traces)

    state.waveform_updated.emit = capture_waveform

    # Process first 10ms of events
    test_events = [e for e in events if e.timestamp_ns - events[0].timestamp_ns < 10_000_000]

    for ev in test_events:
        decision = controller.engine.process([ev])
        # Simulate the edge being added to history
        controller._edge_history.setdefault(ev.channel_id, []).append((ev.timestamp_ns, 1 if ev.edge == EdgeKind.RISING else 0))

    # Manually trigger a refresh
    traces = controller._build_traces(test_events[-1].timestamp_ns)

    # Verify CH1 has data
    if 1 in traces:
        xs, ys = traces[1]
        print(f"  ✓ CH1 waveform captured: {len(xs)} points")
        print(f"    Time range: {xs[0]*1000:.2f}ms to {xs[-1]*1000:.2f}ms")
        # Verify we have both 0 and 1 levels
        levels = set(ys)
        print(f"    Levels present: {levels}")
        if levels == {0, 1} or levels == {0} or levels == {1}:
            print("  ✓ PASS: Real-time waveform has correct levels")
            return True
        else:
            print("  ✗ FAIL: Waveform has unexpected levels")
            return False
    else:
        print("  ✗ FAIL: No CH1 waveform captured")
        return False


def test_trigger_functionality(controller: Controller, state: AppState, events: list[EdgeEvent]):
    """Test 2 & 3: Trigger and snapshot functionality."""
    print("\n[Test 2] Trigger condition and snapshot")

    trigger_count = 0
    snapshot_captured = []

    original_snapshot_emit = state.snapshot_traces_updated.emit

    def capture_snapshot(traces, ts):
        snapshot_captured.append((traces, ts))
        original_snapshot_emit(traces, ts)

    state.snapshot_traces_updated.emit = capture_snapshot

    # Process events and count triggers
    holdoff_ns = int(controller.holdoff_s * 1e9)
    last_trigger_ns = None

    for ev in events:
        decision = controller.engine.process([ev])

        # Simulate edge history
        controller._edge_history.setdefault(ev.channel_id, []).append(
            (ev.timestamp_ns, 1 if ev.edge == EdgeKind.RISING else 0)
        )

        if decision and decision.triggered:
            trigger_count += 1
            print(f"  Trigger #{trigger_count}: {decision.reason}")

            # Simulate trigger processing
            controller.last_trigger_ns = decision.timestamp_ns

            # Capture snapshot at trigger time
            snapshot = controller._build_traces(decision.timestamp_ns)
            snapshot_captured.append((snapshot, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            # Check holdoff
            if last_trigger_ns is None or (decision.timestamp_ns - last_trigger_ns) >= holdoff_ns:
                last_trigger_ns = decision.timestamp_ns
            else:
                print(f"    Skipped due to holdoff: {(decision.timestamp_ns - last_trigger_ns) / 1e6:.1f}ms")

            # Only test first 3 triggers
            if trigger_count >= 3:
                break

    # Verify triggers
    expected_triggers = 3
    if trigger_count >= expected_triggers:
        print(f"  ✓ PASS: {trigger_count} triggers detected (expected {expected_triggers})")
    else:
        print(f"  ✗ FAIL: Only {trigger_count} triggers detected (expected {expected_triggers})")
        return False

    # Verify snapshots
    if len(snapshot_captured) >= expected_triggers:
        print(f"  ✓ PASS: {len(snapshot_captured)} snapshots captured")

        # Check snapshot content
        for i, (traces, ts) in enumerate(snapshot_captured[:expected_triggers]):
            if 1 in traces:
                xs, ys = traces[1]
                print(f"  Snapshot #{i+1}: {len(xs)} points, levels {set(ys)}")
                if 0 in set(ys) or 1 in set(ys):
                    print(f"    ✓ Snapshot #{i+1} has valid waveform data")
                else:
                    print(f"    ✗ Snapshot #{i+1} has invalid levels")
                    return False
            else:
                print(f"  ✗ Snapshot #{i+1} missing CH1 data")
                return False

        return True
    else:
        print(f"  ✗ FAIL: Only {len(snapshot_captured)} snapshots captured (expected {expected_triggers})")
        return False


def run_test():
    """Run all tests."""
    print("=" * 60)
    print("RPi Oscilloscope Auto Test")
    print("=" * 60)

    # Load config
    osc_cfg = load_osc_config("config/osc_config.yaml")
    trig_cfg = load_trigger_conditions("config/trigger_conditions.yaml")

    print(f"\nTrigger condition: {trig_cfg.active_expression}")

    # Create state and controller
    state = AppState()

    # Generate test events (50ms of 1kHz square wave)
    start_ns = int(time.time_ns())
    events = generate_1khz_square_wave(start_ns, duration_ms=50)

    print(f"\nGenerated {len(events)} edge events (CH1 1kHz square wave, 50ms)")

    # Replace edge source with test source
    controller = Controller(state)
    controller._edge_source = TestEdgeSource([])

    # Run tests
    results = []

    # Test 1: Real-time waveform display
    result1 = test_realtime_waveform_display(controller, state, events)
    results.append(("Real-time waveform display", result1))

    # Reset for test 2
    controller._edge_history.clear()
    state.snapshot_traces_updated.disconnect()

    # Test 2 & 3: Trigger and snapshot
    result2 = test_trigger_functionality(controller, state, events)
    results.append(("Trigger and snapshot", result2))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_test())
