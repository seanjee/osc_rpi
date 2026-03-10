# RPi Oscilloscope Bug Fixes and Testing

## Problems Identified

### 1. CH1 上升沿触发多次脉冲 (Rising edge triggers multiple times)

**Root Cause**: The trigger engine's `_evaluate` method was checking if an edge had ever been seen in history, not whether it was just seen in the current batch. This could cause multiple triggers for the same edge across different processing cycles.

**Fix**: Modified `process()` and `_evaluate()` methods to use batch-based edge tracking:
- `_edges_seen_this_batch` now tracks edges only in the current event batch
- `_evaluate()` checks if the edge was in `new_edges` (current batch) rather than in history
- This ensures each edge event only triggers once per occurrence

**Files Changed**:
- `src/rpiosc/trigger_engine.py`: Lines 74-102, 162-227

### 2. 触发后抓取的波形没有CH2变化 (Waveform missing CH2 changes)

**Root Cause**: The trigger timestamp was using `time.time_ns()` (current time) rather than the actual edge event timestamp that caused the trigger. This misaligned the time window, causing valid edge events to be filtered out.

**Fix**: Modified `_fire()` and `_get_trigger_timestamp()` to:
- Use the actual edge event timestamp from `_last_edge_ns_by_ch`
- For "Both Edges", use the most recent edge timestamp
- Ensure the snapshot time window is aligned with the actual trigger event

**Files Changed**:
- `src/rpiosc/trigger_engine.py`: Lines 104-125
- `src/rpiosc/controller.py`: Line 286

### 3. 主窗口无波形显示 (No waveform in main window)

**Root Cause**: Using `stepMode="right"` with edge events creates near-vertical lines that are hard to see.

**Fix**:
- Changed from `stepMode="right"` to `connect="finite"`
- Increased line width from 1 to 2
- This creates clearer visual step transitions

**Files Changed**:
- `src/rpiosc/app.py`: Lines 43-48, 168-173

### 4. CH1双边沿触发，下降沿不触发 (BOTH edges doesn't trigger on falling)

**Root Cause**: The `_edge_to_kind` helper function returned `EdgeKind.RISING` as default for `Edge.BOTH`, causing the evaluation to only check for rising edges.

**Fix**: Modified `_evaluate()` to:
- Check both RISING and FALLING edges separately for `Edge.BOTH`
- Updated `WithinAfter` evaluation to handle BOTH edges correctly

**Files Changed**:
- `src/rpiosc/trigger_engine.py`: Lines 162-168, 183-211

## Testing

### Unit Tests (`test_trigger_engine_unit.py`)

Created comprehensive unit tests for trigger engine:

1. **BOTH Edges Trigger**: Verifies that CH1 Both Edges triggers on both rising and falling edges
2. **Single Edge Not Repeated**: Verifies that the same edge event in one batch only triggers once
3. **FALLING Edge Trigger**: Verifies that falling edge triggers correctly
4. **Complex Trigger Condition**: Verifies AND + WithinAfter timing logic

All tests pass:
```
============================================================
Test Summary
============================================================
✓ PASS: BOTH Edges Trigger
✓ PASS: Single Edge Not Repeated
✓ PASS: FALLING Edge Trigger
✓ PASS: Complex Trigger Condition

Total: 4/4 tests passed

🎉 All tests passed!
```

### Manual Testing Procedure

To verify the fixes manually with real hardware:

1. **Test Setup**:
   - CH1: Connect 1kHz square wave signal
   - CH2: Connect to ground (constant 0)
   - Trigger condition: "CH1 Both Edges"

2. **Verify Real-time Waveform**:
   - Start the application
   - Observe left-top (main) window
   - Should see CH1 yellow waveform showing square wave
   - Should see CH2 green flat line at 0 (with offset)

3. **Verify Trigger**:
   - Monitor right-bottom trigger log
   - Should see trigger events for both rising and falling edges
   - Each trigger should be spaced by holdoff time (1ms default)
   - Expected: ~1 trigger per holdoff period

4. **Verify Snapshot**:
   - When trigger occurs, check right-top (snapshot) window
   - Should show waveform at trigger time
   - CH1 should show edge clearly
   - If CH2 changes within time window, should also be visible

5. **Verify PNG Screenshots**:
   - Check `screenshots/` directory
   - Should see `Trig_*.png` files for each trigger
   - Images should capture the main window at trigger time

## Test with Simulated Data

The unit test file can be run to verify trigger logic without hardware:

```bash
python3 test_trigger_engine_unit.py
```

This simulates:
- CH1 1kHz square wave (50% duty cycle)
- Various trigger conditions
- Validates trigger counting and timing

## Configuration

Current settings in `config/trigger_conditions.yaml`:
```yaml
active_condition:
  name: "CH1 Any Edge"
  expression: "CH1 Both Edges"
```

Holdoff setting in `config/osc_config.yaml`:
```yaml
trigger:
  default_holdoff: 0.001  # 1ms
```

## Expected Behavior

With CH1 Both Edges and 1ms holdoff:
- 1kHz square wave = 1000 cycles/second
- Each cycle = 1ms = 1 rising + 1 falling edge
- With 1ms holdoff, expect ~1 trigger per holdoff period
- Trigger will alternate between rising and falling edges (whichever occurs first after holdoff expires)

## Notes

- The trigger engine now uses batch-based edge detection
- Edges are only consumed after a successful trigger
- Holdoff prevents re-triggering within specified time
- Timestamps are now aligned with actual edge events, not current system time
