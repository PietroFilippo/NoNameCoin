from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Classe Usuario 
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=False, nullable=False)
    saldo = db.Column(db.Float, default=0.0)
    tempo_bloqueio = db.Column(db.DateTime, nullable=True) # Tempo de um minuto de bloqueio caso o remetente faça mais que 100 transações em até um minuto

# Classe Transacao
class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_remetente = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_receptor = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    quantia = db.Column(db.Float, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    horario = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    keys_validacao = db.Column(db.String(100), nullable=False) # Coluna para armazenar as chaves únicas de validação

# Classe Seletor
class Seletor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endereco = db.Column(db.String(100), unique=True, nullable=False)
    saldo = db.Column(db.Float, default=0.0)

# Classe Validador
class Validador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endereco = db.Column(db.String(100), unique=True, nullable=False)
    stake = db.Column(db.Float, nullable=False) # Quantia "apostada"
    key = db.Column(db.String(100), nullable=False) # Chave única do seletor
    chave_seletor = db.Column(db.String(100), nullable=False) # Chave usada para a transação dada pelo seletor
    flag = db.Column(db.Integer, default=0) # Flags de alertas
    status = db.Column(db.String(50), default='ativo') # Status do validador
    selecoes_consecutivas = db.Column(db.Integer, default=0) # Número de seleções consecutivas
    transacoes_coerentes = db.Column(db.Integer, default=0) # Número de transações coerentes
    transacoes_hold_restantes = db.Column(db.Integer, default=0) # Número de transações restantes para sair do on hold
    retorno_contagem = db.Column(db.Integer, default=0) # Número de retornos depois de ter sido expulso
    seletor_id = db.Column(db.Integer, db.ForeignKey('seletor.id'), nullable=False) # Relação com o seletor
    seletor = db.relationship('Seletor', backref=db.backref('validadores', lazy=True)) # Define um relacionamento com a tabela Seletor e adiciona um backref para validadores