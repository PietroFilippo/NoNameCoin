from flask import Blueprint, request, jsonify
import requests
import traceback
from datetime import datetime
from .models import db, Usuario, Transacao, Validador
from .validador import gerenciar_consenso, lista_validadores, update_flags_validador, hold_validador_, registrar_validador_, remover_validador_, validar_transacao

# Criar o blueprint para as rotas
bp = Blueprint('routes', __name__)

BASE_URL = 'http://127.0.0.1:5000'

@bp.route('/trans', methods=['POST'])
def transacao():
    dados = request.json

    # Cria uma única transação a partir dos dados recebidos
    transacao_dados = {
        'id_remetente': dados.get('id_remetente'),
        'id_receptor': dados.get('id_receptor'),
        'quantia': dados.get('quantia'),
        'key': dados.get('key')
    }

    # Transforma a transação em um objeto Transacao
    nova_transacao = Transacao(
        id_remetente=transacao_dados['id_remetente'],
        id_receptor=transacao_dados['id_receptor'],
        quantia=transacao_dados['quantia'],
        status=0,
        key=transacao_dados['key']
    )

    try:
        # Verifica se o remetente tem saldo suficiente
        remetente = db.session.get(Usuario, transacao_dados['id_remetente'])
        if remetente.saldo < transacao_dados['quantia']:
            return jsonify({'mensagem': 'Saldo insuficiente', 'status_code': 400}), 400

        # Verifica se a chave do validador é valida
        validador = Validador.query.filter_by(key=transacao_dados['key']).first()
        if not validador:
            return jsonify({'mensagem': 'Erro na verificação da chave', 'status_code': 500}), 500

        # Sincroniza o horário
        resposta_tempo_atual = requests.get(f'{BASE_URL}/hora')
        tempo_atual = datetime.fromisoformat(resposta_tempo_atual.json()['tempo_atual'])

        # Atribui o horário à transação e a adiciona ao banco de dados
        nova_transacao.horario = tempo_atual
        db.session.add(nova_transacao)
        db.session.commit()

        # Gerencia o consenso e valida a transação
        resultado = gerenciar_consenso([nova_transacao])

        if resultado['status_code'] == 200:
            # Atualiza os saldos do remetente e do receptor se a transação for validada
            if nova_transacao.status == 1:
                print(f"Transação {nova_transacao.id} foi validada com sucesso")
                remetente.saldo -= transacao_dados['quantia']
                receptor = db.session.get(Usuario, transacao_dados['id_receptor'])
                receptor.saldo += transacao_dados['quantia']
                db.session.commit()
                print(f"Saldo atualizado do remetente: {remetente.saldo}")
                print(f"Saldo atualizado do receptor: {receptor.saldo}")
            return jsonify({'mensagem': 'Transação feita com sucesso', 'status_code': 200}), 200
        else:
            return jsonify(resultado), resultado['status_code']
    except Exception as e:
        traceback.print_exc()  # Log de exceção
        return jsonify({'mensagem': str(e), 'status_code': 500}), 500
    
@bp.route('/transacoes', methods=['POST'])
def transacoes():
    dados = request.json
    transacoes_dados = dados.get('transacoes')  # Obtém a lista de transações

    transacoes_objs = []
    for transacao_dados in transacoes_dados:
        id_remetente = transacao_dados.get('id_remetente')
        id_receptor = transacao_dados.get('id_receptor')
        quantia = transacao_dados.get('quantia')
        key = transacao_dados.get('key')

        remetente = db.session.get(Usuario, id_remetente)
        if remetente.saldo < quantia:
            continue  # Ignora transações com saldo insuficiente

        nova_transacao = Transacao(
            id_remetente=id_remetente, id_receptor=id_receptor, quantia=quantia, status=0, key=key
        )
        transacoes_objs.append(nova_transacao)  # Adiciona a nova transação à lista

    db.session.add_all(transacoes_objs)  # Adiciona todas as transações ao banco de dados
    db.session.commit()

    resultado = gerenciar_consenso(transacoes_objs)  # Gerencia o consenso para todas as transações
    return jsonify(resultado), resultado['status_code']
    
@bp.route('/hora', methods=['GET'])
def get_tempo_atual():
    tempo_atual = datetime.utcnow()
    return jsonify({'tempo_atual': tempo_atual.isoformat()}), 200

@bp.route('/seletor/registrar', methods=['POST'])
def registrar_validador():
    dados = request.json
    endereco = dados.get('endereco')
    stake = dados.get('stake')
    key = dados.get('key')
    resultado = registrar_validador_(endereco, stake, key)
    return jsonify(resultado), resultado['status_code']

@bp.route('/seletor/remover', methods=['POST'])
def remover_validador():
    dados = request.json
    endereco = dados.get('endereco')
    resultado = remover_validador_(endereco)
    return jsonify(resultado), resultado['status_code']

@bp.route('/seletor/listar', methods=['GET'])
def listar_validadores():
    resultado = lista_validadores()
    return jsonify(resultado[0]), resultado[1]

# Rota pra aplicar flags aos validadores
@bp.route('/seletor/flag', methods=['POST'])
def flag_validador():
    dados = request.json
    endereco = dados.get('endereco')
    acao = dados.get('acao') # 'add' para adiconar flag e 'remover' para remover
    resultado = update_flags_validador(endereco, acao)
    return jsonify(resultado), resultado['status_code']

@bp.route('/seletor/hold', methods=['POST'])
def hold_validador():
    dados = request.json
    endereco = dados.get('endereco')
    resultado = hold_validador_(endereco)
    return jsonify(resultado), resultado['status_code']

