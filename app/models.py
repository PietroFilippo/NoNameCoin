from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=False, nullable=False)
    saldo = db.Column(db.Float, default = 0.0)

class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Chave primária autoincrementável
    id_remetente = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_receptor = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    quantia = db.Column(db.Float, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    horario = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    key_validacao = db.Column(db.String(100), nullable=False)  # Nova coluna para armazenar a chave única de validação

class Validador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endereco = db.Column(db.String(100), unique=True, nullable=False)
    stake = db.Column(db.Float, nullable=False)  # Quantia "apostada"
    key = db.Column(db.String(100), nullable=False)  # Chave única do seletor
    flag = db.Column(db.Integer, default=0)  # Flags de alertas
    status = db.Column(db.String(50), default='ativo')  # Status do validador
    selecoes_consecutivas = db.Column(db.Integer, default=0)  # Número de seleções consecutivas
    transacoes_coerentes = db.Column(db.Integer, default=0)  # Número de transações coerentes
    retorno_contagem = db.Column(db.Integer, default=0)  # Nova coluna para contagem de retornos