import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def step(dut):
    """Advance one clock cycle and wait for registered outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_arming_latch(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.arm.value = 0
    dut.disarm.value = 0
    await RisingEdge(dut.clk)  # let initial state settle

    # --- Test 0: armed is 1 bit wide ---
    cocotb.log.info("Test 0: armed is 1 bit wide")
    assert len(dut.armed) == 1, (
        f"armed should be 1 bit wide, got {len(dut.armed)}"
    )

    # --- Test 1: armed starts low ---
    cocotb.log.info("Test 1: armed starts low")
    await step(dut)
    assert int(dut.armed.value) == 0, "armed must be low initially"

    # --- Test 2: armed stays low when neither arm nor disarm is asserted ---
    cocotb.log.info("Test 2: armed stays low when neither input is asserted")
    for _ in range(3):
        await step(dut)
        assert int(dut.armed.value) == 0, (
            "armed must stay low when arm and disarm are both low"
        )

    # --- Test 3: arm asserts armed on the next rising edge ---
    cocotb.log.info("Test 3: arm asserts armed")
    dut.arm.value = 1
    await step(dut)
    dut.arm.value = 0
    assert int(dut.armed.value) == 1, (
        "armed must go high on the cycle after arm is asserted"
    )

    # --- Test 4: armed holds high when neither input is asserted ---
    cocotb.log.info("Test 4: armed holds high when neither input is asserted")
    for _ in range(3):
        await step(dut)
        assert int(dut.armed.value) == 1, (
            "armed must remain high when arm and disarm are both low"
        )

    # --- Test 5: disarm clears armed on the next rising edge ---
    cocotb.log.info("Test 5: disarm clears armed")
    dut.disarm.value = 1
    await step(dut)
    dut.disarm.value = 0
    assert int(dut.armed.value) == 0, (
        "armed must go low on the cycle after disarm is asserted"
    )

    # --- Test 6: armed stays low after disarm is released ---
    cocotb.log.info("Test 6: armed stays low after disarm is released")
    for _ in range(3):
        await step(dut)
        assert int(dut.armed.value) == 0, (
            "armed must remain low after disarm is released and arm is not asserted"
        )

    # --- Test 7: disarm takes priority over arm when both are asserted ---
    cocotb.log.info("Test 7: disarm takes priority over arm")
    # First arm the latch
    dut.arm.value = 1
    await step(dut)
    dut.arm.value = 0
    assert int(dut.armed.value) == 1, "armed must be high before priority test"

    # Assert both simultaneously; disarm must win
    dut.arm.value = 1
    dut.disarm.value = 1
    await step(dut)
    dut.arm.value = 0
    dut.disarm.value = 0
    assert int(dut.armed.value) == 0, (
        "disarm must take priority over arm when both are asserted simultaneously"
    )

    # --- Test 8: arm works again after a disarm ---
    cocotb.log.info("Test 8: arm works again after a disarm")
    dut.arm.value = 1
    await step(dut)
    dut.arm.value = 0
    assert int(dut.armed.value) == 1, (
        "armed must be assertable again after a disarm"
    )

    # --- Test 9: arm held high for multiple cycles keeps armed high ---
    cocotb.log.info("Test 9: arm held high for multiple cycles")
    dut.disarm.value = 1  # start from disarmed state
    await step(dut)
    dut.disarm.value = 0
    assert int(dut.armed.value) == 0, "armed must be low before multi-cycle arm test"

    dut.arm.value = 1
    for _ in range(4):
        await step(dut)
        assert int(dut.armed.value) == 1, (
            "armed must remain high while arm is held high"
        )
    dut.arm.value = 0
    await step(dut)
    assert int(dut.armed.value) == 1, (
        "armed must remain high after arm is released"
    )

    # --- Test 10: disarm held high for multiple cycles keeps armed low ---
    cocotb.log.info("Test 10: disarm held high for multiple cycles")
    assert int(dut.armed.value) == 1, "armed must be high before multi-cycle disarm test"

    dut.disarm.value = 1
    for _ in range(4):
        await step(dut)
        assert int(dut.armed.value) == 0, (
            "armed must remain low while disarm is held high"
        )
    dut.disarm.value = 0
    await step(dut)
    assert int(dut.armed.value) == 0, (
        "armed must remain low after disarm is released"
    )

    # --- Test 11: disarm is synchronous — mid-cycle assertion must not clear armed ---
    cocotb.log.info("Test 11: disarm only takes effect on a clock edge")
    # State: armed=0 (from end of test 10).  Arm the latch first.
    dut.arm.value = 1
    await step(dut)
    dut.arm.value = 0
    assert int(dut.armed.value) == 1, "armed must be high before test 11"

    # Pulse disarm between clock edges; a synchronous design must ignore it.
    await Timer(3, unit="ns")   # mid-cycle (clock period is 10 ns)
    dut.disarm.value = 1
    await Timer(1, unit="ns")
    assert int(dut.armed.value) == 1, (
        "armed cleared when disarm was asserted between clock edges -- "
        "disarm must only take effect on a rising clock edge "
        "(check for 'posedge disarm' in the sensitivity list)"
    )
    dut.disarm.value = 0

    # Confirm it clears correctly when disarm is held through a clock edge.
    dut.disarm.value = 1
    await step(dut)
    dut.disarm.value = 0
    assert int(dut.armed.value) == 0, (
        "armed must clear when disarm is held through a rising clock edge"
    )
