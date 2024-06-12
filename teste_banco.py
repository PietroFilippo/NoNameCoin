from app import criar_app
from app.models import db, Usuario, Validador
import random
import string

app = criar_app()

# Limpa o banco de dados
with app.app_context():
    db.drop_all()
    db.create_all()

    # Adiciona 10 usuários de exemplo
    for i in range(1, 11):
        nome = ''.join(random.choices(string.ascii_lowercase, k=5))  # Gera um nome aleatório
        saldo = random.uniform(100.0, 1000.0)  # Gera um saldo aleatório entre 100 e 1000
        usuario = Usuario(nome=nome, saldo=saldo)
        db.session.add(usuario)

    # Adiciona validadores de exemplo
    for i in range(1, 51):
        endereco = ''.join(random.choices(string.ascii_lowercase, k=4))  # Gera um endereço aleatório
        stake = random.uniform(100.0, 1000.0)  # Gera um stake aleatório entre 100 e 1000
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=3))  # Gera uma chave aleatória
        validador = Validador(endereco=endereco, stake=stake, key=key)
        db.session.add(validador)

    db.session.commit()

    # Verifica a criação dos dados do banco
    assert Usuario.query.count() == 10
    assert Validador.query.count() == 50

    print("Banco de dados criado")  
