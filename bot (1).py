"""
GreenInvest AI — Telegram Bot
Использует прямые HTTP запросы к Telegram API (без python-telegram-bot)
Совместим с Python 3.8+
"""
import os
import time
import logging
import requests
import anthropic

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
BASE_URL          = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Ты — GreenInvest AI, профессиональный эксперт-аналитик по инвестициям в области:

• Зелёная экономика и ESG (Environmental, Social, Governance)
• Возобновляемая энергетика (солнечная, ветровая, гидро, геотермальная, водород)
• Строительство (зелёные здания, LEED/BREEAM, энергоэффективность, PropTech)
• Экология (углеродные рынки, биоразнообразие, Water Treatment)
• Циркулярная экономика (Zero Waste, биоэкономика, Biochar, CORCs)
• Финансирование (EU Taxonomy, SFDR Article 8/9, Green Bonds, Impact Investing, PE/VC)

Правила:
- Структура: краткий вывод → детали → цифры
- Упоминай конкретные фонды, платформы (Puro.earth, EBC, EU ETS)
- Явно выделяй риски ⚠️ и возможности ✅
- Пиши на языке пользователя (русский или английский)
- В конце каждого ответа добавляй 2 вопроса под заголовком "🔍 Хотите узнать подробнее:"
"""

histories = {}

def get_history(uid):
    if uid not in histories:
        histories[uid] = []
    return histories[uid]

def tg(method, **kwargs):
    try:
        r = requests.post(f"{BASE_URL}/{method}", json=kwargs, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f"Telegram error: {e}")
        return {}

def send(chat_id, text):
    for i in range(0, len(text), 4000):
        tg("sendMessage", chat_id=chat_id, text=text[i:i+4000])

def typing(chat_id):
    tg("sendChatAction", chat_id=chat_id, action="typing")

def handle_start(chat_id, first_name):
    name = first_name or "Инвестор"
    send(chat_id,
        f"👋 Добро пожаловать, {name}!\n\n"
        "Я GreenInvest AI — аналитик по инвестициям в устойчивое развитие.\n\n"
        "🌱 Специализация:\n"
        "• Зелёная энергетика и ВИЭ\n"
        "• ESG-инвестиции и EU Taxonomy\n"
        "• Циркулярная экономика и Biochar/CORCs\n"
        "• Углеродные рынки (EU ETS, VCM)\n"
        "• Зелёное строительство (LEED, BREEAM)\n"
        "• Гранты ЕС и CleanTech проекты\n\n"
        "💬 Задайте любой вопрос!\n\n"
        "/new — новый диалог\n"
        "/help — примеры вопросов"
    )

def handle_new(chat_id, uid):
    histories[uid] = []
    send(chat_id, "🔄 Новый диалог начат. Задайте вопрос!")

def handle_help(chat_id):
    send(chat_id,
        "💡 Примеры вопросов:\n\n"
        "• Какова доходность зелёных облигаций в ЕС?\n"
        "• Как работает SFDR Article 9?\n"
        "• Что такое Biochar CORC и как зарабатывать?\n"
        "• Как получить гранты ЕС на Zero Waste проект?\n"
        "• Как оценить ROI солнечной электростанции?\n"
        "• Что даёт сертификат LEED инвестору?\n"
        "• Лучшие CleanTech фонды Европы?"
    )

def ask_ai(uid, text):
    history = get_history(uid)
    history.append({"role": "user", "content": text})
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=history
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        log.error(f"Anthropic error: {e}")
        return "⚠️ Ошибка AI. Попробуйте ещё раз или /new"

def main():
    log.info("GreenInvest AI Bot запущен ✅")
    offset = None
    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset
            data = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=40).json()
            if not data.get("ok"):
                time.sleep(3)
                continue
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg:
                    continue
                chat_id    = msg["chat"]["id"]
                uid        = msg["from"]["id"]
                first_name = msg["from"].get("first_name", "")
                text       = msg.get("text", "")
                if not text:
                    continue
                if text == "/start":
                    handle_start(chat_id, first_name)
                elif text == "/new":
                    handle_new(chat_id, uid)
                elif text == "/help":
                    handle_help(chat_id)
                else:
                    typing(chat_id)
                    reply = ask_ai(uid, text)
                    send(chat_id, reply)
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            log.error(f"Loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
