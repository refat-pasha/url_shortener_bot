import os
import string
import random
import asyncio
from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ===============================
# ENV VARIABLES
# ===============================
BOT_TOKEN = os.environ.get("8399469149:AAErBol5WHzM_CKkVibo4jzoo4AK8o7qU9A")
BASE_URL = os.environ.get("urlrefat.up.railway.app")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fix postgres:// issue
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ===============================
# Flask Setup
# ===============================
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ===============================
# Database Model
# ===============================
class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    original_url = db.Column(db.String(1000))
    short_code = db.Column(db.String(50), unique=True)
    clicks = db.Column(db.Integer, default=0)

# ===============================
# Utility
# ===============================
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ===============================
# Redirect
# ===============================
@app.route("/<short_code>")
def redirect_url(short_code):
    url = URL.query.filter_by(short_code=short_code).first()
    if not url:
        return "URL not found", 404

    url.clicks += 1
    db.session.commit()
    return redirect(url.original_url)

# ===============================
# Telegram Setup
# ===============================
telegram_app = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a URL to shorten.")

async def shorten(update: Update, context: ContextTypes.DEFAULT_TYPE):
    original_url = update.message.text.strip()

    short_code = generate_short_code()
    while URL.query.filter_by(short_code=short_code).first():
        short_code = generate_short_code()

    new_url = URL(
        user_id=update.effective_user.id,
        original_url=original_url,
        short_code=short_code
    )
    db.session.add(new_url)
    db.session.commit()

    short_link = f"{BASE_URL}/{short_code}"
    await update.message.reply_text(f"🔗 {short_link}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, shorten))

# ===============================
# Webhook Route
# ===============================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"

# ===============================
# Initialize
# ===============================
with app.app_context():
    db.create_all()

async def set_webhook():
    await telegram_app.bot.set_webhook(f"{BASE_URL}/{BOT_TOKEN}")

asyncio.run(set_webhook())

# ===============================
# Run
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))