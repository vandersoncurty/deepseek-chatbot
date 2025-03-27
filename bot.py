import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from pymongo import MongoClient

load_dotenv()

PERSONALIDADE = "sério"

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

client = MongoClient(os.getenv("MONGO_URI"))
db = client.get_database()

conversas = db.conversas
personalidades = db.personalidades
usuarios = db.usuarios
instrucoes = db.instrucoes

usuarios.update_one(
    {"user_id": 996752722},
    {"$setOnInsert": {"user_id": 996752722, "username": 'admin', "grupo": 'default', "is_mod": True}},
    upsert=True
)

def is_mod(user_id: int) -> bool:
    result = usuarios.find_one({"user_id": user_id})
    return result["is_mod"] if result else False

def obter_personalidade(chat_id: int) -> str:
    result = personalidades.find_one({"chat_id": chat_id})
    return result["personalidade"] if result else "sério"

def definir_personalidade(chat_id: int, personalidade: str) -> None:
    personalidades.update_one(
        {"chat_id": chat_id},
        {"$set": {"personalidade": personalidade}},
        upsert=True
    )

def adicionar_mensagem(chat_id: int, user_id: int, username: str, message: str, role: str) -> None:
    conversas.insert_one({
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "message": message,
        "role": role,
        "timestamp": datetime.utcnow()
    })


def obter_historico(chat_id: int) -> list:
    mensagens = conversas.find({"chat_id": chat_id}).sort("timestamp", 1)
    return [{"role": msg["role"], "content": msg["message"]} for msg in mensagens]

def atualizar_nota_tratamento(user_id: int, nota: int) -> None:
    usuarios.update_one(
        {"user_id": user_id},
        {"$set": {"nota_tratamento": nota}},
        upsert=True
    )

def registrar_informacao_usuario(user_id: int, username: str, informacao: str) -> None:
    usuarios.update_one(
        {"user_id": user_id},
        {"$set": {"informacao": informacao}},
        upsert=True
    )

def obter_informacao_usuario(user_id: int) -> str:
    result = usuarios.find_one({"user_id": user_id})
    return result["informacao"] if result else None

def adicionar_instrucao(instrucao: str) -> None:
    instrucoes.insert_one({"instrucao": instrucao})

def obter_instrucoes() -> list:
    return [instrucao["instrucao"] for instrucao in instrucoes.find()]


def remover_instrucao(instrucao: str) -> None:
    instrucoes.delete_one({"instrucao": instrucao})


def gerar_resposta(chat_id: int, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json",
    }

    historico = obter_historico(chat_id)

    historico.append({"role": "user", "content": prompt})

    data = {
        "model": "deepseek-chat",
        "messages": historico,
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()

        resposta = response.json()["choices"][0]["message"]["content"]

        adicionar_mensagem(chat_id, 0, "bot", resposta, "assistant")

        return resposta
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à API do DeepSeek: {e}")
        return "Desculpe, não consegui processar sua mensagem."

def main() -> None:
    # Inicializa o bot com a API key do .env
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Registra os comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("teach", ensinar))
    application.add_handler(CommandHandler("personalidade", alterar_personalidade))
    application.add_handler(CommandHandler("instruction", instruction))
    application.add_handler(CommandHandler("config", config))
    application.add_handler(CommandHandler("set_mod", set_mod))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))

    print("Bot está rodando...")
    application.run_polling()

if __name__ == "__main__":
    main()
