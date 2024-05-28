from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Interger, primary_key=True)
    nome = db.Column(db.String(100), unique=False, nullable=False)
    saldo = db.Column(db.Float, default = 0.0)

class Transacao(db.Model):
    id = db.Column(db.Interger, primary_key=True)
    id_remetente = db.Column(db.Interger, db.ForeignKey('usuario.id'), nullable = False)
    id_receptor = db.Column(db.Interger, db.ForeignKey('usuario.id'), nullable = False)
    quantia = db.Column(db.Float, nullable = False)
    status = db.Column(db.Interger, nullable = False)
    horario = db.Column(db.DateTime, nullable = False, default=datetime.utcnow)
    key = db.Column(db.String(100), nullable = False)

class Validador(db.Model):
    id = db.Column(db.Interger, primary_key=True)
    endereco = db.Column(db.String(100), unique = True, nullable = False)
    stake = db.Column(db.Float, nullable = False) # Quantia "apostada"
    key = key = db.Column(db.String(100), nullable = False) # Chave única do seletor
    flag = db.Column(db.Interger, default = 0) # Flags de alertas
    status = db.Column(db.String(50), default='active')  # Status do validador
    selecoes_consecutivas = db.Column(db.Interger, default = 0) # Número de seleções consecutivas
