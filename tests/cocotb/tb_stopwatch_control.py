import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Formal verification misses the bug described below because it can promote
# logic var = expr into assign var = expr.
# This necessitates having this testbench in addition to the formal tests.

_BUG_HINT = (
    "output is X/Z after the first clock edge — a combinational signal inside "
    "stopwatch_control is probably declared with 'logic var = expr' instead of "
    "'wire var = expr' (or 'assign'): 'logic' initialises once at elaboration "
    "when inputs are still X, leaving the signal permanently stuck at X"
)


async def step(dut):
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


def check(sig, expected, msg):
    assert sig.value.is_resolvable, f"{msg}: {_BUG_HINT}"
    assert int(sig.value) == expected, (
        f"{msg}: expected {expected}, got {int(sig.value)}"
    )


async def pulse(dut, *, ss=0, lap=0):
    """Assert inputs for one clock cycle, then deassert for one cycle."""
    dut.rise_start_stop.value = ss
    dut.rise_lap.value = lap
    await step(dut)
    dut.rise_start_stop.value = 0
    dut.rise_lap.value = 0
    await step(dut)


@cocotb.test()
async def test_stopwatch_control(dut):
    """Stopwatch control: initial state, start/stop, lap/hold, lap reset, simultaneous press."""

    # All @cocotb.test() functions share a single Icarus simulation, so there is no
    # automatic DUT reset between named tests.  This single function runs all
    # checks sequentially, explicitly managing DUT state as it goes.

    dut.rise_start_stop.value = 0
    dut.rise_lap.value = 0
    await Timer(1, unit="ns")
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await step(dut)  # one idle cycle to let FFs settle

    # -----------------------------------------------------------------------
    # Section 1: initial state — all outputs must be 0
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 1: initial state")
    check(dut.counter_rst, 0, "counter_rst after idle cycle")
    check(dut.counter_enable, 0, "counter_enable after idle cycle")
    check(dut.lap_hold, 0, "lap_hold after idle cycle")

    # -----------------------------------------------------------------------
    # Section 2: start/stop button toggles counter_enable
    # (catches the logic-vs-wire bug: if start_stop is stuck, enable never changes)
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 2: start/stop toggles counter_enable")
    await pulse(dut, ss=1)
    check(dut.counter_enable, 1, "counter_enable must go high after first start press")
    check(dut.lap_hold, 0, "lap_hold must not change on start press")
    check(dut.counter_rst, 0, "counter_rst must not fire on start press")

    await pulse(dut, ss=1)
    check(dut.counter_enable, 0, "counter_enable must go low after second start press")

    # -----------------------------------------------------------------------
    # Section 3: lap button toggles lap_hold while running
    # (catches the logic-vs-wire bug: if lap is stuck, lap_hold never changes)
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 3: lap button toggles lap_hold while running")
    await pulse(dut, ss=1)  # start → counter_enable=1

    await pulse(dut, lap=1)
    check(dut.lap_hold, 1, "lap_hold must go high on first lap press while running")
    check(dut.counter_enable, 1, "counter_enable must not change on lap press")
    check(dut.counter_rst, 0, "counter_rst must not fire while running")

    await pulse(dut, lap=1)
    check(dut.lap_hold, 0, "lap_hold must go low on second lap press")

    # -----------------------------------------------------------------------
    # Section 4: lap button while stopped resets the counter
    # DUT is currently running (counter_enable=1, lap_hold=0); stop it first.
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 4: lap button while stopped asserts counter_rst")
    await pulse(dut, ss=1)  # stop → counter_enable=0
    check(dut.counter_enable, 0, "counter_enable must go low after stop press")

    dut.rise_lap.value = 1
    await step(dut)
    dut.rise_lap.value = 0

    check(dut.counter_rst, 1, "counter_rst must fire when lap pressed while stopped")
    check(dut.counter_enable, 0, "counter_enable must remain 0 on reset")
    check(dut.lap_hold, 0, "lap_hold must remain 0 on reset")

    await step(dut)
    check(dut.counter_rst, 0, "counter_rst must deassert after one cycle")

    # -----------------------------------------------------------------------
    # Section 5: simultaneous press is ignored
    # DUT is currently stopped (counter_enable=0, lap_hold=0).
    # -----------------------------------------------------------------------
    cocotb.log.info("Section 5: simultaneous press is ignored")
    dut.rise_start_stop.value = 1
    dut.rise_lap.value = 1
    await step(dut)
    dut.rise_start_stop.value = 0
    dut.rise_lap.value = 0

    check(dut.counter_enable, 0, "simultaneous press must not change counter_enable")
    check(dut.lap_hold, 0, "simultaneous press must not change lap_hold")
    check(dut.counter_rst, 0, "simultaneous press must not assert counter_rst")
