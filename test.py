def add(a: float, b: float) -> float:
    """Returns the sum of a and b."""
    return a + b


def divide(a: float, b: float) -> float:
    """Returns a divided by b."""
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b