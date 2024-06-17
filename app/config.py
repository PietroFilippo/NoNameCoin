# Define uma classe base de configuração para a aplicação
class Config:
    # URI de conexão com o banco de dados SQLAlchemy usando SQLite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///banco.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Definindo uma classe de configuração para testes
class TestesConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///testes.db'
    TESTING = True
