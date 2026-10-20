import json
import urllib.request
from datetime import datetime

# Stazioni RFI ViaggiaTreno
# S06000 = Rimini, S05000 = Bologna Centrale

def get_station_trains(station_id):
    url = f"http://www.viaggiatreno.it/infomobilitamobile/api/m/partenze?stazione={station_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Errore durante il recupero dei dati per stazione {station_id}: {e}")
    return []

def process_trains():
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Carica lo storico esistente o creane uno nuovo
    try:
        with open("history.json", "r") as f:
            history = json.load(f)
    except Exception:
        history = {}

    if today_str not in history:
        history[today_str] = []

    existing_train_ids = {f"{t['train_no']}_{t['route']}" for t in history[today_str]}
    new_records = []

    # 1. Rilevazione Mattino Rimini -> Bologna (06:00 - 09:00)
    rn_data = get_station_trains("S06000")
    for train in rn_data:
        comp = train.get("compTipologiaTreno", [""])[0]
        num = str(train.get("numeroTreno", ""))
        category = train.get("categoria", "")
        
        # Filtro AV (Frecciarossa / Italo) diretti a Bologna
        if ("FR" in category or "AV" in category or "Italo" in comp or category == "FR"):
            sched = train.get("orarioPartenza", "")
            if sched >= "06:00" and sched <= "09:00":
                key = f"FR{num}_{'RN-BO'}"
                if key not in existing_train_ids:
                    delay = int(train.get("ritardo", 0))
                    op = "Italo" if "ITALO" in comp.upper() or "NTV" in comp.upper() else "Frecciarossa"
                    new_records.append({
                        "operator": op,
                        "train_no": f"FR{num}" if op == "Frecciarossa" else f"IT{num}",
                        "route": "RN-BO",
                        "time_sched": sched,
                        "time_actual": train.get("orarioEffettivo", sched),
                        "delay": max(0, delay)
                    })

    # 2. Rilevazione Sera Bologna -> Rimini (16:00 - 21:00)
    bo_data = get_station_trains("S05000")
    for train in bo_data:
        comp = train.get("compTipologiaTreno", [""])[0]
        num = str(train.get("numeroTreno", ""))
        category = train.get("categoria", "")

        if ("FR" in category or "AV" in category or "Italo" in comp or category == "FR"):
            sched = train.get("orarioPartenza", "")
            if sched >= "16:00" and sched <= "21:00":
                key = f"FR{num}_{'BO-RN'}"
                if key not in existing_train_ids:
                    delay = int(train.get("ritardo", 0))
                    op = "Italo" if "ITALO" in comp.upper() or "NTV" in comp.upper() else "Frecciarossa"
                    new_records.append({
                        "operator": op,
                        "train_no": f"FR{num}" if op == "Frecciarossa" else f"IT{num}",
                        "route": "BO-RN",
                        "time_sched": sched,
                        "time_actual": train.get("orarioEffettivo", sched),
                        "delay": max(0, delay)
                    })

    history[today_str].extend(new_records)

    with open("history.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"Aggiunti {len(new_records)} nuovi treni allo storico del {today_str}.")

if __name__ == "__main__":
    process_trains()
