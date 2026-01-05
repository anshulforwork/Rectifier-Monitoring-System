import time
import threading
from pymodbus.client import ModbusTcpClient


class RectifierModbusDriver:
    def __init__(self, config):
        self.cfg = config

        self.client = ModbusTcpClient(
            host=config["rectifier"]["ip"],
            port=config["rectifier"]["port"],
            timeout=config["rectifier"]["timeout_sec"]
        )

        self.unit = config["rectifier"]["unit_id"]
        self.v_mul = config["scaling"]["voltage_multiplier"]
        self.c_mul = config["scaling"]["current_multiplier"]

        self._lock = threading.Lock()
        self._connected = False

    # -------------------------
    # Connection management
    # -------------------------
    def connect(self):
        if not self._connected:
            if self.client.connect():
                self._connected = True
            else:
                raise ConnectionError("Modbus connection failed")

    def close(self):
        try:
            self.client.close()
        finally:
            self._connected = False

    # -------------------------
    # Internal helper (THREAD SAFE)
    # -------------------------
    def _read_register(self, address: int) -> int:
        with self._lock:
            rr = self.client.read_holding_registers(
                address=address,
                count=1,
                unit=self.unit
            )

        if rr is None or rr.isError():
            raise IOError(f"Modbus read error at register {address}")

        return rr.registers[0]

    # -------------------------
    # Read status (SAFE POLLING)
    # -------------------------
    def read_data(self) -> dict:
        """
        Reads actual voltage, current, power state and polarity
        NEVER reconnects here
        NEVER blocks other threads
        """

        if not self._connected:
            raise ConnectionError("Modbus client not connected")

        try:
            actual_voltage_raw = self._read_register(0)
            actual_current_raw = self._read_register(2)
            power_state_raw    = self._read_register(4)
            polarity_raw       = self._read_register(6)

            return {
                "actual_voltage": round(actual_voltage_raw / self.v_mul, 2),
                "actual_current": round(actual_current_raw / self.c_mul, 2),
                "power": "ON" if power_state_raw == 1 else "OFF",
                "polarity": "FORWARD" if polarity_raw == 0 else "REVERSE",
                "timestamp": time.time()
            }

        except Exception as e:
            # IMPORTANT: never crash polling loop
            return {
                "error": str(e),
                "timestamp": time.time()
            }
