import requests
import random
import string

BASE_URL = 'http://127.0.0.1:5000'

def obter_chaves_validadores():
    response = requests.get(f'{BASE_URL}/seletor/listar')
    if response.status_code == 200:
        validadores = response.json().get('validadores', [])
        return [validador['key'] for validador in validadores]
    else:
        print(f"Erro ao obter validadores: {response.text}")
        return []

def simular_transacoes(n):
    chaves_validador = obter_chaves_validadores()
    
    if not chaves_validador:
        print("Nenhuma chave de validador disponível.")
        return

    transacoes = []
    for _ in range(n):
        transacao = {
            'id_remetente': random.randint(1, 100),  # Gera um ID de remetente aleatório entre 1 e 100
            'id_receptor': random.randint(1, 100),  # Gera um ID de receptor aleatório entre 1 e 100
            'quantia': random.uniform(1.0, 100.0),  # Gera uma quantia aleatória
            'key': random.choice(chaves_validador)  # Seleciona aleatoriamente uma chave de validador
        }
        transacoes.append(transacao)
    
    response = requests.post(f'{BASE_URL}/transacoes', json={'transacoes': transacoes})  # Envia as transações
    try:
        print(response.json())
    except Exception as e:
        print(f"Erro ao decodificar a resposta JSON: {e}")
        print(response.text)

if __name__ == '__main__':
    simular_transacoes(100)  # Simula 100 transações