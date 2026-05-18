import os
import json
import logging
from web3 import Web3
from web3.middleware import geth_poa_middleware
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "123456789").split(",")]
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@your_channel")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/your_channel")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
RPC_URL = os.environ.get("RPC_URL", "https://1rpc.io/matic")
USDT_CONTRACT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
REFER_BONUS = 0.01
MIN_WITHDRAW = 0.01
DB_FILE = "users.json"
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "")

# Validate required configs
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    exit(1)

# ========== STATES ==========
SET_ADDRESS, WITHDRAW_AMOUNT = range(2)

# ========== DATABASE ==========
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving DB: {e}")

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "balance": 0.0,
            "address": "",
            "referrals": 0,
            "referred_by": None,
            "total_withdrawn": 0.0
        }
        save_db(db)
    return db[uid]

def save_user(user_id, data):
    db = load_db()
    db[str(user_id)] = data
    save_db(db)

# ========== WEB3 ==========
def send_polygon_usdt(to_address, amount):
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        abi = [
            {
                "name": "transfer",
                "type": "function",
                "inputs": [
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"name": "", "type": "bool"}]
            }
        ]

        account = w3.eth.account.from_key(PRIVATE_KEY)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDT_CONTRACT),
            abi=abi
        )

        decimals = 6
        amount_in_units = int(amount * (10 ** decimals))

        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price

        txn = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_in_units
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": 100000,
            "chainId": 137
        })

        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status == 0:
            raise Exception("Transaction failed on-chain (status=0)")

        return tx_hash.hex()
    except Exception as e:
        logger.error(f"Web3 Error: {e}")
        raise

# ========== CHANNEL CHECK ==========
async def is_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in [
            ChatMember.MEMBER,
            ChatMember.ADMINISTRATOR,
            ChatMember.OWNER
        ]
    except:
        return True

# ========== KEYBOARDS ==========
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("👥 Refer", callback_data="refer"),
            InlineKeyboardButton("📊 Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton("🔄 Change Address", callback_data="change_address")
        ]
    ])

def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="menu")]
    ])

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    joined = await is_member(context.bot, user_id)
    if not joined:
        await update.message.reply_text(
            "📢 <b>আমাদের Channel Join করুন</b>\n\nBot ব্যবহার করতে Channel Join বাধ্যতামূলক।",
            parse_mode="HTML",
            reply_markup=join_keyboard()
        )
        return

    data = get_user(user_id)

    if args and not data["referred_by"]:
        try:
            ref_id = int(args[0])
            if ref_id != user_id:
                data["referred_by"] = ref_id
                save_user(user_id, data)

                ref_data = get_user(ref_id)
                ref_data["balance"] += REFER_BONUS
                ref_data["referrals"] += 1
                save_user(ref_id, ref_data)

                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=f"🎉 <b>নতুন Referral!</b>\n\n"
                             f"✅ +{REFER_BONUS} USDT আপনার balance এ যোগ হয়েছে!",
                        parse_mode="HTML"
                    )
                except:
                    pass
        except:
            pass

    if not data["address"]:
        await update.message.reply_text(
            "👋 <b>স্বাগতম!</b>\n\n"
            "📥 আপনার <b>Polygon Wallet Address</b> পাঠান:\n\n"
            "<i>উদাহরণ: 0x1234...abcd</i>",
            parse_mode="HTML"
        )
        return SET_ADDRESS

    await show_menu(update, context)
    return ConversationHandler.END

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user(user_id)
    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    text = (
        f"🤖 <b>Polygon USDT Bot</b>\n\n"
        f"💰 <b>Balance:</b> {data['balance']:.4f} USDT\n"
        f"👥 <b>Referrals:</b> {data['referrals']}\n"
        f"📍 <b>Wallet:</b> <code>{data['address'][:10]}...{data['address'][-6:]}</code>\n\n"
        f"🔗 <b>Refer Link:</b>\n<code>{ref_link}</code>"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=main_menu_keyboard()
        )

