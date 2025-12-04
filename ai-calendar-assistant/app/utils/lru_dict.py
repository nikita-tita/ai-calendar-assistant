"""LRU (Least Recently Used) dictionary implementation."""

from collections import OrderedDict
from typing import TypeVar, Generic, Optional

K = TypeVar('K')
V = TypeVar('V')


class LRUDict(Generic[K, V]):
    """
    Dictionary with LRU (Least Recently Used) eviction policy.

    When the dictionary exceeds max_size, the least recently used
    items are automatically removed to make room for new ones.

    Usage:
        cache = LRUDict(max_size=1000)
        cache["key"] = "value"
        value = cache.get("key", default=None)
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU dictionary.

        Args:
            max_size: Maximum number of items to store. When exceeded,
                     least recently used items are removed.
        """
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self.max_size = max_size
        self._data: OrderedDict[K, V] = OrderedDict()

    def __getitem__(self, key: K) -> V:
        """Get item and mark as recently used."""
        self._data.move_to_end(key)
        return self._data[key]

    def __setitem__(self, key: K, value: V) -> None:
        """Set item, evicting oldest if needed."""
        if key in self._data:
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self.max_size:
                # Remove oldest item (first in OrderedDict)
                self._data.popitem(last=False)
        self._data[key] = value

    def __delitem__(self, key: K) -> None:
        """Delete item."""
        del self._data[key]

    def __contains__(self, key: K) -> bool:
        """Check if key exists."""
        return key in self._data

    def __len__(self) -> int:
        """Return number of items."""
        return len(self._data)

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Get item or return default if not found."""
        if key in self._data:
            return self[key]
        return default

    def pop(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Remove and return item, or return default if not found."""
        return self._data.pop(key, default)

    def clear(self) -> None:
        """Remove all items."""
        self._data.clear()

    def keys(self):
        """Return keys."""
        return self._data.keys()

    def values(self):
        """Return values."""
        return self._data.values()

    def items(self):
        """Return items."""
        return self._data.items()
