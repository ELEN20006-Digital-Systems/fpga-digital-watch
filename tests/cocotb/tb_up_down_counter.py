import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def tick(dut):
    """Advance one clock cycle and wait for outputs to settle."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_up_down_counter(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await RisingEdge(dut.clk)  # let initial block settle

    MAX = int(dut.MAX.value)
    WIDTH = int(dut.WIDTH.value)
    cocotb.log.info(f"Testing up_down_counter with WIDTH={WIDTH}, MAX={MAX}")

    # --- count port is exactly WIDTH bits wide ---
    cocotb.log.info(f"Test 0: count is exactly {WIDTH} bits wide")
    assert len(dut.count) == WIDTH, (
        f"count should be {WIDTH} bits wide, got {len(dut.count)}"
    )

    # --- enable=0 holds count at 0 ---
    cocotb.log.info("Test 1: Enable=0 holds count at initial value")
    dut.enable.value = 0
    dut.up.value = 1
    assert int(dut.count.value) == 0, "Initial count should be 0"
    for _ in range(5):
        await tick(dut)
    assert int(dut.count.value) == 0, "Count should not change when disabled"

    # --- counts up ---
    cocotb.log.info("Test 2: Basic counting up")
    dut.enable.value = 1
    dut.up.value = 1
    await Timer(1, unit="ns")
    assert int(dut.count.value) == 0, (
        "count must not change combinationally when enable is asserted"
    )
    await tick(dut)
    assert int(dut.count.value) == 1
    await tick(dut)
    assert int(dut.count.value) == 2

    # --- counts up to MAX and wraps to 0 ---
    cocotb.log.info(f"Test 3: Count up to MAX ({MAX}) and wrap to 0")
    for _ in range(MAX - 2):
        await tick(dut)
    assert int(dut.count.value) == MAX
    await tick(dut)
    assert int(dut.count.value) == 0, f"Should wrap from {MAX} to 0"

    # --- counts down: 0 wraps to MAX ---
    cocotb.log.info(f"Test 4: Count down from 0 wraps to MAX ({MAX})")
    dut.up.value = 0
    await Timer(1, unit="ns")
    assert int(dut.count.value) == 0, (
        "count must not change combinationally when up is deasserted"
    )
    await tick(dut)
    assert int(dut.count.value) == MAX, f"Down from 0 should wrap to {MAX}"
    await tick(dut)
    assert int(dut.count.value) == MAX - 1

    # --- counts down to 0 and wraps to MAX ---
    cocotb.log.info("Test 5: Count down to 0 and wrap to MAX")
    for _ in range(MAX - 1):
        await tick(dut)
    assert int(dut.count.value) == 0
    await tick(dut)
    assert int(dut.count.value) == MAX, f"Down from 0 should wrap to {MAX}"

    # --- enable=0 holds count at different values ---
    cocotb.log.info("Test 6: Enable=0 holds count at MAX and MAX/2")

    # Already at MAX from test 5, test enable=0 holds at MAX
    assert int(dut.count.value) == MAX, f"Should be at MAX ({MAX})"
    dut.enable.value = 0
    for _ in range(5):
        await tick(dut)
    assert int(dut.count.value) == MAX, f"Enable=0 should hold at MAX ({MAX})"

    # Count down from MAX to MAX/2
    dut.enable.value = 1
    dut.up.value = 0
    await Timer(1, unit="ns")
    assert int(dut.count.value) == MAX, (
        f"count must not change combinationally when inputs change (expected {MAX})"
    )
    mid_value = MAX // 2
    steps_to_mid = MAX - mid_value
    for _ in range(steps_to_mid):
        await tick(dut)
    assert int(dut.count.value) == mid_value, f"Should be at MAX/2 ({mid_value})"

    # Test enable=0 holds at MAX/2
    dut.enable.value = 0
    for _ in range(5):
        await tick(dut)
    assert int(dut.count.value) == mid_value, (
        f"Enable=0 should hold at MAX/2 ({mid_value})"
    )
