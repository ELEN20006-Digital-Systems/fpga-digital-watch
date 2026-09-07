import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def step(dut):
    """Advance one clock cycle and wait for registered outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def pulse_tick(dut):
    """Assert tick for one clock cycle then deassert."""
    dut.tick.value = 1
    await step(dut)
    dut.tick.value = 0


@cocotb.test()
async def test_editable_counter(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.tick.value = 0
    dut.edit_mode.value = 0
    dut.inc.value = 0
    dut.dec.value = 0
    await RisingEdge(dut.clk)  # let initial state settle

    # --- Test 0: count is WIDTH bits wide ---
    cocotb.log.info("Test 0: count is WIDTH bits wide")
    width = int(dut.WIDTH.value)
    assert len(dut.count) == width, (
        f"count should be {width} bits wide, got {len(dut.count)}"
    )

    # --- Test 1: count starts at zero ---
    cocotb.log.info("Test 1: count starts at zero")
    await step(dut)
    assert int(dut.count.value) == 0, "count must be zero initially"

    # --- Test 2: count holds in tick mode with no tick ---
    cocotb.log.info("Test 2: count holds with no tick in tick mode")
    for _ in range(3):
        await step(dut)
        assert int(dut.count.value) == 0, "count must not advance without a tick"

    # --- Test 3: count increments on each tick and wraps at N ---
    cocotb.log.info("Test 3: count increments on tick and wraps at N")
    n = int(dut.N.value)
    for expected in range(1, n):
        await pulse_tick(dut)
        assert int(dut.count.value) == expected, (
            f"expected count {expected} after tick, got {int(dut.count.value)}"
        )
    await pulse_tick(dut)
    assert int(dut.count.value) == 0, f"count must wrap from {n - 1} to 0"

    # --- Test 4: inc is ignored in tick mode ---
    cocotb.log.info("Test 4: inc is ignored when edit_mode is low")
    dut.inc.value = 1
    for _ in range(4):
        await step(dut)
        assert int(dut.count.value) == 0, (
            "count must not advance on inc when edit_mode is low"
        )
    await pulse_tick(dut)
    assert int(dut.count.value) == 1, (
        "count must still increment on tick even when inc is held"
    )
    dut.inc.value = 0

    # --- Test 5: dec is ignored in tick mode ---
    cocotb.log.info("Test 5: dec is ignored when edit_mode is low")
    dut.dec.value = 1
    for _ in range(4):
        await step(dut)
        assert int(dut.count.value) == 1, (
            "count must not change on dec when edit_mode is low"
        )
    await pulse_tick(dut)
    assert int(dut.count.value) == 2, (
        "count must still increment on tick even when dec is held"
    )
    dut.dec.value = 0

    # --- Test 6: tick is ignored in edit mode ---
    cocotb.log.info("Test 6: tick is ignored when edit_mode is high")
    dut.edit_mode.value = 1
    held = int(dut.count.value)
    for _ in range(4):
        await pulse_tick(dut)
        assert int(dut.count.value) == held, (
            "count must not change on tick when edit_mode is high and inc/dec are low"
        )
    dut.edit_mode.value = 0

    # --- Test 7: edit mode inc counts up each cycle and wraps at N ---
    cocotb.log.info("Test 7: edit mode inc counts up each cycle and wraps at N")
    dut.edit_mode.value = 1
    start = int(dut.count.value)
    dut.inc.value = 1
    await Timer(1, unit="ns")
    assert int(dut.count.value) == start, (
        "count must not change combinationally when inc is asserted"
    )
    for i in range(1, n + 1):
        await step(dut)
        expected = (start + i) % n
        assert int(dut.count.value) == expected, (
            f"expected count {expected} after {i} inc cycles, got {int(dut.count.value)}"
        )
    dut.inc.value = 0

    # --- Test 8: edit mode dec counts down each cycle and wraps 0 -> N-1 ---
    cocotb.log.info("Test 8: edit mode dec counts down each cycle and wraps 0 to N-1")
    start = int(dut.count.value)
    dut.dec.value = 1
    await Timer(1, unit="ns")
    assert int(dut.count.value) == start, (
        "count must not change combinationally when dec is asserted"
    )
    for i in range(1, n + 1):
        await step(dut)
        expected = (start - i) % n
        assert int(dut.count.value) == expected, (
            f"expected count {expected} after {i} dec cycles, got {int(dut.count.value)}"
        )
    dut.dec.value = 0

    # --- Test 9: inc and dec together hold count in edit mode ---
    cocotb.log.info("Test 9: inc and dec together hold count in edit mode")
    held = int(dut.count.value)
    dut.inc.value = 1
    dut.dec.value = 1
    await Timer(1, unit="ns")
    assert int(dut.count.value) == held, (
        "count must not change combinationally when inc and dec are both asserted"
    )
    for _ in range(5):
        await step(dut)
        assert int(dut.count.value) == held, (
            "count must not change when both inc and dec are high"
        )
    dut.inc.value = 0
    dut.dec.value = 0
    dut.edit_mode.value = 0
