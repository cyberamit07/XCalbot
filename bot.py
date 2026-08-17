import asyncio
import logging
import sys
from contextlib import suppress
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.utils.formatting import Text, Bold, Italic, Code, Pre
from aiogram.utils.markdown import htmlescape

from config import Config
from database import Database
from calculator import Calculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize
config = Config()
db = Database(config.DATABASE_PATH)
calculator = Calculator()

# Bot and Dispatcher
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Custom emoji IDs
EMOJIS = {
    'calculator': '5893161718179173515',
    'premium': '5976721857406048634',
    'sparkle': '5893321843149902412',
    'success': '5895514131896733546',
    'error': '5893163582194978381',
    'admin': '5809838858715535455',
    'stats': '5895444149699612825',
    'users': '5902335789798265487',
    'broadcast': '5893297890117292323',
    'settings': '5902432207519093015',
    'security': '5893365724830765382',
    'bot': '5893161718179173515',
    'info': '5893290369629556374',
    'fire': '5893185207355315979',
    'growth': '5231200819986047254',
    'loading': '5893102202817352158',
    'blocked': '5893401729541608160',
    'delete': '5904542823167824187',
    'back': '5814296854380158492'
}

def format_emoji(emoji_id: str, fallback: str = "⭐") -> str:
    """Format custom emoji with fallback"""
    try:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    except Exception:
        return fallback

# Helper functions
def escape_html(text: str) -> str:
    """Escape HTML content safely"""
    return htmlexcape(str(text))

def format_result(expression: str, result: str) -> str:
    """Format calculator result with premium styling"""
    calc_emoji = format_emoji(EMOJIS['calculator'], '🧮')
    premium_emoji = format_emoji(EMOJIS['premium'], '💎')
    success_emoji = format_emoji(EMOJIS['success'], '✅')
    sparkle_emoji = format_emoji(EMOJIS['sparkle'], '✨')
    
    return f"""
{calc_emoji} <b>CALCULATOR</b> {calc_emoji}

{sparkle_emoji} <b>Expression</b>
{escape_html(expression)}

━━━━━━━━━━━━━━

{success_emoji} <b>Result</b>
{escape_html(result)}

{premium_emoji} <i>Calculated instantly</i>
"""

def format_error(error_msg: str) -> str:
    """Format error message"""
    error_emoji = format_emoji(EMOJIS['error'], '❌')
    return f"{error_emoji} <b>Error</b>\n{escape_html(error_msg)}"

# States for admin broadcast
class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

# User tracking
async def track_user(message: Message) -> None:
    """Track user in database"""
    try:
        user_data = {
            'user_id': message.from_user.id,
            'username': message.from_user.username or '',
            'first_name': message.from_user.first_name or '',
            'last_name': message.from_user.last_name or '',
            'language_code': message.from_user.language_code or '',
            'is_bot': message.from_user.is_bot or False
        }
        db.update_user(user_data)
    except Exception as e:
        logger.error(f"Error tracking user: {e}")

# Start command
@dp.message(CommandStart())
async def start_command(message: Message) -> None:
    """Handle /start command"""
    await track_user(message)
    
    calc_emoji = format_emoji(EMOJIS['calculator'], '🧮')
    sparkle_emoji = format_emoji(EMOJIS['sparkle'], '✨')
    info_emoji = format_emoji(EMOJIS['info'], 'ℹ️')
    
    welcome_text = f"""
{calc_emoji} <b>Welcome to XCalbot!</b> {calc_emoji}

{sparkle_emoji} <b>Premium Calculator</b>

Send me any mathematical expression and I'll calculate it instantly!

<b>Examples:</b>
• 25 + 75
• 100 - 25
• 50 * 5
• 500 / 10
• 500 × 12%
• (250 + 150) / 2
• 2 ^ 10
• 10% + 20%
• 100% * 500

{info_emoji} <i>Just type your expression and get the result!</i>
"""
    await message.answer(welcome_text)

# Admin command
@dp.message(Command("admin"))
async def admin_command(message: Message) -> None:
    """Handle /admin command"""
    await track_user(message)
    
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("❌ You are not authorized to use this command.")
        return
    
    await show_admin_panel(message)

async def show_admin_panel(message: Message) -> None:
    """Show admin panel"""
    admin_emoji = format_emoji(EMOJIS['admin'], '🔐')
    stats_emoji = format_emoji(EMOJIS['stats'], '📊')
    broadcast_emoji = format_emoji(EMOJIS['broadcast'], '📢')
    users_emoji = format_emoji(EMOJIS['users'], '👥')
    refresh_emoji = format_emoji(EMOJIS['sparkle'], '🔄')
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text=f"{stats_emoji} Statistics",
                callback_data="admin_stats"
            )
        ],
        [
            types.InlineKeyboardButton(
                text=f"{broadcast_emoji} Broadcast",
                callback_data="admin_broadcast"
            )
        ],
        [
            types.InlineKeyboardButton(
                text=f"{users_emoji} Users",
                callback_data="admin_users"
            )
        ],
        [
            types.InlineKeyboardButton(
                text=f"{refresh_emoji} Refresh",
                callback_data="admin_refresh"
            )
        ]
    ])
    
    await message.answer(
        f"{admin_emoji} <b>Admin Panel</b> {admin_emoji}\n\n"
        f"Welcome, {message.from_user.first_name}!",
        reply_markup=keyboard
    )

