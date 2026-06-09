"""
SMOKE ROOM — Telegram Bot (aiogram 2.x — без pydantic)
"""
import asyncio, json, logging, os
from pathlib import Path
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8707908880:AAEOZnNOBK4IG30KyQ6518NQQlhVF14BnB4")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "1438736640"))
DB_FILE   = Path("products.json")

DEFAULT = [
    {"id":1,"cat":"liquid","name":"Рідина 1","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":2,"cat":"liquid","name":"Рідина 2","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":3,"cat":"liquid","name":"Рідина 3","price":250,"desc":"Опис","variants":["30мл·50мг","30мл·60мг"]},
    {"id":6,"cat":"pod","name":"Pod-система 1","price":150,"desc":"Опис","variants":["Black","Blue"]},
    {"id":7,"cat":"pod","name":"Картридж 1","price":150,"desc":"Опис","variants":["0.6Ω Mesh"]},
    {"id":9,"cat":"snus","name":"Снюс 1","price":180,"desc":"Опис","variants":["Slim","Mini"]},
    {"id":10,"cat":"snus","name":"Снюс 2","price":160,"desc":"Опис","variants":["Normal","Strong"]},
]

def load():
    if not DB_FILE.exists(): save(DEFAULT)
    with open(DB_FILE, encoding="utf-8") as f: return json.load(f)

def save(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def find(pid): return next((p for p in load() if p["id"]==pid), None)
def nid(): items=load(); return max((p["id"] for p in items),default=0)+1
def is_admin(uid): return uid==ADMIN_ID

def card(p):
    cats={"liquid":"💧 Рідина","pod":"⚡ Система","snus":"🌿 Снюс"}
    return (f"<b>{p['name']}</b> [ID:{p['id']}]\n"
            f"Категорія: {cats.get(p['cat'],'—')}\n"
            f"Ціна: <b>{p['price']}₴</b>\n"
            f"Опис: {p['desc']}\n"
            f"Варіанти: <code>{' | '.join(p.get('variants',[]))}</code>")

class Edit(StatesGroup):
    field=State(); value=State()
class Add(StatesGroup):
    name=State(); cat=State(); price=State(); desc=State(); variants=State()

bot=Bot(token=BOT_TOKEN,parse_mode="HTML")
dp=Dispatcher(bot,storage=MemoryStorage())

def admin_kb():
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📋 Товари"); kb.add("➕ Додати","🗑 Видалити"); kb.add("📊 Статистика","❌ Закрити"); return kb

def cat_kb():
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True); kb.add("💧 Рідини","⚡ Системи","🌿 Снюс"); return kb

def products_ik(items):
    kb=types.InlineKeyboardMarkup(); icons={"liquid":"💧","pod":"⚡","snus":"🌿"}
    for p in items: kb.add(types.InlineKeyboardButton(f"{icons.get(p['cat'],'📦')} {p['name']} — {p['price']}₴",callback_data=f"ep:{p['id']}"))
    return kb

def edit_field_ik(pid):
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🔤 Назва",callback_data=f"ef:{pid}:name"),
           types.InlineKeyboardButton("💰 Ціна",callback_data=f"ef:{pid}:price"),
           types.InlineKeyboardButton("📝 Опис",callback_data=f"ef:{pid}:desc"),
           types.InlineKeyboardButton("🎨 Варіанти",callback_data=f"ef:{pid}:variants"))
    kb.add(types.InlineKeyboardButton("◀️ Назад",callback_data="back")); return kb

def delete_ik(items):
    kb=types.InlineKeyboardMarkup()
    for p in items: kb.add(types.InlineKeyboardButton(f"❌ {p['name']}",callback_data=f"del:{p['id']}"))
    kb.add(types.InlineKeyboardButton("◀️ Скасувати",callback_data="cancel")); return kb

def confirm_ik(pid):
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("✅ Так",callback_data=f"delyes:{pid}"),
           types.InlineKeyboardButton("❌ Ні",callback_data="cancel")); return kb

