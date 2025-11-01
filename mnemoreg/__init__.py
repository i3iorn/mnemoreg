"""mnemoreg — small thread-safe registry package.

This package exposes a simple `Registry` mapping useful for registering
callables and values by string keys. It's intentionally small and dependency-free.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Optional

from mnemoreg.core import (
    AlreadyRegisteredError,
    NotRegisteredError,
    Registry,
)


def _read_version_file() -> Optional[str]:
    try:
        return Path(__file__).with_name("VERSION").read_text(encoding="utf8").strip()
    except Exception:
        return None


def _get_version() -> str:
    # 1) Try to read installed distribution metadata
    try:
        return _pkg_version("mnemoreg")
    except PackageNotFoundError:
        pass

    # 2) Try the VERSION file that setuptools_scm can write at build time
    v = _read_version_file()
    if v:
        return v

    # 3) Fall back to a safe default
    return "0.0.0"


__version__ = _get_version()


__all__ = [
    "Registry",
    "AlreadyRegisteredError",
    "NotRegisteredError",
    "__version__",
]
