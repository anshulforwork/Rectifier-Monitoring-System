import time
import threading
from enum import Enum


class RectifierState(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


class RectifierService:
    def __init__(self, config, modbus_driver, csv_logger, app_logger):
        self.cfg = config
        self.modbus = modbus_driver
        self.csv = csv_logger
        self.log = app_logger

        self.state = RectifierState.DISCONNECTED
        self.running = False
        self.fail_count = 0

        self._lock = threading.Lock()
        self._latest_data = {}
        self._last_good_data = {}

    # -------------------------
    # Lifecycle
    # -------------------------
    def start(self):
        if self.running:
            return

        self.running = True
        self.log.info("Rectifier service starting")

        # Connect once
        try:
            self._set_state(RectifierState.CONNECTING)
            self.modbus.connect()
            self._set_state(RectifierState.CONNECTED)
        except Exception as e:
            self.log.error(f"Initial Modbus connect failed: {e}")
            self._set_state(RectifierState.ERROR)

        threading.Thread(target=self._poll_loop, daemon=True).start()

    # -------------------------
    # Polling Loop
    # -------------------------
    def _poll_loop(self):
        interval = self.cfg["polling"]["interval_sec"]
        max_fail = self.cfg["polling"]["max_failures"]

        next_poll = time.monotonic()

        while self.running:
            try:
                data = self.modbus.read_data()

                # Ignore error packets from driver
                if "error" in data:
                    raise IOError(data["error"])

                with self._lock:
                    self._latest_data = data
                    self._last_good_data = data

                # CSV logs ONLY valid data
                self.csv.write(data)

                self.fail_count = 0
                self._set_state(RectifierState.CONNECTED)

            except Exception as e:
                self.fail_count += 1
                self.log.error(f"Polling failed ({self.fail_count}): {e}")

                if self.fail_count >= max_fail:
                    self._set_state(RectifierState.ERROR)
                    try:
                        self.modbus.close()
                        self.modbus.connect()
                        self.fail_count = 0
                        self._set_state(RectifierState.CONNECTED)
                    except Exception as e:
                        self.log.error(f"Reconnect failed: {e}")

            # Drift-free sleep
            next_poll += interval
            sleep_time = next_poll - time.monotonic()
            if sleep_time > 0:
                time.sleep(sleep_time)

    # -------------------------
    # State
    # -------------------------
    def _set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
            self.log.info(f"State → {new_state.value}")

    # -------------------------
    # Flask APIs
    # -------------------------
    def get_state(self):
        return self.state.value

    def get_data(self):
        with self._lock:
            # Always return last known GOOD data
            return dict(self._last_good_data)
