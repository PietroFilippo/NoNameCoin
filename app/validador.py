from .models import db, Usuario, Transacao, Validador
import random
from datetime import datetime, timedelta

def selecionar_validadores():
    validadores = Validador.query.filter_by(status='ativo').all()
    stake_total = sum(validador.stake for validador in validadores)
    validadores_selecionados = []

    print(f"Validadores selecionados de {len(validadores)} disponiveis com stake total de {stake_total}")

    if stake_total == 0:
        return validadores_selecionados
    
    for validador in validadores:
        probabilidade = validador.stake / stake_total
        if validador.flag == 1:
            probabilidade *= 0.5
        elif validador.flag == 2:
            probabilidade *= 0.25

        if validador.selecoes_consecutivas >= 5:
            probabilidade = 0

        if random.random() < probabilidade:
            validadores_selecionados.append(validador)
            validador.selecoes_consecutivas += 1
            if len(validadores_selecionados) ==3:
                break
    
    for validador in validadores:
        if validador not in validadores_selecionados:
            validador.selecoes_consecutivas = 0

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
    ultima_transacao = Transacao.query.filter_by(sender_id = transacao.id_remetente).order_by(Transacao.horario.desc()).first()
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
    
def gerenciar_consenso(transacao):
    validadores = selecionar_validadores()
    if not validadores:
        print("Sem validadores disponiveis")
        return {'mensagem': 'Sem validadores disponiveis', 'status_code': 503}
    
    aprovacoes = 0
    rejeicoes = 0
    for validador in validadores:
        if logica_validacao(validador, transacao):
            aprovacoes += 1
        else:
            rejeicoes += 1

    consenso = 1 if aprovacoes > len(validadores) // 2 else 2
    transacao.status = consenso
    db.session.commit()

    print(f"Transação {transacao.id}: aprovações = {aprovacoes}, rejeições = {rejeicoes}, consenso = {consenso}")

    return {'consenso': consenso, 'status_code': 200}

def lista_validadores():
    validadores = Validador.query.all()
    dados_validadores = [{'endereco': validador.endereco, 'stake': validador.stake} for validador in validadores]
    return {'validadores': dados_validadores}, 200