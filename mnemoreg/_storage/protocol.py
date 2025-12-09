from typing import (
    Dict,
    Iterator,
    Mapping,
    Optional,
    Protocol,
    runtime_checkable,
)

from mnemoreg._types import K, Stored, V


@runtime_checkable
class StorageProtocol(Protocol[K, V]):
    """Minimal protocol describing the storage interface expected by Registry.

    Only the methods and members that `mnemoreg.core.Registry` uses are
    specified here so the protocol stays small and permissive.
    """

    def set(
        self, key: K, value: Optional[V], description: Optional[str] = None
    ) -> None:  # pragma: no cover - interface
        ...

    def get(
        self, key: K, default: Optional[V] = None
    ) -> Stored[V]:  # pragma: no cover - interface
        ...

    def delete(self, key: K) -> None:  # pragma: no cover - interface
        ...

    def clear(self) -> None:  # pragma: no cover - interface
        ...

    def to_dict(self) -> Dict[K, Stored[V]]:  # pragma: no cover - interface
        ...

    def update(
        self, data: Mapping[K, Stored[V]]
    ) -> None:  # pragma: no cover - interface
        ...

    def keys(self) -> Iterator[K]:  # pragma: no cover - interface
        ...

    def __len__(self) -> int:  # pragma: no cover - interface
        ...

    def __contains__(self, key: object) -> bool:  # pragma: no cover - interface
        ...
