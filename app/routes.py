from flask import Blueprint, current_app, request, jsonify
import requests
from datetime import datetime
from .models import db, Usuario, Transacao, Seletor
from .validacao import (
    distribuir_taxas, gerenciar_consenso, update_flags_validador, hold_validador_, registrar_validador_, expulsar_validador_, 
    selecionar_validadores, gerar_chave, lista_validadores, remover_validador_, registrar_seletor_, remover_seletor_
)
import logging

# Configura o logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Define o nível de log

# Cria o blueprint para as rotas
bp = Blueprint('routes', __name__)

BASE_URL = 'http://127.0.0.1:5000' # URL base para as requisições internas

@bp.route('/trans', methods=['POST'])
def transacao():
    dados = request.json  # Obtém os dados JSON da requisição

    if not isinstance(dados, list):
        dados = [dados]  # Transforma um único objeto em uma lista para processamento uniforme

    resultados = []

    for transacao in dados:
        try:
            # Verifica e extrai os dados da transação
            id_remetente = transacao.get('id_remetente')
            id_receptor = transacao.get('id_receptor')
            quantia = transacao.get('quantia')
            chaves_validacao = transacao.get('keys_validacao')  # Lista de chaves de validação

            if not all([id_remetente, id_receptor, quantia, chaves_validacao]):
                raise ValueError("Dados da transação incompletos")

            transacao_dados = {
                'id_remetente': id_remetente,
                'id_receptor': id_receptor,
                'quantia': quantia
            }

            # Verifica se os validadores já foram selecionados
            validadores_selecionados = current_app.config.get('validadores_selecionados')
            if not validadores_selecionados:
                return jsonify({'mensagem': 'Validadores não selecionados', 'status_code': 400}), 400

            logger.debug(f"Validadores selecionados: {[v.endereco for v in validadores_selecionados]}")

            # Verifica se todas as chaves de validação fornecidas são válidas
            chaves_geradas = [gerar_chave(v.seletor_id, v.endereco) for v in validadores_selecionados]
            chaves_validas = all(k in chaves_geradas for k in chaves_validacao)

            if not chaves_validas:
                logger.debug(f"Chave de validação inválida: fornecida {chaves_validacao}")
                resultados.append({'mensagem': 'Chave de validação inválida', 'status_code': 400})
                continue

            transacao_dados['keys_validacao'] = ",".join(chaves_validacao)
            logger.debug(f"Chaves de validação a serem armazenadas na transação: {chaves_validacao}")

            # Cria e armazena a nova transação no banco de dados
            nova_transacao = Transacao(
                id_remetente=id_remetente,
                id_receptor=id_receptor,
                quantia=quantia,
                status=0,
                keys_validacao=",".join(chaves_validacao),  # Armazena as chaves de validação como string separada por vírgulas
                horario=datetime.utcnow()
            )

            db.session.add(nova_transacao)
            db.session.commit()

        except Exception as e:
            # Lida com exceções durante a criação da transação
            logger.error("Erro ao processar a transação", exc_info=True)
            resultados.append({'mensagem': str(e), 'status_code': 500})
            continue

        try:
            # Recupera a nova transação criada do banco de dados
            transacao_atual = db.session.get(Transacao, nova_transacao.id)
            if not transacao_atual:
                logger.error("Transação não encontrada no banco de dados")
                resultados.append({'mensagem': 'Transação não encontrada', 'status_code': 404})
                continue

            # Verifica o saldo do remetente
            remetente = db.session.get(Usuario, id_remetente)
            taxa = quantia * 0.015
            if remetente.saldo < (quantia + taxa):
                logger.debug(f"Saldo insuficiente: {remetente.saldo} < {quantia} + {taxa}")
                transacao_atual.status = 2  # Status 2 = transação rejeitada por saldo insuficiente
                db.session.commit()
                resultados.append({'id_transacao': transacao_atual.id, 'mensagem': 'Saldo insuficiente', 'status': 'rejeitada'})
                continue

            # Obtém o tempo atual
            resposta_tempo_atual = requests.get(f'{BASE_URL}/hora')
            if resposta_tempo_atual.status_code != 200:
                logger.error(f"Erro ao obter o tempo atual: {resposta_tempo_atual.status_code}")
                resultados.append({'id_transacao': transacao_atual.id, 'mensagem': 'Erro ao obter o tempo atual', 'status': 'rejeitada'})
                continue

            # Verifica a chave de validação fornecida
            chaves_geradas = transacao_atual.keys_validacao.split(",")
            if not any(k in chaves_geradas for k in chaves_validacao):
                logger.debug(f"Chave de validação inválida: fornecida {chaves_validacao}")
                transacao_atual.status = 2  # Status 2 = transação rejeitada por chave de validação inválida
                db.session.commit()
                resultados.append({'id_transacao': transacao_atual.id, 'mensagem': 'Chave de validação inválida', 'status': 'rejeitada'})
                continue

            # Gerencia o consenso dos validadores para a transação
            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            seletor = db.session.get(Seletor, seletor_id)
            resultado = gerenciar_consenso([transacao_atual], validadores_selecionados, seletor)
            logger.debug(f"Resultado da validação do consenso: {resultado}")

            if resultado['status_code'] == 200:
                if transacao_atual.status == 1:
                    # Se a transação é validada com sucesso, atualiza os saldos
                    remetente.saldo -= quantia
                    receptor = db.session.get(Usuario, id_receptor)
                    receptor.saldo += quantia
                    db.session.commit()
                    resultados.append({'id_transacao': transacao_atual.id, 'mensagem': 'Transação feita com sucesso', 'status': 'sucesso'})

                    # Distribui as taxas
                    distribuir_taxas(transacao_atual, seletor)
                else:
                    resultado.update({'id_transacao': transacao_atual.id, 'mensagem': 'Transação rejeitada', 'status': 'rejeitada'})
                    resultados.append(resultado)
            else:
                # Se a transação é rejeitada pelo consenso dos validadores
                transacao_atual.status = 2  # Status 2 = transação rejeitada por consenso
                db.session.commit()
                resultado.update({'id_transacao': transacao_atual.id, 'mensagem': 'Transação rejeitada', 'status': 'rejeitada'})
                resultados.append(resultado)

        except Exception as e:
            # Lida com exceções
            logger.error("Erro ao processar a transação", exc_info=True)
            resultados.append({'mensagem': str(e), 'status_code': 500})

    return jsonify(resultados), 200  # Retorna os resultados das transações processadas

