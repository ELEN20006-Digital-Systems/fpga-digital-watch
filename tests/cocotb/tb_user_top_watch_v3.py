import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


async def tick(dut):
    """Advance one clock cycle and wait for outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def tick_n(dut, n):
    """Advance n clock cycles."""
    if n <= 0:
        return
    await ClockCycles(dut.clk, n)
    await Timer(1, unit="ns")


async def press_mode(dut, cycles):
    """Hold button[3] high for `cycles` clock cycles, then release."""
    dut.button.value = dut.button.value.to_unsigned() | 0b1000
    await tick_n(dut, cycles)
    dut.button.value = dut.button.value.to_unsigned() & ~0b1000
    await tick(dut)


async def press_inc(dut, cycles):
    """Hold button[1] high for `cycles` clock cycles, then release."""
    dut.button.value = dut.button.value.to_unsigned() | 0b0010
    await tick_n(dut, cycles)
    dut.button.value = dut.button.value.to_unsigned() & ~0b0010
    await tick(dut)


async def press_dec(dut, cycles):
    """Hold button[0] high for `cycles` clock cycles, then release."""
    dut.button.value = dut.button.value.to_unsigned() | 0b0001
    await tick_n(dut, cycles)
    dut.button.value = dut.button.value.to_unsigned() & ~0b0001
    await tick(dut)


@cocotb.test()
async def test_edit_logic(dut):
    """Edit logic: inc/dec buttons adjust the selected counter in edit mode,
    auto-repeat fires on a sustained press, and timekeeping is suspended during
    editing and resumes on exit."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)

    CPS = int(dut.CYCLES_PER_SECOND.value)
    HOLD = CPS  # long-press threshold for mode selector
    INC_HOLD = CPS // 2  # hold threshold inside button_auto_repeat
    INC_REPEAT = CPS // 10  # repeat interval inside button_auto_repeat
    # Hold threshold passed to button_hold_detect inside button_auto_repeat:
    #   INC_QUAL = INC_HOLD - INC_REPEAT + 1
    # A short press must be fewer than INC_QUAL cycles to produce exactly one pulse.
    INC_QUAL = INC_HOLD - INC_REPEAT + 1
    SHORT = max(2, INC_QUAL // 2)
    cocotb.log.info(
        f"CPS={CPS}  HOLD={HOLD}  INC_HOLD={INC_HOLD}  "
        f"INC_REPEAT={INC_REPEAT}  INC_QUAL={INC_QUAL}  SHORT={SHORT}"
    )

    # -----------------------------------------------------------------------
    # Section 1: inc and dec are ignored in normal mode
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 1: inc/dec ignored in normal mode")
    await press_inc(dut, SHORT)
    await press_dec(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.seconds_disp.value) == 0, (
        "seconds must not change from inc/dec in normal mode"
    )
    assert int(dut.minutes_disp.value) == 0, (
        "minutes must not change from inc/dec in normal mode"
    )
    assert int(dut.hours_disp.value) == 0, (
        "hours must not change from inc/dec in normal mode"
    )

    # -----------------------------------------------------------------------
    # Section 2: enter seconds edit; single presses of inc and dec each
    #            move seconds by exactly one step
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 2: seconds edit - single inc and dec steps")
    await press_mode(dut, HOLD)  # long press -> enter edit, seconds selected
    await tick_n(dut, 3)

    # Capture the current seconds value: the 1 Hz tick may have fired during
    # the HOLD press (before edit_mode was asserted), advancing seconds by one.
    seconds_snap = int(dut.seconds_disp.value)

    await press_inc(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.seconds_disp.value) == (seconds_snap + 1) % 60, (
        "seconds must increment by 1 on a short inc press in seconds edit mode"
    )

    await press_dec(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.seconds_disp.value) == seconds_snap, (
        "seconds must decrement by 1 on a short dec press in seconds edit mode"
    )

    # -----------------------------------------------------------------------
    # Section 3: dec wraps seconds 0 -> 59
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 3: dec wraps seconds 0 to 59")
    # Navigate to 0 first: the 1 Hz tick may have advanced seconds during the
    # HOLD press, so we cannot assume we are already at 0.
    while int(dut.seconds_disp.value) != 0:
        await press_dec(dut, SHORT)
        await tick_n(dut, 3)
    await press_dec(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.seconds_disp.value) == 59, "seconds must wrap from 0 to 59 on dec"

    # -----------------------------------------------------------------------
    # Section 4: inc wraps seconds 59 -> 0
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 4: inc wraps seconds 59 to 0")
    await press_inc(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.seconds_disp.value) == 0, "seconds must wrap from 59 to 0 on inc"

    # -----------------------------------------------------------------------
    # Section 5: auto-repeat - exact inc counts
    # Holding for INC_HOLD + N*INC_REPEAT cycles produces exactly 2+N
    # increments: 1 from the initial rise pulse, N in-press repeats, plus
    # 1 post-release repeat at the tick() after button release.  The
    # post-release repeat occurs because count reaches 1 in restartable_rate_generator at
    # the last in-press edge, and held is still high at the tick() edge
    # before button_hold_detect captures button=0.
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 5: auto-repeat - exact inc counts")
    # Boundary: one cycle short of the hold threshold -> exactly 1, no repeat
    seconds_before = int(dut.seconds_disp.value)
    await press_inc(dut, INC_QUAL - 1)
    await tick_n(dut, 3)
    increments = (int(dut.seconds_disp.value) - seconds_before) % 60
    assert increments == 1, (
        f"holding inc for INC_QUAL-1={INC_QUAL - 1} cycles must produce "
        f"exactly 1 increment (no auto-repeat); got {increments}"
    )

    for n in range(4):
        hold = INC_HOLD + n * INC_REPEAT
        seconds_before = int(dut.seconds_disp.value)
        await press_inc(dut, hold)
        await tick_n(dut, 3)
        increments = (int(dut.seconds_disp.value) - seconds_before) % 60
        # Calculate expected pulse count using formula
        expected = 1 + max(0, (hold - INC_HOLD) // INC_REPEAT)
        assert increments == expected, (
            f"holding inc for {hold} cycles (INC_HOLD={INC_HOLD}, INC_REPEAT={INC_REPEAT}) "
            f"must produce {expected} increment(s); got {increments}"
        )
        cocotb.log.info(
            f"  inc hold={hold} cycles: {increments} increment(s) (expected {expected})"
        )

    # -----------------------------------------------------------------------
    # Section 6: auto-repeat - exact dec counts
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 6: auto-repeat - exact dec counts")
    # Boundary: one cycle short of the hold threshold -> exactly 1, no repeat
    seconds_before = int(dut.seconds_disp.value)
    await press_dec(dut, INC_QUAL - 1)
    await tick_n(dut, 3)
    decrements = (seconds_before - int(dut.seconds_disp.value)) % 60
    assert decrements == 1, (
        f"holding dec for INC_QUAL-1={INC_QUAL - 1} cycles must produce "
        f"exactly 1 decrement (no auto-repeat); got {decrements}"
    )

    for n in range(4):
        hold = INC_HOLD + n * INC_REPEAT
        seconds_before = int(dut.seconds_disp.value)
        await press_dec(dut, hold)
        await tick_n(dut, 3)
        decrements = (seconds_before - int(dut.seconds_disp.value)) % 60
        expected = 1 + max(0, (hold - INC_HOLD) // INC_REPEAT)
        assert decrements == expected, (
            f"holding dec for {hold} cycles (INC_HOLD={INC_HOLD}, INC_REPEAT={INC_REPEAT}) "
            f"must produce {expected} decrement(s); got {decrements}"
        )
        cocotb.log.info(
            f"  dec hold={hold} cycles: {decrements} decrement(s) (expected {expected})"
        )

    # -----------------------------------------------------------------------
    # Section 7: timekeeping is frozen while in seconds edit mode
    # -----------------------------------------------------------------------
    cocotb.log.info(
        "Section 7: 1 Hz tick does not advance seconds while in seconds edit mode"
    )
    frozen_seconds = int(dut.seconds_disp.value)
    await tick_n(dut, CPS + 5)  # more than one full second of clock cycles
    assert int(dut.seconds_disp.value) == frozen_seconds, (
        "seconds must not advance from the 1 Hz tick while in seconds edit mode"
    )

    # Cycle through remaining fields to exit edit mode:
    # seconds -> minutes -> hours -> normal
    await press_mode(dut, 2)
    await press_mode(dut, 2)
    await press_mode(dut, 2)
    await tick_n(dut, 3)

    # -----------------------------------------------------------------------
    # Section 8: minutes edit - inc and dec adjust minutes
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 8: minutes edit - inc and dec adjust minutes")
    await press_mode(dut, HOLD)  # long press -> seconds selected
    await press_mode(dut, 2)  # short press -> minutes selected
    await tick_n(dut, 3)

    minutes_snap = int(dut.minutes_disp.value)
    await press_inc(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.minutes_disp.value) == (minutes_snap + 1) % 60, (
        "minutes must increment by 1 when inc is pressed in minutes edit mode"
    )

    await press_dec(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.minutes_disp.value) == minutes_snap, (
        "minutes must decrement by 1 when dec is pressed in minutes edit mode"
    )

    # seconds must still tick while editing minutes
    cocotb.log.info("Section 8b: seconds continues to tick in minutes edit mode")
    seconds_before = int(dut.seconds_disp.value)
    await tick_n(dut, CPS + 5)
    ticks = (int(dut.seconds_disp.value) - seconds_before) % 60
    assert ticks >= 1, (
        f"seconds must advance by at least 1 within CPS+5 cycles while in minutes "
        f"edit mode; advanced by {ticks}"
    )

    # -----------------------------------------------------------------------
    # Section 9: hours edit - inc and dec adjust hours
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 9: hours edit - inc and dec adjust hours")
    await press_mode(dut, 2)  # short press -> hours selected
    await tick_n(dut, 3)

    hours_snap = int(dut.hours_disp.value)
    await press_inc(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.hours_disp.value) == (hours_snap + 1) % 24, (
        "hours must increment by 1 when inc is pressed in hours edit mode"
    )

    await press_dec(dut, SHORT)
    await tick_n(dut, 3)
    assert int(dut.hours_disp.value) == hours_snap, (
        "hours must decrement by 1 when dec is pressed in hours edit mode"
    )

    # seconds must still tick while editing hours
    cocotb.log.info("Section 9b: seconds continues to tick in hours edit mode")
    seconds_before = int(dut.seconds_disp.value)
    await tick_n(dut, CPS + 5)
    ticks = (int(dut.seconds_disp.value) - seconds_before) % 60
    assert ticks >= 1, (
        f"seconds must advance by at least 1 within CPS+5 cycles while in hours "
        f"edit mode; advanced by {ticks}"
    )

    # Exit edit mode
    await press_mode(dut, 2)
    await tick_n(dut, 3)

    # -----------------------------------------------------------------------
    # Section 10: timekeeping resumes after exiting edit mode
    # -----------------------------------------------------------------------
    # The restartable_rate_generator is at an unknown phase on exit, so wait 2*CPS+2 cycles
    # to guarantee at least one 1 Hz tick regardless of phase.
    cocotb.log.info(
        "Section 10: seconds advances from 1 Hz tick after exiting edit mode"
    )
    seconds_at_exit = int(dut.seconds_disp.value)
    await tick_n(dut, 2 * CPS + 2)
    ticks = (int(dut.seconds_disp.value) - seconds_at_exit) % 60
    assert ticks >= 1, (
        f"seconds must advance by at least 1 within 2*CPS+2 cycles after exiting "
        f"edit mode; advanced by {ticks}"
    )
