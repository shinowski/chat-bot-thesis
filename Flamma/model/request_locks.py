"""Serialize a browser's mutations without blocking other browsers."""

from contextlib import contextmanager
from threading import Lock, RLock


class OwnerLocks:
    def __init__(self):
        self._registry = {}
        self._lock = Lock()

    @contextmanager
    def hold(self, owner):
        with self._lock:
            entry = self._registry.setdefault(owner, [RLock(), 0])
            entry[1] += 1
        try:
            with entry[0]:
                yield
        finally:
            with self._lock:
                entry[1] -= 1
                if entry[1] == 0:
                    del self._registry[owner]
