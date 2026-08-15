import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv, dotenv_values
import mysql.connector

load_dotenv()
_config = dotenv_values(".env")

# Configuração de logging: nível moderado (evita logar todas as queries).
logging.basicConfig(level=logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Engine e Session reutilizados em toda a aplicação (evita recriar o pool de
# conexões a cada chamada, o que deixava operações como "mover saldo" lentas).
_engine = None
_Session = None


# Função para criar a conexão com o banco de dados
def criar_conexao(config=None):
    global _config

    if not _config and not config:
        raise ValueError("É necessário fornecer um valor para o parâmetro 'config'")

    if not _config:
        _config = config

    connection = mysql.connector.connect(
        host=_config['HOST'],
        user=_config['USER'],
        password=_config['PASSWORD'],
        database=_config['DATABASE']
    )

    return connection


def criar_engine(config=None):
    global _engine, _Session

    if _engine is not None:
        return _engine

    connection_url = (
        f"mysql+mysqlconnector://{_config['USER']}:{_config['PASSWORD']}"
        f"@{_config['HOST']}/{_config['DATABASE']}"
    )
    _engine = create_engine(connection_url, pool_pre_ping=True, echo=False)
    _Session = sessionmaker(bind=_engine)

    return _engine


def get_session():
    criar_engine()
    return _Session()
