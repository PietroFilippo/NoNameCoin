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
    dados = request.json.get('transacoes')
    if not dados:
        return jsonify({'mensagem': 'Nenhuma transação fornecida'}), 400

    respostas = []

    try:
        for transacao_dados in dados:
            id_remetente = transacao_dados.get('id_remetente')
            id_receptor = transacao_dados.get('id_receptor')
            quantia = transacao_dados.get('quantia')
            key = transacao_dados.get('key')

            remetente = db.session.get(Usuario, id_remetente)
            receptor = db.session.get(Usuario, id_receptor)
            validador = Validador.query.filter_by(key=key).first()

            if not validador:
                respostas.append({'id_remetente': id_remetente, 'mensagem': 'Erro na verificação da chave'})
                continue

            if remetente.saldo < quantia:
                #respostas.append({'id_remetente': id_remetente, 'mensagem': 'Saldo insuficiente'})
                continue

            nova_transacao = Transacao(
                id_remetente=id_remetente, id_receptor=id_receptor, quantia=quantia, status=0, key=key
            )
            db.session.add(nova_transacao)

            # Atualiza os saldos dos usuários
            remetente.saldo -= quantia
            receptor.saldo += quantia

            #respostas.append({'id_remetente': id_remetente, 'mensagem': 'Transação feita com sucesso'})

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({'mensagem': 'Erro ao processar transações', 'erro': str(e)}), 500

    return jsonify({'transacoes': respostas}), 200
    
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
    validadores = Validador.query.all()
    return jsonify({
        'validadores': [
            {'endereco': v.endereco, 'stake': v.stake, 'key': v.key}
            for v in validadores
        ]
    }), 200

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