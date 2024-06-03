import requests
import random
import string

BASE_URL = 'http://127.0.0.1:5000'

def simular_transacoes(n):
    chaves_validador = [''.join(random.choices(string.ascii_letters + string.digits, k=16)) for _ in range(n)]
    
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
    print(response.json())

if __name__ == '__main__':
    simular_transacoes(100)  # Simula 100 transações

# Arrumar atualização de saldos aspós as transaçãoes