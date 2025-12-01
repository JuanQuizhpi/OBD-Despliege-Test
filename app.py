from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, messaging
from datetime import datetime
import re
import random
import os, json
from generar_informe_ia import generar_informe_ia

app = Flask(__name__)

# -----------------------------
# INICIALIZAR FIREBASE (Render-friendly)
# -----------------------------
firebase_json = os.environ.get("FIREBASE_JSON")

if not firebase_json:
    raise Exception("❌ No se encontró FIREBASE_JSON en variables de entorno.")

firebase_dict = json.loads(firebase_json)
cred = credentials.Certificate(firebase_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()

# -----------------------------
# FUNCIONES AUXILIARES
# -----------------------------
def clean_string(s):
    return "".join(c for c in s if c.isalnum()).upper()

def is_valid_dtc(code):
    return bool(re.match(r'^[PCBU][0-9]{4,5}$', code))

def clean_dtc_list(dtc_list):
    cleaned = []
    for code in dtc_list:
        if not isinstance(code, str):
            continue
        c = clean_string(code)
        if is_valid_dtc(c):
            cleaned.append(c)
    return sorted(list(set(cleaned)))

def remove_duplicates_from_firestore():
    docs = db.collection("obd_data").stream()
    all_dtcs = []
    for doc in docs:
        data = doc.to_dict()
        if "dtc" in data and isinstance(data["dtc"], list):
            all_dtcs.extend(data["dtc"])
    unique_dtcs = clean_dtc_list(all_dtcs)

    batch = db.batch()
    for doc in db.collection("obd_data").stream():
        batch.delete(doc.reference)
    batch.commit()

    for code in unique_dtcs:
        db.collection("obd_data").add({
            "dtc": [code],
            "timestamp": datetime.now().isoformat()
        })

    return unique_dtcs

# -----------------------------
# NOTIFICACIONES (FCM)
# -----------------------------
def send_push_notification(title, body, codigo):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data={ "dtc": codigo },
        topic='todos'
    )
    response = messaging.send(message)
    print('Notificación enviada:', response)

# -----------------------------
# ENDPOINT: RECIBIR OBD
# -----------------------------
@app.route('/obd', methods=['POST'])
def obd_data():
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "dtc" not in data:
            return jsonify({"error": "Datos inválidos"}), 400

        data["dtc"] = clean_dtc_list(data["dtc"])
        if len(data["dtc"]) == 0:
            return jsonify({"error": "Sin códigos válidos"}), 400

        data["timestamp"] = datetime.now().isoformat()
        db.collection("obd_data").add(data)

        unique = remove_duplicates_from_firestore()

        send_push_notification(
            title="Nuevo DTC registrado",
            body=f"Código(s): {', '.join(data['dtc'])}",
            codigo=data["dtc"][0]
        )

        return jsonify({"status": "ok", "saved": data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# GET DTC ÚNICOS
# -----------------------------
@app.route('/data', methods=['GET'])
def get_data():
    try:
        docs = db.collection("obd_data").stream()
        all_dtcs = []
        for doc in docs:
            data = doc.to_dict()
            if "dtc" in data:
                all_dtcs.extend(data["dtc"])

        unique_dtcs = clean_dtc_list(all_dtcs)
        return jsonify({"unique_dtc": unique_dtcs}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# SIMULAR DTC
# -----------------------------
@app.route('/simulate', methods=['GET'])
def simulate_data():
    try:
        prefix = random.choice(["P", "C", "B", "U"])
        numbers = str(random.randint(1000, 99999))
        generated = prefix + numbers
        cleaned = clean_dtc_list([generated])

        data = {"dtc": cleaned, "timestamp": datetime.now().isoformat()}
        db.collection("obd_data").add(data)

        unique = remove_duplicates_from_firestore()

        send_push_notification(
            title="Nuevo DTC simulado",
            body=f"Código: {cleaned[0]}",
            codigo=cleaned[0]
        )

        return jsonify({"simulated": cleaned}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# VEHÍCULO
# -----------------------------
@app.route('/vehicle', methods=['POST'])
def save_vehicle():
    try:
        data = request.get_json()

        required = ["marca", "modelo", "año", "vin"]
        for key in required:
            if key not in data:
                return jsonify({"error": f"Falta el campo: {key}"}), 400

        db.collection("vehicle_config").document("config").set({
            "marca": data["marca"],
            "modelo": data["modelo"],
            "anio": data["año"],
            "vin": data["vin"],
            "timestamp": datetime.now().isoformat()
        })

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/vehicle', methods=['GET'])
def get_vehicle():
    try:
        doc = db.collection("vehicle_config").document("config").get()

        if not doc.exists:
            return jsonify({"exists": False})

        data = doc.to_dict()
        data["exists"] = True

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# GEMINI IA
# -----------------------------
@app.route('/ia/<codigo>', methods=['GET'])
def ia_dtc(codigo):
    try:
        vehiculo = db.collection("vehicle_config").document("config").get().to_dict()

        codigo = clean_string(codigo)
        if not is_valid_dtc(codigo):
            return jsonify({"error": "Código inválido"}), 400

        informe = generar_informe_ia(codigo, vehiculo)

        return jsonify({"codigo": codigo, "informe": informe}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Iniciar (solo local)
# -----------------------------
if __name__ == "__main__":
    app.run()
