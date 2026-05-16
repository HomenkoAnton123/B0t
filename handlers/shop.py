import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import bot_instance
from config import OWNER_ID
from database import (
    get_shop_items, get_shop_item, add_shop_item, delete_shop_item,
    is_shop_visible, set_shop_visible,
    save_payment_msg, get_payment_msg, clear_payment_msg
)
from texts import TEXTS
from keyboards import (
    shop_list_keyboard, shop_item_keyboard,
    owner_shop_keyboard, order_keyboard, owner_keyboard,
    payment_manage_keyboard
)
from utils import get_lang

router = Router()


class ShopAddState(StatesGroup):
    title        = State()
    description  = State()
    price        = State()
    payment_info = State()
    photo        = State()


# ── Юзер ──────────────────────────────────────────────

@router.message(Command("shop"))
async def cmd_shop(message: Message):
    uid = message.from_user.id

    if uid == OWNER_ID:
        visible = is_shop_visible()
        status  = "Магазин сейчас: <b>открыт</b>" if visible else "Магазин сейчас: <b>скрыт</b>"
        await message.answer(
            f"{status}\n\nУправление магазином:",
            parse_mode="HTML",
            reply_markup=owner_shop_keyboard(visible)
        )
        return

    lang = get_lang(uid)
    if not is_shop_visible():
        await message.answer(TEXTS[lang]["shop_hidden"])
        return

    items = get_shop_items()
    if not items:
        await message.answer(TEXTS[lang]["shop_empty"])
        return
    await message.answer(TEXTS[lang]["shop_title"], parse_mode="HTML", reply_markup=shop_list_keyboard(items))



