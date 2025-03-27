import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["chatbot_db"]
conversas_collection = db["conversas"]
usuarios_collection = db["usuarios"]

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def gerar_resposta(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()  # Lança uma exceção para erros HTTP
        resposta = response.json()["choices"][0]["message"]["content"]
        return resposta
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à API do DeepSeek: {e}")
        return "Desculpe, não consegui processar sua mensagem."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Olá! Eu sou o ChingeChatBot.")

async def responder_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.message
    prompt = mensagem.text

    resposta = gerar_resposta(prompt)

    await mensagem.reply_text(resposta)

def main() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))

    print("Bot está rodando...")
    application.run_polling()

if __name__ == "__main__":
    main()
