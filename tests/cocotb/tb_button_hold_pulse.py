import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Must match the HOLD_CYCLES parameter passed by the test runner.
HOLD_CYCLES = 5


async def step(dut):
    """Advance one clock cycle and wait for registered outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_button_hold_pulse(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    await RisingEdge(dut.clk)  # let initial state settle

    # --- Test 0: pulse is 1 bit wide ---
    cocotb.log.info("Test 0: pulse is 1 bit wide")
    assert len(dut.pulse) == 1, f"pulse should be 1 bit wide, got {len(dut.pulse)}"

    # --- Test 1: pulse stays low while button is low ---
    cocotb.log.info("Test 1: pulse stays low while button is low")
    for _ in range(HOLD_CYCLES + 2):
        await step(dut)
        assert int(dut.pulse.value) == 0, "pulse must stay low when button is low"

    # --- Test 2: pulse stays low for the first HOLD_CYCLES-1 cycles of a hold ---
    cocotb.log.info("Test 2: pulse stays low before HOLD_CYCLES is reached")
    dut.button.value = 1
    for i in range(HOLD_CYCLES - 1):
        await step(dut)
        assert int(dut.pulse.value) == 0, (
            f"pulse must stay low before {HOLD_CYCLES} cycles are reached (cycle {i + 1})"
        )

    # --- Test 3: pulse asserts on the cycle that held first goes high ---
    cocotb.log.info("Test 3: pulse asserts on cycle HOLD_CYCLES")
    await step(dut)
    assert int(dut.pulse.value) == 1, (
        f"pulse must assert on the cycle held goes high "
        f"(after {HOLD_CYCLES} consecutive cycles of button held high)"
    )

    # --- Test 4: pulse deasserts after exactly one cycle ---
    cocotb.log.info("Test 4: pulse is high for exactly one cycle")
    await step(dut)
    assert int(dut.pulse.value) == 0, (
        "pulse must deassert after one cycle (held_d has caught up)"
    )

    # --- Test 5: pulse stays low while button remains held ---
    cocotb.log.info("Test 5: pulse stays low while button remains held")
    for _ in range(3):
        await step(dut)
        assert int(dut.pulse.value) == 0, (
            "pulse must not fire again while button remains held"
        )

    # --- Test 6: pulse does not fire when button is released ---
    # held falls on release; a falling edge does not trigger pulse.
    cocotb.log.info("Test 6: pulse does not fire when button is released")
    dut.button.value = 0
    await step(dut)
    assert int(dut.pulse.value) == 0, (
        "pulse must not fire when held falls (only rising edges produce a pulse)"
    )
    await step(dut)
    assert int(dut.pulse.value) == 0, "pulse must remain low after button is released"

    # --- Test 7: partial hold does not fire pulse ---
    cocotb.log.info("Test 7: partial hold does not fire pulse")
    dut.button.value = 1
    for _ in range(HOLD_CYCLES - 1):
        await step(dut)
    assert int(dut.pulse.value) == 0, (
        "pulse must not fire when button is released before HOLD_CYCLES"
    )
    dut.button.value = 0
    await step(dut)
    assert int(dut.pulse.value) == 0, (
        "pulse must not fire after a partial hold followed by a release"
    )

    # --- Test 8: pulse fires again after a full re-hold ---
    cocotb.log.info("Test 8: pulse fires again after a full re-hold")
    dut.button.value = 1
    for _ in range(HOLD_CYCLES):
        await step(dut)
    assert int(dut.pulse.value) == 1, (
        "pulse must assert again after a full hold following a counter reset"
    )
    await step(dut)
    assert int(dut.pulse.value) == 0, (
        "pulse must deassert after one cycle on the second hold"
    )

    # --- Test 9: pulse holds high until the next clock edge when button released immediately ---
    # This guards against a combinational held implementation: if held deasserts the instant
    # button goes low, pulse vanishes before the arming latch (or any downstream FF) can
    # capture it at the next clock edge.
    cocotb.log.info("Test 9: pulse stays high after immediate sub-cycle button release")
    dut.button.value = 0
    await step(dut)  # release and let counter reset
    dut.button.value = 1
    for _ in range(HOLD_CYCLES - 1):
        await step(dut)
    assert int(dut.pulse.value) == 0, "pulse must not fire before threshold"
    # Cross the threshold edge manually so we can release button in the same clock period.
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.pulse.value) == 1, "pulse must assert at the threshold edge"
    dut.button.value = 0  # release immediately — still within the same clock period
    await Timer(1, unit="ns")
    assert int(dut.pulse.value) == 1, (
        "pulse must stay high after immediate button release "
        "(held is registered, deasserts at the clock edge not combinationally)"
    )
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.pulse.value) == 0, "pulse must deassert at the clock edge after button release"
