import os
import sys
import time
import yaml
import logging

# -------------------------------------------------
# FIX IMPORT PATH (PROJECT ROOT)
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# -------------------------------------------------
# INTERNAL IMPORTS
# -------------------------------------------------
from core.modbus_driver import RectifierModbusDriver
from services.csv_logger import CSVLogger

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("test-modbus")

# -------------------------------------------------
# LOAD CONFIG
# -------------------------------------------------
CONFIG_PATH = os.path.join(BASE_DIR, "config", "system.yaml")
with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

# -------------------------------------------------
# INIT DRIVER + CSV LOGGER
# -------------------------------------------------
driver = RectifierModbusDriver(cfg)
csv_logger = CSVLogger(cfg)

# -------------------------------------------------
# MAIN TEST
# -------------------------------------------------
try:
    log.info("Connecting to rectifier (Node-RED)...")
    driver.connect()

    start = time.time()
    duration = 10  # seconds

    while time.time() - start < duration:
        data = driver.read_data()

        log.info(f"READ: {data}")

        # write to CSV
        csv_logger.write(data)

        time.sleep(1)

    log.info("Writing test values...")
    driver.write_voltage(12.0)
    driver.write_current(120.0)
    driver.set_power(False)
    driver.set_polarity("REVERSE")

    log.info("Write commands sent successfully")

except Exception as e:
    log.error(f"ERROR: {e}")

finally:
    driver.close()
    log.info("Test finished")