@dp.message_handler(commands="start")
async def cmd_start(msg:types.Message):
    await msg.answer("👋 <b>Smoke Room Bot</b>\nЗамовлення приходять сюди.\nАдмін: /admin")

@dp.message_handler(commands="admin",state="*")
async def cmd_admin(msg:types.Message,state:FSMContext):
    if not is_admin(msg.from_user.id): await msg.answer("⛔️"); return
    await state.finish()
    await msg.answer(f"🔧 <b>Адмін-панель</b>\nТоварів: <b>{len(load())}</b>",reply_markup=admin_kb())

@dp.message_handler(lambda m:m.text=="❌ Закрити",state="*")
async def close(msg:types.Message,state:FSMContext):
    if not is_admin(msg.from_user.id): return
    await state.finish(); await msg.answer("Закрито.",reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda m:m.text=="📋 Товари")
async def show(msg:types.Message):
    if not is_admin(msg.from_user.id): return
    items=load()
    if not items: await msg.answer("Порожньо."); return
    cats={"liquid":[],"pod":[],"snus":[]}
    for p in items: cats.get(p["cat"],[]).append(p)
    text="📋 <b>Всі товари:</b>\n\n"
    for cat,icon,label in [("liquid","💧","Рідини"),("pod","⚡","Системи"),("snus","🌿","Снюс")]:
        if cats[cat]:
            text+=f"{icon} <b>{label}</b>\n"
            for p in cats[cat]: text+=f"  • {p['name']} — {p['price']}₴\n"
            text+="\n"
    await msg.answer(text,reply_markup=products_ik(items))

@dp.callback_query_handler(lambda c:c.data.startswith("ep:"),state="*")
async def cb_ep(cb:types.CallbackQuery,state:FSMContext):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️",show_alert=True); return
    pid=int(cb.data.split(":")[1]); p=find(pid)
    if not p: await cb.answer("Не знайдено"); return
    await state.update_data(pid=pid); await Edit.field.set()
    await cb.message.edit_text(f"✏️ Редагуємо:\n\n{card(p)}\n\n<b>Що змінюємо?</b>",reply_markup=edit_field_ik(pid))
    await cb.answer()

@dp.callback_query_handler(lambda c:c.data=="back",state="*")
async def cb_back(cb:types.CallbackQuery,state:FSMContext):
    await state.finish(); await cb.message.edit_text("📋 Обери товар:",reply_markup=products_ik(load())); await cb.answer()

@dp.callback_query_handler(lambda c:c.data.startswith("ef:"),state=Edit.field)
async def cb_ef(cb:types.CallbackQuery,state:FSMContext):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️",show_alert=True); return
    _,pid,field=cb.data.split(":")
    labels={"name":"назву","price":"ціну (число)","desc":"опис","variants":"варіанти через кому"}
    await state.update_data(pid=int(pid),field=field); await Edit.value.set()
    await cb.message.answer(f"✏️ Введи нове значення для <b>{labels.get(field,field)}</b>:"); await cb.answer()

@dp.message_handler(state=Edit.value)
async def save_edit(msg:types.Message,state:FSMContext):
    if not is_admin(msg.from_user.id): return
    data=await state.get_data(); pid=data["pid"]; field=data["field"]; val=msg.text.strip()
    items=load(); p=next((x for x in items if x["id"]==pid),None)
    if not p: await msg.answer("❌"); await state.finish(); return
    if field=="price":
        if not val.isdigit(): await msg.answer("⚠️ Тільки число!"); return
        p[field]=int(val)
    elif field=="variants": p[field]=[v.strip() for v in val.split(",")]
    else: p[field]=val
    save(items); await state.finish()
    await msg.answer(f"✅ Оновлено!\n\n{card(p)}",reply_markup=admin_kb())

