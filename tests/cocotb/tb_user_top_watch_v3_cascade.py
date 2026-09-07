import cocotb
from cocotb.clock import Clock

from tb_user_top_watch_v3 import tick, tick_n, press_mode, press_dec


@cocotb.test()
async def test_cascade_blocked_in_edit_mode(dut):
    """The seconds->minutes->hours carry chain must not propagate while the
    upstream counter is in edit mode.

    Section A: seconds edit, seconds=59  -> minutes must not tick
    Section B: seconds edit, seconds=59 and minutes=59 -> hours must not tick
    Section C: minutes edit, minutes=59  -> hours must not tick as seconds
               runs freely through 59
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)

    CPS = int(dut.CYCLES_PER_SECOND.value)
    HOLD = CPS
    INC_HOLD = CPS // 2
    INC_REPEAT = CPS // 10
    INC_QUAL = INC_HOLD - INC_REPEAT + 1
    SHORT = max(2, INC_QUAL // 2)

    # -----------------------------------------------------------------------
    # Section A: seconds edit, seconds=59 -> minutes must not advance
    # -----------------------------------------------------------------------
    cocotb.log.info("Section A: minutes must not tick when editing seconds=59")

    await press_mode(dut, HOLD)  # long press -> enter edit, seconds selected
    await tick_n(dut, 3)

    # Navigate seconds to 59 by decrementing (0 wraps to 59 in one press)
    while int(dut.seconds_disp.value) != 59:
        await press_dec(dut, SHORT)
        await tick_n(dut, 3)

    minutes_snap = int(dut.minutes_disp.value)
    await tick_n(dut, 2 * CPS + 5)  # let at least two 1 Hz ticks fire
    assert int(dut.minutes_disp.value) == minutes_snap, (
        f"minutes must not advance while editing seconds=59; "
        f"started at {minutes_snap}, now {int(dut.minutes_disp.value)}"
    )

    # -----------------------------------------------------------------------
    # Section B: seconds edit, seconds=59 and minutes=59 -> hours must not advance
    # -----------------------------------------------------------------------
    cocotb.log.info("Section B: hours must not tick when editing seconds=59, minutes=59")

    # Still in seconds edit - move to minutes edit and set minutes to 59
    await press_mode(dut, 2)  # seconds -> minutes edit
    await tick_n(dut, 3)
    while int(dut.minutes_disp.value) != 59:
        await press_dec(dut, SHORT)
        await tick_n(dut, 3)

    # Exit to normal, then re-enter with seconds selected
    await press_mode(dut, 2)  # minutes -> hours edit
    await press_mode(dut, 2)  # hours -> exit
    await tick_n(dut, 3)
    await press_mode(dut, HOLD)  # long press -> re-enter, seconds selected
    await tick_n(dut, 3)

    # Navigate seconds back to 59
    while int(dut.seconds_disp.value) != 59:
        await press_dec(dut, SHORT)
        await tick_n(dut, 3)

    hours_snap = int(dut.hours_disp.value)
    await tick_n(dut, 2 * CPS + 5)
    assert int(dut.hours_disp.value) == hours_snap, (
        f"hours must not advance while editing seconds=59 with minutes=59; "
        f"started at {hours_snap}, now {int(dut.hours_disp.value)}"
    )

    # Exit seconds edit
    await press_mode(dut, 2)  # seconds -> minutes edit
    await press_mode(dut, 2)  # minutes -> hours edit
    await press_mode(dut, 2)  # hours -> exit
    await tick_n(dut, 3)

    # -----------------------------------------------------------------------
    # Section C: minutes edit, minutes=59 -> hours must not advance while
    #            seconds counts freely through 59
    # -----------------------------------------------------------------------
    cocotb.log.info("Section C: hours must not tick when editing minutes=59 (seconds running)")

    # Enter minutes edit
    await press_mode(dut, HOLD)  # long press -> seconds selected
    await press_mode(dut, 2)    # -> minutes selected
    await tick_n(dut, 3)

    # Navigate minutes to 59
    while int(dut.minutes_disp.value) != 59:
        await press_dec(dut, SHORT)
        await tick_n(dut, 3)

    hours_snap = int(dut.hours_disp.value)
    # Seconds ticks freely at 1 Hz in minutes edit mode.  Wait long enough to
    # guarantee seconds has passed through 59 at least once (worst case ~60 s).
    await tick_n(dut, 62 * CPS)
    assert int(dut.hours_disp.value) == hours_snap, (
        f"hours must not advance while editing minutes=59; "
        f"started at {hours_snap}, now {int(dut.hours_disp.value)}"
    )

    # Exit minutes edit
    await press_mode(dut, 2)  # minutes -> hours edit
    await press_mode(dut, 2)  # hours -> exit
    await tick_n(dut, 3)
