"""
SMOKE ROOM BOT — тільки requests, без aiogram
Працює на будь-якому Python 3.7+
"""
import json, logging, os, time
from pathlib import Path
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

TOKEN    = os.getenv("BOT_TOKEN", "8707908880:AAEOZnNOBK4IG30KyQ6518NQQlhVF14BnB4")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1438736640"))
API      = f"https://api.telegram.org/bot{TOKEN}"
DB_FILE  = Path("products.json")

DEFAULT = [
    {"id":1,"cat":"liquid","name":"Рідина 1","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":2,"cat":"liquid","name":"Рідина 2","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":3,"cat":"liquid","name":"Рідина 3","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":4,"cat":"liquid","name":"Рідина 4","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":5,"cat":"liquid","name":"Рідина 5","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":6,"cat":"pod","name":"Pod-система 1","price":150,"desc":"Опис","variants":["Black","Blue","Red"]},
    {"id":7,"cat":"pod","name":"Картридж 1","price":150,"desc":"Опис","variants":["0.6Ω Mesh"]},
    {"id":9,"cat":"snus","name":"Снюс 1","price":180,"desc":"Опис","variants":["Slim","Mini"]},
    {"id":10,"cat":"snus","name":"Снюс 2","price":160,"desc":"Опис","variants":["Normal","Strong"]},
]

# ── DB ────────────────────────────────────────────────────────
def load():
    if not DB_FILE.exists(): save(DEFAULT)
    return json.loads(DB_FILE.read_text(encoding="utf-8"))

def save(data):
    DB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def find(pid):
    return next((p for p in load() if p["id"]==pid), None)

def nid():
    items = load()
    return max((p["id"] for p in items), default=0) + 1

def card(p):
    cats = {"liquid":"💧 Рідина","pod":"⚡ Система","snus":"🌿 Снюс"}
    return (f"<b>{p['name']}</b> [ID:{p['id']}]\n"
            f"Категорія: {cats.get(p['cat'],'—')}\n"
            f"Ціна: <b>{p['price']}₴</b>\n"
            f"Опис: {p['desc']}\n"
            f"Варіанти: <code>{' | '.join(p.get('variants',[]))}</code>")

