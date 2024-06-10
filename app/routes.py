from flask import Blueprint, current_app, request, jsonify
import requests
from datetime import datetime
from .models import db, Usuario, Transacao, Validador
from .validador import gerenciar_consenso, update_flags_validador, hold_validador_, registrar_validador_, remover_validador_, selecionar_validadores, gerar_chave_validacao
import logging

# Configurar o logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Define o nível de log para o módulo routes.py

# Criar o blueprint para as rotas
bp = Blueprint('routes', __name__)

BASE_URL = 'http://127.0.0.1:5000'

@bp.route('/trans', methods=['POST'])
def transacao():
    dados = request.json
    logger.debug(f"Dados recebidos para a transação: {dados}")

    try:
        transacao_dados = {
            'id_remetente': dados.get('id_remetente'),
            'id_receptor': dados.get('id_receptor'),
            'quantia': dados.get('quantia')
        }

        logger.debug(f"Dados antes da geração da chave de validação: {transacao_dados}")

        # Verifica se os validadores já foram selecionados no contexto do aplicativo Flask
        if 'validadores_selecionados' not in current_app.config:
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados
        else:
            validadores_selecionados = current_app.config['validadores_selecionados']

        logger.debug(f"Validadores selecionados: {[v.endereco for v in validadores_selecionados]}")

        chave_validacao = gerar_chave_validacao(validadores_selecionados, dados.get('id'))
        transacao_dados['key_validacao'] = chave_validacao
        logger.debug(f"Chave de validação a ser armazenada na transação: {chave_validacao}")

        nova_transacao = Transacao(
            id=dados.get('id'),
            id_remetente=transacao_dados['id_remetente'],
            id_receptor=transacao_dados['id_receptor'],
            quantia=transacao_dados['quantia'],
            status=0,
            key_validacao=chave_validacao
        )

        nova_transacao.horario = datetime.utcnow()
        db.session.add(nova_transacao)
        db.session.commit()
        logger.debug("Chave de validação armazenada na transação com sucesso.")

    except Exception as e:
        logger.error("Erro ao processar a transação", exc_info=True)
        return jsonify({'mensagem': str(e), 'status_code': 500}), 500

    try:
        transacao_atual = Transacao.query.filter_by(id=dados.get('id')).first()
        if not transacao_atual:
            logger.error("Transação não encontrada no banco de dados")
            return jsonify({'mensagem': 'Transação não encontrada', 'status_code': 404}), 404

        remetente = db.session.get(Usuario, transacao_dados['id_remetente'])
        taxa = transacao_dados['quantia'] * 0.015
        if remetente.saldo < (transacao_dados['quantia'] + taxa):
            logger.debug(f"Saldo insuficiente: {remetente.saldo} < {transacao_dados['quantia']} + {taxa}")
            return jsonify({'mensagem': 'Saldo insuficiente', 'status_code': 400}), 400

        resposta_tempo_atual = requests.get(f'{BASE_URL}/hora')
        if resposta_tempo_atual.status_code != 200:
            logger.error(f"Erro ao obter o tempo atual: {resposta_tempo_atual.status_code}")
            return jsonify({'mensagem': 'Erro ao obter o tempo atual', 'status_code': 500}), 500

        tempo_atual = datetime.fromisoformat(resposta_tempo_atual.json()['tempo_atual'])
        logger.debug(f"Tempo atual sincronizado: {tempo_atual}")

        chave_fornecida = dados.get('key_validacao')
        chave_gerada = transacao_atual.key_validacao
        logger.debug(f"Chave fornecida: {chave_fornecida}, Chave gerada: {chave_gerada}")
        if chave_fornecida != chave_gerada:
            logger.debug(f"Chave de validação inválida: {chave_fornecida}")
            return jsonify({'mensagem': 'Chave de validação inválida', 'status_code': 500}), 500

        resultado = gerenciar_consenso([transacao_atual], validadores_selecionados)
        logger.debug(f"Resultado da validação do consenso: {resultado}")

        if resultado['status_code'] == 200:
            if transacao_atual.status == 1:
                logger.debug(f"Transação {transacao_atual.id} foi validada com sucesso")
                remetente.saldo -= transacao_dados['quantia']
                receptor = db.session.get(Usuario, transacao_dados['id_receptor'])
                receptor.saldo += transacao_dados['quantia']
                db.session.commit()
                logger.debug(f"Saldo atualizado do remetente: {remetente.saldo}")
                logger.debug(f"Saldo atualizado do receptor: {receptor.saldo}")
                return jsonify({'mensagem': 'Transação feita com sucesso', 'status_code': 200}), 200
            else:
                return jsonify(resultado), resultado['status_code']
        else:
            return jsonify(resultado), resultado['status_code']

    except Exception as e:
        logger.error("Erro ao processar a transação", exc_info=True)
        return jsonify({'mensagem': str(e), 'status_code': 500}), 500

@bp.route('/hora', methods=['GET'])
def get_tempo_atual():
    tempo_atual = datetime.utcnow()
    logger.debug(f"Tempo atual retornado: {tempo_atual}")
    return jsonify({'tempo_atual': tempo_atual.isoformat()}), 200

@bp.route('/seletor/registrar', methods=['POST'])
def registrar_validador():
    dados = request.json
    logger.debug(f"Dados recebidos para registrar validador: {dados}")
    endereco = dados.get('endereco')
    stake = dados.get('stake')
    key = dados.get('key')
    resultado = registrar_validador_(endereco, stake, key)
    logger.debug(f"Resultado do registro do validador: {resultado}")
    return jsonify(resultado), resultado['status_code']

@bp.route('/seletor/remover', methods=['POST'])
def remover_validador():
    dados = request.json
    logger.debug(f"Dados recebidos para remover validador: {dados}")
    endereco = dados.get('endereco')
    resultado = remover_validador_(endereco)
    logger.debug(f"Resultado da remoção do validador: {resultado}")
    return jsonify(resultado), resultado['status_code']

@bp.route('/usuarios', methods=['GET'])
def obter_usuarios():
    usuarios = Usuario.query.all()
    usuarios_list = [{'id': usuario.id, 'nome': usuario.nome, 'saldo': usuario.saldo} for usuario in usuarios]
    #logger.debug(f"Usuários retornados: {usuarios_list}")
    return jsonify({'usuarios': usuarios_list})

@bp.route('/seletor/listar', methods=['GET'])
def listar_validadores():
    validadores = Validador.query.all()
    validadores_list = [{'endereco': v.endereco, 'stake': v.stake, 'key': v.key} for v in validadores]
    #logger.debug(f"Validadores retornados: {validadores_list}")
    return jsonify({'validadores': validadores_list}), 200

# Rota pra aplicar flags aos validadores
@bp.route('/seletor/flag', methods=['POST'])
def flag_validador():
    dados = request.json
    logger.debug(f"Dados recebidos para flag validador: {dados}")
    endereco = dados.get('endereco')
    acao = dados.get('acao') # 'add' para adiconar flag e 'remover' para remover
    resultado = update_flags_validador(endereco, acao)
    logger.debug(f"Resultado da atualização de flags: {resultado}")
    return jsonify(resultado), resultado['status_code']

@bp.route('/seletor/hold', methods=['POST'])
def hold_validador():
    dados = request.json
    logger.debug(f"Dados recebidos para hold validador: {dados}")
    endereco = dados.get('endereco')
    resultado = hold_validador_(endereco)
    logger.debug(f"Resultado do hold do validador: {resultado}")
    return jsonify(resultado), resultado['status_code']