async def set_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    addr = update.message.text.strip()

    if not addr.startswith("0x") or len(addr) != 42:
        await update.message.reply_text(
            "❌ <b>ভুল Address!</b>\n\nআবার পাঠান (0x দিয়ে শুরু, ৪২ character):",
            parse_mode="HTML"
        )
        return SET_ADDRESS

    valid = "0123456789abcdefABCDEF"
    for c in addr[2:]:
        if c not in valid:
            await update.message.reply_text("❌ ভুল character! আবার পাঠান:")
            return SET_ADDRESS

    user_id = update.effective_user.id
    data = get_user(user_id)
    data["address"] = addr.lower()
    save_user(user_id, data)

    await update.message.reply_text(
        "✅ <b>Address সেট হয়েছে!</b>",
        parse_mode="HTML"
    )
    await show_menu(update, context)
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data_key = query.data

    if data_key == "menu":
        await show_menu(update, context)

    elif data_key == "check_join":
        joined = await is_member(context.bot, user_id)
        if joined:
            data = get_user(user_id)
            if not data["address"]:
                await query.edit_message_text(
                    "✅ Join Confirmed!\n\n📥 আপনার Polygon Wallet Address পাঠান:",
                    parse_mode="HTML"
                )
                context.user_data["awaiting"] = "address"
            else:
                await show_menu(update, context)
        else:
            await query.answer("❌ আগে Channel Join করুন!", show_alert=True)

    elif data_key == "balance":
        data = get_user(user_id)
        await query.edit_message_text(
            f"💼 <b>আপনার Balance</b>\n\n"
            f"💰 <b>Balance:</b> {data['balance']:.4f} USDT\n"
            f"👥 <b>Referrals:</b> {data['referrals']}\n"
            f"💵 <b>মোট Withdrawn:</b> {data['total_withdrawn']:.4f} USDT\n"
            f"🌐 <b>Network:</b> Polygon\n"
            f"💲 <b>Min Withdraw:</b> {MIN_WITHDRAW} USDT",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )

    elif data_key == "refer":
        data = get_user(user_id)
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        earned = data["referrals"] * REFER_BONUS
        await query.edit_message_text(
            f"🔗 <b>আপনার Refer Link</b>\n\n"
            f"<code>{ref_link}</code>\n\n"
            f"🎁 <b>প্রতি Refer:</b> {REFER_BONUS} USDT\n"
            f"👥 <b>মোট Refer:</b> {data['referrals']}\n"
            f"💵 <b>মোট Earned:</b> {earned:.4f} USDT\n\n"
            f"Share করুন এবং প্রতি নতুন user থেকে {REFER_BONUS} USDT পান!",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )

    elif data_key == "stats":
        data = get_user(user_id)
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        await query.edit_message_text(
            f"📊 <b>আপনার Stats</b>\n\n"
            f"💰 Balance: {data['balance']:.4f} USDT\n"
            f"👥 Referrals: {data['referrals']}\n"
            f"💵 Total Withdrawn: {data['total_withdrawn']:.4f} USDT\n"
            f"📍 Wallet: <code>{data['address']}</code>\n"
            f"🌐 Network: Polygon\n\n"
            f"🔗 Link:\n<code>{ref_link}</code>",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )

    elif data_key == "withdraw":
        data = get_user(user_id)
        if data["balance"] < MIN_WITHDRAW:
            await query.answer(
                f"❌ Minimum {MIN_WITHDRAW} USDT লাগবে। আপনার আছে {data['balance']:.4f} USDT",
                show_alert=True
            )
            return
        await query.edit_message_text(
            f"💸 <b>Withdrawal</b>\n\n"
            f"💰 Balance: {data['balance']:.4f} USDT\n"
            f"💲 Minimum: {MIN_WITHDRAW} USDT\n\n"
            f"কত USDT তুলতে চান লিখুন:\n"
            f"<i>(শুধু সংখ্যা লিখুন, যেমন: 0.5)</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="menu")]
            ])
        )
        context.user_data["awaiting"] = "withdraw"

    elif data_key == "change_address":
        await query.edit_message_text(
            "📥 নতুন Polygon Wallet Address পাঠান:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="menu")]
            ])
        )
        context.user_data["awaiting"] = "address"

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    awaiting = context.user_data.get("awaiting")

    if awaiting == "address":
        addr = text
        if not addr.startswith("0x") or len(addr) != 42:
            await update.message.reply_text("❌ ভুল Address! আবার পাঠান:")
            return

        data = get_user(user_id)
        data["address"] = addr.lower()
        save_user(user_id, data)
        context.user_data["awaiting"] = None

        await update.message.reply_text("✅ Address আপডেট হয়েছে!")
        await show_menu(update, context)

    elif awaiting == "withdraw":
        if not text.replace(".", "", 1).isdigit():
            await update.message.reply_text("❌ সঠিক সংখ্যা লিখুন:")
            return

        amount = float(text)
        data = get_user(user_id)

        if amount < MIN_WITHDRAW or amount > 1000:
            await update.message.reply_text(f"❌ Minimum {MIN_WITHDRAW} এবং Maximum 1000 USDT।")
            return

        if data["balance"] < amount:
            await update.message.reply_text("❌ Balance যথেষ্ট নেই।")
            return

        if not data["address"]:
            await update.message.reply_text("❌ আগে address সেট করুন।")
            return

        context.user_data["awaiting"] = None
        processing_msg = await update.message.reply_text("⏳ Processing... অপেক্ষা করুন।")

        try:
            tx_hash = send_polygon_usdt(data["address"], amount)

            data["balance"] -= amount
            data["total_withdrawn"] += amount
            save_user(user_id, data)

            success_text = (
                f"✅ <b>Withdrawal Successful!</b>\n\n"
                f"💰 Amount: {amount:.4f} USDT\n"
                f"🌐 Network: Polygon\n"
                f"📍 To: <code>{data['address']}</code>\n"
                f"🔗 TX:\nhttps://polygonscan.com/tx/{tx_hash}"
            )

            await processing_msg.delete()
            await update.message.reply_text(success_text, parse_mode="HTML")

            if LOG_CHANNEL:
                try:
                    await context.bot.send_message(
                        chat_id=LOG_CHANNEL,
                        text=(
                            f"💸 <b>New Withdrawal</b>\n\n"
                            f"👤 User: @{update.effective_user.username or 'N/A'} ({user_id})\n"
                            f"💰 Amount: {amount:.4f} USDT\n"
                            f"📍 To: <code>{data['address']}</code>\n"
                            f"🔗 TX: https://polygonscan.com/tx/{tx_hash}"
                        ),
                        parse_mode="HTML"
                    )
                except:
                    pass

        except Exception as e:
            await processing_msg.delete()
            await update.message.reply_text(f"❌ Withdrawal Failed.\n<code>{str(e)}</code>", parse_mode="HTML")

    elif awaiting == "broadcast":
        if user_id not in ADMIN_IDS:
            return
        context.user_data["awaiting"] = None
        db = load_db()
        success = 0
        failed = 0
        for uid in db:
            try:
                await context.bot.send_message(chat_id=int(uid), text=text, parse_mode="HTML")
                success += 1
            except:
                failed += 1
        await update.message.reply_text(
            f"📢 Broadcast Complete!\n✅ Success: {success}\n❌ Failed: {failed}"
        )

