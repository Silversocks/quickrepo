import json
import re
import socket
import struct
import threading
from queue import Queue
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from obd_ai import query_model  

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OBDRequest(BaseModel):
    code: str


# ======= Existing AI Analyzer Code =======
def clean_json(text: str):
    """Extract and clean JSON-like AI output."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    text = text.replace("|", "").replace("•", "").replace("json", "").strip()
    text = re.sub(r",\s*([\]}])", r"\1", text)
    text = text.replace("“", "\"").replace("”", "\"").replace("’", "'")
    return text

@app.post("/analyze")
def analyze_code(request: OBDRequest):
    raw_response = query_model(request.code)
    cleaned = clean_json(raw_response)
    try:
        parsed = json.loads(cleaned)
        return parsed
    except json.JSONDecodeError:
        return {
            "title": "Parsing Error",
            "severity": "-",
            "description": "AI returned unstructured text.",
            "causes": [cleaned],
            "fixes": []
        }


# ======= New ECU Simulator Listener =======

TCP_HOST = "127.0.0.1"
TCP_PORT = 55555
dtc_queue = Queue()

def listen_to_ecu():
    """Continuously read diagnostic data from ECU simulator."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((TCP_HOST, TCP_PORT))
    print(f"✅ Connected to ECU simulator at {TCP_HOST}:{TCP_PORT}")

    while True:
        data = sock.recv(13)
        if len(data) == 13:
            arb_id, dlc, msg_data = struct.unpack('<I B 8s', data)
            payload = msg_data[:dlc]
            # Check for OBD-II DTC Response (Mode 0x43)
            if len(payload) > 1 and payload[1] == 0x43:
                for i in range(2, len(payload), 2):
                    if i + 1 < len(payload):
                        a, b = payload[i], payload[i + 1]
                        if a == 0 and b == 0:
                            continue
                        code = f"P{a:02X}{b:02X}"
                        dtc_queue.put(code)
                        print(f"📡 Received DTC: {code}")

@app.on_event("startup")
def startup_event():
    threading.Thread(target=listen_to_ecu, daemon=True).start()

@app.get("/latest_dtc")
def latest_dtc():
    """Returns the latest diagnostic trouble code (DTC) from ECU simulator."""
    if not dtc_queue.empty():
        return {"code": dtc_queue.get()}
    return {"code": None}


'''@app.websocket("/ws/dtc")
async def websocket_dtc(websocket: WebSocket):
    """Push DTC updates to Flutter in real time (optional)."""
    await websocket.accept()
    while True:
        if not dtc_queue.empty():
            code = dtc_queue.get()
            await websocket.send_json({"code": code})'''
