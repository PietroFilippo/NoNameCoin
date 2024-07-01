from .models import db, Usuario, Transacao, Validador, Seletor
import random
from datetime import datetime, timedelta
import logging

# Configura o logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Define o nível de log

def selecionar_validadores():
    # Seleciona os validadores disponíveis
    validadores_disponiveis = Validador.query.filter_by(status='ativo').all()
    stake_total = sum(validador.stake for validador in validadores_disponiveis)
    validadores_selecionados = []

    if stake_total == 0:
        return validadores_selecionados  # Se não houver stake total é retornado uma lista vazia

    tentativa_inicio = datetime.utcnow()  # Registra o início da tentativa de seleção

    while len(validadores_selecionados) < 3 and (datetime.utcnow() - tentativa_inicio).seconds < 60:
        # Loop até selecionar 3 validadores ou espera 60 segundos caso tenha nenhum validador disponivel
        validadores_disponiveis = [validador for validador in validadores_disponiveis if validador not in validadores_selecionados]
        for validador in validadores_disponiveis:
            if validador.status == 'on_hold':
                validador.transacoes_hold_restantes -= 1
                if validador.transacoes_hold_restantes <= 0:
                    validador.status = 'ativo'  # Ativa o validador se o hold terminar
                db.session.commit()
                continue

            probabilidade = min(validador.stake / stake_total, 0.20)
            if validador.flag == 1:
                probabilidade *= 0.5  # Reduz a probabilidade se o validador tiver uma flag
            elif validador.flag == 2:
                probabilidade *= 0.25  # Reduz mais ainda a probabilidade se o validador tiver duas flags
            if validador.selecoes_consecutivas >= 5:
                validador.status = 'on_hold'
                validador.transacoes_hold_restantes = 5  # Define a quantidade de transações requiridas para sair do hold
                validador.selecoes_consecutivas = 0
                db.session.commit()
                continue

            if random.random() < probabilidade:
                validador.selecoes_consecutivas += 1
                validadores_selecionados.append(validador)
                if len(validadores_selecionados) == 3:
                    break

    if len(validadores_selecionados) < 3:
        logger.debug("Não há validadores suficientes, colocando a transação em espera.")
        return []

    for validador in validadores_disponiveis:
        if validador not in validadores_selecionados:
            validador.selecoes_consecutivas = 0  # Reseta o contador de seleções consecutivas

    db.session.commit()

    chaves_validadores = [validador.key for validador in validadores_selecionados]
    #logger.debug(f"Chaves dos validadores selecionados: {chaves_validadores}")

    return validadores_selecionados

def logica_validacao(validador, transacao):
    remetente = db.session.get(Usuario, transacao.id_remetente)
    tempo_atual = datetime.utcnow()

    # Verifica se o remetente está bloqueado
    if remetente.tempo_bloqueio:
        if remetente.tempo_bloqueio > tempo_atual:
            logger.debug(f"Validação falhou: remetente {remetente.id} está bloqueado até {remetente.tempo_bloqueio}")
            return False, "Remetente bloqueado"
        else:
            # Remove o bloqueio se o tempo de bloqueio tiver expirado
            remetente.tempo_bloqueio = None
            db.session.commit()
            logger.debug(f"Remetente {remetente.id} não está mais bloqueado")

    # Verifica se o remetente tem saldo suficiente para a transação acrescido das taxas
    taxas = transacao.quantia * 0.015
    if remetente.saldo < transacao.quantia + taxas:
        logger.debug(f"Validação falhou: remetente {remetente.id} não tem saldo suficiente")
        return False, "Saldo insuficiente"

    # Verifica o horário da transação
    if transacao.horario > tempo_atual:
        logger.debug(f"Validação falhou: horário da transação está incorreto {transacao.horario}")
        return False, "Horário incorreto"

    # Verifica se a transação é posterior à última transação
    ultima_transacao = Transacao.query.filter_by(id_remetente=transacao.id_remetente).order_by(Transacao.horario.desc()).first()
    if ultima_transacao and transacao.horario < ultima_transacao.horario:
        logger.debug(f"Validação falhou: horário da transação {transacao.horario} foi feita antes da última transação {ultima_transacao.horario}")
        return False, "Transação anterior à última"

    # Verifica o número de transações feitas em 1 minuto
    um_minuto = tempo_atual - timedelta(minutes=1)
    num_transacoes = Transacao.query.filter(Transacao.id_remetente == transacao.id_remetente, Transacao.horario > um_minuto).count()
    if num_transacoes >= 100:
        remetente.tempo_bloqueio = tempo_atual + timedelta(minutes=1)
        db.session.commit()
        logger.debug(f"Validação falhou: remetente {remetente.id} fez mais de 100 transações no último minuto e está bloqueado até {remetente.tempo_bloqueio}")
        return False, "Número de transações excedido, remetente bloqueado"

    # Verifica a chave de validação
    chaves_validacao = transacao.keys_validacao.split(",")
    if validador.chave_seletor not in chaves_validacao:
        logger.debug(f"Chave de validação inválida: fornecida {validador.chave_seletor}, esperada {chaves_validacao}")
        return False, "Chave de validação inválida"

    logger.debug(f"Chave de validação válida. Chave do validador: {validador.chave_seletor}, Chaves da transação: {chaves_validacao}")
    return True, "Validação bem-sucedida"

