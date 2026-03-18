import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

# ── Настройка логов ──────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Ключи из переменных окружения ────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Системный промпт эксперта ─────────────────────────────────
SYSTEM_PROMPT = """Ты — GreenInvest AI, профессиональный эксперт-аналитик по инвестициям в области:

• Зелёная экономика и ESG (Environmental, Social, Governance)
• Возобновляемая энергетика (солнечная, ветровая, гидро, геотермальная, водород)
• Строительство (зелёные здания, LEED/BREEAM, энергоэффективность, PropTech)
• Экология (углеродные рынки, биоразнообразие, Water Treatment)
• Циркулярная экономика (Zero Waste, биоэкономика, Biochar, CORCs)
• Финансирование (EU Taxonomy, SFDR Article 8/9, Green Bonds, Impact Investing, PE/VC)

Правила ответов:
- Структура: краткий вывод → детали → цифры
- Используй реальные данные: фонды, компании, платформы (Puro.earth, EBC, EU ETS и т.д.)
- Явно выделяй риски и возможности
- Для конкретных проектов давай практические рекомендации
- Пиши на языке пользователя (русский или английский)
- Используй эмодзи для структуры: 📊 для данных, ⚠️ для рисков, ✅ для плюсов, 💡 для советов
- В конце каждого ответа добавляй 2 коротких follow-up вопроса под заголовком "🔍 Хотите узнать подробнее:"
"""

# ── Память диалогов (по каждому пользователю отдельно) ───────
user_histories = {}

def get_history(user_id: int) -> list:
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def clear_history(user_id: int):
    user_histories[user_id] = []

# ── Команда /start ────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Инвестор"
    await update.message.reply_text(
        f"👋 Добро пожаловать, {name}!\n\n"
        "Я *GreenInvest AI* — ваш персональный аналитик по инвестициям в устойчивое развитие.\n\n"
        "🌱 *Специализация:*\n"
        "• Зелёная энергетика и ВИЭ\n"
        "• ESG-инвестиции и EU Taxonomy\n"
        "• Циркулярная экономика и Biochar\n"
        "• Углеродные рынки (EU ETS, VCM, CORCs)\n"
        "• Зелёное строительство (LEED, BREEAM)\n"
        "• Гранты ЕС и CleanTech проекты\n\n"
        "💬 Просто задайте вопрос — и я отвечу как профессиональный аналитик.\n\n"
        "📌 *Команды:*\n"
        "/start — начало\n"
        "/new — начать новый диалог\n"
        "/help — примеры вопросов",
        parse_mode="Markdown"
    )

# ── Команда /new — сбросить историю ──────────────────────────
async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await update.message.reply_text(
        "🔄 Новый диалог начат. История очищена.\n\nЗадайте ваш вопрос!"
    )

# ── Команда /help ─────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 *Примеры вопросов:*\n\n"
        "📊 *Финансы и рынки:*\n"
        "• Какова доходность зелёных облигаций в ЕС?\n"
        "• Как работает SFDR Article 9?\n"
        "• Лучшие CleanTech фонды для инвестиций\n\n"
        "🌱 *Зелёная энергетика:*\n"
        "• Как оценить ROI солнечной электростанции?\n"
        "• Перспективы водородной энергетики в 2025\n\n"
        "♻️ *Циркулярная экономика:*\n"
        "• Что такое Biochar CORC и как на этом зарабатывать?\n"
        "• Как получить гранты ЕС на Zero Waste проект?\n\n"
        "🏗️ *Строительство:*\n"
        "• Что даёт сертификат LEED инвестору?\n"
        "• Энергоэффективная реновация — где финансирование?\n\n"
        "🌍 *ESG:*\n"
        "• Как провести ESG-скоринг проекта?\n"
        "• Что такое EU Taxonomy и зачем он нужен?",
        parse_mode="Markdown"
    )

# ── Основной обработчик сообщений ────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_text = update.message.text

    # Показываем "печатает..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=history
        )
        reply = response.content[0].text

        history.append({"role": "assistant", "content": reply})

        # Telegram ограничивает 4096 символов — режем если нужно
        if len(reply) > 4096:
            reply = reply[:4090] + "...\n\n_(ответ сокращён)_"

        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка API: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при обращении к AI. Попробуйте через несколько секунд.\n"
            "Если ошибка повторяется — напишите /new и задайте вопрос заново."
        )

# ── Запуск бота ───────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new",   new_chat))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("GreenInvest AI Bot запущен ✅")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
