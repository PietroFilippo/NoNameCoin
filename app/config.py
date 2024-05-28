class Config:
    SQLALCHEMY_DATABASE_URL = 'sqlite:///banco.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class TestesConfig(Config):
    SQLALCHEMY_DATABASE_URL = 'sqlite:///testes.db'
    TESTING = True