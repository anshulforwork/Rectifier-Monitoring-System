import os
import sys
import logging
import yaml
from flask import Flask, jsonify, render_template, send_file
from werkzeug.utils import secure_filename

# =================================================
# BASE DIR (PYTHON + EXE SAFE)
# =================================================
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# =================================================
# INTERNAL IMPORTS
# =================================================
from core.modbus_driver import RectifierModbusDriver
from services.rectifier_service import RectifierService
from services.csv_logger import CSVLogger

# =================================================
# LOAD CONFIG
# =================================================
CONFIG_PATH = os.path.join(BASE_DIR, "config", "system.yaml")

if not os.path.exists(CONFIG_PATH):
    print("FATAL: config/system.yaml not found")
    sys.exit(1)

with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)

# =================================================
# LOGGING
# =================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
app_log = logging.getLogger("rectifier-app")

# =================================================
# BACKEND SERVICES
# =================================================
modbus = RectifierModbusDriver(cfg)
csv_logger = CSVLogger(cfg)

log_root = cfg["logging"].get("root_dir", "logs")
csv_subdir = cfg["logging"].get("csv", {}).get("subdir", "data")
csv_dir = os.path.join(log_root, csv_subdir)
os.makedirs(csv_dir, exist_ok=True)
csv_logger.set_root_dir(csv_dir)

service = RectifierService(
    config=cfg,
    modbus_driver=modbus,
    csv_logger=csv_logger,
    app_logger=app_log,
)

# =================================================
# FLASK APP
# =================================================
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "web", "templates"),
    static_folder=os.path.join(BASE_DIR, "web", "static"),
)

# =================================================
# DISABLE CACHE (IMPORTANT FOR REAL-TIME UI)
# =================================================
@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# =================================================
# CSV SAFE DOWNLOAD (WINDOWS SAFE)
# =================================================
def safe_copy_for_download(src_path):
    """
    Create a temporary safe copy of CSV for download.
    Prevents Windows file-lock issues.
    """
    import shutil
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="csv_dl_")
    dst_path = os.path.join(tmp_dir, os.path.basename(src_path))

    shutil.copy2(src_path, dst_path)
    return dst_path

# =================================================
# API – STATE
# =================================================
@app.route("/api/state")
def api_state():
    return jsonify({"state": service.get_state()})

# =================================================
# API – LIVE DATA
# =================================================
@app.route("/api/data")
def api_data():
    data = service.get_data()
    if not data:
        return jsonify({"status": "WAITING_FOR_DATA"})
    return jsonify(data)

# =================================================
# API – CSV LOG LIST
# =================================================
@app.route("/api/logs")
def list_logs():
    if not os.path.exists(csv_dir):
        return jsonify({"files": []})

    files = sorted(
        [f for f in os.listdir(csv_dir) if f.endswith(".csv")],
        reverse=True
    )
    return jsonify({"files": files})

# =================================================
# API – DOWNLOAD LATEST CSV (SAFE)
# =================================================
@app.route("/api/logs/latest")
def download_latest_log():
    files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    if not files:
        return jsonify({"error": "No CSV logs yet"}), 404

    files.sort(reverse=True)
    latest_path = os.path.join(csv_dir, files[0])

    safe_copy = safe_copy_for_download(latest_path)

    return send_file(
        safe_copy,
        as_attachment=True,
        download_name=files[0],
    )

# =================================================
# API – DOWNLOAD SELECTED CSV (SAFE)
# =================================================
@app.route("/api/logs/<filename>")
def download_log(filename):
    filename = secure_filename(filename)
    full_path = os.path.join(csv_dir, filename)

    if not os.path.exists(full_path):
        return jsonify({"error": "File not found"}), 404

    safe_copy = safe_copy_for_download(full_path)

    return send_file(
        safe_copy,
        as_attachment=True,
        download_name=filename,
    )

# =================================================
# UI
# =================================================
@app.route("/")
def index():
    return render_template("index.html")

# =================================================
# MAIN
# =================================================
if __name__ == "__main__":
    app_log.info("Starting Rectifier Monitoring Backend")

    # Start polling AFTER everything is ready
    service.start()

    app.run(
        host=cfg["web"]["host"],
        port=cfg["web"]["port"],
        debug=False,
        threaded=False,   # IMPORTANT for stability
    )
