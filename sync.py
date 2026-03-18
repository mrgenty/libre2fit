import pandas as pd
import datetime
import requests
import os
import pickle
import tkinter as tk
from tkinter import filedialog
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/fitness.blood_glucose.write',
    'https://www.googleapis.com/auth/fitness.blood_glucose.read'
]
SYNC_FILE = "last_sync.txt"

def get_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def get_or_create_data_source(creds):
    url = "https://www.googleapis.com/fitness/v1/users/me/dataSources"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }
    
    r_get = requests.get(url, headers=headers)
    if r_get.status_code == 200:
        for ds in r_get.json().get("dataSource", []):
            app_name = ds.get("application", {}).get("name", "")
            dt_name = ds.get("dataType", {}).get("name", "")
            if app_name == "Libre Import Script" and dt_name == "com.google.blood_glucose":
                fields = ds.get("dataType", {}).get("field", [])
                return ds.get("dataStreamId"), fields
                
    print("Sorgente non trovata. Passo alla creazione.")
    payload = {
        "dataStreamName": "LibreImport",
        "type": "raw",
        "application": {"name": "Libre Import Script"},
        "dataType": {
            "name": "com.google.blood_glucose"
        },
        "device": {
            "manufacturer": "Abbott",
            "model": "FreeStyle Libre",
            "type": "scale",
            "uid": "12345678",
            "version": "1.0"
        }
    }
    
    r_post = requests.post(url, headers=headers, json=payload)
    if r_post.status_code in [200, 201]:
        ds = r_post.json()
        fields = ds.get("dataType", {}).get("field", [])
        return ds.get("dataStreamId"), fields
    else:
        print("Errore critico nella creazione della sorgente dati:", r_post.text)
        return None, None

def get_last_sync_time():
    if os.path.exists(SYNC_FILE):
        with open(SYNC_FILE, "r") as f:
            date_str = f.read().strip()
            if date_str:
                try:
                    return datetime.datetime.fromisoformat(date_str)
                except ValueError:
                    pass
    return datetime.datetime.min

def save_last_sync_time(dt):
    with open(SYNC_FILE, "w") as f:
        f.write(dt.isoformat())

def upload_glucose(dt, value_mgdl, creds, data_source_id, expected_fields):
    start_ns = int(dt.timestamp() * 1e9)
    end_ns = start_ns + int(1e9)
    dataset_id = f"{start_ns}-{end_ns}"

    value_mmol = value_mgdl / 18.01559

    if not expected_fields:
        expected_fields = [{"name": "blood_glucose_level", "format": "floatPoint"}]

    point_values = []
    for f in expected_fields:
        name = f.get("name", "")
        fmt = f.get("format", "")
        
        if name == "blood_glucose_level":
            point_values.append({"fpVal": value_mmol})
        elif name == "blood_glucose_specimen_source":
            point_values.append({"intVal": 1})
        else:
            if fmt == "integer":
                point_values.append({"intVal": 0})
            elif fmt == "floatPoint":
                point_values.append({"fpVal": 0.0})
            else:
                point_values.append({"stringVal": ""})

    body = {
        "dataSourceId": data_source_id,
        "maxEndTimeNs": end_ns,
        "minStartTimeNs": start_ns,
        "point": [{
            "startTimeNanos": str(start_ns),
            "endTimeNanos": str(end_ns),
            "dataTypeName": "com.google.blood_glucose",
            "value": point_values
        }]
    }

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }

    url = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{data_source_id}/datasets/{dataset_id}"
    r = requests.patch(url, headers=headers, json=body)

    if r.status_code not in [200, 204]:
        print(f"Errore su {dt}:", r.text)
        return False
    else:
        print(f"OK -> {dt} : {value_mgdl} mg/dL")
        return True

def main():
    creds = get_credentials()

    data_source_id, expected_fields = get_or_create_data_source(creds)
    if not data_source_id:
        print("Impossibile ottenere un DataSource ID valido. Fermo tutto.")
        return

    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Seleziona il CSV esportato da LibreView.com",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )

    if not file_path:
        print("Nessun file selezionato. Missione annullata.")
        return

    last_sync = get_last_sync_time()
    if last_sync != datetime.datetime.min:
        print(f"Ultima sincronizzazione registrata: {last_sync.strftime('%d-%m-%Y %H:%M')}")
    else:
        print("Nessuna sincronizzazione precedente trovata. Carico tutto il file...")

    df = pd.read_csv(file_path, skiprows=1)

    col_mapping = {
        "Storico del glucosio mg/dL": "Historic Glucose mg/dL",
        "Timestamp del dispositivo": "Device Timestamp"
    }
    df.rename(columns=col_mapping, inplace=True)

    if "Historic Glucose mg/dL" not in df.columns:
        print("\nErrore: Impossibile trovare la colonna della glicemia. Sicuro che sia il file giusto o hai esportato in svedese? Vedi il README per maggiori dettagli.")
        return

    df = df[df["Historic Glucose mg/dL"].notna()]

    new_last_sync = last_sync
    caricati_con_successo = 0
    ignorati = 0

    for _, row in df.iterrows():
        dt = datetime.datetime.strptime(row["Device Timestamp"], "%d-%m-%Y %H:%M")
        
        if dt > last_sync:
            value = row["Historic Glucose mg/dL"]
            success = upload_glucose(dt, value, creds, data_source_id, expected_fields)
            
            if success:
                caricati_con_successo += 1
                if dt > new_last_sync:
                    new_last_sync = dt
        else:
            ignorati += 1

    if caricati_con_successo > 0:
        save_last_sync_time(new_last_sync)
        print(f"\nImport completato! Caricati {caricati_con_successo} nuovi valori.")
        print(f"Saltati {ignorati} valori già presenti in archivio.")
    else:
        print(f"\nImport completato. Nessun nuovo dato da caricare ({ignorati} valori saltati).")

if __name__ == "__main__":
    main()