@dp.message_handler(lambda m:m.text=="➕ Додати")
async def add_start(msg:types.Message):
    if not is_admin(msg.from_user.id): return
    await Add.name.set(); await msg.answer("➕ <b>Новий товар</b>\nНазва:",reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=Add.name)
async def add_name(msg:types.Message,state:FSMContext):
    await state.update_data(name=msg.text.strip()); await Add.cat.set(); await msg.answer("Категорія:",reply_markup=cat_kb())

@dp.message_handler(state=Add.cat)
async def add_cat(msg:types.Message,state:FSMContext):
    m={"💧 Рідини":"liquid","⚡ Системи":"pod","🌿 Снюс":"snus"}
    cat=m.get(msg.text)
    if not cat: await msg.answer("Обери з клавіатури 👇"); return
    await state.update_data(cat=cat); await Add.price.set(); await msg.answer("Ціна:",reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=Add.price)
async def add_price(msg:types.Message,state:FSMContext):
    if not msg.text.strip().isdigit(): await msg.answer("⚠️ Тільки число!"); return
    await state.update_data(price=int(msg.text.strip())); await Add.desc.set(); await msg.answer("Опис:")

@dp.message_handler(state=Add.desc)
async def add_desc(msg:types.Message,state:FSMContext):
    await state.update_data(desc=msg.text.strip()); await Add.variants.set()
    await msg.answer("Варіанти через кому:\n<i>Приклад: 30мл·50мг, 30мл·60мг</i>")

@dp.message_handler(state=Add.variants)
async def add_variants(msg:types.Message,state:FSMContext):
    data=await state.get_data(); items=load()
    new_p={"id":nid(),"cat":data["cat"],"name":data["name"],"price":data["price"],"desc":data["desc"],"variants":[v.strip() for v in msg.text.split(",")]}
    items.append(new_p); save(items); await state.finish()
    await msg.answer(f"✅ Додано!\n\n{card(new_p)}",reply_markup=admin_kb())

@dp.message_handler(lambda m:m.text=="🗑 Видалити")
async def del_start(msg:types.Message):
    if not is_admin(msg.from_user.id): return
    items=load()
    if not items: await msg.answer("Порожньо."); return
    await msg.answer("Який товар видалити?",reply_markup=delete_ik(items))

@dp.callback_query_handler(lambda c:c.data.startswith("del:"))
async def cb_del(cb:types.CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️",show_alert=True); return
    pid=int(cb.data.split(":")[1]); p=find(pid)
    if not p: await cb.answer("Не знайдено"); return
    await cb.message.edit_text(f"⚠️ Видалити <b>{p['name']}</b> ({p['price']}₴)?",reply_markup=confirm_ik(pid)); await cb.answer()

@dp.callback_query_handler(lambda c:c.data.startswith("delyes:"))
async def cb_del_yes(cb:types.CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️",show_alert=True); return
    pid=int(cb.data.split(":")[1]); p=find(pid); items=load()
    save([x for x in items if x["id"]!=pid])
    await cb.message.edit_text(f"✅ <b>{p['name']}</b> видалено."); await cb.answer()

@dp.callback_query_handler(lambda c:c.data=="cancel")
async def cb_cancel(cb:types.CallbackQuery):
    await cb.message.delete(); await cb.answer("Скасовано.")

@dp.message_handler(lambda m:m.text=="📊 Статистика")
async def stats(msg:types.Message):
    if not is_admin(msg.from_user.id): return
    items=load(); c={"liquid":0,"pod":0,"snus":0}
    for p in items: c[p.get("cat","liquid")]+=1
    await msg.answer(f"📊 <b>Статистика</b>\n\n💧 Рідини: {c['liquid']}\n⚡ Системи: {c['pod']}\n🌿 Снюс: {c['snus']}\n──\nВсього: <b>{len(items)}</b>")

if __name__=="__main__":
    log.info("Bot started. Admin: %s",ADMIN_ID)
    executor.start_polling(dp,skip_updates=True)
