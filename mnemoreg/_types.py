from typing import Optional, Tuple, TypeVar

K = TypeVar("K", bound=str)
V = TypeVar("V")

# Stored is a convenient alias for the internal storage representation:
# a tuple of (value or None, optional description string)
Stored = Tuple[Optional[V], Optional[str]]

__all__ = ["K", "V", "Stored"]
