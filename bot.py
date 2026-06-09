"""
SMOKE ROOM — Telegram Bot
Без Google Sheets. Товари зберігаються в products.json.
Редагування прямо через Telegram.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ── CONFIG ────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8707908880:AAEOZnNOBK4IG30KyQ6518NQQlhVF14BnB4")
ADMIN_ID  = int(os.getenv("ADMIN_ID", "1438736640"))
DB_FILE   = Path("products.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── PRODUCTS DB (простий JSON-файл) ──────────────────────────
def load_products() -> list:
    if not DB_FILE.exists():
        return []
    with open(DB_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_products(products: list):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def next_id(products: list) -> int:
    return max((p["id"] for p in products), default=0) + 1

def find_product(products: list, pid: int):
    return next((p for p in products if p["id"] == pid), None)


# ── ПОЧАТКОВІ ТОВАРИ (якщо файл відсутній) ───────────────────
DEFAULT_PRODUCTS = [
    {"id":1,  "cat":"liquid", "name":"Рідина 1",      "price":250, "desc":"Опис товару", "variants":["30мл·50мг","30мл·60мг"]},
    {"id":2,  "cat":"liquid", "name":"Рідина 2",      "price":250, "desc":"Опис товару", "variants":["30мл·50мг","30мл·60мг"]},
    {"id":3,  "cat":"liquid", "name":"Рідина 3",      "price":250, "desc":"Опис товару", "variants":["30мл·50мг","30мл·60мг"]},
    {"id":6,  "cat":"pod",    "name":"Pod-система 1", "price":150, "desc":"Опис товару", "variants":["Black","Blue","Red"]},
    {"id":7,  "cat":"pod",    "name":"Картридж 1",    "price":150, "desc":"Опис товару", "variants":["0.6Ω Mesh"]},
    {"id":9,  "cat":"snus",   "name":"Снюс 1",        "price":180, "desc":"Опис товару", "variants":["Slim","Mini"]},
    {"id":10, "cat":"snus",   "name":"Снюс 2",        "price":160, "desc":"Опис товару", "variants":["Normal","Strong"]},
]

if not DB_FILE.exists():
    save_products(DEFAULT_PRODUCTS)
    log.info("Створено products.json з дефолтними товарами")


# ── FSM ───────────────────────────────────────────────────────
class EditProduct(StatesGroup):
    choose_field = State()
    enter_value  = State()

class AddProduct(StatesGroup):
    name     = State()
    cat      = State()
    price    = State()
    desc     = State()
    variants = State()

class DeleteProduct(StatesGroup):
    confirm = State()


# ── KEYBOARDS ─────────────────────────────────────────────────
def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Товари")],
        [KeyboardButton(text="➕ Додати"), KeyboardButton(text="🗑 Видалити")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❌ Закрити")],
    ], resize_keyboard=True)

def cat_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💧 Рідини"), KeyboardButton(text="⚡ Системи")],
        [KeyboardButton(text="🌿 Снюс")],
    ], resize_keyboard=True)

def products_kb(products):
    rows = []
    for p in products:
        cat_icon = {"liquid":"💧","pod":"⚡","snus":"🌿"}.get(p["cat"],"📦")
        rows.append([InlineKeyboardButton(
            text=f"{cat_icon} {p['name']} — {p['price']}₴",
            callback_data=f"ep:{p['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def edit_field_kb(pid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔤 Назва",    callback_data=f"ef:{pid}:name")],
        [InlineKeyboardButton(text="💰 Ціна",     callback_data=f"ef:{pid}:price")],
        [InlineKeyboardButton(text="📝 Опис",     callback_data=f"ef:{pid}:desc")],
        [InlineKeyboardButton(text="🎨 Варіанти", callback_data=f"ef:{pid}:variants")],
        [InlineKeyboardButton(text="🏷 Категорія",callback_data=f"ef:{pid}:cat")],
        [InlineKeyboardButton(text="◀️ Назад",    callback_data="back_list")],
    ])

def delete_kb(products):
    rows = []
    for p in products:
        rows.append([InlineKeyboardButton(
            text=f"❌ {p['name']}",
            callback_data=f"del:{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Скасувати", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_kb(pid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Так",      callback_data=f"delyes:{pid}"),
        InlineKeyboardButton(text="❌ Скасувати",callback_data="cancel"),
    ]])


# ── UTILS ─────────────────────────────────────────────────────
def is_admin(uid): return uid == ADMIN_ID

def product_card(p) -> str:
    cat_label = {"liquid":"💧 Рідина","pod":"⚡ Система","snus":"🌿 Снюс"}.get(p["cat"],"📦")
    variants  = " | ".join(p.get("variants", []))
    return (
        f"<b>{p['name']}</b> [ID:{p['id']}]\n"
        f"Категорія: {cat_label}\n"
        f"Ціна: <b>{p['price']}₴</b>\n"
        f"Опис: {p['desc']}\n"
        f"Варіанти: <code>{variants}</code>"
    )


# ── BOT ───────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


# /start
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    text = (
        "👋 <b>Smoke Room Bot</b>\n\n"
        "Сюди приходять замовлення з сайту.\n\n"
        "📦 Замовлення отримуєш одразу в цей чат.\n"
        "🔧 Адмін-панель: /admin"
    )
    await msg.answer(text, parse_mode="HTML")


# /admin
@dp.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔️ Доступ заборонено."); return
    await state.clear()
    products = load_products()
    await msg.answer(
        f"🔧 <b>Адмін-панель Smoke Room</b>\n"
        f"Товарів у базі: <b>{len(products)}</b>",
        parse_mode="HTML",
        reply_markup=admin_kb()
    )


# Закрити
@dp.message(F.text == "❌ Закрити")
async def close_admin(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await state.clear()
    await msg.answer("Панель закрита.", reply_markup=ReplyKeyboardRemove())


# ── СПИСОК ТОВАРІВ ────────────────────────────────────────────
@dp.message(F.text == "📋 Товари")
async def show_products(msg: Message):
    if not is_admin(msg.from_user.id): return
    products = load_products()
    if not products:
        await msg.answer("База порожня. Додай перший товар!"); return

    # Групуємо по категоріях
    cats = {"liquid":[],"pod":[],"snus":[]}
    for p in products:
        cats.get(p["cat"], cats["liquid"]).append(p)

    text = "📋 <b>Всі товари:</b>\n\n"
    icons = {"liquid":"💧","pod":"⚡","snus":"🌿"}
    names = {"liquid":"Рідини","pod":"Системи","snus":"Снюс"}
    for cat, items in cats.items():
        if items:
            text += f"{icons[cat]} <b>{names[cat]}</b>\n"
            for p in items:
                text += f"  • {p['name']} — {p['price']}₴\n"
            text += "\n"

    await msg.answer(text, parse_mode="HTML", reply_markup=products_kb(products))


# ── РЕДАГУВАТИ: вибір товару ──────────────────────────────────
@dp.callback_query(F.data.startswith("ep:"))
async def cb_edit_pick(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️", show_alert=True); return
    pid = int(cb.data.split(":")[1])
    products = load_products()
    p = find_product(products, pid)
    if not p: await cb.answer("Товар не знайдений"); return
    await state.update_data(edit_pid=pid)
    await state.set_state(EditProduct.choose_field)
    await cb.message.edit_text(
        f"✏️ Редагуємо:\n\n{product_card(p)}\n\n<b>Що змінюємо?</b>",
        parse_mode="HTML",
        reply_markup=edit_field_kb(pid)
    )
    await cb.answer()


# ── РЕДАГУВАТИ: вибір поля ────────────────────────────────────
@dp.callback_query(F.data.startswith("ef:"))
async def cb_edit_field(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️", show_alert=True); return
    _, pid, field = cb.data.split(":")
    labels = {"name":"назву","price":"ціну (число)","desc":"опис",
              "variants":"варіанти через кому (напр: Black, Blue, Red)",
              "cat":"категорію (liquid / pod / snus)"}
    await state.update_data(edit_pid=int(pid), edit_field=field)
    await state.set_state(EditProduct.enter_value)
    await cb.message.answer(f"✏️ Введи нове значення для <b>{labels.get(field,field)}</b>:",
                            parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data == "back_list")
async def cb_back(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    products = load_products()
    await cb.message.edit_text("📋 Обери товар:", reply_markup=products_kb(products))
    await cb.answer()


# ── РЕДАГУВАТИ: збереження ────────────────────────────────────
@dp.message(EditProduct.enter_value)
async def save_edit(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    data  = await state.get_data()
    pid   = data["edit_pid"]
    field = data["edit_field"]
    value = msg.text.strip()

    products = load_products()
    p = find_product(products, pid)
    if not p:
        await msg.answer("❌ Товар не знайдений"); await state.clear(); return

    # Конвертація типів
    if field == "price":
        if not value.isdigit():
            await msg.answer("⚠️ Ціна — тільки число! Введи ще раз:"); return
        p[field] = int(value)
    elif field == "variants":
        p[field] = [v.strip() for v in value.split(",")]
    else:
        p[field] = value

    save_products(products)
    await state.clear()
    await msg.answer(
        f"✅ <b>{p['name']}</b> оновлено!\n{product_card(p)}",
        parse_mode="HTML",
        reply_markup=admin_kb()
    )


# ── ДОДАТИ ТОВАР ──────────────────────────────────────────────
@dp.message(F.text == "➕ Додати")
async def add_start(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await state.set_state(AddProduct.name)
    await msg.answer("➕ <b>Новий товар</b>\n\nВведи назву:",
                     parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

@dp.message(AddProduct.name)
async def add_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(AddProduct.cat)
    await msg.answer("Категорія:", reply_markup=cat_kb())

@dp.message(AddProduct.cat)
async def add_cat(msg: Message, state: FSMContext):
    cat_map = {"💧 Рідини":"liquid","⚡ Системи":"pod","🌿 Снюс":"snus"}
    cat = cat_map.get(msg.text)
    if not cat:
        await msg.answer("Обери категорію з клавіатури 👇"); return
    await state.update_data(cat=cat)
    await state.set_state(AddProduct.price)
    await msg.answer("Ціна (тільки число):", reply_markup=ReplyKeyboardRemove())

@dp.message(AddProduct.price)
async def add_price(msg: Message, state: FSMContext):
    if not msg.text.strip().isdigit():
        await msg.answer("⚠️ Тільки число!"); return
    await state.update_data(price=int(msg.text.strip()))
    await state.set_state(AddProduct.desc)
    await msg.answer("Опис товару:")

@dp.message(AddProduct.desc)
async def add_desc(msg: Message, state: FSMContext):
    await state.update_data(desc=msg.text.strip())
    await state.set_state(AddProduct.variants)
    await msg.answer("Варіанти через кому:\n<i>Приклад: 30мл·50мг, 30мл·60мг</i>",
                     parse_mode="HTML")

@dp.message(AddProduct.variants)
async def add_variants(msg: Message, state: FSMContext):
    data = await state.get_data()
    variants = [v.strip() for v in msg.text.split(",")]
    products = load_products()
    new_p = {
        "id":       next_id(products),
        "cat":      data["cat"],
        "name":     data["name"],
        "price":    data["price"],
        "desc":     data["desc"],
        "variants": variants,
    }
    products.append(new_p)
    save_products(products)
    await state.clear()
    await msg.answer(
        f"✅ Товар додано!\n\n{product_card(new_p)}",
        parse_mode="HTML",
        reply_markup=admin_kb()
    )


# ── ВИДАЛИТИ ТОВАР ────────────────────────────────────────────
@dp.message(F.text == "🗑 Видалити")
async def delete_start(msg: Message):
    if not is_admin(msg.from_user.id): return
    products = load_products()
    if not products:
        await msg.answer("База порожня."); return
    await msg.answer("Який товар видалити?", reply_markup=delete_kb(products))

@dp.callback_query(F.data.startswith("del:"))
async def cb_del_pick(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️", show_alert=True); return
    pid = int(cb.data.split(":")[1])
    products = load_products()
    p = find_product(products, pid)
    if not p: await cb.answer("Не знайдено"); return
    await cb.message.edit_text(
        f"⚠️ Видалити <b>{p['name']}</b> ({p['price']}₴)?\nЦю дію не можна скасувати.",
        parse_mode="HTML",
        reply_markup=confirm_kb(pid)
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("delyes:"))
async def cb_del_yes(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔️", show_alert=True); return
    pid = int(cb.data.split(":")[1])
    products = load_products()
    p = find_product(products, pid)
    if not p: await cb.answer("Не знайдено"); return
    products = [x for x in products if x["id"] != pid]
    save_products(products)
    await cb.message.edit_text(f"✅ <b>{p['name']}</b> видалено.", parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data == "cancel")
async def cb_cancel(cb: CallbackQuery):
    await cb.message.delete()
    await cb.answer("Скасовано.")


# ── СТАТИСТИКА ────────────────────────────────────────────────
@dp.message(F.text == "📊 Статистика")
async def stats(msg: Message):
    if not is_admin(msg.from_user.id): return
    products = load_products()
    cats = {"liquid":0,"pod":0,"snus":0}
    for p in products:
        cats[p.get("cat","liquid")] += 1
    await msg.answer(
        f"📊 <b>База товарів</b>\n\n"
        f"💧 Рідини: {cats['liquid']}\n"
        f"⚡ Системи: {cats['pod']}\n"
        f"🌿 Снюс: {cats['snus']}\n"
        f"──────────\n"
        f"Всього: <b>{len(products)}</b>",
        parse_mode="HTML"
    )


# ── ЗАМОВЛЕННЯ З САЙТУ ────────────────────────────────────────
# Сайт надсилає повідомлення напряму через Bot API — вони вже є в чаті.
# Цей хендлер додатково логує їх.
@dp.message(F.text.contains("Замовлення"))
async def handle_order(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        log.info(f"Нове замовлення: {msg.text[:80]}")


# ── MAIN ──────────────────────────────────────────────────────
async def main():
    log.info("Smoke Room Bot started. Admin ID: %s", ADMIN_ID)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