# ========== ADMIN COMMANDS ==========
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only.")
        return

    db = load_db()
    total_users = len(db)
    total_balance = sum(u["balance"] for u in db.values())
    total_withdrawn = sum(u["total_withdrawn"] for u in db.values())

    await update.message.reply_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 মোট Users: {total_users}\n"
        f"💰 মোট Balance: {total_balance:.4f} USDT\n"
        f"💸 মোট Withdrawn: {total_withdrawn:.4f} USDT\n\n"
        f"📌 <b>Admin Commands:</b>\n"
        f"/addbal [user_id] [amount]\n"
        f"/removebal [user_id] [amount]\n"
        f"/checkuser [user_id]\n"
        f"/broadcast — সবাইকে message\n"
        f"/ban [user_id]\n",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👥 Total Users", callback_data="admin_users")]
        ])
    )

async def addbal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /addbal [user_id] [amount]")
        return
    try:
        target = int(args[0])
        amount = float(args[1])
        data = get_user(target)
        data["balance"] += amount
        save_user(target, data)
        await update.message.reply_text(f"✅ {target} কে {amount} USDT দেওয়া হয়েছে।")
        try:
            await context.bot.send_message(
                chat_id=target,
                text=f"🎁 Admin আপনাকে {amount:.4f} USDT দিয়েছেন!",
                parse_mode="HTML"
            )
        except:
            pass
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def removebal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /removebal [user_id] [amount]")
        return
    try:
        target = int(args[0])
        amount = float(args[1])
        data = get_user(target)
        data["balance"] = max(0, data["balance"] - amount)
        save_user(target, data)
        await update.message.reply_text(f"✅ {target} এর {amount} USDT কাটা হয়েছে।")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def checkuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /checkuser [user_id]")
        return
    try:
        target = int(args[0])
        data = get_user(target)
        await update.message.reply_text(
            f"👤 <b>User Info</b>\n\n"
            f"🆔 ID: <code>{target}</code>\n"
            f"💰 Balance: {data['balance']:.4f} USDT\n"
            f"👥 Referrals: {data['referrals']}\n"
            f"💸 Total Withdrawn: {data['total_withdrawn']:.4f} USDT\n"
            f"📍 Wallet: <code>{data['address'] or 'Not set'}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    await update.message.reply_text("📢 Broadcast করতে চান এমন message টা পাঠান:")
    context.user_data["awaiting"] = "broadcast"

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        return

    if query.data == "admin_broadcast":
        await query.edit_message_text("📢 Broadcast message টা পাঠান:")
        context.user_data["awaiting"] = "broadcast"

    elif query.data == "admin_users":
        db = load_db()
        await query.answer(f"মোট Users: {len(db)}", show_alert=True)

# ========== MAIN ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_address)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("addbal", addbal))
    app.add_handler(CommandHandler("removebal", removebal))
    app.add_handler(CommandHandler("checkuser", checkuser))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
