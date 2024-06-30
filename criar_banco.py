import random
from app import criar_app, db
from app.models import Usuario, Validador, Seletor
from app.validacao import gerar_chave

# Inicializa o aplicativo Flask
app = criar_app()

def limpar_banco_de_dados():
    with app.app_context():
        # Limpa todas as tabelas do banco de dados
        db.drop_all()
        print("Todas as tabelas do banco de dados foram removidas.")

def criar_e_popular_banco():
    with app.app_context():
        # Verifica se o banco de dados já existe
        if db.engine.url.database not in ('', ':memory:'):
            print(f"Banco de dados '{db.engine.url.database}' já existe. Limpando e recriando.")
            limpar_banco_de_dados()

        # Cria todas as tabelas
        db.create_all()

        # Cria usuários aleatórios a partir do indice 1
        for i in range(1, 34):
            usuario = Usuario(
                nome=f'usuario{i}',
                saldo=random.uniform(1000, 5000)
            )
            db.session.add(usuario)

        # Cria um seletor
        seletor = Seletor(
            endereco='seletor1',
            saldo=random.uniform(10000, 50000)
        )
        db.session.add(seletor)
        db.session.commit() 

        # Cria validadores aleatórios associados ao seletor a partir do indice 1
        for i in range(1, 31):
            chave_validador = gerar_chave(seletor.id, f'validador{i}')
            validador = Validador(
                endereco=f'validador{i}',
                stake=random.uniform(1000, 5000),
                key=f'key{i}',
                chave_seletor=chave_validador,
                seletor_id=seletor.id
            )
            db.session.add(validador)

        # Confirma todas as operações no banco de dados
        db.session.commit()
        print("Banco de dados criado e populado com sucesso.")

if __name__ == '__main__':
    criar_e_popular_banco()
