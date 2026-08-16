import ast
import asyncio
import logging
import operator
import re
from typing import Union

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import BOT_TOKEN, ADMIN_ID, custom_emoji
from database import (
    get_active_users,
    get_statistics,
    init_database,
    mark_user_blocked,
    save_user,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# VALIDATION
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing. Add BOT_TOKEN in Render Environment Variables."
    )

if ADMIN_ID <= 0:
    raise RuntimeError(
        "ADMIN_ID is missing or invalid. Add your numeric Telegram ID."
    )


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=None
)

dp = Dispatcher(storage=MemoryStorage())


# ============================================================
# ADMIN STATES
# ============================================================

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()


# ============================================================
# SAFE CALCULATOR
# ============================================================

NUMBER = Union[int, float]


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def safe_calculate(expression: str) -> NUMBER:
    expression = expression.strip()

    if not expression:
        raise ValueError

    if len(expression) > 100:
        raise ValueError

    # Friendly calculator symbols
    expression = expression.replace("×", "*")
    expression = expression.replace("÷", "/")
    expression = expression.replace("−", "-")
    expression = expression.replace("^", "**")

    # 50% -> (50/100)
    expression = re.sub(
        r"(\d+(?:\.\d+)?)%",
        r"(\1/100)",
        expression
    )

    # Only calculator characters
    if not re.fullmatch(
        r"[0-9+\-*/().%\s]+",
        expression
    ):
        raise ValueError

    tree = ast.parse(expression, mode="eval")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):
            if not is_number(node.value):
                raise ValueError

            if abs(node.value) > 10**15:
                raise ValueError

            return node.value

        if isinstance(node, ast.UnaryOp):
            operation = ALLOWED_OPERATORS.get(type(node.op))

            if operation is None:
                raise ValueError

            value = evaluate(node.operand)

            if abs(value) > 10**15:
                raise ValueError

            return operation(value)

        if isinstance(node, ast.BinOp):
            operation = ALLOWED_OPERATORS.get(type(node.op))

            if operation is None:
                raise ValueError

            left = evaluate(node.left)
            right = evaluate(node.right)

            if type(node.op) is ast.Div and right == 0:
                raise ValueError

            if type(node.op) is ast.Mod and right == 0:
                raise ValueError

            # Protect against huge calculations
            if type(node.op) is ast.Pow:
                if abs(right) > 100:
                    raise ValueError

                if abs(left) > 100000:
                    raise ValueError

            result = operation(left, right)

            if not is_number(result):
                raise ValueError

            if abs(result) > 10**100:
                raise ValueError

            return result

        raise ValueError

    return evaluate(tree)


def format_result(value: NUMBER) -> str:
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))

        return f"{value:.12g}"

    return str(value)


def looks_like_calculation(text: str) -> bool:
    text = text.strip()

    if not text:
        return False

    if len(text) > 100:
        return False

    # At least one digit
    if not any(char.isdigit() for char in text):
        return False

    # Prevent bot from touching normal messages
    return bool(
        re.fullmatch(
            r"[0-9+\-*/().%\s×÷−^]+",
            text
        )
    )


# ============================================================
# ADMIN KEYBOARD
# ============================================================

