from flask import Flask
from .models import db
from. routes import bp as routes_bp

def criar_app(config_object='app.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Iniciar as extensões
    db.init_app(app)

    # Regeistro dos blueprints
    app.register_blueprint(routes_bp)

    return app