import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Ler URI do MongoDB do .env
MONGO_URI = os.getenv("MONGO_URI")

# Conectar ao banco
client = MongoClient(MONGO_URI)
db = client.get_database()

# Exemplo de coleção
colecao = db["chatbot"]

# Testando a conexão
if __name__ == "__main__":
    print("Conexão bem-sucedida ao MongoDB!")
    print("Bancos disponíveis:", client.list_database_names())
