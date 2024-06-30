import random
from app import criar_app, db
from app.models import Usuario
from app.validacao import selecionar_validadores, gerar_chave
from flask import current_app

# Inicializa o aplicativo Flask
app = criar_app()

def simular_transacoes(num_transacoes):
    with app.app_context():
        # Obtém a quantidade de usuários no banco de dados
        num_usuarios = Usuario.query.count()
        
        for _ in range(num_transacoes):
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados

            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            chaves_validacao = [gerar_chave(seletor_id, v.endereco) for v in validadores_selecionados]

            id_remetente = random.randint(1, num_usuarios)
            id_receptor = random.randint(1, num_usuarios)
            while id_receptor == id_remetente:
                id_receptor = random.randint(1, num_usuarios)

            quantia = random.uniform(10, 500)
            chave_validacao = random.choice(chaves_validacao)

            transacao_dados = {
                'id_remetente': id_remetente,
                'id_receptor': id_receptor,
                'quantia': quantia,
                'keys_validacao': chave_validacao
            }

            resposta = app.test_client().post('/trans', json=transacao_dados)
            #print(f"Transação: {transacao_dados}")
            #print(f"Resposta: {resposta.json}")

if __name__ == '__main__':
    num_transacoes = 1000
    simular_transacoes(num_transacoes)
