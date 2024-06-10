import unittest
import requests
from app import criar_app
from app.models import db, Usuario, Validador
from app.validador import gerar_chave_validacao, selecionar_validadores, gerenciar_consenso
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BASE_URL = 'http://127.0.0.1:5000'

import unittest
from datetime import datetime
from flask import current_app, jsonify
from app import criar_app, db
from app.models import Usuario, Validador, Transacao
from app.validador import gerar_chave_validacao, selecionar_validadores, gerenciar_consenso

class TesteRotas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = criar_app('app.config.TestesConfig')
        cls.app.testing = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
            usuario1 = Usuario(nome='usuario1', saldo=600.0)
            usuario2 = Usuario(nome='usuario2', saldo=200.0)
            validador1 = Validador(endereco='validador1', stake=200.0, key='key1')
            validador2 = Validador(endereco='validador2', stake=250.0, key='key2')
            validador4 = Validador(endereco='validador4', stake=250.0, key='key4')
            validador5 = Validador(endereco='validador5', stake=250.0, key='key5')
            validador6 = Validador(endereco='validador6', stake=250.0, key='key6')
            db.session.add_all([usuario1, usuario2, validador1, validador2, validador4, validador5, validador6])
            db.session.commit()
            
    def teste_transacao_bem_sucedida(self):
        with self.app.app_context():
            # Suponha que você tenha validadores selecionados que aceitam essa transação
            validadores_selecionados = selecionar_validadores()

            # Gere a chave de validação com base nos validadores selecionados
            chave_validacao = gerar_chave_validacao(validadores_selecionados, id_transacao=3)

            # Armazene os validadores selecionados no contexto do aplicativo Flask
            current_app.config['validadores_selecionados'] = validadores_selecionados

            # Configure os dados da transação com a chave de validação correta
            transacao_dados = {
                'id': 3,
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 100.0,
                'key_validacao': chave_validacao
            }

            # Envie a transação para o servidor
            resposta = self.client.post('/trans', json=transacao_dados)

            # Verifique se a resposta indica que a transação foi bem-sucedida
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('Transação feita com sucesso', resposta.json['mensagem'])

            # Verifique se o saldo do remetente foi deduzido corretamente
            remetente = Usuario.query.get(transacao_dados['id_remetente'])
            self.assertEqual(remetente.saldo, 500.0)

            # Verifique se o saldo do receptor foi aumentado corretamente
            receptor = Usuario.query.get(transacao_dados['id_receptor'])
            self.assertEqual(receptor.saldo, 300.0)
            
    def teste_transacao_insuficiente(self):
        with self.app.app_context():
            # Suponha que você tenha validadores selecionados que rejeitam essa transação
            validadores_selecionados = selecionar_validadores()

            # Armazene os validadores selecionados no contexto do aplicativo Flask
            current_app.config['validadores_selecionados'] = validadores_selecionados

            # Configure os dados da transação
            transacao_dados = {
                'id': 2,
                'id_remetente': 2,
                'id_receptor': 1,
                'quantia': 300.0,
            }

            # Envie a transação para o servidor
            resposta = self.client.post('/trans', json=transacao_dados)

            # Verifique se a resposta indica que a transação foi mal sucedida
            self.assertEqual(resposta.status_code, 400)
            self.assertIn('Saldo insuficiente', resposta.json['mensagem'])

    def teste_transacao_chave_invalida(self):
        with self.app.app_context():
            # Suponha que você tenha validadores selecionados que rejeitam essa transação
            validadores_selecionados = selecionar_validadores()
    
            # Armazene os validadores selecionados no contexto do aplicativo Flask
            current_app.config['validadores_selecionados'] = validadores_selecionados
    
            # Configure os dados da transação
            transacao_dados = {
                'id': 1,
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 400.0,
                'key_validacao': 'chave_invalida'
            }
    
            # Envie a transação para o servidor
            resposta = self.client.post('/trans', json=transacao_dados)
    
            # Verifique se a resposta indica que a transação foi mal sucedida
            self.assertEqual(resposta.status_code, 500)
            self.assertIn('Chave de validação inválida', resposta.json['mensagem'])
    
    def teste_get_hora(self):
        resposta = self.client.get('/hora')
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('tempo_atual', resposta.json)       

    def teste_registrar_validador(self):
        dados = {
            'endereco': 'validador3',
            'stake': 150.0,
            'key': 'key3',
        }
        resposta = self.client.post('/seletor/registrar', json=dados)
        print(f"Resposta do servidor para teste_registrar_validador: {resposta.json}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi registrado', resposta.json['mensagem'])

    def teste_remover_validador(self):
        dados = {'endereco': 'validador3'}
        resposta = self.client.post('/seletor/remover', json=dados)
        print(f"Resposta do servidor para teste_remover_validador: {resposta.json}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi removido', resposta.json['mensagem'])
    
    def teste_listar_validadores(self):
        resposta = self.client.get('/seletor/listar')
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue('validadores' in resposta.json)
        print("\nLista de Validadores:")
        for validador in resposta.json['validadores']:
            print(f"Endereço: {validador['endereco']}, Stake: {validador['stake']}, Key: {validador['key']}")
    
    def teste_flag_validador(self):
        dados = {'endereco': 'validador1', 'acao': 'add'}
        resposta = self.client.post('/seletor/flag', json=dados)
        print(f"Resposta do servidor para teste_flag_validador: {resposta.json}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Flag de validador atualizado', resposta.json['mensagem'])
    
    def teste_hold_validador(self):
        dados = {'endereco': 'validador1'}
        resposta = self.client.post('/seletor/hold', json=dados)
        print(f"Resposta do servidor para teste_hold_validador: {resposta.json}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} está on hold', resposta.json['mensagem'])
    
if __name__ == '__main__':
    unittest.main()