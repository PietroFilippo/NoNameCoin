from flask import Blueprint, request, jsonify
import requests
import traceback
from datetime import datetime
from .models import db, Usuario, Transacao, Validador
from .validador import gerenciar_consenso, lista_validadores

# Criar o blueprint para as rotas
bp = Blueprint('routes', __name__)

BASE_URL = 'http://127.0.0.1:5000'

@bp.route('/trans', methods=['POST'])
def transacao():
    dados = request.json
    id_remetente = dados.get('id_remetente')
    id_receptor = dados.get('id_receptor')
    quantia = dados.get('quantia')
    key = dados.get('key') # Chave única do validador

    try:
        # Verifica se o remetente tem saldo suficiente
        remetente = db.session.get(Usuario, id_remetente)
        if remetente.saldo < quantia:
            return jsonify({'mensagem': 'Saldo insuficiente', 'status_code': 400}), 400
        
        #Verifica se a chave do validador é valida
        validador = Validador.query.filter_by(key=key).first()
        if not validador:
            return jsonify({'mensagem': 'Erro na verificação da chave', 'status_code': 500}), 500
        
        # Sincroniza o horário
        resposta_tempo_atual = requests.get(f'{BASE_URL}/hora')
        tempo_atual = datetime.fromisoformat(resposta_tempo_atual.json()['tempo_atual'])

        # Cria a transação
        nova_transacao = Transacao(
            id_remetente = id_remetente, id_receptor = id_receptor, quantia = quantia, status = 0, horario = tempo_atual, key = key
        )
        db.session.add(nova_transacao)
        db.session.commit()

        # Grencia o consenso e valida a transação
        resultado = gerenciar_consenso(nova_transacao)

        if resultado['status_code'] == 200:
            # Atualiza os saldos do remetente e do receptor se a transação for validada
            if nova_transacao.status == 1:
                print(f"Transação {nova_transacao.id} foi validada com sucesso")
                remetente.saldo -= quantia
                receptor = db.session.get(Usuario, id_receptor)
                receptor.saldo += quantia
                db.session.commit()
                print(f"Saldo atualizado do remetente: {remetente.saldo}")
                print(f"Saldo atualizado do receptor: {receptor.saldo}")
            return jsonify({'mensagem': 'Transação feita com sucesso', 'status_code': 200}), 200
        else:
            return jsonify(resultado), resultado['status_code']
    except Exception as e:
        traceback.print_exc() # Log de exceção
        return jsonify({'mensagem': str(e), 'status_code': 500}), 500
    
@bp.route('/hora', methods=['GET'])
def get_tempo_atual():
    tempo_atual = datetime.utcnow
    return jsonify({'tempo_atual': tempo_atual.isoformat()}), 200

@bp.route('/seletor/registrar', methods=['POST'])
def registrar_validador():
    dados = request.json
    endereco = dados.get('endereco')
    stake = dados.get('stake')
    key = dados.get('key')
    resultado = registrar_validador(endereco, stake, key)
    return jsonify(resultado), resultado['staus_code']

@bp.route('/seletor/remover', methods=['POST'])
def remover_validador():
    dados = request.json
    endereco = dados.get('endereco')
    resultado = remover_validador(endereco)
    return jsonify(resultado), resultado['staus_code']

@bp.route('/seletor/listar', methods=['GET'])
def listar_validadores():
    resultado = lista_validadores()
    return jsonify(resultado[0]), resultado[1]


