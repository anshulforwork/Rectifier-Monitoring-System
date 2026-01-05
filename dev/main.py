import time
import yaml
import logging

from core.modbus_driver import RectifierModbusDriver
from services.csv_logger import CSVLogger


def load_config():
    with open("config/system.yaml", "r") as f:
        return yaml.safe_load(f)


def setup_logging(log_file):
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )


def main():
    config = load_config()
    setup_logging(config["logging"]["app_log"])

    driver = RectifierModbusDriver(config)
    csv_logger = CSVLogger(config["logging"]["csv_path"])

    while True:
        try:
            driver.connect()
            data = driver.read_data()

            # 1️⃣ Console
            print("Rectifier Data:", data)

            # 2️⃣ App log (debug / audit)
            logging.info(data)

            # 3️⃣ CSV / Excel (PROCESS DATA)
            csv_logger.write(data)

            time.sleep(config["polling"]["interval_sec"])

        except KeyboardInterrupt:
            print("Stopped by user")
            break

        except Exception as e:
            logging.error(str(e))
            time.sleep(config["polling"]["reconnect_delay_sec"])


if __name__ == "__main__":
    main()
