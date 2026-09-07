import pytest
from conftest import rtl_exists

SOURCES = [
    "up_down_counter.sv",
    "restartable_rate_generator.sv",
    "editable_counter.sv",
    "rising_edge_detector.sv",
    "button_hold_detect.sv",
    "button_hold_pulse.sv",
    "button_auto_repeat.sv",
    "arming_latch.sv",
    "mod_n_counter.sv",
    "edit_mode_selector.sv",
    "pwm_generator.sv",
    "user_top_watch_v4.sv",
]

# CYCLES_PER_SECOND=20 gives:
#   Mode selector HOLD        = 20 cycles
#   Inc/dec HOLD threshold    = 10 cycles  (CPS // 2)
#   Inc/dec REPEAT interval   =  2 cycles  (CPS // 10)
#   Inc/dec QUAL threshold    =  9 cycles  (HOLD - REPEAT + 1)
#   Short press (< QUAL)      =  4 cycles  (QUAL // 2)
CYCLES_PER_SECOND = 20

skip = pytest.mark.skipif(
    not rtl_exists("user_top_watch_v4.sv"),
    reason="user_top_watch_v4 module not implemented yet",
)


@skip
def test_user_top_watch_v4_timekeeping(cocotb_runner):
    """Timekeeping feature: seconds/minutes/hours counting and rollovers."""
    cocotb_runner(
        top="user_top_watch_v4",
        sources=SOURCES,
        test_module="tb_user_top_watch_v1",
        parameters={"CYCLES_PER_SECOND": CYCLES_PER_SECOND},
    )


@skip
def test_user_top_watch_v4_mode_selection(cocotb_runner):
    """Mode selection feature: long press, field cycling, PWM flashing."""
    cocotb_runner(
        top="user_top_watch_v4",
        sources=SOURCES,
        test_module="tb_user_top_watch_v2",
        parameters={"CYCLES_PER_SECOND": CYCLES_PER_SECOND},
    )


@skip
def test_user_top_watch_v4_edit_logic(cocotb_runner):
    """Edit logic: inc/dec buttons adjust the selected counter; auto-repeat fires
    on a sustained press; timekeeping pauses during editing and resumes on exit."""
    cocotb_runner(
        top="user_top_watch_v4",
        sources=SOURCES,
        test_module="tb_user_top_watch_v3",
        parameters={"CYCLES_PER_SECOND": CYCLES_PER_SECOND},
    )


@skip
def test_user_top_watch_v4_cascade_blocked(cocotb_runner):
    """Carry chain must be suppressed when the upstream counter is in edit mode."""
    cocotb_runner(
        top="user_top_watch_v4",
        sources=SOURCES,
        test_module="tb_user_top_watch_v3_cascade",
        parameters={"CYCLES_PER_SECOND": CYCLES_PER_SECOND},
    )


@skip
def test_divider_reset_on_exit_hours_edit(cocotb_runner):
    """Divider reset: clock divider resets to zero when exiting hours edit."""
    cocotb_runner(
        top="user_top_watch_v4",
        sources=SOURCES,
        test_module="tb_user_top_watch_v4",
        parameters={"CYCLES_PER_SECOND": CYCLES_PER_SECOND},
    )