def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Statistics",
                    callback_data="admin_stats"
                ),
                InlineKeyboardButton(
                    text="📢 Broadcast",
                    callback_data="admin_broadcast"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 Users",
                    callback_data="admin_users"
                ),
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="admin_refresh"
                ),
            ],
        ]
    )


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start_command(message: Message):
    save_user(message.from_user)

    text = (
        f"{custom_emoji('calculator')} "
        "<b>Premium Calculator</b>\n\n"
        f"{custom_emoji('sparkle')} "
        "Send any valid mathematical expression.\n\n"
        "<code>25+75</code>\n"
        "<code>500×12%</code>\n"
        "<code>(250+150)/2</code>\n\n"
        f"{custom_emoji('premium')} "
        "<i>Fast • Simple • Secure</i>"
    )

    await message.answer(
        text,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# /ADMIN
# ============================================================

@dp.message(Command("admin"))
async def admin_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    total, active, blocked = get_statistics()

    text = (
        f"{custom_emoji('admin')} "
        "<b>ADMIN PANEL</b>\n\n"
        f"👥 Users: <b>{total}</b>\n"
        f"🟢 Active: <b>{active}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>\n\n"
        "Choose an option below:"
    )

    await message.answer(
        text,
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.HTML
    )


# ============================================================
# ADMIN - STATS
# ============================================================

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return

    total, active, blocked = get_statistics()

    text = (
        f"{custom_emoji('stats')} "
        "<b>BOT STATISTICS</b>\n\n"
        f"👥 Total Users: <b>{total}</b>\n"
        f"🟢 Active Users: <b>{active}</b>\n"
        f"🚫 Blocked Users: <b>{blocked}</b>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await callback.answer()


# ============================================================
# ADMIN - USERS
# ============================================================

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return

    total, active, blocked = get_statistics()

    await callback.answer(
        f"Total: {total} | Active: {active} | Blocked: {blocked}",
        show_alert=True
    )


# ============================================================
# ADMIN - REFRESH
# ============================================================

@dp.callback_query(F.data == "admin_refresh")
async def admin_refresh(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return

    total, active, blocked = get_statistics()

    text = (
        f"{custom_emoji('admin')} "
        "<b>ADMIN PANEL</b>\n\n"
        f"👥 Users: <b>{total}</b>\n"
        f"🟢 Active: <b>{active}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await callback.answer("Updated ✓")


# ============================================================
# ADMIN - BROADCAST START
# ============================================================

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(
    callback: CallbackQuery,
    state: FSMContext
):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.set_state(
        AdminStates.waiting_for_broadcast
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Cancel",
                    callback_data="broadcast_cancel"
                )
            ]
        ]
    )

    await callback.message.answer(
        f"{custom_emoji('broadcast')} "
        "<b>BROADCAST MODE</b>\n\n"
        "Ab jo message users ko bhejna hai "
        "woh send karo.\n\n"
        "Text, photo, video, document etc. bhej sakte ho.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    await callback.answer()


# ============================================================
# CANCEL BROADCAST
# ============================================================

@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext
):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.clear()

    await callback.message.answer(
        f"{custom_emoji('back')} "
        "<b>Broadcast cancelled.</b>",
        parse_mode=ParseMode.HTML
    )

    await callback.answer()


# ============================================================
# BROADCAST MESSAGE
# ============================================================

@dp.message(
    AdminStates.waiting_for_broadcast,
    F.from_user.id == ADMIN_ID
)
async def broadcast_message(
    message: Message,
    state: FSMContext
):
    users = get_active_users()

    if not users:
        await state.clear()

        await message.answer(
            "❌ No active users found."
        )

        return

    await state.clear()

    status = await message.answer(
        f"{custom_emoji('loading')} "
        "<b>Broadcasting...</b>",
        parse_mode=ParseMode.HTML
    )

    sent = 0
    failed = 0

    for user_id in users:
        try:
            await message.copy_to(
                chat_id=user_id
            )

            sent += 1

        except Exception as error:
            failed += 1

            # Usually means user blocked the bot,
            # chat unavailable, etc.
            logger.warning(
                "Broadcast failed for %s: %s",
                user_id,
                error
            )

            mark_user_blocked(user_id)

        # Telegram flood protection
        await asyncio.sleep(0.06)

    result = (
        f"{custom_emoji('success')} "
        "<b>BROADCAST COMPLETE</b>\n\n"
        f"📨 Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>"
    )

    await status.edit_text(
        result,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# CALCULATOR
# ============================================================

@dp.message(F.text)
async def calculator_message(message: Message):
    save_user(message.from_user)

    text = message.text.strip()

    # Normal messages silently ignored
    if not looks_like_calculation(text):
        return

    try:
        result = safe_calculate(text)
        result = format_result(result)

    except Exception:
        # Invalid calculations silently ignored
        return

    response = (
        f"{custom_emoji('calculator')} "
        "<b>CALCULATOR</b>\n\n"
        f"{custom_emoji('sparkle')} "
        f"<code>{text}</code>\n"
        "━━━━━━━━━━━━━━\n"
        f"{custom_emoji('success')} "
        f"<b>{result}</b>\n\n"
        f"{custom_emoji('premium')} "
        "<i>Calculated instantly</i>"
    )

    await message.reply(
        response,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# ERRORS
# ============================================================

@dp.errors()
async def global_error_handler(event):
    logger.exception(
        "Unhandled update error: %s",
        event.exception
    )


# ============================================================
# MAIN
# ============================================================

async def main():
    init_database()

    logger.info("Starting Calculator Bot...")

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
