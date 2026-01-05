/* ================== ELEMENTS ================== */
const voltageEl  = document.getElementById("voltage");
const currentEl  = document.getElementById("current");
const powerEl    = document.getElementById("power");
const polarityEl = document.getElementById("polarity");

const connDot  = document.getElementById("connDot");
const connText = document.getElementById("connText");
const commandLog = document.getElementById("commandLog");

/* ================== LOG ================== */
function addLog(msg, type = "info") {
  const time = new Date().toLocaleTimeString();
  const icon = type === "ok" ? "✔" : type === "err" ? "✖" : "•";
  commandLog.textContent += `\n[${time}] ${icon} ${msg}`;
  commandLog.scrollTop = commandLog.scrollHeight;
}

/* ================== UI STATE ================== */
function setConnected(text = "CONNECTED") {
  connDot.className = "dot online";
  connText.textContent = text;
}

function setDisconnected(text = "DISCONNECTED") {
  connDot.className = "dot offline";
  connText.textContent = text;
}

/* ================== DATA ================== */
function updateUI(data) {
  voltageEl.textContent  = Number(data.actual_voltage).toFixed(2);
  currentEl.textContent  = Number(data.actual_current).toFixed(2);
  powerEl.textContent    = data.power;
  polarityEl.textContent = data.polarity;
}

/* ================== POLLING CONTROL ================== */
let lastTimestamp = 0;
let polling = false;
let pollTimer = null;

/* ================== BACKEND STATE ================== */
async function pollState() {
  try {
    const res = await fetch("/api/state", { cache: "no-store" });
    const data = await res.json();

    if (data.state === "CONNECTED") {
      setConnected("CONNECTED");
    } else if (data.state === "CONNECTING") {
      setDisconnected("CONNECTING");
    } else {
      setDisconnected(data.state);
    }
  } catch {
    setDisconnected("NO SERVER");
  }
}

/* ================== DATA POLLING ================== */
async function pollData() {
  if (polling) return;
  polling = true;

  try {
    const res = await fetch("/api/data", { cache: "no-store" });
    const data = await res.json();

    if (data.status === "WAITING_FOR_DATA") {
      setDisconnected("WAITING");
      return;
    }

    if (!data.timestamp) {
      addLog("Invalid data received", "err");
      return;
    }

    if (data.timestamp === lastTimestamp) {
      // Backend alive but data unchanged
      return;
    }

    lastTimestamp = data.timestamp;

    updateUI(data);
    setConnected("LIVE");

  } catch (e) {
    setDisconnected("ERROR");
    addLog("Data polling failed", "err");
  } finally {
    polling = false;
  }
}

/* ================== POLL LOOP ================== */
function startPolling() {
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(() => {
    pollState();
    pollData();
  }, 1000);
}

/* ================== CSV ================== */
async function showLogFiles() {
  try {
    addLog("Fetching CSV files...");
    const res = await fetch("/api/logs", { cache: "no-store" });
    if (!res.ok) throw new Error();

    const data = await res.json();

    if (!data.files || data.files.length === 0) {
      addLog("No CSV files found");
      return;
    }

    data.files.forEach(f => {
      addLog(`CSV → ${f}`, "ok");
    });

  } catch {
    addLog("Failed to fetch CSV list", "err");
  }
}

function downloadLatestCSV() {
  addLog("Downloading latest CSV...");
  window.location.href = "/api/logs/latest";
}

function downloadLog(filename) {
  if (!filename) return;
  window.location.href = `/api/logs/${filename}`;
}

/* ================== INIT ================== */
addLog("Dashboard initialized");
startPolling();
