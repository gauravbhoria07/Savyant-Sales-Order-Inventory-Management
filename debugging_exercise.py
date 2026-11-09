"""
debugging_exercise.py - Technical Assignment Debugging Exercise

=============================================================================
1. THE ORIGINAL BUGGY FUNCTION
=============================================================================
def calculate_total(items):
    total = 0

    for item in items:
        amount = item["qty"] * item["rate"]
        total = amount

    return total

=============================================================================
2. CAUSE OF THE BUG & EXPLANATION
=============================================================================
- Bug: Inside the loop, the assignment `total = amount` overwrites the accumulator
  with only the last item's amount instead of adding to it (`total += amount`).
- Why it occurred: The developer accidentally used assignment `=` instead of
  augmented addition assignment `+=`. Consequently, all previous items in the
  list are completely discarded, and only the value of the final element is returned.
  For the input:
      [{"qty": 2, "rate": 100}, {"qty": 3, "rate": 50}]
  The first iteration calculated amount = 200 and set total = 200.
  The second iteration calculated amount = 150 and overwrote total = 150.
  The returned result was 150 instead of the expected 350 (200 + 150).

=============================================================================
3. EDGE CASES & DEFENSIVE PROGRAMMING CONSIDERATIONS
=============================================================================
A production-ready financial function must safely handle:
1. Empty list: Returns Decimal('0.00') or 0 cleanly without errors.
2. Missing keys ('qty' or 'rate'): Raises a descriptive ValueError or KeyError.
3. Invalid quantities / rates (strings that cannot be converted, None): Raises ValueError.
4. Negative numbers: Rejects negative quantity or rate with ValueError.
5. Monetary precision: Uses Decimal with consistent rounding (ROUND_HALF_UP)
   to eliminate binary floating-point inaccuracy (e.g., 0.1 + 0.2 != 0.3).
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import unittest


def calculate_total(items):
    """
    Calculates the total monetary sum of an order item list.
    
    Parameters:
        items (list[dict]): List of dictionaries, each containing 'qty' and 'rate'.
        
    Returns:
        Decimal: Total sum of (qty * rate) rounded to 2 decimal places.
        
    Raises:
        TypeError: If items is not an iterable / list.
        KeyError: If a dictionary is missing 'qty' or 'rate'.
        ValueError: If qty or rate cannot be converted to Decimal or is negative.
    """
    if items is None:
        return Decimal('0.00')

    if not isinstance(items, (list, tuple)):
        raise TypeError(f"Expected list of items, got {type(items).__name__}")

    total = Decimal('0.00')

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise TypeError(f"Item at index {idx} must be a dictionary, got {type(item).__name__}")

        if "qty" not in item:
            raise KeyError(f"Item at index {idx} is missing required 'qty' key.")
        if "rate" not in item:
            raise KeyError(f"Item at index {idx} is missing required 'rate' key.")

        try:
            qty = Decimal(str(item["qty"]))
        except (InvalidOperation, TypeError):
            raise ValueError(f"Item at index {idx} has invalid quantity: {item['qty']}")

        try:
            rate = Decimal(str(item["rate"]))
        except (InvalidOperation, TypeError):
            raise ValueError(f"Item at index {idx} has invalid rate: {item['rate']}")

        if qty < 0:
            raise ValueError(f"Item at index {idx} has negative quantity: {qty}")
        if rate < 0:
            raise ValueError(f"Item at index {idx} has negative rate: {rate}")

        # Correct calculation: accumulate item amount into total
        amount = qty * rate
        total += amount

    # Consistent rounding to 2 decimal places
    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# =============================================================================
# 4. AUTOMATED TESTS DEMONSTRATING THE CORRECTION & EDGE CASES
# =============================================================================

class TestCalculateTotal(unittest.TestCase):

    def test_assignment_sample_input(self):
        """Validates the exact input from technical assignment produces 350."""
        items = [
            {"qty": 2, "rate": 100},
            {"qty": 3, "rate": 50}
        ]
        result = calculate_total(items)
        self.assertEqual(result, Decimal('350.00'))

    def test_empty_list(self):
        """An empty list should return 0.00 without error."""
        self.assertEqual(calculate_total([]), Decimal('0.00'))

    def test_none_input(self):
        """None input should safely return 0.00."""
        self.assertEqual(calculate_total(None), Decimal('0.00'))

    def test_single_item(self):
        """Single item should calculate correctly."""
        items = [{"qty": 5, "rate": 19.99}]
        self.assertEqual(calculate_total(items), Decimal('99.95'))

    def test_missing_qty_key(self):
        """Should raise KeyError when 'qty' is missing."""
        items = [{"rate": 100}]
        with self.assertRaises(KeyError):
            calculate_total(items)

    def test_missing_rate_key(self):
        """Should raise KeyError when 'rate' is missing."""
        items = [{"qty": 2}]
        with self.assertRaises(KeyError):
            calculate_total(items)

    def test_invalid_qty_type(self):
        """Should raise ValueError when qty cannot be parsed as a number."""
        items = [{"qty": "not_a_number", "rate": 100}]
        with self.assertRaises(ValueError):
            calculate_total(items)

    def test_negative_quantity(self):
        """Should reject negative quantity."""
        items = [{"qty": -2, "rate": 100}]
        with self.assertRaises(ValueError):
            calculate_total(items)

    def test_negative_rate(self):
        """Should reject negative rate."""
        items = [{"qty": 2, "rate": -50}]
        with self.assertRaises(ValueError):
            calculate_total(items)

    def test_float_precision_rounding(self):
        """Tests that Decimal prevents floating point rounding errors."""
        items = [
            {"qty": 3, "rate": Decimal('10.33')}, # 30.99
            {"qty": 1, "rate": Decimal('0.01')}   # 0.01
        ]
        self.assertEqual(calculate_total(items), Decimal('31.00'))


if __name__ == "__main__":
    print("Running Debugging Exercise Test Suite...")
    unittest.main()
