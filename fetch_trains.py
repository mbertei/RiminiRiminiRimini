import json
import urllib.request
from datetime import datetime

# S06000 = Rimini, S05000 = Bologna Centrale

def get_station_trains(station_id):
    url = f"http://www.viaggiatreno.it/infomobilitamobile/api/m/partenze?stazione={station_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Errore recupero dati per stazione {station_id}: {e}")
    return []

def add_minutes_to_time(time_str, minutes):
    try:
        dt = datetime.strptime(time_str, "%H:%M")
        dt_new = dt.replace(minute=(dt.minute + minutes) % 60)
        return dt_new.strftime("%H:%M")
    except Exception:
        return time_str

def process_trains():
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        with open("history.json", "r") as f:
            history = json.load(f)
    except Exception:
        history = {}

    if today_str not in history:
        history[today_str] = []

    existing_keys = {f"{t['train_no']}_{t['route']}" for t in history[today_str]}
    new_records = []

    # 1. Mattina Rimini -> Bologna
    rn_data = get_station_trains("S06000")
    for train in rn_data:
        comp = train.get("compTipologiaTreno", [""])[0]
        num = str(train.get("numeroTreno", ""))
        category = train.get("categoria", "")
        
        if "FR" in category or "AV" in category or "Italo" in comp or category == "FR":
            dep_sched = train.get("orarioPartenza", "")
            if "06:00" <= dep_sched <= "09:00":
                op = "Italo" if ("ITALO" in comp.upper() or "NTV" in comp.upper()) else "Frecciarossa"
                train_no = f"IT{num}" if op == "Italo" else f"FR{num}"
                key = f"{train_no}_RN-BO"
                
                if key not in existing_keys:
                    dep_delay = max(0, int(train.get("ritardo", 0)))
                    dep_actual = train.get("orarioEffettivo", add_minutes_to_time(dep_sched, dep_delay))
                    
                    # Stima orario e ritardo arrivo (durata media 55m)
                    arr_sched = add_minutes_to_time(dep_sched, 55)
                    arr_delay = dep_delay  # stima
                    arr_actual = add_minutes_to_time(arr_sched, arr_delay)
                    
                    avg_delay = round((dep_delay + arr_delay) / 2.0, 1)

                    new_records.append({
                        "operator": op,
                        "train_no": train_no,
                        "route": "RN-BO",
                        "dep_sched": dep_sched,
                        "dep_actual": dep_actual,
                        "dep_delay": dep_delay,
                        "arr_sched": arr_sched,
                        "arr_actual": arr_actual,
                        "arr_delay": arr_delay,
                        "avg_delay": avg_delay
                    })

    # 2. Sera Bologna -> Rimini
    bo_data = get_station_trains("S05000")
    for train in bo_data:
        comp = train.get("compTipologiaTreno", [""])[0]
        num = str(train.get("numeroTreno", ""))
        category = train.get("categoria", "")

        if "FR" in category or "AV" in category or "Italo" in comp or category == "FR":
            dep_sched = train.get("orarioPartenza", "")
            if "16:00" <= dep_sched <= "21:00":
                op = "Italo" if ("ITALO" in comp.upper() or "NTV" in comp.upper()) else "Frecciarossa"
                train_no = f"IT{num}" if op == "Italo" else f"FR{num}"
                key = f"{train_no}_BO-RN"
                
                if key not in existing_keys:
                    dep_delay = max(0, int(train.get("ritardo", 0)))
                    dep_actual = train.get("orarioEffettivo", add_minutes_to_time(dep_sched, dep_delay))
                    
                    arr_sched = add_minutes_to_time(dep_sched, 55)
                    arr_delay = dep_delay
                    arr_actual = add_minutes_to_time(arr_sched, arr_delay)
                    
                    avg_delay = round((dep_delay + arr_delay) / 2.0, 1)

                    new_records.append({
                        "operator": op,
                        "train_no": train_no,
                        "route": "BO-RN",
                        "dep_sched": dep_sched,
                        "dep_actual": dep_actual,
                        "dep_delay": dep_delay,
                        "arr_sched": arr_sched,
                        "arr_actual": arr_actual,
                        "arr_delay": arr_delay,
                        "avg_delay": avg_delay
                    })

    history[today_str].extend(new_records)

    with open("history.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"Aggiunti {len(new_records)} nuovi treni allo storico del {today_str}.")

if __name__ == "__main__":
    process_trains()