@bp.route('/hora', methods=['GET'])
def get_tempo_atual():
    # Obtém o tempo atual do servidor
    tempo_atual = datetime.utcnow()
    logger.debug(f"Tempo atual retornado: {tempo_atual}")
    return jsonify({'tempo_atual': tempo_atual.isoformat()}), 200

@bp.route('/validador/registrar', methods=['POST'])
def registrar_validador():
    # Registra um novo validador
    dados = request.json
    logger.debug(f"Dados recebidos para registrar validador: {dados}")
    endereco = dados.get('endereco')
    stake = dados.get('stake')
    key = dados.get('key')
    seletor_id = dados.get('seletor_id')
    resultado = registrar_validador_(endereco, stake, key, seletor_id)
    logger.debug(f"Resultado do registro do validador: {resultado}")
    return jsonify(resultado), resultado['status_code']

@bp.route('/validador/expulsar', methods=['POST'])
def expulsar_validador():
    # Expulsa um validador
    dados = request.json
    logger.debug(f"Dados recebidos para expulsar validador: {dados}")
    endereco = dados.get('endereco')
    resultado = expulsar_validador_(endereco)
    logger.debug(f"Resultado da expulsão do validador: {resultado}")
    return jsonify(resultado), resultado['status_code']

@bp.route('/validador/remover', methods=['POST'])
def remover_validador():
    # Remove um validador
    dados = request.get_json()
    endereco = dados.get('endereco')
    resultado = remover_validador_(endereco)
    return jsonify(resultado), resultado['status_code']

@bp.route('/usuarios', methods=['GET'])
def obter_usuarios():
    # Obtém a lista de usuários
    usuarios = Usuario.query.all()
    usuarios_list = [{'id': usuario.id, 'nome': usuario.nome, 'saldo': usuario.saldo} for usuario in usuarios]
    logger.debug(f"Usuários retornados: {usuarios_list}")
    return jsonify({'usuarios': usuarios_list})

@bp.route('/validador/listar', methods=['GET'])
def listar_validadores():
    # Lista todos os validadores
    resultado, status_code = lista_validadores()
    logger.debug(f"Validadores retornados: {resultado}")
    return jsonify(resultado), status_code

@bp.route('/validador/flag', methods=['POST'])
def flag_validador():
    # Adiciona ou remove flags de validadores
    dados = request.json
    logger.debug(f"Dados recebidos para flag validador: {dados}")
    endereco = dados.get('endereco')
    acao = dados.get('acao')  # 'add' para adicionar flag e 'remover' para remover
    resultado = update_flags_validador(endereco, acao)
    logger.debug(f"Resultado da atualização de flags: {resultado}")
    return jsonify(resultado), resultado['status_code']

@bp.route('/validador/hold', methods=['POST'])
def hold_validador():
    # Coloca o validador em hold
    dados = request.json
    logger.debug(f"Dados recebidos para hold validador: {dados}")
    endereco = dados.get('endereco')
    resultado = hold_validador_(endereco)
    logger.debug(f"Resultado do hold do validador: {resultado}")
    return jsonify(resultado), resultado['status_code']

# Rota para registrar um novo seletor
@bp.route('/seletor/registrar', methods=['POST'])
def registrar_seletor():
    dados = request.get_json()
    nome = dados.get('nome')
    endereco = dados.get('endereco')
    saldo = dados.get('saldo')
    resultado = registrar_seletor_(nome, endereco, saldo)
    return jsonify(resultado), resultado['status_code']

# Rota para remover um seletor
@bp.route('/seletor/remover', methods=['POST'])
def remover_seletor():
    dados = request.get_json()
    endereco = dados.get('endereco')
    resultado = remover_seletor_(endereco)
    return jsonify(resultado), resultado['status_code']

@bp.route('/seletor/<int:seletor_id>/selecionar_validadores', methods=['POST'])
def selecionar_validadores_seletor(seletor_id):
    try:
        seletor = db.session.get(Seletor, seletor_id)
        if not seletor:
            return jsonify({'mensagem': 'Seletor não encontrado', 'status_code': 404}), 404

        validadores_selecionados = selecionar_validadores()
        if not validadores_selecionados:
            return jsonify({'mensagem': 'Não há validadores suficientes', 'status_code': 400}), 400

        # Armazena os validadores selecionados na configuração da aplicação
        current_app.config['validadores_selecionados'] = validadores_selecionados
        current_app.config['seletor_id'] = seletor_id
        return jsonify({'mensagem': 'Validadores selecionados com sucesso', 'validadores': [v.id for v in validadores_selecionados]}), 200
    except Exception as e:
        logger.error("Erro ao selecionar validadores", exc_info=True)
        return jsonify({'mensagem': str(e), 'status_code': 500}), 500