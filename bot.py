import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from pymongo import MongoClient

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Variável global para armazenar a personalidade do bot
PERSONALIDADE = "sério"

# URL da API do DeepSeek
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Conecta ao MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client.get_database()

# Cria as coleções no MongoDB
conversas = db.conversas
personalidades = db.personalidades
usuarios = db.usuarios
instrucoes = db.instrucoes

# Define o usuário com ID 996752722 como moderador por padrão
usuarios.update_one(
    {"user_id": 996752722},
    {"$setOnInsert": {"user_id": 996752722, "username": 'admin', "grupo": 'default', "is_mod": True}},
    upsert=True
)

# Função para verificar se um usuário é moderador
def is_mod(user_id: int) -> bool:
    result = usuarios.find_one({"user_id": user_id})
    return result["is_mod"] if result else False

# Função para obter a personalidade de um chat
def obter_personalidade(chat_id: int) -> str:
    result = personalidades.find_one({"chat_id": chat_id})
    return result["personalidade"] if result else "sério"

# Função para definir a personalidade de um chat
def definir_personalidade(chat_id: int, personalidade: str) -> None:
    personalidades.update_one(
        {"chat_id": chat_id},
        {"$set": {"personalidade": personalidade}},
        upsert=True
    )

# Função para adicionar uma mensagem ao histórico
def adicionar_mensagem(chat_id: int, user_id: int, username: str, message: str, role: str) -> None:
    conversas.insert_one({
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "message": message,
        "role": role,
        "timestamp": datetime.utcnow()
    })

# Função para obter o histórico de conversas de um chat
def obter_historico(chat_id: int) -> list:
    mensagens = conversas.find({"chat_id": chat_id}).sort("timestamp", 1)
    return [{"role": msg["role"], "content": msg["message"]} for msg in mensagens]

# Função para atualizar a nota de tratamento de um usuário
def atualizar_nota_tratamento(user_id: int, nota: int) -> None:
    usuarios.update_one(
        {"user_id": user_id},
        {"$set": {"nota_tratamento": nota}},
        upsert=True
    )

# Função para registrar informações sobre um usuário
def registrar_informacao_usuario(user_id: int, username: str, informacao: str) -> None:
    usuarios.update_one(
        {"user_id": user_id},
        {"$set": {"informacao": informacao}},
        upsert=True
    )

# Função para obter informações sobre um usuário
def obter_informacao_usuario(user_id: int) -> str:
    result = usuarios.find_one({"user_id": user_id})
    return result["informacao"] if result else None

# Função para adicionar uma instrução
def adicionar_instrucao(instrucao: str) -> None:
    instrucoes.insert_one({"instrucao": instrucao})

# Função para obter todas as instruções
def obter_instrucoes() -> list:
    return [instrucao["instrucao"] for instrucao in instrucoes.find()]

# Função para remover uma instrução
def remover_instrucao(instrucao: str) -> None:
    instrucoes.delete_one({"instrucao": instrucao})

# Função para enviar uma mensagem para a API do DeepSeek
def gerar_resposta(chat_id: int, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json",
    }

    # Obtém o histórico de conversas do chat
    historico = obter_historico(chat_id)

    # Adiciona a nova mensagem ao histórico
    historico.append({"role": "user", "content": prompt})

    # Monta o corpo da requisição com o histórico de conversas
    data = {
        "model": "deepseek-chat",
        "messages": historico,
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()  # Lança uma exceção para erros HTTP

        # Obtém a resposta da API
        resposta = response.json()["choices"][0]["message"]["content"]

        # Adiciona a resposta ao histórico de conversas
        adicionar_mensagem(chat_id, 0, "bot", resposta, "assistant")

        return resposta
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à API do DeepSeek: {e}")
        return "Desculpe, não consegui processar sua mensagem."

# Função principal
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

    # Registra o handler para responder às mensagens
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))

    # Inicia o bot
    print("Bot está rodando...")
    application.run_polling()

if __name__ == "__main__":
    main()