# Admin callback handler
@dp.callback_query(F.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery) -> None:
    """Handle admin callbacks"""
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("❌ Unauthorized", show_alert=True)
        await callback.message.delete()
        return
    
    await callback.answer()
    action = callback.data.split("_")[1]
    
    if action == "stats":
        await show_stats(callback.message)
    elif action == "broadcast":
        await start_broadcast(callback.message)
    elif action == "users":
        await show_users(callback.message)
    elif action == "refresh":
        await refresh_admin(callback.message)
    elif action == "cancel_broadcast":
        await cancel_broadcast(callback)

async def show_stats(message: Message) -> None:
    """Show statistics"""
    stats_emoji = format_emoji(EMOJIS['stats'], '📊')
    users_emoji = format_emoji(EMOJIS['users'], '👥')
    fire_emoji = format_emoji(EMOJIS['fire'], '🔥')
    growth_emoji = format_emoji(EMOJIS['growth'], '📈')
    
    stats = db.get_statistics()
    
    stats_text = f"""
{stats_emoji} <b>Statistics</b> {stats_emoji}

{users_emoji} <b>Total Users:</b> {stats['total']}
{fire_emoji} <b>Active Today:</b> {stats['active_today']}
{growth_emoji} <b>Joined Today:</b> {stats['joined_today']}

<b>— Blocked:</b> {stats['blocked']}
<b>— Active:</b> {stats['active']}
"""
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="🔄 Refresh",
                callback_data="admin_stats"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🔙 Back",
                callback_data="admin_back"
            )
        ]
    ])
    
    await message.edit_text(stats_text, reply_markup=keyboard)

async def show_users(message: Message) -> None:
    """Show users list"""
    users_emoji = format_emoji(EMOJIS['users'], '👥')
    users = db.get_users()
    
    if not users:
        await message.edit_text("No users found.")
        return
    
    user_text = f"{users_emoji} <b>Recent Users</b>\n\n"
    for user in users[:20]:  # Show first 20
        user_text += f"• <b>{escape_html(user['first_name'])}</b>"
        if user['username']:
            user_text += f" (@{escape_html(user['username'])})"
        user_text += f"\n  ID: <code>{user['user_id']}</code>\n"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="🔄 Refresh",
                callback_data="admin_users"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🔙 Back",
                callback_data="admin_back"
            )
        ]
    ])
    
    await message.edit_text(user_text[:4000], reply_markup=keyboard)

async def refresh_admin(message: Message) -> None:
    """Refresh admin panel"""
    await show_admin_panel(message)

async def start_broadcast(message: Message) -> None:
    """Start broadcast process"""
    broadcast_emoji = format_emoji(EMOJIS['broadcast'], '📢')
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="❌ Cancel Broadcast",
                callback_data="admin_cancel_broadcast"
            )
        ]
    ])
    
    await message.edit_text(
        f"{broadcast_emoji} <b>Broadcast Mode Active</b> {broadcast_emoji}\n\n"
        "Send me the message you want to broadcast to all users.\n\n"
        "You can send:\n"
        "• Text\n"
        "• Photo\n"
        "• Video\n"
        "• Document\n"
        "• Animation\n"
        "• Sticker\n\n"
        "<i>Click Cancel to abort.</i>",
        reply_markup=keyboard
    )
    
    await dp.fsm.set_state(message.from_user.id, BroadcastStates.waiting_for_message)

async def cancel_broadcast(callback: CallbackQuery) -> None:
    """Cancel broadcast"""
    await dp.fsm.clear_state(callback.from_user.id)
    await callback.message.edit_text("❌ Broadcast cancelled.")
    await asyncio.sleep(2)
    await show_admin_panel(callback.message)

# Broadcast message handler
@dp.message(StateFilter(BroadcastStates.waiting_for_message))
async def broadcast_message(message: Message, state: FSMContext) -> None:
    """Handle broadcast message"""
    if message.from_user.id != config.ADMIN_ID:
        return
    
    broadcast_emoji = format_emoji(EMOJIS['broadcast'], '📢')
    success_emoji = format_emoji(EMOJIS['success'], '✅')
    error_emoji = format_emoji(EMOJIS['error'], '❌')
    
    # Get all users
    users = db.get_active_users()
    if not users:
        await message.answer(f"{error_emoji} No active users found.")
        await state.clear()
        return
    
    # Send confirmation
    confirm_text = f"""
{broadcast_emoji} <b>Broadcast Confirmation</b> {broadcast_emoji}

You are about to send this message to <b>{len(users)}</b> users:

━━━━━━━━━━━━━━
{message.html_text}
━━━━━━━━━━━━━━

<i>Reply with "yes" to confirm or "no" to cancel.</i>
"""
    
    await message.answer(confirm_text)
    await state.update_data(broadcast_message=message)
    await state.set_state(BroadcastStates.waiting_for_confirmation)

