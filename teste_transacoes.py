import time
import random
from app import criar_app, db
from app.models import Usuario, Validador, Seletor
from app.validacao import gerar_chave
from flask import current_app

# Inicializa o aplicativo Flask
app = criar_app()

def obter_seletor():
    with app.app_context():
        # Obtém o seletor do banco de dados
        seletor = Seletor.query.first()
        return seletor.id if seletor else None

def simular_transacoes(num_transacoes):
    with app.app_context():
        # Obtém o seletor existente
        seletor_id = obter_seletor()
        if not seletor_id:
            print("Seletor não encontrado.")
            return

        # Obtém a quantidade de usuários no banco de dados
        num_usuarios = Usuario.query.count()

        for _ in range(num_transacoes):
            # Seleciona validadores usando a rota
            resposta_selecao = app.test_client().post(f'/seletor/{seletor_id}/selecionar_validadores')
            if resposta_selecao.status_code != 200:
                print(f"Erro ao selecionar validadores: {resposta_selecao.json}")
                return

            validadores_ids = resposta_selecao.json['validadores']

            # Recupera os validadores do banco de dados com base nos IDs
            validadores = Validador.query.filter(Validador.id.in_(validadores_ids)).all()
            current_app.config['validadores_selecionados'] = validadores

            chaves_validacao = [gerar_chave(seletor_id, v.endereco) for v in validadores]

            id_remetente = random.randint(1, num_usuarios)
            id_receptor = random.randint(1, num_usuarios)
            while id_receptor == id_remetente:
                id_receptor = random.randint(1, num_usuarios)

            quantia = random.uniform(10, 500)
            chave_validacao = chaves_validacao

            transacao_dados = {
                'id_remetente': id_remetente,
                'id_receptor': id_receptor,
                'quantia': quantia,
                'keys_validacao': chave_validacao
            }

            resposta = app.test_client().post('/trans', json=transacao_dados)
            print(f"Transação: {transacao_dados}")
            print(f"Resposta: {resposta.json}")

if __name__ == '__main__':
    num_transacoes = 50
    simular_transacoes(num_transacoes)