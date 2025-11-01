"""mnemoreg — small thread-safe registry package.

This package exposes a simple `Registry` mapping useful for registering
callables and values by string keys. It's intentionally small and
well-tested.
"""
from mnemoreg.core import (
    AlreadyRegisteredError,
    NotRegisteredError,
    Registry,
)

__version__ = "0.1.0"


__all__ = [
    "Registry",
    "AlreadyRegisteredError",
    "NotRegisteredError",
    "__version__",
]
