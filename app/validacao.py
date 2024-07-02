from .models import db, Usuario, Transacao, Validador, Seletor
import random
from datetime import datetime, timedelta
import logging

# Configura o logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Define o nível de log

def selecionar_validadores(seletor):
    # Seleciona os validadores disponíveis que pertencem ao seletor específico
    validadores_disponiveis = Validador.query.filter_by(status='ativo', seletor_id=seletor.id).all()
    
    # Calcula o stake total dos validadores disponíveis
    stake_total = sum(validador.stake for validador in validadores_disponiveis)
    
    # Inicializa uma lista para armazenar os validadores selecionados
    validadores_selecionados = []

    # Se não houver stake total, retorna uma lista vazia
    if stake_total == 0:
        return validadores_selecionados

    # Registra o início da tentativa de seleção
    tentativa_inicio = datetime.utcnow()

    # Continua tentando selecionar validadores até que tenha selecionado 3 ou até que tenha passado 60 segundos
    while len(validadores_selecionados) < 3 and (datetime.utcnow() - tentativa_inicio).seconds < 60:
        # Atualiza a lista de validadores disponíveis removendo os já selecionados
        validadores_disponiveis = [validador for validador in validadores_disponiveis if validador not in validadores_selecionados]
        
        for validador in validadores_disponiveis:
            # Gerencia o status 'on_hold' dos validadores
            if validador.status == 'on_hold':
                validador.transacoes_hold_restantes -= 1
                if validador.transacoes_hold_restantes <= 0:
                    validador.status = 'ativo'
                db.session.commit()
                continue

            # Calcula a probabilidade de seleção baseada no stake
            probabilidade = min(validador.stake / stake_total, 0.20)
            
            # Ajusta a probabilidade se o validador tiver flags
            if validador.flag == 1:
                probabilidade *= 0.5
            elif validador.flag == 2:
                probabilidade *= 0.25
            
            # Coloca o validador em 'on_hold' caso ele tenha sido selecionado 5 vezes consecutivas
            if validador.selecoes_consecutivas >= 5:
                validador.status = 'on_hold'
                validador.transacoes_hold_restantes = 5
                validador.selecoes_consecutivas = 0
                db.session.commit()
                continue

            # Seleciona o validador baseado na probabilidade
            if random.random() < probabilidade:
                validador.selecoes_consecutivas += 1
                validadores_selecionados.append(validador)
                if len(validadores_selecionados) == 3:
                    break

    # Se menos de 3 validadores forem selecionados, retorna uma lista vazia
    if len(validadores_selecionados) < 3:
        logger.debug("Não há validadores suficientes, colocando a transação em espera.")
        return []

    # Reseta o contador de seleções consecutivas para os validadores não selecionados
    for validador in validadores_disponiveis:
        if validador not in validadores_selecionados:
            validador.selecoes_consecutivas = 0

    # Faz o commit das mudanças no banco de dados
    db.session.commit()

    # Retorna a lista de validadores selecionados
    return validadores_selecionados

def logica_validacao(validador, transacao):
    # Obtém o remetente da transação do banco de dados
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

    # Calcula as taxas da transação (1.5% da quantia)
    taxas = transacao.quantia * 0.015
    
    # Verifica se o remetente tem saldo suficiente para a transação acrescido das taxas
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
        logger.debug(f"Chave de validação inválida: fornecida: {validador.chave_seletor}, esperada {chaves_validacao}")
        return False, "Chave de validação inválida"

    # Se todas as verificações passaram a transação é válida
    logger.debug(f"Chave de validação válida. Chave do validador: {validador.chave_seletor}, Chaves da transação: {chaves_validacao}")
    return True, "Validação bem-sucedida"