def gerenciar_consenso(transacoes, validadores, seletor):
    # Gerencia o consenso dos validadores nas transações
    if not validadores:
        return {'mensagem': 'Sem validadores disponíveis', 'status_code': 503}

    resultados = []
    for transacao in transacoes:
        if not isinstance(transacao, Transacao):
            logger.error(f"Objeto inválido encontrado na lista de transações: {transacao}")
            continue
        aprovacoes = 0
        rejeicoes = 0
        validadores_maliciosos = []
        chaves_validas = [validador.chave_seletor for validador in validadores]

        # Verifica a chave de validação
        chaves_validacao = transacao.keys_validacao.split(",")
        if not all(chave in chaves_validacao for chave in chaves_validas):
            logger.debug(f"Chave de validação inválida: esperadas {chaves_validas}, fornecidas {chaves_validacao}")
            resultados.append({'id_transacao': transacao.id, 'status': 'rejeitada', 'mensagem': 'Chave de validação inválida'})
            continue

        # Verifica todos os validadores selecionados
        for validador in validadores:
            valido, motivo = logica_validacao(validador, transacao)
            if valido:
                aprovacoes += 1
                validador.transacoes_coerentes += 1
                #logger.debug(f"Validador {validador.id} - Depois do incremento: {validador.transacoes_coerentes}")
            else:
                rejeicoes += 1
                validadores_maliciosos.append(validador)

            remover_flag_validador(validador)  # Remove flags do validador
            db.session.commit()  # Commit dentro do loop para persistir cada alteração

        logger.debug(f"Transação {transacao.id}: Aprovado por {aprovacoes} validadores, Rejeitado por {rejeicoes} validadores")

        consenso = 1 if aprovacoes > len(validadores) // 2 else 2
        transacao.status = consenso
        db.session.commit()  # Commit das alterações na transação

        distribuir_taxas(transacao, seletor)  # Distribui as taxas

        if consenso == 1 and validadores_maliciosos:  # Transação rejeitada para validadores maliciosos
            for validador_malicioso in validadores_maliciosos:
                update_flags_validador(validador_malicioso.endereco, 'add')  # Aplica uma FLAG a cada validador malicioso

        resultados.append({'id_transacao': transacao.id, 'status': 'validada' if consenso == 1 else 'rejeitada'})

    status_code = 200 if all(transacao.status == 1 for transacao in transacoes) else 500
    db.session.commit()  # Commit final após processar todas as transações
    return {'resultados': resultados, 'status_code': status_code}

def lista_validadores():
    # Lista todos os validadores
    validadores = Validador.query.all()
    dados_validadores = [{'endereco': validador.endereco, 'stake': validador.stake, 'key': validador.key} for validador in validadores]
    return {'validadores': dados_validadores}, 200

def update_flags_validador(endereco, acao):
    # Atualiza as flags de um validador
    validador = Validador.query.filter_by(endereco=endereco).first()
    if not validador:
        return {'mensagem': f'Endereço {endereco} não foi encontrado', 'status_code': 404}
    
    if acao == 'add':
        validador.flag = min(validador.flag + 1, 3)
        if validador.flag > 2:
            expulsar_validador_(endereco)
            return {'mensagem': f'Validador de endereço {endereco} foi expulso por excesso de flags', 'status_code': 200}
    elif acao == 'remover':
        validador.flag = max(validador.flag - 1, 0)
    else:
        return {'mensagem': f'Ação {acao} inválida', 'status_code': 400}

    db.session.commit()
    return {'mensagem': f'Flag do validador de endereço {endereco} foi atualizado', 'status_code': 200}

def remover_flag_validador(validador):
    # Remove flags de um validador após 10000 transações coerentes
    if validador.transacoes_coerentes >= 10000:
        validador.flag = max(validador.flag - 1, 0)
        validador.transacoes_coerentes = 0  # Reseta o contador de transações coerentes
        db.session.commit()

def hold_validador_(endereco):
    # Coloca um validador em hold
    validador = Validador.query.filter_by(endereco=endereco).first()
    if not validador:
        return {'mensagem': f'Endereço {endereco} não foi encontrado', 'status_code': 404}

    validador.status = 'on_hold'
    db.session.commit()
    return {'mensagem': f'Validador de endereço {endereco} está on hold', 'status_code': 200}

def gerar_chave(seletor_id, validador_endereco):
    # Gera uma chave de validação com base no seletor e no endereço do validador
    chave = f"{seletor_id}-{validador_endereco}"
    return chave

