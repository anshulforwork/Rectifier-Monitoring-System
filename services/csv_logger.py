import os
import csv
from datetime import datetime
from threading import Lock


class CSVLogger:
    def __init__(self, cfg):
        self.root_dir = os.path.abspath(cfg["logging"]["root_dir"])
        self._lock = Lock()

        self._current_date = None
        self._file = None
        self._writer = None

        self._ensure_dir()

    # -------------------------
    # Directory Handling
    # -------------------------
    def _ensure_dir(self):
        os.makedirs(self.root_dir, exist_ok=True)

    def set_root_dir(self, path: str):
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Invalid log directory")

        with self._lock:
            self.root_dir = os.path.abspath(path)
            self._ensure_dir()
            self._rotate_file(force=True)

    # -------------------------
    # File Rotation
    # -------------------------
    def _rotate_file(self, force=False):
        date = datetime.now().strftime("%Y-%m-%d")

        if force or self._current_date != date:
            if self._file:
                self._file.flush()
                self._file.close()

            self._current_date = date
            path = os.path.join(self.root_dir, f"rectifier_{date}.csv")

            file_exists = os.path.exists(path)

            self._file = open(path, "a", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)

            if not file_exists:
                self._writer.writerow([
                    "timestamp",
                    "actual_voltage",
                    "actual_current",
                    "power",
                    "polarity",
                ])
                self._file.flush()

    # -------------------------
    # Write Data (SAFE)
    # -------------------------
    def write(self, data: dict):
        required = ("timestamp", "actual_voltage", "actual_current", "power", "polarity")

        if not all(k in data for k in required):
            return  # silently ignore bad data

        with self._lock:
            self._rotate_file()

            ts = datetime.fromtimestamp(data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

            self._writer.writerow([
                ts,
                data["actual_voltage"],
                data["actual_current"],
                data["power"],
                data["polarity"],
            ])

            # IMPORTANT for real-time download
            self._file.flush()