def gerenciar_consenso(transacoes, validadores, seletor):
    # Gerencia o consenso dos validadores nas transações
    if not validadores:
        return {'mensagem': 'Sem validadores disponíveis', 'status_code': 503}

    # Inicializa a lista de resultados
    resultados = []
    
    # Processa cada transação
    for transacao in transacoes:
        if not isinstance(transacao, Transacao):
            logger.error(f"Objeto inválido encontrado na lista de transações: {transacao}")
            continue

        # Inicializa contadores para aprovações e rejeições
        aprovacoes = 0
        rejeicoes = 0
        validadores_maliciosos = []
        rejeicoes_legitimas = False

        # Verifica todos os validadores selecionados
        for validador in validadores:
            # Aplica a lógica de validação para cada validador
            valido, motivo = logica_validacao(validador, transacao)
            if valido:
                aprovacoes += 1
                validador.transacoes_coerentes += 1
            else:
                rejeicoes += 1
                # Identifica se a rejeição é legítima ou maliciosa
                if motivo in ['Saldo insuficiente', 'Horário incorreto', 'Transação anterior à última', 'Número de transações excedido, remetente bloqueado', 'Remetente bloqueado']:
                    rejeicoes_legitimas = True
                else:
                    validadores_maliciosos.append(validador)

            # Remove flags do validador caso tenha transações coerentes suficientes
            remover_flag_validador(validador)
            db.session.commit()

        logger.debug(f"Transação {transacao.id}: Aprovado por {aprovacoes} validadores, Rejeitado por {rejeicoes} validadores")

        # Verifica o consenso baseado na aprovação de pelo menos dois validadores honestos
        consenso = 1 if aprovacoes > 1 else 2
        transacao.status = consenso
        db.session.commit()

        # Distribui as taxas se a transação foi validada
        if consenso == 1:
            distribuir_taxas(transacao, seletor, validadores, validadores_maliciosos)

        # Adiciona flags aos validadores maliciosos se não houver rejeições legítimas
        if not rejeicoes_legitimas:
            for validador_malicioso in validadores_maliciosos:
                update_flags_validador(validador_malicioso.endereco, 'add')

        # Adiciona o resultado da transação na lista de resultados
        resultados.append({'id_transacao': transacao.id, 'status': 'validada' if consenso == 1 else 'rejeitada'})

    # Define o código de status com base no consenso de todas as transações
    status_code = 200 if all(transacao.status == 1 for transacao in transacoes) else 500
    db.session.commit()
    
    # Retorna os resultados e o código de status
    return {'resultados': resultados, 'status_code': status_code}

def lista_validadores():
    # Lista todos os validadores
    validadores = Validador.query.all()
    dados_validadores = [{'endereco': validador.endereco, 'stake': validador.stake, 'key': validador.key} for validador in validadores]
    return {'validadores': dados_validadores}, 200

def update_flags_validador(endereco, acao):
    # Atualiza as flags de um validador com base na ação especificada
    validador = Validador.query.filter_by(endereco=endereco).first()
    
    if not validador:
        return {'mensagem': f'Endereço {endereco} não foi encontrado', 'status_code': 404}
    
    # Adiciona uma flag ao validador
    if acao == 'add':
        # Incrementa a flag do validador limitando ao máximo de 3
        validador.flag = min(validador.flag + 1, 3)
        
        # Verifica se o validador deve ser expulso por excesso de flags
        if validador.flag > 2:
            expulsar_validador_(endereco)
            return {'mensagem': f'Validador de endereço {endereco} foi expulso por excesso de flags', 'status_code': 200}
    
    # Remove uma flag do validador
    elif acao == 'remover':
        # Decrementa a flag do validador limitando ao mínimo de 0
        validador.flag = max(validador.flag - 1, 0)
    
    else:
        # Retorna uma mensagem de erro se a ação for inválida
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
    # Verifica se o stake é suficiente
    if stake < 50.0:
        return {'mensagem': 'O saldo mínimo de 50 NoNameCoins é necessário para registrar um validador', 'status_code': 400}
    
    # Verifica se o validador já existe
    validador_existente = Validador.query.filter_by(endereco=endereco).first()
    
    # Verifica se o seletor existe
    seletor = db.session.get(Seletor, seletor_id)
    if not seletor:
        return {'mensagem': 'Seletor não encontrado', 'status_code': 404}

    # Gera a chave do seletor
    chave_seletor = gerar_chave(seletor_id, endereco)
    logger.debug(f"Chave de validação gerada: {chave_seletor} para seletor_id: {seletor_id} e validador_endereco: {endereco}")

    # Caso o validador já exista
    if validador_existente:
        if validador_existente.status == 'expulso':
            # Se o validador foi expulso mais de duas vezes ele é removido permanentemente
            if validador_existente.retorno_contagem >= 2:
                remover_validador_(validador_existente.endereco)
                return {'mensagem': f'Validador de endereço {endereco} não pode retornar mais vezes e será deletado da rede', 'status_code': 400}
            # Caso ainda consiga retornar a rede, verifica se tem o dobro do stake minimo
            if stake < 2 * 50.0:
                return {'mensagem': f'Validador de endereço {endereco} precisa travar pelo menos o dobro do saldo mínimo', 'status_code': 400}
            # Atualiza os dados do validador para reativá-lo
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

    # Cria um novo validador se ele não existir
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

