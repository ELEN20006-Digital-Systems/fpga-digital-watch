import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Must match the HOLD_CYCLES parameter passed by the test runner.
# 3 = 2^2 - 1: the counter target equals the highest representable value (all
# bits high), which is the edge case for saturation and counter-width logic.
HOLD_CYCLES = 3


async def step(dut):
    """Advance one clock cycle and wait for registered outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_button_hold_detect(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.button.value = 0
    await RisingEdge(dut.clk)  # let initial state settle

    # --- Test 0: held is 1 bit wide ---
    cocotb.log.info("Test 0: held is 1 bit wide")
    assert len(dut.held) == 1, (
        f"held should be 1 bit wide, got {len(dut.held)}"
    )

    # --- Test 1: held stays low while button is low ---
    cocotb.log.info("Test 1: held stays low while button is low")
    for _ in range(HOLD_CYCLES + 2):
        await step(dut)
        assert int(dut.held.value) == 0, (
            "held must stay low when button is low"
        )

    # --- Test 2: held stays low for the first HOLD_CYCLES-1 cycles of a hold ---
    cocotb.log.info("Test 2: held stays low before HOLD_CYCLES is reached")
    dut.button.value = 1
    for i in range(HOLD_CYCLES - 1):
        await step(dut)
        assert int(dut.held.value) == 0, (
            f"held must stay low before {HOLD_CYCLES} cycles are reached "
            f"(cycle {i + 1})"
        )

    # --- Test 3: held goes high after exactly HOLD_CYCLES cycles ---
    cocotb.log.info("Test 3: held goes high after exactly HOLD_CYCLES cycles")
    await step(dut)
    assert int(dut.held.value) == 1, (
        f"held must go high after {HOLD_CYCLES} consecutive cycles of button held high"
    )

    # --- Test 4: held stays high while button remains held ---
    cocotb.log.info("Test 4: held stays high while button remains held")
    for _ in range(3):
        await step(dut)
        assert int(dut.held.value) == 1, (
            "held must stay high while button remains held"
        )

    # --- Test 5: held deasserts when button is released ---
    cocotb.log.info("Test 5: held deasserts when button is released")
    dut.button.value = 0
    await Timer(1, unit="ns")  # settle combinational logic, still before next clock edge
    assert int(dut.held.value) == 1, (
        "held must still be high immediately after button release "
        "(deasserts at the clock edge, not combinationally)"
    )
    await step(dut)
    assert int(dut.held.value) == 0, (
        "held must deassert on the cycle after button is released"
    )
    await step(dut)
    assert int(dut.held.value) == 0, (
        "held must remain low while button stays low"
    )

    # --- Test 6: a partial hold that is interrupted does not assert held ---
    cocotb.log.info("Test 6: partial hold does not assert held")
    dut.button.value = 1
    for _ in range(HOLD_CYCLES - 1):
        await step(dut)
    assert int(dut.held.value) == 0, (
        "held must not assert when button has been held for fewer than HOLD_CYCLES cycles"
    )
    dut.button.value = 0
    await step(dut)
    assert int(dut.held.value) == 0, (
        "held must not assert after a partial hold followed by a release"
    )

    # --- Test 7: counter resets on release; a full hold is required again ---
    cocotb.log.info("Test 7: counter resets on release; full hold required again")
    dut.button.value = 1
    for _ in range(HOLD_CYCLES):
        await step(dut)
    assert int(dut.held.value) == 1, (
        "held must assert again after a full hold following a counter reset"
    )