# ── TELEGRAM API ──────────────────────────────────────────────
def send(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        log.error("send error: %s", e)

def edit(chat_id, msg_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{API}/editMessageText", json=payload, timeout=10)
    except Exception as e:
        log.error("edit error: %s", e)

def answer_cb(cb_id, text=""):
    try:
        requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": cb_id, "text": text}, timeout=10)
    except: pass

def delete_msg(chat_id, msg_id):
    try:
        requests.post(f"{API}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=10)
    except: pass

# ── KEYBOARDS ─────────────────────────────────────────────────
def admin_kb():
    return {"keyboard": [["📋 Товари"],["➕ Додати","🗑 Видалити"],["📊 Статистика","❌ Закрити"]], "resize_keyboard": True}

def cat_kb():
    return {"keyboard": [["💧 Рідини","⚡ Системи","🌿 Снюс"]], "resize_keyboard": True}

def remove_kb():
    return {"remove_keyboard": True}

def products_ik(items):
    icons = {"liquid":"💧","pod":"⚡","snus":"🌿"}
    return {"inline_keyboard": [[{"text": f"{icons.get(p['cat'],'📦')} {p['name']} — {p['price']}₴", "callback_data": f"ep:{p['id']}"}] for p in items]}

def edit_field_ik(pid):
    return {"inline_keyboard": [
        [{"text":"🔤 Назва","callback_data":f"ef:{pid}:name"},{"text":"💰 Ціна","callback_data":f"ef:{pid}:price"}],
        [{"text":"📝 Опис","callback_data":f"ef:{pid}:desc"},{"text":"🎨 Варіанти","callback_data":f"ef:{pid}:variants"}],
        [{"text":"◀️ Назад","callback_data":"back"}],
    ]}

def delete_ik(items):
    rows = [[{"text":f"❌ {p['name']}","callback_data":f"del:{p['id']}"}] for p in items]
    rows.append([{"text":"◀️ Скасувати","callback_data":"cancel"}])
    return {"inline_keyboard": rows}

def confirm_ik(pid):
    return {"inline_keyboard": [[{"text":"✅ Так","callback_data":f"delyes:{pid}"},{"text":"❌ Ні","callback_data":"cancel"}]]}

# ── STATE MACHINE ─────────────────────────────────────────────
# state[chat_id] = {"step": ..., "data": {...}}
state = {}

def get_state(cid): return state.get(cid, {})
def set_state(cid, step, data=None): state[cid] = {"step": step, "data": data or {}}
def clear_state(cid): state.pop(cid, None)

# ── HANDLERS ─────────────────────────────────────────────────
def handle_message(msg):
    cid  = msg["chat"]["id"]
    uid  = msg["from"]["id"]
    text = msg.get("text", "")
    st   = get_state(cid)
    step = st.get("step")
    data = st.get("data", {})

    # ── FSM: Edit value ──
    if step == "edit_value":
        field = data["field"]; pid = data["pid"]
        val = text.strip()
        items = load()
        p = next((x for x in items if x["id"]==pid), None)
        if not p: send(cid, "❌ Не знайдено"); clear_state(cid); return
        if field == "price":
            if not val.isdigit(): send(cid, "⚠️ Тільки число!"); return
            p[field] = int(val)
        elif field == "variants":
            p[field] = [v.strip() for v in val.split(",")]
        else:
            p[field] = val
        save(items); clear_state(cid)
        send(cid, f"✅ Оновлено!\n\n{card(p)}", admin_kb())
        return

    # ── FSM: Add product ──
    if step == "add_name":
        set_state(cid, "add_cat", {"name": text.strip()})
        send(cid, "Категорія:", cat_kb()); return

    if step == "add_cat":
        m = {"💧 Рідини":"liquid","⚡ Системи":"pod","🌿 Снюс":"snus"}
        cat = m.get(text)
        if not cat: send(cid, "Обери з клавіатури 👇"); return
        data["cat"] = cat; set_state(cid, "add_price", data)
        send(cid, "Ціна (число):", remove_kb()); return

    if step == "add_price":
        if not text.strip().isdigit(): send(cid, "⚠️ Тільки число!"); return
        data["price"] = int(text.strip()); set_state(cid, "add_desc", data)
        send(cid, "Опис товару:"); return

    if step == "add_desc":
        data["desc"] = text.strip(); set_state(cid, "add_variants", data)
        send(cid, "Варіанти через кому:\n<i>Приклад: 30мл·50мг, 30мл·60мг</i>"); return

    if step == "add_variants":
        items = load()
        new_p = {"id":nid(),"cat":data["cat"],"name":data["name"],"price":data["price"],
                 "desc":data["desc"],"variants":[v.strip() for v in text.split(",")]}
        items.append(new_p); save(items); clear_state(cid)
        send(cid, f"✅ Додано!\n\n{card(new_p)}", admin_kb()); return

    # ── Regular commands ──
    if text == "/start":
        send(cid, "👋 <b>Smoke Room Bot</b>\nЗамовлення приходять сюди.\nАдмін: /admin")
        return

    if text == "/admin":
        if uid != ADMIN_ID: send(cid, "⛔️ Доступ заборонено."); return
        clear_state(cid)
        send(cid, f"🔧 <b>Адмін-панель</b>\nТоварів: <b>{len(load())}</b>", admin_kb()); return

    if uid != ADMIN_ID: return  # далі тільки адмін

    if text == "❌ Закрити":
        clear_state(cid); send(cid, "Закрито.", remove_kb()); return

    if text == "📋 Товари":
        items = load()
        if not items: send(cid, "Порожньо."); return
        cats = {"liquid":[],"pod":[],"snus":[]}
        for p in items: cats.get(p["cat"],[]).append(p)
        t = "📋 <b>Всі товари:</b>\n\n"
        for cat,icon,label in [("liquid","💧","Рідини"),("pod","⚡","Системи"),("snus","🌿","Снюс")]:
            if cats[cat]:
                t += f"{icon} <b>{label}</b>\n"
                for p in cats[cat]: t += f"  • {p['name']} — {p['price']}₴\n"
                t += "\n"
        send(cid, t, products_ik(items)); return

    if text == "➕ Додати":
        set_state(cid, "add_name"); send(cid, "➕ <b>Новий товар</b>\nНазва:", remove_kb()); return

    if text == "🗑 Видалити":
        items = load()
        if not items: send(cid, "Порожньо."); return
        send(cid, "Який товар видалити?", delete_ik(items)); return

    if text == "📊 Статистика":
        items = load(); c={"liquid":0,"pod":0,"snus":0}
        for p in items: c[p.get("cat","liquid")]+=1
        send(cid, f"📊 <b>Статистика</b>\n\n💧 {c['liquid']}\n⚡ {c['pod']}\n🌿 {c['snus']}\n──\n<b>{len(items)}</b> всього"); return


def handle_callback(cb):
    cid    = cb["message"]["chat"]["id"]
    uid    = cb["from"]["id"]
    msg_id = cb["message"]["message_id"]
    d      = cb["data"]
    answer_cb(cb["id"])

    if uid != ADMIN_ID: return

    if d.startswith("ep:"):
        pid = int(d.split(":")[1]); p = find(pid)
        if not p: return
        set_state(cid, "edit_field", {"pid": pid})
        edit(cid, msg_id, f"✏️ Редагуємо:\n\n{card(p)}\n\n<b>Що змінюємо?</b>", edit_field_ik(pid)); return

    if d.startswith("ef:"):
        _, pid, field = d.split(":")
        labels={"name":"назву","price":"ціну (число)","desc":"опис","variants":"варіанти через кому"}
        set_state(cid, "edit_value", {"pid":int(pid),"field":field})
        send(cid, f"✏️ Введи нове значення для <b>{labels.get(field,field)}</b>:"); return

    if d == "back":
        clear_state(cid)
        edit(cid, msg_id, "📋 Обери товар:", products_ik(load())); return

    if d.startswith("del:"):
        pid = int(d.split(":")[1]); p = find(pid)
        if not p: return
        edit(cid, msg_id, f"⚠️ Видалити <b>{p['name']}</b> ({p['price']}₴)?", confirm_ik(pid)); return

    if d.startswith("delyes:"):
        pid = int(d.split(":")[1]); p = find(pid); items = load()
        save([x for x in items if x["id"]!=pid])
        edit(cid, msg_id, f"✅ <b>{p['name']}</b> видалено."); return

    if d == "cancel":
        delete_msg(cid, msg_id); return


# ── POLLING LOOP ──────────────────────────────────────────────
def main():
    log.info("Smoke Room Bot started. Admin: %s", ADMIN_ID)
    offset = 0
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            updates = r.json().get("result", [])
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    if "message" in u:
                        handle_message(u["message"])
                    elif "callback_query" in u:
                        handle_callback(u["callback_query"])
                except Exception as e:
                    log.error("handler error: %s", e)
        except Exception as e:
            log.error("polling error: %s", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
