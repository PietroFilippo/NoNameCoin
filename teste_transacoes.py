import time
import random
import logging  # Importe o módulo logging
from app import criar_app, db
from app.models import Usuario, Seletor, Validador, Transacao
from flask import current_app, json

from app.validacao import gerar_chave, selecionar_validadores

# Inicializa o aplicativo Flask
app = criar_app()

# Configuração do logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def criar_dados_transacao():
    with app.app_context():
        # Seleciona dois usuários aleatórios
        usuarios = Usuario.query.all()
        if len(usuarios) < 2:
            raise ValueError("Número insuficiente de usuários no banco de dados.")
        remetente, receptor = random.sample(usuarios, 2)

        validadores_selecionados = selecionar_validadores()
        current_app.config['validadores_selecionados'] = validadores_selecionados
        seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
        chaves_validacao = [gerar_chave(seletor_id, v.endereco) for v in validadores_selecionados]

        # Cria dados de transação aleatória
        quantia = random.uniform(1, remetente.saldo / 2)
        transacao_dados = {
            'id_remetente': remetente.id,
            'id_receptor': receptor.id,
            'quantia': quantia,
            'keys_validacao': chaves_validacao[0]
        }
        return transacao_dados

def simular_transacoes(num_transacoes):
    with app.test_client() as client:
        try:
            with app.app_context():
                for _ in range(num_transacoes):
                    # Cria dados de transação
                    transacao_dados = criar_dados_transacao()
                    resposta = client.post('/trans', data=json.dumps(transacao_dados), content_type='application/json')

                    if resposta.status_code == 200:
                        resultados = resposta.json
                        for resultado in resultados:
                            if resultado.get('status') == 'sucesso':
                                print(f"Transação {resultado.get('id_transacao')} feita com sucesso")
                            else:
                                print(f"Transação {resultado.get('id_transacao')} falhou: {resultado.get('mensagem')}")
                    else:
                        print(f"Falha ao criar transação: {resposta.status_code} - {resposta.data}")
                    
                    # Adicionar log para verificar o incremento de transacoes_coerentes
                    validadores_selecionados = current_app.config.get('validadores_selecionados', [])
                    for validador in validadores_selecionados:
                        logger.debug(f"Validador {validador.id} - Depois do incremento: {validador.transacoes_coerentes}")

        except Exception as e:
            print(f"Erro ao simular transação: {e}")

if __name__ == '__main__':
    simular_transacoes(10)  # Simula 10 transações
