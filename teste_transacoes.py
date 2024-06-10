# import requests
# import random
# import time

# BASE_URL = 'http://127.0.0.1:5000'

# def obter_chaves_validadores():
#     response = requests.get(f'{BASE_URL}/seletor/listar')
#     if response.status_code == 200:
#         validadores = response.json().get('validadores', [])
#         return [validador['key'] for validador in validadores]
#     else:
#         print(f"Erro ao obter validadores: {response.text}")
#         return []

# def obter_usuarios():
#     response = requests.get(f'{BASE_URL}/usuarios')
#     if response.status_code == 200:
#         usuarios = response.json().get('usuarios', [])
#         return [usuario['id'] for usuario in usuarios]
#     else:
#         print(f"Erro ao obter usuários: {response.text}")
#         return []

# def gerar_transacao():
#     id_remetente = random.choice(obter_usuarios())
#     id_receptor = random.choice(obter_usuarios())
#     quantia = round(random.uniform(1.0, 100.0), 2)
#     chave_validador = random.choice(obter_chaves_validadores())
#     return {'id_remetente': id_remetente, 'id_receptor': id_receptor, 'quantia': quantia, 'key': chave_validador}

# def simular_transacoes(numero_transacoes):
#     transacoes = [gerar_transacao() for _ in range(numero_transacoes)]
#     dados = {'transacoes': transacoes}
#     response = requests.post(f'{BASE_URL}/transacoes', json=dados)
#     return response.json()

# if __name__ == '__main__':
#     numero_transacoes = 5 # Altere conforme necessário
#     resultado = simular_transacoes(numero_transacoes)
#     print("Resultado da simulação de transações:")
#     #print(resultado)

# @bp.route('/transacoes', methods=['POST'])
# def transacoes():
#     dados = request.json.get('transacoes')
#     if not dados:
#         logger.debug("Nenhuma transação fornecida")
#         return jsonify({'mensagem': 'Nenhuma transação fornecida'}), 400

#     respostas = []

#     try:
#         for transacao_dados in dados:
#             logger.debug(f"Processando transação: {transacao_dados}")

#             # Crie uma instância de Transacao com os dados da transação
#             nova_transacao = Transacao(
#                 id_remetente=transacao_dados.get('id_remetente'),
#                 id_receptor=transacao_dados.get('id_receptor'),
#                 quantia=transacao_dados.get('quantia'),
#                 status=0,
#                 key=transacao_dados.get('key')
#             )

#             # Verifique se o remetente tem saldo suficiente
#             remetente = db.session.get(Usuario, nova_transacao.id_remetente)
#             if remetente.saldo < nova_transacao.quantia:
#                 logger.debug(f"Saldo insuficiente para o remetente: {remetente.saldo} < {nova_transacao.quantia}")
#                 respostas.append({'id_remetente': nova_transacao.id_remetente, 'mensagem': 'Saldo insuficiente'})
#                 continue

#             # Verifique se a chave do validador é válida
#             validador = Validador.query.filter_by(key=nova_transacao.key).first()
#             if not validador:
#                 logger.debug(f"Validador não encontrado para a chave: {nova_transacao.key}")
#                 respostas.append({'id_remetente': nova_transacao.id_remetente, 'mensagem': 'Erro na verificação da chave'})
#                 continue

#             # Sincronize o horário
#             resposta_tempo_atual = requests.get(f'{BASE_URL}/hora')
#             tempo_atual = datetime.fromisoformat(resposta_tempo_atual.json()['tempo_atual'])
#             logger.debug(f"Tempo atual sincronizado: {tempo_atual}")

#             # Atribua o horário à transação e adicione-a ao banco de dados
#             nova_transacao.horario = tempo_atual
#             db.session.add(nova_transacao)

#             # Commit das alterações no banco de dados
#             db.session.commit()
#             logger.debug(f"Transação adicionada ao banco de dados: {nova_transacao}")

#             # Gerencie o consenso e valide a transação
#             resultado = gerenciar_consenso([nova_transacao])
#             logger.debug(f"Resultado da validação do consenso: {resultado}")

#             # Atualize o status da transação com base no resultado do consenso
#             if resultado['status_code'] == 200:
#                 # Se a transação for validada, atualize o status para 1
#                 nova_transacao.status = 1
#                 logger.debug(f"Transação {nova_transacao.id} foi validada com sucesso")
#             else:
#                 # Se ocorrer um erro, atualize o status para outro valor (por exemplo, 2 para erro)
#                 nova_transacao.status = 2
#                 logger.debug(f"Transação {nova_transacao.id} não foi validada devido a um erro")

#             # Adicione a resposta ao lista de respostas
#             respostas.append({'id_remetente': nova_transacao.id_remetente, 'mensagem': 'Transação processada com sucesso'})

#         # Commit das alterações no banco de dados
#         db.session.commit()

#     except Exception as e:
#         db.session.rollback()
#         logger.error("Erro ao processar transações", exc_info=True)
#         return jsonify({'mensagem': 'Erro ao processar transações', 'erro': str(e)}), 500

#     return jsonify({'transacoes': respostas}), 200