@router.callback_query(F.data == "shop_show")
async def shop_show(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    set_shop_visible(True)
    await callback.message.edit_text(
        "Магазин сейчас: <b>открыт</b>\n\nУправление магазином:",
        parse_mode="HTML",
        reply_markup=owner_shop_keyboard(True)
    )
    await callback.answer("Магазин открыт.", show_alert=True)


@router.callback_query(F.data == "shop_hide")
async def shop_hide(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    set_shop_visible(False)
    await callback.message.edit_text(
        "Магазин сейчас: <b>скрыт</b>\n\nУправление магазином:",
        parse_mode="HTML",
        reply_markup=owner_shop_keyboard(False)
    )
    await callback.answer("Магазин скрыт.", show_alert=True)


@router.callback_query(F.data == "shopback")
async def shop_back(callback: CallbackQuery):
    uid   = callback.from_user.id
    lang  = get_lang(uid)
    items = get_shop_items()
    if not items:
        await callback.message.edit_text(TEXTS[lang]["shop_empty"])
    else:
        await callback.message.edit_text(
            TEXTS[lang]["shop_title"], parse_mode="HTML",
            reply_markup=shop_list_keyboard(items)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("shopitem_"))
async def shop_item_view(callback: CallbackQuery):
    uid     = callback.from_user.id
    lang    = get_lang(uid)
    item_id = int(callback.data.split("_")[1])
    item    = get_shop_item(item_id)

    if not item:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    _, title, description, price, payment_info, photo_id = item
    text = f"<b>{title}</b>\n\n"
    if description:
        text += f"{description}\n\n"
    text += f"<b>Цена:</b> {price}"

    kb = shop_item_keyboard(item_id, lang)
    if photo_id:
        await callback.message.delete()
        await bot_instance.bot.send_photo(uid, photo_id, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("shopbuy_"))
async def shop_buy(callback: CallbackQuery):
    uid     = callback.from_user.id
    lang    = get_lang(uid)
    item_id = int(callback.data.split("_")[1])
    item    = get_shop_item(item_id)

    if not item:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    _, title, _, price, _, _ = item
    username  = callback.from_user.username or ""
    full_name = callback.from_user.full_name or ""
    display   = f"@{username}" if username else full_name

    await bot_instance.bot.send_message(
        OWNER_ID,
        f"<b>Новый заказ</b>\n\n"
        f"Товар: {title}\n"
        f"Цена: {price}\n\n"
        f"От: {display} (<code>{uid}</code>)",
        parse_mode="HTML",
        reply_markup=order_keyboard(uid, item_id)
    )
    await callback.answer(TEXTS[lang]["order_done"], show_alert=True)


# ── Владелец — принять / отменить заказ ───────────────

@router.callback_query(F.data.startswith("order_accept_"))
async def order_accept(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    parts   = callback.data.split("_")
    user_id = int(parts[2])
    item_id = int(parts[3])
    item    = get_shop_item(item_id)
    lang    = get_lang(user_id)

    payment_info = item[4] if item else ""
    title        = item[1] if item else "товар"

    accept_texts = {
        "ru": f"Заказ принят.\n\nТовар: <b>{title}</b>",
        "uk": f"Замовлення прийнято.\n\nТовар: <b>{title}</b>",
        "en": f"Order accepted.\n\nItem: <b>{title}</b>",
    }
    text = accept_texts.get(lang, accept_texts["ru"])
    if payment_info:
        pay_label = {"ru": "Реквизиты для оплаты", "uk": "Реквізити для оплати", "en": "Payment details"}
        text += f"\n\n<b>{pay_label.get(lang, 'Payment details')}:</b>\n{payment_info}"

    try:
        sent = await bot_instance.bot.send_message(user_id, text, parse_mode="HTML")
        # Сохраняем msg_id чтобы потом можно было скрыть реквизиты
        save_payment_msg(user_id, sent.message_id, title, lang)
    except Exception:
        pass

    # Убираем кнопки заказа, добавляем кнопку "Скрыть реквизиты"
    await callback.message.edit_reply_markup(reply_markup=payment_manage_keyboard(user_id, item_id, payment_visible=True))
    await callback.answer("Заказ принят, реквизиты отправлены.", show_alert=True)


@router.callback_query(F.data.startswith("revoke_pay_"))
async def revoke_payment(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    parts   = callback.data.split("_")
    user_id = int(parts[2])
    item_id = int(parts[3])
    lang    = get_lang(user_id)

    row = get_payment_msg(user_id)
    if row:
        msg_id, title, _ = row
        revoked_texts = {
            "ru": f"Заказ: <b>{title}</b>\n\n<i>Реквизиты скрыты.</i>",
            "uk": f"Замовлення: <b>{title}</b>\n\n<i>Реквізити приховані.</i>",
            "en": f"Order: <b>{title}</b>\n\n<i>Payment details are hidden.</i>",
        }
        try:
            await bot_instance.bot.edit_message_text(
                revoked_texts.get(lang, revoked_texts["ru"]),
                chat_id=user_id,
                message_id=msg_id,
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Меняем кнопку на "Показать реквизиты"
    await callback.message.edit_reply_markup(
        reply_markup=payment_manage_keyboard(user_id, item_id, payment_visible=False)
    )
    await callback.answer("Реквизиты скрыты.", show_alert=True)


@router.callback_query(F.data.startswith("show_pay_"))
async def show_payment(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    parts   = callback.data.split("_")
    user_id = int(parts[2])
    item_id = int(parts[3])
    lang    = get_lang(user_id)
    item    = get_shop_item(item_id)

    if not item:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    payment_info = item[4] or ""
    title        = item[1]

    row = get_payment_msg(user_id)
    if row:
        msg_id, _, _ = row
        accept_texts = {
            "ru": f"Заказ принят.\n\nТовар: <b>{title}</b>",
            "uk": f"Замовлення прийнято.\n\nТовар: <b>{title}</b>",
            "en": f"Order accepted.\n\nItem: <b>{title}</b>",
        }
        text = accept_texts.get(lang, accept_texts["ru"])
        if payment_info:
            pay_label = {"ru": "Реквизиты для оплаты", "uk": "Реквізити для оплати", "en": "Payment details"}
            text += f"\n\n<b>{pay_label.get(lang, 'Payment details')}:</b>\n{payment_info}"
        try:
            await bot_instance.bot.edit_message_text(
                text,
                chat_id=user_id,
                message_id=msg_id,
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.message.edit_reply_markup(
        reply_markup=payment_manage_keyboard(user_id, item_id, payment_visible=True)
    )
    await callback.answer("Реквизиты показаны.", show_alert=True)


@router.callback_query(F.data.startswith("delete_order_"))
async def delete_order(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    parts   = callback.data.split("_")
    user_id = int(parts[2])
    item_id = int(parts[3])
    lang    = get_lang(user_id)

    # Удаляем сообщение с реквизитами у юзера
    row = get_payment_msg(user_id)
    if row:
        msg_id, title, _ = row
        deleted_texts = {
            "ru": f"Заказ: <b>{title}</b>\n\n<i>Заказ был удалён владельцем.</i>",
            "uk": f"Замовлення: <b>{title}</b>\n\n<i>Замовлення було видалено власником.</i>",
            "en": f"Order: <b>{title}</b>\n\n<i>The order has been deleted by the owner.</i>",
        }
        try:
            await bot_instance.bot.edit_message_text(
                deleted_texts.get(lang, deleted_texts["ru"]),
                chat_id=user_id,
                message_id=msg_id,
                parse_mode="HTML"
            )
        except Exception:
            pass
        clear_payment_msg(user_id)

    # Удаляем само сообщение заказа у владельца
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Заказ удалён.", show_alert=True)


@router.callback_query(F.data.startswith("order_decline_"))
async def order_decline(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    parts   = callback.data.split("_")
    user_id = int(parts[2])
    lang    = get_lang(user_id)

    decline_texts = {
        "ru": "Заказ отменён.",
        "uk": "Замовлення скасовано.",
        "en": "Order declined.",
    }
    try:
        await bot_instance.bot.send_message(user_id, decline_texts.get(lang, "Order declined."))
    except Exception:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Заказ отменён.", show_alert=True)


# ── Владелец — управление товарами ────────────────────

@router.callback_query(F.data == "shop_add")
async def shop_add_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return
    await state.set_state(ShopAddState.title)
    await callback.message.answer("Введи название товара:")
    await callback.answer()


@router.message(ShopAddState.title)
async def shop_add_title(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.update_data(title=message.text)
    await state.set_state(ShopAddState.description)
    await message.answer("Описание товара (или отправь — чтобы пропустить):")


@router.message(ShopAddState.description)
async def shop_add_description(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.update_data(description=message.text if message.text != "—" else "")
    await state.set_state(ShopAddState.price)
    await message.answer("Цена (например: 500 грн, $20):")


@router.message(ShopAddState.price)
async def shop_add_price(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.update_data(price=message.text)
    await state.set_state(ShopAddState.payment_info)
    await message.answer("Реквизиты для оплаты (или — чтобы пропустить):")


@router.message(ShopAddState.payment_info)
async def shop_add_payment(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.update_data(payment_info=message.text if message.text != "—" else "")
    await state.set_state(ShopAddState.photo)
    await message.answer("Отправь фото товара (или — чтобы без фото):")


@router.message(ShopAddState.photo)
async def shop_add_photo(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data     = await state.get_data()
    photo_id = message.photo[-1].file_id if message.photo else None
    await state.clear()
    add_shop_item(data["title"], data["description"], data["price"], data["payment_info"], photo_id)
    await message.answer(f"Товар «{data['title']}» добавлен в магазин.")


@router.callback_query(F.data == "shop_list_owner")
async def shop_list_owner(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    items = get_shop_items()
    if not items:
        await callback.answer("Магазин пуст.", show_alert=True)
        return
    lines = ["<b>Товары в магазине:</b>\n"]
    for item_id, title, _, price, _, _ in items:
        lines.append(f"• [{item_id}] {title} — {price}")
    lines.append("\nУдалить: /delitem_ID (пример: /delitem_3)")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.message(F.text.regexp(r"^/delitem_(\d+)$"))
async def shop_delete_item(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    item_id = int(message.text.split("_")[1])
    if not get_shop_item(item_id):
        await message.answer("Товар не найден.")
        return
    delete_shop_item(item_id)
    await message.answer(f"Товар [{item_id}] удалён.")