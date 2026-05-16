from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="RU", callback_data="lang_ru"),
        InlineKeyboardButton(text="UA", callback_data="lang_uk"),
        InlineKeyboardButton(text="EN", callback_data="lang_en"),
    ]])


def owner_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Ответить", callback_data=f"reply_{user_id}"),
        InlineKeyboardButton(text="Бан",      callback_data=f"ban_{user_id}"),
        InlineKeyboardButton(text="Разбан",   callback_data=f"unban_{user_id}"),
    ]])


def order_keyboard(user_id, item_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Принять",  callback_data=f"order_accept_{user_id}_{item_id}"),
            InlineKeyboardButton(text="Отменить", callback_data=f"order_decline_{user_id}_{item_id}"),
        ],
        [InlineKeyboardButton(text="Ответить", callback_data=f"reply_{user_id}")],
    ])


def shop_list_keyboard(items):
    rows = []
    for item_id, title, *_ in items:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"shopitem_{item_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shop_item_keyboard(item_id, lang):
    labels = {"ru": "Оформить заказ", "uk": "Оформити замовлення", "en": "Place order"}
    back   = {"ru": "Назад",          "uk": "Назад",               "en": "Back"}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=labels.get(lang, "Place order"), callback_data=f"shopbuy_{item_id}")],
        [InlineKeyboardButton(text=back.get(lang, "Back"),          callback_data="shopback")],
    ])


def owner_shop_keyboard(shop_visible: bool = False):
    status = "Скрыть магазин" if shop_visible else "Показать магазин"
    toggle_cb = "shop_hide" if shop_visible else "shop_show"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить товар", callback_data="shop_add")],
        [InlineKeyboardButton(text="Список товаров", callback_data="shop_list_owner")],
        [InlineKeyboardButton(text=status,           callback_data=toggle_cb)],
    ])


def payment_manage_keyboard(user_id, item_id, payment_visible=True):
    """Кнопки управления после принятия заказа."""
    toggle_text = "Скрыть реквизиты" if payment_visible else "Показать реквизиты"
    toggle_cb   = f"revoke_pay_{user_id}_{item_id}" if payment_visible else f"show_pay_{user_id}_{item_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)],
        [InlineKeyboardButton(text="Удалить заказ", callback_data=f"delete_order_{user_id}_{item_id}")],
    ])