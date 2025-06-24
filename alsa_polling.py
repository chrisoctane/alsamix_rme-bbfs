import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal

class AlsaPollingWorker(QObject):
    alsa_update = pyqtSignal(dict)  # Emits {channel_name: value, ...}

    def __init__(self, channel_names, interval=0.5):
        super().__init__()
        self.channel_names = channel_names
        self.interval = interval
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._thread.join()

    def set_channels(self, channel_names):
        self.channel_names = channel_names
        self._vals = {name: None for name in channel_names}
        self._batch_index = 0  # if using batch polling

    def _worker_loop(self):
        import alsa_backend  # import here to avoid circular imports
        last_vals = {name: None for name in self.channel_names}
        while self._running:
            vals = {}
            for name in self.channel_names:
                try:
                    v = alsa_backend.get_volume(name)
                except Exception:
                    v = None
                vals[name] = v
            if vals != last_vals:
                self.alsa_update.emit(vals)
                last_vals = vals.copy()
            time.sleep(self.interval)

