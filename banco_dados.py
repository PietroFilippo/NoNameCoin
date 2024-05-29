from app import criar_app
from app.models import db, Usuario, Transacao, Validador

app = criar_app()

    # Limpa o banco de dados
with app.app_context():
    db.drop_all()
    db.create_all()

    # Adiciona os usuarios de exemplo
    usuario1 = Usuario(nome = 'usuario1', saldo = 500.0)
    usuario2 = Usuario(nome = 'usuario2', saldo = 200.0)
    db.session.add(usuario1)
    db.session.add(usuario2)

    # Adiciona os validadores de exemplo
    validador1 = Validador(endereco = 'validador1', stake = 200.0, key = 'key1')
    validador2 = Validador(endereco = 'validador2', stake = 100.0, key = 'key2')
    db.session.add(validador1)
    db.session.add(validador2)

    db.session.commit()

    # Verifica a criação dos dados do banco
    assert Usuario.query.count() == 2
    assert Validador.query.count() == 2

    print("Banco de dados criado")

