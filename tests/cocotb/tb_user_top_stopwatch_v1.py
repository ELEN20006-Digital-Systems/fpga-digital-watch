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


async def press(dut, bit):
    """Single button press: raise button[bit] for one cycle then release."""
    dut.button.value = 1 << bit
    await tick(dut)
    dut.button.value = 0
    await tick(dut)


@cocotb.test()
async def test_stopwatch(dut):
    """Stopwatch: initial state, start/stop, lap/resume, and reset."""

    # Without this, FSM will contain unknown values
    dut.button.value = 0
    await Timer(1, unit="ns")

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    dut.sw.value = 0
    await tick(dut)

    CPS = int(dut.CYCLES_PER_SECOND.value)
    CSTICK = CPS // 100  # clock cycles per centisecond tick

    # -----------------------------------------------------------------------
    # Section 1: outputs defined, initial display is 00:00:00, blanks are 0
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 1: initial state is 00:00:00 with no blanking")
    assert dut.seconds_disp.value.is_resolvable, "seconds_disp must be defined"
    assert dut.minutes_disp.value.is_resolvable, "minutes_disp must be defined"
    assert dut.hours_disp.value.is_resolvable, "hours_disp must be defined"
    assert int(dut.seconds_disp.value) == 0, "seconds_disp must start at 0"
    assert int(dut.minutes_disp.value) == 0, "minutes_disp must start at 0"
    assert int(dut.hours_disp.value) == 0, "hours_disp must start at 0"
    assert int(dut.blank_hours.value) == 0, "blank_hours must be 0"
    assert int(dut.blank_minutes.value) == 0, "blank_minutes must be 0"
    assert int(dut.blank_seconds.value) == 0, "blank_seconds must be 0"

    # -----------------------------------------------------------------------
    # Section 2: counter advances after start button is pressed (button[0])
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 2: counter advances after start")
    await press(dut, 0)  # start/stop -> start
    cs_after_start = int(dut.seconds_disp.value)
    await tick_n(dut, 4 * CSTICK)
    assert int(dut.seconds_disp.value) > cs_after_start, (
        "seconds_disp must increment while running"
    )

    # -----------------------------------------------------------------------
    # Section 3: counter freezes after stop button is pressed
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 3: counter freezes after stop")
    await press(dut, 0)  # start/stop -> stop
    cs_stopped = int(dut.seconds_disp.value)
    await tick_n(dut, 4 * CSTICK)
    assert int(dut.seconds_disp.value) == cs_stopped, (
        "seconds_disp must not change while stopped"
    )

    # -----------------------------------------------------------------------
    # Section 4: lap button (button[1]) freezes the display while the
    # counter keeps running underneath
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 4: lap button freezes the display")
    await press(dut, 0)  # start again
    await tick_n(dut, 4 * CSTICK)
    cs_at_lap = int(dut.seconds_disp.value)
    await press(dut, 1)  # lap -> freeze display
    await tick_n(dut, 8 * CSTICK)  # counter keeps running; display frozen
    assert int(dut.seconds_disp.value) == cs_at_lap, (
        "seconds_disp must remain at the lap value while hold is active"
    )

    # -----------------------------------------------------------------------
    # Section 5: second lap press resumes the live counter display
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 5: second lap press resumes live display")
    await press(dut, 1)  # release lap
    # The counter has been running throughout the hold, so the live value
    # must now be strictly greater than the frozen lap value.
    assert int(dut.seconds_disp.value) > cs_at_lap, (
        "seconds_disp must show a value greater than the frozen lap value after resuming"
    )

    # -----------------------------------------------------------------------
    # Section 6: pressing lap while stopped (and not in lap hold) resets
    # the counter to zero
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 6: lap while stopped resets the counter")
    await press(dut, 0)  # stop
    await tick_n(dut, 2)
    await press(dut, 1)  # lap while stopped -> reset
    await tick_n(dut, 2)
    assert int(dut.seconds_disp.value) == 0, "seconds_disp must be 0 after reset"
    assert int(dut.minutes_disp.value) == 0, "minutes_disp must be 0 after reset"
    assert int(dut.hours_disp.value) == 0, "hours_disp must be 0 after reset"

    # -----------------------------------------------------------------------
    # Section 7: counter advances after CSTICKS cycles after pressing start
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 7: correct delay after pressing start")
    await press(dut, 0)  # start - consumes 1 cycle
    assert int(dut.seconds_disp.value) == 0, "timer incremented too soon"
    await tick_n(dut, CSTICK - 2)
    assert int(dut.seconds_disp.value) == 0, "timer incremented too soon"
    await tick(dut)
    assert int(dut.seconds_disp.value) == 1, "timer incremented too late"

    # -----------------------------------------------------------------------
    # Section 8: check start button goes through rising edge detector
    # Holding the button after the first rising edge must not toggle the FSM
    # again — verified by confirming the display stays frozen for 2 full
    # centisecond periods while the button remains high.
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 8: rising edge detector used on start")
    dut.button.value = 1
    await tick(dut)  # first rising edge -> stop
    cs_held = int(dut.seconds_disp.value)
    await tick_n(dut, 2 * CSTICK)  # hold button for 2 centisecond periods
    assert int(dut.seconds_disp.value) == cs_held, (
        "timer must stay stopped while button is held (rising edge detector not working)"
    )
    dut.button.value = 0
    await tick(dut)

    # -----------------------------------------------------------------------
    # Section 9: check lap button goes through rising edge detector
    # After the first rising edge engages lap hold, the display must remain
    # frozen for several centisecond periods even though the counter advances.
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 9: rising edge detector used on lap")
    await press(dut, 0)  # start
    await tick_n(dut, 2 * CSTICK)  # let counter advance
    lap_display = int(dut.seconds_disp.value)
    dut.button.value = 2  # hold button[1] high — first rising edge -> lap hold on
    await tick(dut)
    await tick_n(dut, 4 * CSTICK)  # counter advances; display must stay frozen
    assert int(dut.seconds_disp.value) == lap_display, (
        "display must stay frozen while lap button is held (rising edge detector not working)"
    )
    dut.button.value = 0
    await tick(dut)
