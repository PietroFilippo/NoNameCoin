from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=False, nullable=False)
    saldo = db.Column(db.Float, default=0.0)

class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_remetente = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_receptor = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    quantia = db.Column(db.Float, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    horario = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    keys_validacao = db.Column(db.String(100), nullable=False)  # Coluna para armazenar a chaves únicas de validação

class Seletor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endereco = db.Column(db.String(100), unique=True, nullable=False)
    saldo = db.Column(db.Float, default=0.0)

class Validador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endereco = db.Column(db.String(100), unique=True, nullable=False)
    stake = db.Column(db.Float, nullable=False)  # Quantia "apostada"
    key = db.Column(db.String(100), nullable=False)  # Chave única do seletor
    chave_seletor = db.Column(db.String(100), nullable=False)  # Adiciona a coluna chave_seletor
    flag = db.Column(db.Integer, default=0)  # Flags de alertas
    status = db.Column(db.String(50), default='ativo')  # Status do validador
    selecoes_consecutivas = db.Column(db.Integer, default=0)  # Número de seleções consecutivas
    transacoes_coerentes = db.Column(db.Integer, default=0)  # Número de transações coerentes
    transacoes_hold_restantes = db.Column(db.Integer, default=0)
    retorno_contagem = db.Column(db.Integer, default=0)  # Nova coluna para contagem de retornos
    seletor_id = db.Column(db.Integer, db.ForeignKey('seletor.id'), nullable=False)  # Relação com o seletor
    seletor = db.relationship('Seletor', backref=db.backref('validadores', lazy=True))