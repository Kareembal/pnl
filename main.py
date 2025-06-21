from telethon import TelegramClient, events, Button
from pnl_generator import draw_crypto_pro_pnl_calendar
import datetime
import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests

# ========== CONFIG ==========

API_ID = 28451499
API_HASH = 'e47bccaa1fc3760f17058a6e00ca3922'
BOT_TOKEN = '7884069612:AAHTBRggqyr5W-X4JQ76CSdxkEX0dM0xx7Q'
ADMIN_ID = 7658751974
PAYMENT_ADDRESS = "88X52XgjsNpw4aKKvft2bPuo5ZjhCQ9SChCq7LYEvG1P"
HELIUS_API_KEY = "55b9908d-e619-4bdc-82eb-76afcec80e45"
SUBSCRIBED_USERS_FILE = "subscribed.txt"
WALLET_DIR = "wallets"

bot = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
scheduler = AsyncIOScheduler()

# ========== HELPERS ==========

def is_subscribed(user_id):
    if str(user_id) == str(ADMIN_ID):
        return True
    if not os.path.exists(SUBSCRIBED_USERS_FILE):
        return False
    with open(SUBSCRIBED_USERS_FILE, "r") as f:
        return str(user_id) in f.read()

def add_subscription(user_id):
    with open(SUBSCRIBED_USERS_FILE, "a") as f:
        f.write(str(user_id) + "\n")

def get_user_wallets(user_id):
    os.makedirs(WALLET_DIR, exist_ok=True)
    path = f"{WALLET_DIR}/{user_id}.txt"
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def add_wallet(user_id, address):
    os.makedirs(WALLET_DIR, exist_ok=True)
    with open(f"{WALLET_DIR}/{user_id}.txt", "a") as f:
        f.write(address + "\n")

def get_sol_usd():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd").json()
        return float(data["solana"]["usd"])
    except:
        return 0.0

def fetch_sol_transactions(wallet):
    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transfers?api-key={HELIUS_API_KEY}&type=SOL"
    try:
        res = requests.get(url)
        data = res.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "transfers" in data:
            return data["transfers"]
        else:
            return []
    except:
        return []

def compute_sol_pnl(wallets):
    daily = {}
    sol_usd = get_sol_usd()
    for wallet in wallets:
        txns = fetch_sol_transactions(wallet)
        for tx in txns:
            date = datetime.datetime.fromisoformat(tx["timestamp"].replace("Z", "")).date()
            amount = float(tx["amount"])
            direction = tx["direction"]
            net = amount if direction == "in" else -amount
            daily[date] = daily.get(date, 0) + (net * sol_usd)
    return daily

def summarize_pnl(pnl_data):
    total = sum(pnl_data.values())
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_pnl = pnl_data.get(yesterday, 0)
    def fmt(val):
        abs_val = abs(val)
        if abs_val >= 1_000_000:
            return f"{val / 1_000_000:.2f}M"
        elif abs_val >= 1_000:
            return f"{val / 1_000:.2f}K"
        return f"{val:.2f}"
    return f"🧾 Total PNL this month: {fmt(total)}$\n📉 Yesterday: {fmt(yesterday_pnl)}$"

async def send_daily_cards():
    if not os.path.exists(SUBSCRIBED_USERS_FILE):
        return
    with open(SUBSCRIBED_USERS_FILE, "r") as f:
        user_ids = [int(u.strip()) for u in f.readlines() if u.strip()]
    for user_id in user_ids:
        try:
            wallets = get_user_wallets(user_id)
            if not wallets:
                continue
            user = await bot.get_entity(user_id)
            username = user.username or f"user{user.id}"
            pnl_data = compute_sol_pnl(wallets)
            image_path = draw_crypto_pro_pnl_calendar(pnl_data, username)
            summary = summarize_pnl(pnl_data)
            await bot.send_file(user_id, image_path, caption=f"{summary}\n\n📆 Your daily xPNL update.")
        except Exception as e:
            print(f"Failed to send to {user_id}: {e}")

# ========== COMMANDS ==========

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    if is_subscribed(user_id):
        await event.respond("👋 Welcome back to xPNL!\nUse /pnlcard to generate your PNL calendar instantly.")
    else:
        await event.respond(
            f"💸 Access to xPNL costs *$50 USDC in SOL*.\nSend payment to:\n\n`{PAYMENT_ADDRESS}`\n\n"
            "After sending, click below:",
            buttons=[[Button.text("✅ I've Paid")]],
            parse_mode='md'
        )

@bot.on(events.NewMessage(pattern="✅ I've Paid"))
async def confirm_payment(event):
    user_id = event.sender_id
    if not is_subscribed(user_id):
        add_subscription(user_id)
        await event.respond("✅ Subscription confirmed!\nYou can now use /pnlcard anytime.")
    else:
        await event.respond("✅ You are already subscribed.")

@bot.on(events.NewMessage(pattern='/addwallet (.+)'))
async def addwallet(event):
    user_id = event.sender_id
    wallet = event.pattern_match.group(1)
    add_wallet(user_id, wallet)
    await event.respond(f"✅ Wallet `{wallet}` added.", parse_mode='md')

@bot.on(events.NewMessage(pattern='/pnlcard'))
async def handle_pnlcard(event):
    user = await event.get_sender()
    user_id = user.id
    username = user.username or f"user{user.id}"

    if not is_subscribed(user_id):
        await event.respond("❌ You need to subscribe to use this feature.\nUse /start to get started.")
        return

    wallets = get_user_wallets(user_id)
    if not wallets:
        await event.respond("❗ You haven't added any wallets yet. Use /addwallet <address>.")
        return

    await event.respond("📆 Generating your PNL calendar...")
    pnl_data = compute_sol_pnl(wallets)
    image_path = draw_crypto_pro_pnl_calendar(pnl_data, username)
    summary = summarize_pnl(pnl_data)
    await bot.send_file(event.chat_id, image_path, caption=f"{summary}\n\n✅ Your PNL calendar, powered by xPNL.")

@bot.on(events.NewMessage(pattern='/giveaccess'))
async def give_access(event):
    if event.sender_id != ADMIN_ID:
        await event.respond("⛔ Only the admin can use this command.")
        return
    try:
        target_id = int(event.message.message.split(' ')[1])
        add_subscription(target_id)
        await event.respond(f"✅ Access granted to user ID: {target_id}")
    except:
        await event.respond("❌ Usage: /giveaccess 123456789")

@bot.on(events.NewMessage(pattern='/subscribers'))
async def list_subscribers(event):
    if event.sender_id != ADMIN_ID:
        await event.respond("⛔ Only the admin can use this command.")
        return
    if not os.path.exists(SUBSCRIBED_USERS_FILE):
        await event.respond("No subscribers yet.")
        return
    with open(SUBSCRIBED_USERS_FILE, "r") as f:
        users = f.readlines()
    await event.respond(f"📋 Subscribers ({len(users)}):\n" + ''.join(users))

@bot.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    await event.respond("""
🤖 *xPNL Bot Commands:*

/start - Begin or resume access
/pnlcard - Generate your latest PNL calendar
/addwallet <address> - Track a Solana wallet
/help - Show this help message

*Admin Only:*
/giveaccess <user_id>
/subscribers
    """, parse_mode='md')

# ========== SCHEDULER ==========

scheduler.add_job(send_daily_cards, 'cron', hour=9, minute=0)

# ========== RUN ==========

async def main():
    scheduler.start()
    print("✅ Bot is running...")
    await bot.run_until_disconnected()

asyncio.get_event_loop().run_until_complete(main())
