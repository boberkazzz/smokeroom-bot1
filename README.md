# SMOKE ROOM BOT — без Google Sheets

Всі товари зберігаються у файлі `products.json`.
Редагування прямо через Telegram команди.

## Структура файлів
```
smokeroom-bot/
├── bot.py           ← основний файл
├── products.json    ← база товарів
├── requirements.txt
└── README.md
```

## Запуск локально

```bash
pip install -r requirements.txt
python bot.py
```

## Змінні середовища

Встав у середовище або просто змінні вже вшиті в код:
```
BOT_TOKEN = 8707908880:AAEOZnNOBK4IG30KyQ6518NQQlhVF14BnB4
ADMIN_ID  = 1438736640
```

## Деплой на Railway (безкоштовно)

1. Зайди на https://railway.app → Sign up через Google
2. **New Project → Deploy from GitHub**
   або **New Project → Empty Project → Add Service → GitHub Repo**
3. Завантаж файли у GitHub репо (або через drag & drop в Railway)
4. Railway автоматично запустить `python bot.py`

### Або через GitHub (найпростіше):
1. Зареєструйся на github.com
2. New repository → назва `smokeroom-bot` → Public
3. Upload files → перетягни всі 4 файли
4. На Railway: New Project → GitHub → обери репо
5. Бот запуститься автоматично ✅

## Команди адмін-панелі

| Кнопка | Дія |
|--------|-----|
| 📋 Товари | Список всіх товарів з кнопками редагування |
| ✏️ [товар] | Вибір поля: назва / ціна / опис / варіанти / категорія |
| ➕ Додати | Додати новий товар крок за кроком |
| 🗑 Видалити | Видалити товар з підтвердженням |
| 📊 Статистика | Кількість по категоріях |

## Формат products.json

```json
[
  {
    "id": 1,
    "cat": "liquid",
    "name": "Назва товару",
    "price": 250,
    "desc": "Опис",
    "variants": ["30мл·50мг", "30мл·60мг"]
  }
]
```

Категорії: `liquid` | `pod` | `snus`
