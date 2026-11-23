"""Functional tests for Feature A: Transfer extreme values validation.

Expected Manager API:
- ``manager.set_transfer_limits(min_amount: float, max_amount: float) -> None``:
  Sets the inclusive allowed range ``[min_amount, max_amount]`` for transfer/refund
  amounts (``Transfer.amount_pln``). Raises ``ValueError`` if ``min_amount > max_amount``.
- ``manager.validate_transfers() -> list[Transfer]``:
  Checks every transfer in ``manager.transfers`` against the configured limits and
  returns a list of all invalid ``Transfer`` objects (those with
  ``amount_pln < min_amount`` or ``amount_pln > max_amount``). Returns ``[]`` when
  all transfers are valid or when ``manager.transfers`` is empty.
"""

import pytest

from src.manager import Manager
from src.models import Parameters, Transfer


def _make_transfer(amount_pln: float, transfer_type: str | None = None) -> Transfer:
    return Transfer(
        amount_pln=amount_pln,
        date="2025-01-10",
        settlement_year=2025,
        settlement_month=1,
        tenant="tenant-1",
        type=transfer_type,
    )


def test_validate_transfers_default_data_valid():
    """Default transfers from data/transfers.json (2500 PLN) should pass default limits."""
    manager = Manager(Parameters())

    invalid_transfers = manager.validate_transfers()

    assert invalid_transfers == []


def test_validate_transfers_boundary_values():
    """Limits are inclusive: exact min/max values are valid, values just outside are invalid."""
    manager = Manager(Parameters())
    manager.set_transfer_limits(-500.0, 5000.0)

    exact_min = _make_transfer(-500.0, transfer_type="refund")
    exact_max = _make_transfer(5000.0)
    manager.transfers = [exact_min, exact_max]

    assert manager.validate_transfers() == []

    below_min = _make_transfer(-500.01, transfer_type="refund")
    above_max = _make_transfer(5000.01)
    manager.transfers.extend([below_min, above_max])

    invalid_transfers = manager.validate_transfers()
    assert invalid_transfers == [below_min, above_max]


def test_validate_transfers_exceeds_max():
    """A transfer exceeding max_amount should be reported as invalid."""
    manager = Manager(Parameters())
    manager.set_transfer_limits(0.0, 3000.0)

    too_high = _make_transfer(3500.0)
    manager.transfers.append(too_high)

    invalid_transfers = manager.validate_transfers()

    assert invalid_transfers == [too_high]


def test_validate_transfers_below_min_and_refunds():
    """Refunds within [min_amount, max_amount] are valid; those below min_amount are invalid."""
    manager = Manager(Parameters())
    manager.set_transfer_limits(-1000.0, 5000.0)

    valid_refund = _make_transfer(-500.0, transfer_type="refund")
    invalid_refund = _make_transfer(-1500.0, transfer_type="refund")
    manager.transfers.extend([valid_refund, invalid_refund])

    invalid_transfers = manager.validate_transfers()

    assert invalid_transfers == [invalid_refund]


def test_validate_transfers_multiple_errors():
    """Validation should return all invalid transfers (both below min and above max)."""
    manager = Manager(Parameters())
    manager.set_transfer_limits(-1000.0, 4000.0)

    valid_refund = _make_transfer(-250.0, transfer_type="refund")
    too_low = _make_transfer(-2500.0, transfer_type="refund")
    too_high_1 = _make_transfer(4500.0)
    too_high_2 = _make_transfer(100000.0)
    manager.transfers.extend([valid_refund, too_low, too_high_1, too_high_2])

    invalid_transfers = manager.validate_transfers()

    assert invalid_transfers == [too_low, too_high_1, too_high_2]


def test_validate_transfers_after_updating_limits():
    """Updating limits on the manager should immediately affect validation results."""
    manager = Manager(Parameters())  # 3 transfers of 2500.0 PLN

    manager.set_transfer_limits(0.0, 3000.0)
    assert manager.validate_transfers() == []

    manager.set_transfer_limits(0.0, 2000.0)
    assert len(manager.validate_transfers()) == 3

    manager.set_transfer_limits(3000.0, 5000.0)
    assert len(manager.validate_transfers()) == 3


def test_set_transfer_limits_invalid_range_raises_value_error():
    """Setting min_amount greater than max_amount should raise ValueError."""
    manager = Manager(Parameters())

    with pytest.raises(ValueError):
        manager.set_transfer_limits(5000.0, 1000.0)


def test_validate_transfers_empty_list():
    """Validation on an empty transfers list should return an empty list."""
    manager = Manager(Parameters())
    manager.transfers = []
    manager.set_transfer_limits(-1000.0, 5000.0)

    assert manager.validate_transfers() == []
