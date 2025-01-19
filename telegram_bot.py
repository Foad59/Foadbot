
import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

# گرفتن توکن از متغیر محیطی
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

# API URLs
API_COIN_GECKO_URL = 'https://api.coingecko.com/api/v3/coins/markets'
API_SOLSCAN_URL = 'https://api.solscan.io/tokens'
API_SERUM_URL = 'https://api.serum.io'
API_MYSTEN_LABS_URL = 'https://api.sui.mystenlabs.com/v1/tokens'
API_SUI_EXPLORER_URL = 'https://explorer.sui.io/api'

user_data = {}

def format_volume(volume):
    if volume >= 1_000_000_000:
        return f"{volume / 1_000_000_000:.1f}B"
    elif volume >= 1_000_000:
        return f"{volume / 1_000_000:.1f}M"
    elif volume >= 1_000:
        return f"{volume / 1_000:.0f}k"
    else:
        return str(volume)

def get_tokens_from_api(api_url, params=None):
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {api_url}: {e}")
        return []

def start(update, context):
    update.message.reply_text(
        "Hello! I can help you analyze tokens based on trading volume. Choose a blockchain to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Ethereum", callback_data="ethereum")],
            [InlineKeyboardButton("Solana", callback_data="solana")],
            [InlineKeyboardButton("BNB", callback_data="bnb")],
            [InlineKeyboardButton("Polygon", callback_data="polygon")],
            [InlineKeyboardButton("Sui", callback_data="sui")]
        ])
    )

def blockchain_selected(update, context):
    query = update.callback_query
    query.answer()
    selected_blockchain = query.data.lower()
    user_data[query.message.chat_id] = {'blockchain': selected_blockchain}
    message = f"You selected {selected_blockchain.capitalize()}.
Now, please enter the time period in hours (e.g., 2 for 2 hours):"
    context.bot.send_message(query.message.chat_id, message)

def time_received(update, context):
    chat_id = update.message.chat_id
    try:
        time_period = int(update.message.text)
        if time_period <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("Please enter a positive integer for the time period.")
        return
    user_data[chat_id]['time_period'] = time_period
    update.message.reply_text("Now, please enter the percentage increase in trading volume (e.g., 50 for 50%):")

def percent_received(update, context):
    chat_id = update.message.chat_id
    try:
        percent_increase = int(update.message.text)
        if percent_increase <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("Please enter a positive integer for the percentage increase.")
        return
    user_data[chat_id]['percent_increase'] = percent_increase
    update.message.reply_text("Now, please enter the minimum market cap (e.g., 100000 for 100,000):")

def market_cap_received(update, context):
    chat_id = update.message.chat_id
    try:
        market_cap = int(update.message.text)
        if market_cap <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("Please enter a positive integer for the market cap.")
        return
    user_data[chat_id]['market_cap'] = market_cap

    blockchain = user_data[chat_id]['blockchain']
    time_period = user_data[chat_id]['time_period']
    percent_increase = user_data[chat_id]['percent_increase']
    min_market_cap = user_data[chat_id]['market_cap']

    # Fetch tokens based on the selected blockchain
    if blockchain == 'ethereum':
        tokens = get_tokens_from_api(API_COIN_GECKO_URL, params={'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 100})
    elif blockchain == 'solana':
        tokens = get_tokens_from_api(API_SOLSCAN_URL, params={'limit': 100})
    elif blockchain == 'bnb':
        tokens = get_tokens_from_api(API_COIN_GECKO_URL, params={'vs_currency': 'usd', 'category': 'bnb-chain', 'per_page': 100})
    elif blockchain == 'polygon':
        tokens = get_tokens_from_api(API_COIN_GECKO_URL, params={'vs_currency': 'usd', 'category': 'polygon', 'per_page': 100})
    elif blockchain == 'sui':
        tokens = get_tokens_from_api(API_MYSTEN_LABS_URL)

    # Process tokens
    found_tokens = []
    for token in tokens:
        symbol = token.get('symbol', 'N/A')
        volume_now = token.get('volume', 0)
        market_cap = token.get('market_cap', 0)
        price = token.get('price', 0)
        percent_change = token.get('price_change_percentage_24h', 0)

        if market_cap >= min_market_cap and percent_change >= percent_increase:
            formatted_volume = format_volume(volume_now)
            found_tokens.append(f"Token: {symbol}\nPrice: ${price}\nVolume: {formatted_volume}\nMarket Cap: {market_cap}\nChange: {percent_change:.2f}%\n")

    # Send results to the user
    if found_tokens:
        message = "\n".join(found_tokens)
    else:
        message = "No tokens found matching your criteria."
    context.bot.send_message(chat_id, message)

def main():
    updater = Updater(TELEGRAM_API_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(blockchain_selected, pattern="^(ethereum|solana|bnb|polygon|sui)$"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, time_received))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