def registrar_validador_(endereco, stake, key, seletor_id):
    # Registra um novo validador
    if stake < 50.0:
        return {'mensagem': 'O saldo mínimo de 50 NoNameCoins é necessário para registrar um validador', 'status_code': 400}
    
    validador_existente = Validador.query.filter_by(endereco=endereco).first()
    seletor = db.session.get(Seletor, seletor_id)
    if not seletor:
        return {'mensagem': 'Seletor não encontrado', 'status_code': 404}

    chave_seletor = gerar_chave(seletor_id, endereco)
    logger.debug(f"Chave de validação gerada: {chave_seletor} para seletor_id: {seletor_id} e validador_endereco: {endereco}")

    if validador_existente:
        if validador_existente.status == 'expulso':
            if validador_existente.retorno_contagem >= 2:
                return {'mensagem': f'Validador de endereço {endereco} não pode retornar mais vezes', 'status_code': 400}
            if stake < 2 * 50.0:
                return {'mensagem': f'Validador de endereço {endereco} precisa travar pelo menos o dobro do saldo mínimo', 'status_code': 400}
            validador_existente.status = 'ativo'
            validador_existente.retorno_contagem += 1
            validador_existente.stake = stake
            validador_existente.key = key
            validador_existente.chave_seletor = chave_seletor
            validador_existente.seletor_id = seletor_id
            db.session.commit()
            return {'mensagem': f'Validador de endereço {endereco} foi reativado', 'status_code': 200}
        else:
            return {'mensagem': f'Validador de endereço {endereco} já existe', 'status_code': 400}

    novo_validador = Validador(
        endereco=endereco, 
        stake=stake, 
        key=key, 
        chave_seletor=chave_seletor, 
        status='ativo', 
        retorno_contagem=0,
        seletor_id=seletor_id
    )
    db.session.add(novo_validador)
    db.session.commit()

    return {'mensagem': f'Validador de endereço {endereco} foi registrado', 'status_code': 200, 'chave_seletor': chave_seletor}

def expulsar_validador_(endereco):
    # Expulsa um validador
    validador = Validador.query.filter_by(endereco=endereco).first()
    if validador:
        validador.status = 'expulso'
        validador.stake = 0  # Zera o saldo do validador
        db.session.commit()
        return {"mensagem": f"Validador de endereço {endereco} foi expulso", "status_code": 200}
    else:
        return {"mensagem": "Validador não encontrado", "status_code": 404}
    
def remover_validador_(endereco):
    # Remove um validador do banco de dados
    validador = Validador.query.filter_by(endereco=endereco).first()
    if validador:
        db.session.delete(validador)
        db.session.commit()
        return {"mensagem": f"Validador de endereço {endereco} foi removido do banco de dados", "status_code": 200}
    else:
        return {"mensagem": "Validador não encontrado", "status_code": 404}
    
def registrar_seletor_(nome, endereco, saldo):
    # Registra um novo seletor
    seletor_existente = Seletor.query.filter_by(endereco=endereco).first()
    if seletor_existente:
        return {'mensagem': f'Seletor de endereço {endereco} já existe', 'status_code': 400}

    novo_seletor = Seletor(nome=nome, endereco=endereco, saldo=saldo)
    db.session.add(novo_seletor)
    db.session.commit()

    return {'mensagem': f'Seletor de endereço {endereco} foi registrado', 'status_code': 200}

def remover_seletor_(endereco):
    # Remove um seletor do banco de dados
    seletor = Seletor.query.filter_by(endereco=endereco).first()
    if seletor:
        db.session.delete(seletor)
        db.session.commit()
        return {"mensagem": f"Seletor de endereço {endereco} foi removido do banco de dados", "status_code": 200}
    else:
        return {"mensagem": "Seletor não encontrado", "status_code": 404}

def distribuir_taxas(transacao, seletor):
    # Distribui as taxas de uma transação entre o seletor e os validadores
    quantia_transacionada = transacao.quantia
    taxa_seletor = quantia_transacionada * 0.015  # 1,5% da quantia transacionada
    taxa_validadores = quantia_transacionada * 0.01  # 1% da quantia transacionada
    taxa_travada = quantia_transacionada * 0.005  # 0,5% da quantia transacionada

    validadores = selecionar_validadores()
    if not validadores:
        return {'mensagem': 'Sem validadores disponíveis', 'status_code': 503}

    # Distribui a taxa de 1% entre os validadores
    for validador in validadores:
        validador.stake += taxa_validadores / len(validadores)

    # Adiciona a taxa travada de 0,5% a cada validador individualmente
    for validador in validadores:
        validador.stake += taxa_travada

    # Adiciona a taxa ao saldo do seletor
    seletor.saldo += taxa_seletor

    db.session.commit()

    return {'mensagem': 'Taxas distribuídas', 'status_code': 200}
