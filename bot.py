import ast
import operator
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, ADMIN_ID, EMOJIS
from database import (
    init_db,
    add_user,
    get_all_users,
    mark_blocked,
    get_stats
)


logging.basicConfig(level=logging.INFO)


def emoji(name):
    return f'<tg-emoji emoji-id="{EMOJIS[name]}">▫️</tg-emoji>'


# -----------------------------
# SAFE CALCULATOR
# -----------------------------

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_calculate(expression: str):
    expression = expression.replace("×", "*")
    expression = expression.replace("÷", "/")
    expression = expression.replace("^", "**")

    # Percentage:
    # 50% -> 0.5
    import re

    expression = re.sub(
        r'(\d+(?:\.\d+)?)%',
        r'(\1/100)',
        expression
    )

    if len(expression) > 100:
        raise ValueError

    tree = ast.parse(expression, mode="eval")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError

        if isinstance(node, ast.BinOp):
            if type(node.op) not in OPERATORS:
                raise ValueError

            left = evaluate(node.left)
            right = evaluate(node.right)

            # Prevent huge exponent calculations
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError

            return OPERATORS[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in OPERATORS:
                raise ValueError

            return OPERATORS[type(node.op)](
                evaluate(node.operand)
            )

        raise ValueError

    result = evaluate(tree)

    if not isinstance(result, (int, float)):
        raise ValueError

    if abs(result) > 10**100:
        raise ValueError

    return result


def format_result(result):
    if isinstance(result, float):
        if result.is_integer():
            return str(int(result))

        return f"{result:.12g}"

    return str(result)


# -----------------------------
# ADMIN KEYBOARD
# -----------------------------

def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{emoji('stats')} Stats",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{emoji('broadcast')} Broadcast",
                    callback_data="admin_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{emoji('users')} Users",
                    callback_data="admin_users"
                )
            ]
        ]
    )


# -----------------------------
# BOT
# -----------------------------

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# -----------------------------
# START
# -----------------------------

@dp.message(CommandStart())
async def start_handler(message: Message):

    user = message.from_user

    add_user(
        user.id,
        user.username,
        user.first_name
    )

    text = (
        f"{emoji('calculator')} <b>Calculator Bot</b>\n\n"
        f"{emoji('sparkle')} Send any valid mathematical expression.\n\n"
        f"<code>25+75</code>\n"
        f"<code>500×12%</code>\n"
        f"<code>(250+150)/2</code>\n\n"
        f"{emoji('premium')} Fast • Simple • Premium"
    )

    await message.answer(text)


# -----------------------------
# ADMIN PANEL
# -----------------------------

@dp.message(Command("admin"))
async def admin_handler(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        f"{emoji('admin')} <b>Admin Panel</b>\n\n"
        f"{emoji('settings')} Manage your bot from here.",
        reply_markup=admin_keyboard()
    )


# -----------------------------
# ADMIN CALLBACKS
# -----------------------------

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback):

    if callback.from_user.id != ADMIN_ID:
        return

    total, active, blocked = get_stats()

    text = (
        f"{emoji('stats')} <b>Bot Statistics</b>\n\n"
        f"{emoji('users')} Total Users: <b>{total}</b>\n"
        f"{emoji('growth')} Active Users: <b>{active}</b>\n"
        f"{emoji('blocked')} Blocked Users: <b>{blocked}</b>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_users")
async def admin_users(callback):

    if callback.from_user.id != ADMIN_ID:
        return

    total, active, blocked = get_stats()

    await callback.answer(
        f"Total: {total} | Active: {active} | Blocked: {blocked}",
        show_alert=True
    )


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback):

    if callback.from_user.id != ADMIN_ID:
        return

    await callback.message.answer(
        f"{emoji('broadcast')} <b>Broadcast Mode</b>\n\n"
        "Ab jo message sab users ko bhejna hai, "
        "use send karo.\n\n"
        "Cancel karne ke liye /cancel use karo."
    )

    await callback.answer()


# -----------------------------
# CANCEL
# -----------------------------

@dp.message(Command("cancel"))
async def cancel_handler(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        f"{emoji('back')} Broadcast cancelled."
    )


# -----------------------------
# BROADCAST
# -----------------------------

broadcast_mode = False


@dp.message(
    F.from_user.id == ADMIN_ID,
    F.text
)
async def admin_text_handler(message: Message):

    global broadcast_mode

    # Admin panel commands are handled separately
    if message.text.startswith("/"):
        return

    # Start broadcast when admin sends text after
    # clicking Broadcast
    if broadcast_mode:
        broadcast_mode = False

        users = get_all_users()

        sent = 0
        failed = 0

        status = await message.answer(
            f"{emoji('loading')} Broadcasting..."
        )

        for user_id in users:

            try:
                await bot.send_message(
                    user_id,
                    message.text
                )

                sent += 1

            except Exception:
                failed += 1
                mark_blocked(user_id)

            await asyncio.sleep(0.05)

        await status.edit_text(
            f"{emoji('success')} <b>Broadcast Complete</b>\n\n"
            f"{emoji('users')} Sent: <b>{sent}</b>\n"
            f"{emoji('error')} Failed: <b>{failed}</b>"
        )


# -----------------------------
# CALCULATOR
# -----------------------------

@dp.message(F.text)
async def calculator_handler(message: Message):

    user = message.from_user

    add_user(
        user.id,
        user.username,
        user.first_name
    )

    text = message.text.strip()

    # Only calculator-looking input
    allowed_chars = set(
        "0123456789+-*/().%×÷^ "
    )

    if not text:
        return

    if not all(char in allowed_chars for char in text):
        return

    # Must contain at least one number
    if not any(char.isdigit() for char in text):
        return

    try:
        result = safe_calculate(text)
        result = format_result(result)

    except Exception:
        # Invalid input silently ignored
        return

    response = (
        f"{emoji('calculator')} <b>CALCULATOR</b>\n\n"
        f"{emoji('sparkle')} <code>{text}</code>\n"
        f"━━━━━━━━━━━━━━\n"
        f"{emoji('success')} <b>{result}</b>\n\n"
        f"{emoji('premium')} <i>Calculated instantly</i>"
    )

    await message.reply(response)


# -----------------------------
# MAIN
# -----------------------------

async def main():

    init_db()

    print("Calculator Bot Started...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
