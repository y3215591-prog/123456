from PySide6.QtCore import QTimer, QObject
from functools import wraps
import functools


class AutoSaveManager(QObject):
    _instance = None

    def __init__(self):
        super().__init__()
        self._timers = {}
        self._callbacks = {}
        self._dirty = set()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, key, callback, delay_ms=2000):
        self._callbacks[key] = callback
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(delay_ms)
        timer.timeout.connect(functools.partial(self._do_save, key))
        self._timers[key] = timer

    def mark_dirty(self, key):
        self._dirty.add(key)
        if key in self._timers:
            self._timers[key].start()

    def _do_save(self, key):
        self._dirty.discard(key)
        if key in self._callbacks:
            self._callbacks[key]()

    def save_now(self, key):
        if key in self._timers:
            self._timers[key].stop()
        self._dirty.discard(key)
        if key in self._callbacks:
            self._callbacks[key]()

    def save_all(self):
        for key in list(self._dirty):
            self.save_now(key)


def autosave(key, delay_ms=2000):
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            AutoSaveManager.instance().mark_dirty(key)
            return result
        return wrapper
    return decorator
