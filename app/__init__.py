from flask import Flask
from .models import db
from .routes import bp as routes_bp
import logging

# Cria a aplicação Flask
def criar_app(config_object='app.config.Config'):
    # Cria uma instância da aplicação flask
    app = Flask(__name__)
    # Carrega a configuração da aplicação a partir do objeto especificado
    app.config.from_object(config_object)

    # Configura o nível de logging para DEBUG
    logging.basicConfig(level=logging.DEBUG)

    # Inicializa o banco de dados com flask
    db.init_app(app)

    # Registra o blueprint de rotas na aplicação
    app.register_blueprint(routes_bp)

    # Retorna a instância da aplicação flask
    return app