def editar_validador_(validador_id, novo_stake):
    # Encontra o validador pelo ID
    validador = db.session.get(Validador, validador_id)
    if not validador:
        return {'mensagem': f'Validador com ID {validador_id} não encontrado', 'status_code': 404}

    # Atualiza os campos do validador
    validador.stake = novo_stake

    # Persiste as mudanças no banco de dados
    db.session.commit()

    return {'mensagem': f'Validador com ID {validador_id} foi atualizado', 'status_code': 200}

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
    
def registrar_seletor_(endereco, saldo):
    # Registra um novo seletor
    seletor_existente = Seletor.query.filter_by(endereco=endereco).first()
    if seletor_existente:
        return {'mensagem': f'Seletor de endereço {endereco} já existe', 'status_code': 400}

    novo_seletor = Seletor(endereco=endereco, saldo=saldo)
    db.session.add(novo_seletor)
    db.session.commit()

    return {'mensagem': f'Seletor de endereço {endereco} foi registrado', 'status_code': 200}

def editar_seletor_(seletor_id, novo_endereco, novo_saldo):
        # Busca o seletor existente pelo ID
        seletor = db.session.get(Seletor, seletor_id)
        if not seletor:
            return {'mensagem': 'Seletor não encontrado', 'status_code': 404}

        # Verifica se o novo endereço já está em uso por outro seletor
        if novo_endereco != seletor.endereco:
            seletor_existente = Seletor.query.filter_by(endereco=novo_endereco).first()
            if seletor_existente:
                return {'mensagem': f'Endereço {novo_endereco} já está em uso por outro seletor', 'status_code': 400}

        # Atualiza os campos do seletor
        seletor.endereco = novo_endereco
        seletor.saldo = novo_saldo

        # Persiste as mudanças no banco de dados
        db.session.commit()

        return {'mensagem': f'Seletor {seletor_id} atualizado com sucesso', 'status_code': 200}

def remover_seletor_(endereco):
    # Remove um seletor do banco de dados
    seletor = Seletor.query.filter_by(endereco=endereco).first()
    if seletor:
        db.session.delete(seletor)
        db.session.commit()
        return {"mensagem": f"Seletor de endereço {endereco} foi removido do banco de dados", "status_code": 200}
    else:
        return {"mensagem": "Seletor não encontrado", "status_code": 404}

def distribuir_taxas(transacao, seletor, validadores, validadores_maliciosos):
    # Filtra validadores para remover os maliciosos
    validadores_honestos = [validador for validador in validadores if validador not in validadores_maliciosos]

    if not validadores_honestos:
        return {'mensagem': 'Sem validadores honestos disponíveis', 'status_code': 503}

    # Calcula as taxas
    quantia_transacionada = transacao.quantia
    taxa_seletor = quantia_transacionada * 0.015  # 1,5% da quantia transacionada
    taxa_validadores = quantia_transacionada * 0.01  # 1% da quantia transacionada
    taxa_travada = quantia_transacionada * 0.005  # 0,5% da quantia transacionada

    # Distribui a taxa de 1% entre os validadores honestos
    taxa_por_validador = taxa_validadores / len(validadores_honestos)
    for validador in validadores_honestos:
        validador.stake += taxa_por_validador

    # Adiciona a taxa travada de 0,5% a cada validador individualmente
    for validador in validadores_honestos:
        validador.stake += taxa_travada

    # Adiciona a taxa ao saldo do seletor
    seletor.saldo += taxa_seletor

    db.session.commit()

    return {'mensagem': 'Taxas distribuídas', 'status_code': 200}