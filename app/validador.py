from .models import db, Usuario, Transacao, Validador
import random
from datetime import datetime, timedelta

def selecionar_validadores():
    validadores = Validador.query.filter_by(status='ativo').all()  # Seleciona todos os validadores ativos
    stake_total = sum(validador.stake for validador in validadores)  # Calcula o total de stake
    validadores_selecionados = []

    print(f"Validadores selecionados de {len(validadores)} disponiveis com stake total de {stake_total}")

    if stake_total == 0:
        return validadores_selecionados
    
    for validador in validadores:
        probabilidade = validador.stake / stake_total  # Calcula a probabilidade de seleção com base no stake
        if validador.flag == 1:
            probabilidade *= 0.5  # Reduz a probabilidade se o validador tiver flag 1
        elif validador.flag == 2:
            probabilidade *= 0.25  # Reduz mais ainda se tiver flag 2

        if validador.selecoes_consecutivas >= 5:
            probabilidade = 0  # Impede seleções consecutivas excessivas

        if random.random() < probabilidade:
            validadores_selecionados.append(validador)
            validador.selecoes_consecutivas += 1  # Incrementa o contador de seleções consecutivas
            if len(validadores_selecionados) == 3:
                break  # Seleciona até 3 validadores
    
    for validador in validadores:
        if validador not in validadores_selecionados:
            validador.selecoes_consecutivas = 0  # Reseta o contador para validadores não selecionados

    db.session.commit()

    print(f"Validadores selecionados: {[v.endereco for v in validadores_selecionados]}")
    return validadores_selecionados

def logica_validacao(validador, transacao):
    remetente = db.session.get(Usuario, transacao.id_remetente)
    tempo_atual = datetime.utcnow()

    print(f"Validando transação {transacao.id} com validador {validador.endereco}")
    
    # Regra 1 - verifica se o remetente tem saldo suficiente para a transação
    if remetente.saldo < transacao.quantia:
        print(f"Validação falhou: remetente {remetente.id} não tem saldo suficiente")
        return False
    
    # Regra 2 - verifica o horário da transação
    if transacao.horario > tempo_atual:
        print(f"Validação falhou: horário da transação está incorreto {transacao.horario}")
        return False
    
    # Verifica se a transação é posterior a última transação
    ultima_transacao = Transacao.query.filter_by(id_remetente = transacao.id_remetente).order_by(Transacao.horario.desc()).first()
    if ultima_transacao and transacao.horario < ultima_transacao.horario:
        print(f"Validação falhou: horário da transação {transacao.horario} foi feita antes da última transação {ultima_transacao.horario}")
        return False
    
    # Regra 3 - verifica o número de transações feitas em 1 minuto
    um_minuto = datetime.utcnow() - timedelta(minutes=1)
    num_transacoes = Transacao.query.filter(Transacao.id_remetente == transacao.id_remetente, Transacao.horario > um_minuto).count()
    if num_transacoes >= 100:
        print(f"Validação falhou: mais de 100 transações foram feitas no último minuto")
        return False
    
    # Regra 4 - verifica a chave do validador 
    if transacao.key != validador.key:
        print(f"Validação falhou: erro na validação na chave {validador.endereco}")
        return False
    
    return True
    
def gerenciar_consenso(transacoes):
    validadores = selecionar_validadores()  # Seleciona os validadores
    if not validadores:
        return {'mensagem': 'Sem validadores disponíveis', 'status_code': 503}
    
    resultados = []
    for transacao in transacoes:
        if not isinstance(transacao, Transacao):
            print(f"Objeto inválido encontrado na lista de transações: {transacao}")
            continue
    for transacao in transacoes:
        aprovacoes = 0
        rejeicoes = 0
        for validador in validadores:
            if logica_validacao(validador, transacao):  # Verifica se a transação é válida
                aprovacoes += 1
            else:
                rejeicoes += 1

        consenso = 1 if aprovacoes > len(validadores) // 2 else 2  # Determina o consenso
        transacao.status = consenso  # Atualiza o status da transação
        db.session.commit()
        #resultados.append({'id_transacao': transacao.id, 'consenso': consenso})

    return {'resultados': resultados, 'status_code': 200}

def lista_validadores():
    validadores = Validador.query.all()
    dados_validadores = [{'endereco': validador.endereco, 'stake': validador.stake} for validador in validadores]
    return {'validadores': dados_validadores}, 200

def update_flags_validador(endereco, acao):
    validador = Validador.query.filter_by(endereco=endereco).first()
    if not validador:
        return {'mensagem': f'Endereço {endereco} não foi encontrado', 'status_code': 404}
    if acao == 'add':
        validador.flag = min(validador.flag + 1, 2)
    elif acao == 'remover':
        validador.flag = max(validador.flag - 1, 0)
    else:
        return {'mensagem': f'Endereço {endereco} não foi encontrado', 'status_code': 404}

    db.session.commit()
    return {'mensagem': 'Flag de validador atualizado', 'status_code': 200}

def hold_validador_(endereco):
    validador = Validador.query.filter_by(endereco=endereco).first()
    if not validador:
        return {'mensagem': f'Endereço {endereco} não foi encontrado', 'status_code': 404}

    validador.status = 'on_hold'
    db.session.commit()
    return {'mensagem': f'Validador de endereço {endereco} está on hold', 'status_code': 200}

def registrar_validador_(endereco, stake, key):
    # Verifica se já está cadastrado
    validador_existente = Validador.query.filter_by(endereco=endereco).first()
    if validador_existente:
        return {'mensagem': f'Validador de endereço {endereco} já existe', 'status_code': 400}
    
    # Registra novo validador
    novo_validador = Validador(endereco=endereco, stake=stake, key=key)
    db.session.add(novo_validador)
    db.session.commit()

    return {'mensagem': f'Validador de endereço {endereco} foi registrado', 'status_code': 200}

def remover_validador_(endereco):
    # Verifica se já está cadastrado
    validador_existente = Validador.query.filter_by(endereco=endereco).first()
    if not validador_existente:
        return {'mensagem': f'Validador de endereço {endereco} já existe', 'status_code': 404}

    # Remove validador
    db.session.delete(validador_existente)
    db.session.commit()

    return {'mensagem': f'Validador de endereço {endereco} foi removido', 'status_code': 200}

def validar_transacao(id_transacao):
    transacao = db.session.get(Transacao, id_transacao)
    validadores_selecionados = selecionar_validadores()
    if not validadores_selecionados:
        return {'mensagem': 'Sem validadores disponiveis' , 'status_code': 503}
    
    # Simula validação para os validadores
    aprovacoes = 0
    rejeicoes = 0
    for validador in validadores_selecionados:
        if transacao.key != validador.key: # Adiciona verificação da chave
            rejeicoes += 1
        elif logica_validacao(validador, transacao):
            aprovacoes += 1
        else:
            rejeicoes += 1

    if aprovacoes > len(validadores_selecionados) // 2:
        transacao.status = 1 # Concluida
    else:
        transacao.status = 2 # Não aprovada
    db.session.commit()

    if rejeicoes > 0:
        return {'mensagem': 'Erro na validação', 'status_code': 500}
    
    return {'mensagem': 'Transação validada', 'status_code': 200}