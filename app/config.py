class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///banco.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class TestesConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///testes.db'
    TESTING = True