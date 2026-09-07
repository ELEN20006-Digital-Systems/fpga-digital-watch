import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

HEX_SIGNALS = ["HEX5", "HEX4", "HEX3", "HEX2", "HEX1", "HEX0"]

# Active-high segment encoding [g,f,e,d,c,b,a]; DE1-SoC uses active-low.
_ACTIVE_HIGH = {
    0: 0b0111111,
    1: 0b0000110,
    2: 0b1011011,
    3: 0b1001111,
    4: 0b1100110,
    5: 0b1101101,
    6: 0b1111101,
    7: 0b0000111,
    8: 0b1111111,
    9: 0b1101111,
}
_SEG_MASK = 0b1111111


def seg(digit):
    """Expected active-low segment value for a decimal digit 0-9."""
    return (~_ACTIVE_HIGH[digit]) & _SEG_MASK


async def tick(dut):
    """Advance one clock cycle and wait for outputs to settle."""
    await RisingEdge(dut.CLOCK_50)
    await Timer(1, unit="ns")


async def tick_n(dut, n):
    """Advance n clock cycles."""
    if n <= 0:
        return
    await ClockCycles(dut.CLOCK_50, n)
    await Timer(1, unit="ns")


def hex_snapshot(dut):
    """Return a tuple of current HEX output values."""
    return tuple(int(getattr(dut, s).value) for s in HEX_SIGNALS)


def all_defined(dut):
    """Return True if every HEX output is fully resolved (no X or Z bits)."""
    return all(getattr(dut, s).value.is_resolvable for s in HEX_SIGNALS)


