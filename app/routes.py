from flask import Blueprint, current_app, request, jsonify
from datetime import datetime
from .models import db, Usuario, Transacao, Seletor
from .validacao import (
    editar_seletor_, editar_validador_, gerenciar_consenso, update_flags_validador, hold_validador_, registrar_validador_, expulsar_validador_, 
    selecionar_validadores, lista_validadores, remover_validador_, registrar_seletor_, remover_seletor_
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

    # Verifica se os dados recebidos são uma lista. Se não forem, transforma o único objeto em uma lista.
    if not isinstance(dados, list):
        dados = [dados]  # Transforma um único objeto em uma lista para processamento uniforme

    resultados = []  # Lista para armazenar os resultados das transações processadas

    for transacao in dados:
        try:
            # Verifica e extrai os dados da transação
            id_remetente = transacao.get('id_remetente')
            id_receptor = transacao.get('id_receptor')
            quantia = transacao.get('quantia')
            chaves_validacao = transacao.get('keys_validacao')  # Lista de chaves de validação

            # Verifica se todos os dados necessários da transação estão presentes
            if not all([id_remetente, id_receptor, quantia, chaves_validacao]):
                raise ValueError("Dados da transação incompletos")

            # Verifica se os validadores já foram selecionados
            validadores_selecionados = current_app.config.get('validadores_selecionados')
            if not validadores_selecionados:
                return jsonify({'mensagem': 'Validadores não selecionados', 'status_code': 400}), 400

            logger.debug(f"Validadores selecionados: {[v.endereco for v in validadores_selecionados]}")

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
            continue  # Continua para a próxima transação

    try:
        # Recupera todas as transações criadas do banco de dados com status 0 (pendente)
        transacoes_criadas = db.session.query(Transacao).filter(Transacao.status == 0).all()
        
        # Gerencia o consenso dos validadores para cada transação pendente
        for transacao_atual in transacoes_criadas:
            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            seletor = db.session.get(Seletor, seletor_id)
            resultado = gerenciar_consenso([transacao_atual], validadores_selecionados, seletor)
            logger.debug(f"Resultado da validação do consenso: {resultado}")

            if resultado['status_code'] == 200:
                if transacao_atual.status == 1:
                    # Se a transação é validada com sucesso, atualiza os saldos
                    remetente = db.session.get(Usuario, transacao_atual.id_remetente)
                    receptor = db.session.get(Usuario, transacao_atual.id_receptor)
                    remetente.saldo -= transacao_atual.quantia
                    receptor.saldo += transacao_atual.quantia
                    db.session.commit()
                    resultados.append({'id_transacao': transacao_atual.id, 'mensagem': 'Transação feita com sucesso', 'status': 'sucesso'})
                else:
                    resultado.update({'id_transacao': transacao_atual.id, 'mensagem': 'Transação rejeitada', 'status': 'rejeitada'})
                    resultados.append(resultado)
            else:
                # Se a transação é rejeitada pelo consenso
                transacao_atual.status = 2  # Status 2
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

@bp.route('/validador/editar/<int:validador_id>', methods=['POST'])
def editar_validador(validador_id):
    # Edita um validador existente
    dados = request.get_json()
    stake = dados.get('stake')
    resultado = editar_validador_(validador_id, stake)
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
    endereco = dados.get('endereco')
    saldo = dados.get('saldo')
    resultado = registrar_seletor_(endereco, saldo)
    return jsonify(resultado), resultado['status_code']

# Rota para editar um seletor existente
@bp.route('/seletor/editar/<int:seletor_id>', methods=['POST'])
def editar_seletor(seletor_id):
    dados = request.get_json()
    endereco = dados.get('endereco')
    saldo = dados.get('saldo')
    resultado = editar_seletor_(seletor_id, endereco, saldo)
    return jsonify(resultado), resultado['status_code']

# Rota para remover um seletor
@bp.route('/seletor/remover', methods=['POST'])
def remover_seletor():
    dados = request.get_json()
    endereco = dados.get('endereco')
    resultado = remover_seletor_(endereco)
    return jsonify(resultado), resultado['status_code']

# Rota para um seletor selecionar validadores
@bp.route('/seletor/<int:seletor_id>/selecionar_validadores', methods=['POST'])
def selecionar_validadores_seletor(seletor_id):
    try:
        # Obtem o seletor com o ID fornecido do banco de dados
        seletor = db.session.get(Seletor, seletor_id)
        if not seletor:
            return jsonify({'mensagem': 'Seletor não encontrado', 'status_code': 404}), 404

        # Chama a função selecionar_validadores passando o seletor e armazena os validadores selecionados
        validadores_selecionados = selecionar_validadores(seletor)
        if not validadores_selecionados:
            return jsonify({'mensagem': 'Não há validadores suficientes', 'status_code': 400}), 400

        # Armazena os validadores selecionados e o ID do seletor na configuração da aplicação para uso na rota de transação
        current_app.config['validadores_selecionados'] = validadores_selecionados
        current_app.config['seletor_id'] = seletor_id
        
        return jsonify({'mensagem': 'Validadores selecionados com sucesso', 'validadores': [v.id for v in validadores_selecionados]}), 200
    except Exception as e:
        logger.error("Erro ao selecionar validadores", exc_info=True)
        return jsonify({'mensagem': str(e), 'status_code': 500}), 500

# Rota para registrar um usuário
@bp.route('/usuario/registrar', methods=['POST'])
def registrar_usuario():
    dados = request.get_json()
    nome = dados.get('nome')
    saldo = dados.get('saldo', 0.0)  # saldo default se não fornecido
    
    # Verifica se o usuário já existe pelo nome
    usuario_existente = Usuario.query.filter_by(nome=nome).first()
    if usuario_existente:
        return jsonify({'mensagem': f'Usuário {nome} já existe', 'status_code': 400}), 400

    novo_usuario = Usuario(nome=nome, saldo=saldo)
    db.session.add(novo_usuario)
    db.session.commit()

    return jsonify({'mensagem': f'Usuário {nome} foi registrado', 'status_code': 200}), 200

# Rota para editar um usuário existente
@bp.route('/usuario/editar/<int:usuario_id>', methods=['POST'])
def editar_usuario(usuario_id):
    dados = request.get_json()
    nome = dados.get('nome')
    saldo = dados.get('saldo')

    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return jsonify({'mensagem': 'Usuário não encontrado', 'status_code': 404}), 404

    if nome:
        # Verifica se o nome já existe
        nome_existe = db.session.query(Usuario.id).filter(Usuario.nome == nome, Usuario.id != usuario_id).first()
        if nome_existe:
            return jsonify({'mensagem': 'Nome já está em uso', 'status_code': 400}), 400
        usuario.nome = nome

    if saldo is not None:
        usuario.saldo = saldo

    db.session.commit()

    return jsonify({'mensagem': f'Usuário {usuario.nome} foi atualizado', 'status_code': 200}), 200

# Rota para remover um usuário
@bp.route('/usuario/remover', methods=['POST'])
def remover_usuario():
    dados = request.get_json()
    nome = dados.get('nome')

    usuario = Usuario.query.filter_by(nome=nome).first()
    if not usuario:
        return jsonify({'mensagem': 'Usuário não encontrado', 'status_code': 404}), 404

    db.session.delete(usuario)
    db.session.commit()

    return jsonify({'mensagem': f'Usuário {nome} foi removido', 'status_code': 200}), 200