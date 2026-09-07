import pytest
from conftest import rtl_exists


@pytest.mark.skipif(
    not rtl_exists("stopwatch_control.sv"),
    reason="stopwatch_control not implemented yet",
)
def test_stopwatch_control(cocotb_runner):
    """Unit tests for stopwatch_control."""
    cocotb_runner(
        top="stopwatch_control",
        sources=["stopwatch_control.sv"],
        test_module="tb_stopwatch_control",
    )