@dp.message(StateFilter(BroadcastStates.waiting_for_confirmation))
async def confirm_broadcast(message: Message, state: FSMContext) -> None:
    """Handle broadcast confirmation"""
    if message.from_user.id != config.ADMIN_ID:
        return
    
    if message.text and message.text.lower() in ["yes", "y"]:
        data = await state.get_data()
        original_msg = data.get('broadcast_message')
        
        if not original_msg:
            await message.answer("❌ No message to broadcast.")
            await state.clear()
            return
        
        await message.answer("📢 Broadcasting... This may take a moment.")
        
        sent = 0
        failed = 0
        
        users = db.get_active_users()
        
        for i, user in enumerate(users):
            try:
                user_id = user['user_id']
                
                # Copy message based on type
                if original_msg.text:
                    await bot.send_message(
                        user_id,
                        original_msg.html_text,
                        parse_mode=ParseMode.HTML
                    )
                elif original_msg.photo:
                    await bot.send_photo(
                        user_id,
                        original_msg.photo[-1].file_id,
                        caption=original_msg.caption
                    )
                elif original_msg.video:
                    await bot.send_video(
                        user_id,
                        original_msg.video.file_id,
                        caption=original_msg.caption
                    )
                elif original_msg.document:
                    await bot.send_document(
                        user_id,
                        original_msg.document.file_id,
                        caption=original_msg.caption
                    )
                elif original_msg.animation:
                    await bot.send_animation(
                        user_id,
                        original_msg.animation.file_id,
                        caption=original_msg.caption
                    )
                elif original_msg.sticker:
                    await bot.send_sticker(
                        user_id,
                        original_msg.sticker.file_id
                    )
                
                sent += 1
                
                # Delay to avoid flood limits
                if i % 30 == 0:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(0.1)
                
            except Exception as e:
                failed += 1
                error_msg = str(e)
                
                # Mark user as blocked if error indicates
                if "bot was blocked by the user" in error_msg.lower() or \
                   "user is deactivated" in error_msg.lower() or \
                   "chat not found" in error_msg.lower():
                    db.set_user_blocked(user_id, True)
                
                logger.error(f"Failed to send broadcast to {user_id}: {error_msg}")
        
        # Send completion message
        result_text = f"""
📢 <b>Broadcast Complete</b> 📢

{sent} messages sent successfully
{failed} messages failed

<i>Users who blocked the bot have been marked as blocked.</i>
"""
        await message.answer(result_text)
        
        await state.clear()
        await show_admin_panel(message)
        
    elif message.text and message.text.lower() in ["no", "n"]:
        await message.answer("❌ Broadcast cancelled.")
        await state.clear()
        await show_admin_panel(message)

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery) -> None:
    """Handle back to admin panel"""
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    await show_admin_panel(callback.message)

# Calculator handler
@dp.message()
async def calculate_expression(message: Message) -> None:
    """Handle calculator expressions"""
    await track_user(message)
    
    expression = message.text.strip()
    if not expression:
        return
    
    try:
        result = calculator.calculate(expression)
        formatted_result = format_result(expression, str(result))
        await message.answer(formatted_result)
        
    except ValueError:
        # Invalid expression - silently ignore
        pass
    except Exception as e:
        logger.error(f"Calculator error: {e}")
        # Only show error for serious issues
        pass

# Error handler
@dp.errors()
async def error_handler(update: types.Update, exception: Exception) -> None:
    """Global error handler"""
    logger.error(f"Unhandled error: {exception}", exc_info=True)
    return True

# Health check server
async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="XCalBot is running")

async def health_check_ok(request):
    """Detailed health check"""
    return web.Response(text="OK")

async def start_health_server():
    """Start HTTP health server"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check_ok)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = config.PORT
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"Health server started on port {port}")
    return runner

async def on_startup() -> None:
    """Actions on startup"""
    logger.info("Starting XCalbot...")
    
    # Clear webhook to avoid conflicts
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook cleared")
    except Exception as e:
        logger.warning(f"Failed to clear webhook: {e}")
    
    # Set commands
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="admin", description="Admin panel")
    ])
    
    logger.info("Bot started successfully")

async def shutdown() -> None:
    """Graceful shutdown"""
    logger.info("Shutting down...")
    await bot.session.close()
    await dp.fsm.storage.close()
    logger.info("Shutdown complete")

async def main():
    """Main function"""
    try:
        # Start health server
        health_runner = await start_health_server()
        
        # Start bot
        await on_startup()
        await dp.start_polling(
            bot,
            skip_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