@cocotb.test()
async def test_top_time_display_v1(dut):
    cocotb.start_soon(Clock(dut.CLOCK_50, 20, unit="ns").start())
    dut.SW.value = 0b00  # slow rate: enable stays low for millions of cycles
    await RisingEdge(dut.CLOCK_50)  # let initial block settle

    # --- SW=2'b11 (50 MHz): enable is high every cycle, counter advances ---
    cocotb.log.info("Test 1: SW=2'b11 --- HEX outputs are defined and counter advances")
    dut.SW.value = 0b11
    await tick(dut)
    assert all_defined(dut), "HEX outputs must have no undefined bits with SW=2'b11"
    snap_initial = hex_snapshot(dut)

    # After 65 cycles the seconds have rolled over (0..59 -> 0) and minutes=1;
    # HEX0, HEX1, and HEX2 must all differ from their initial values.
    await tick_n(dut, 65)
    assert all_defined(dut), "HEX outputs must remain defined after counting"
    snap_after = hex_snapshot(dut)
    assert snap_after != snap_initial, "HEX outputs must change when SW=2'b11"

    # State here: s=6, m=1, h=0  (1 + 65 ticks of SW=2'b11)

    # --- All three slow SW positions hold the counter ---
    # Each restartable_rate_generator needs millions of cycles to tick; none will fire
    # in 6 cycles.  This also verifies SW=2'b01 and 2'b10 do not
    # accidentally connect to the 50 MHz (always-enable) path.
    cocotb.log.info("Test 2: all slow SW positions hold the counter")
    for sw_val in [0b00, 0b01, 0b10]:
        dut.SW.value = sw_val
        await tick(dut)
        snap_before = hex_snapshot(dut)
        await tick_n(dut, 5)
        assert hex_snapshot(dut) == snap_before, (
            f"Counter must hold with SW=2'b{sw_val:02b}"
        )

    # State here: still s=6, m=1, h=0 (all ticks above used slow SW)

    # --- Exact HEX values at known state s=6, m=1, h=0 ---
    cocotb.log.info("Test 3: exact HEX values at s=6, m=1, h=0")
    # hours=0  -> tens=0, ones=0
    assert int(dut.HEX5.value) == seg(0), f"HEX5 (hours tens=0):   expected {seg(0)}"
    assert int(dut.HEX4.value) == seg(0), f"HEX4 (hours ones=0):   expected {seg(0)}"
    # minutes=1 -> tens=0, ones=1
    assert int(dut.HEX3.value) == seg(0), f"HEX3 (minutes tens=0): expected {seg(0)}"
    assert int(dut.HEX2.value) == seg(1), f"HEX2 (minutes ones=1): expected {seg(1)}"
    # seconds=6 -> tens=0, ones=6
    assert int(dut.HEX1.value) == seg(0), f"HEX1 (seconds tens=0): expected {seg(0)}"
    assert int(dut.HEX0.value) == seg(6), f"HEX0 (seconds ones=6): expected {seg(6)}"

    # --- SW switching freezes and resumes the counter ---
    cocotb.log.info("Test 4: SW switching freezes and resumes the counter")
    # Advance 4 cycles at SW=2'b11: s=6 -> s=10 (tens=1, ones=0)
    dut.SW.value = 0b11
    await tick_n(dut, 4)
    assert int(dut.HEX1.value) == seg(1), "seconds tens should be 1 at s=10"
    assert int(dut.HEX0.value) == seg(0), "seconds ones should be 0 at s=10"
    # Freeze: switch to slow rate and verify counter holds
    dut.SW.value = 0b00
    snap_frozen = hex_snapshot(dut)
    await tick_n(dut, 5)
    assert hex_snapshot(dut) == snap_frozen, (
        "Counter must hold when SW switches to a slow rate"
    )
    # Resume: one more tick at SW=2'b11 -> s=11, ones=1
    dut.SW.value = 0b11
    await tick(dut)
    assert int(dut.HEX0.value) == seg(1), (
        "seconds ones should be 1 after resuming from freeze"
    )

    # --- 1 kHz rate: seconds advances at the correct rate ---
    # Switch to 1 kHz and wait for the first tick (partial period, unknown
    # duration, depending on the restartable_rate_generator's current count).  Then count
    # cycles to the next tick: that interval must be exactly CYCLES_PER_KHZ.
    PERIOD = int(dut.CYCLES_PER_SECOND.value) // 1000
    cocotb.log.info(
        f"Test 5: SW=2'b10 (1 kHz, PERIOD={PERIOD}) --- seconds advances at correct rate"
    )
    dut.SW.value = 0b10
    snap = hex_snapshot(dut)
    for _ in range(PERIOD + PERIOD // 5):  # upper bound: one full period + 20% margin
        await tick(dut)
        if hex_snapshot(dut) != snap:
            break
    else:
        assert False, f"1 kHz: seconds did not advance within {PERIOD + PERIOD // 5} cycles"
    # First tick consumed; now measure the next full period exactly.
    snap = hex_snapshot(dut)
    cycles = 0
    for _ in range(PERIOD + PERIOD // 10):  # upper bound: one full period + 10% margin
        await tick(dut)
        cycles += 1
        if hex_snapshot(dut) != snap:
            break
    else:
        assert False, f"1 kHz: seconds did not advance again within {PERIOD + PERIOD // 10} cycles"
    assert cycles == PERIOD, f"1 kHz tick period: expected {PERIOD} cycles, got {cycles}"


@cocotb.test()
async def test_sw_switch_no_spurious_edge(dut):
    """Switching SW to 2'b11 while CLOCK_50=1 must not advance the counter.

    A common mistake is to wire 'tick' (a combinational mux of CLOCK_50 and
    rate-generator outputs) directly to hms_counter.clk.  When SW changes from
    a slow mode (tick=0) to 2'b11 while CLOCK_50 is already HIGH, the mux
    output transitions 0->1 -- a spurious rising edge that advances the counter
    before any intended clock cycle.  The fix is to always clock hms_counter
    from CLOCK_50 and use tick only as the enable.

    This test uses only relative comparisons so it is safe to run after other
    tests that leave the counter at a non-zero value.
    """
    cocotb.start_soon(Clock(dut.CLOCK_50, 20, unit="ns").start())
    dut.SW.value = 0b00
    await tick(dut)   # posedge + 1 ns settle; CLOCK_50 is still HIGH after the edge

    snap_before = hex_snapshot(dut)
    dut.SW.value = 0b11              # switch while CLOCK_50 = 1
    await Timer(1, unit="ns")        # combinational paths settle; no new clock edge

    assert hex_snapshot(dut) == snap_before, (
        "HEX outputs changed when SW was switched to 2'b11 while CLOCK_50=1, "
        "before any additional rising edge -- check the connections to "
        "hms_counter.clk and hms_counter.enable."
    )

    # Sanity-check the converse: a real rising edge must advance the counter.
    await tick(dut)
    assert hex_snapshot(dut) != snap_before, (
        "Counter did not advance on a real CLOCK_50 rising edge with SW=2'b11"
    )
