import unittest
import logging
from datetime import datetime
from flask import current_app
from app import criar_app, db
from app.models import Usuario, Validador, Transacao
from app.validador import gerar_chave_validacao, selecionar_validadores, gerenciar_consenso

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BASE_URL = 'http://127.0.0.1:5000'

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
            validador2 = Validador(endereco='validador2', stake=350.0, key='key2')
            validador4 = Validador(endereco='validador4', stake=250.0, key='key4')
            validador5 = Validador(endereco='validador5', stake=300.0, key='key5')
            validador6 = Validador(endereco='validador6', stake=250.0, key='key6')
            validador7 = Validador(endereco='validador7', stake=250.0, key='key7', status='on_hold')
            validador8 = Validador(endereco='validador8', stake=150.0, key='key8', status='expulso')
            db.session.add_all([usuario1, usuario2, validador1, validador2, validador4, validador5, validador6, validador7, validador8])
            db.session.commit()

    def test_transacao_bem_sucedida(self):
        with self.app.app_context():
            # Suponha que você tenha validadores selecionados que aceitam essa transação
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados

            # Dados da transação
            transacao_dados = {
                'id': 1,
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 100.0,
                'key_validacao': gerar_chave_validacao(validadores_selecionados, id_transacao=1)
            }

            # Envie a transação para o servidor
            resposta = self.client.post('/trans', json=transacao_dados)

            # Verifique se a resposta indica que a transação foi bem-sucedida
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('Transação feita com sucesso', resposta.json[0]['mensagem'])

    def test_multiplas_transacoes(self):
        with self.app.app_context():
            # Suponha que você tenha validadores selecionados que aceitam essas transações
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados
            
            # Dados das transações
            transacoes_dados = [
                {
                    'id': 4,
                    'id_remetente': 1,
                    'id_receptor': 2,
                    'quantia': 50.0,
                    'key_validacao': gerar_chave_validacao(validadores_selecionados, id_transacao=4)
                },
                {
                    'id': 5,
                    'id_remetente': 2,
                    'id_receptor': 1,
                    'quantia': 30.0,
                    'key_validacao': gerar_chave_validacao(validadores_selecionados, id_transacao=5)
                }
            ]
    
            # Envie as transações para o servidor
            resposta = self.client.post('/trans', json=transacoes_dados)
            
            # Verifique se a resposta indica que as transações foram bem-sucedidas
            self.assertEqual(resposta.status_code, 200)
            for resultado in resposta.json:
                self.assertIn('Transação feita com sucesso', resultado['mensagem'])

    def test_chave_invalida(self):
        with self.app.app_context():
            # Suponha que você tenha validadores selecionados
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados

            # Dados da transação com chave inválida
            transacao_dados = {
                'id': 6,
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 100.0,
                'key_validacao': 'chave_invalida'
            }

            # Envie a transação para o servidor
            resposta = self.client.post('/trans', json=transacao_dados)

            # Verifique se a resposta indica que a chave de validação é inválida
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('Chave de validação inválida', resposta.json[0]['mensagem'])

    def test_saldo_insuficiente(self):
        with self.app.app_context():
           # Suponha que você tenha validadores selecionados
           validadores_selecionados = selecionar_validadores()
           current_app.config['validadores_selecionados'] = validadores_selecionados
           
           # Dados da transação com saldo insuficiente
           transacao_dados = {
               'id': 9,
               'id_remetente': 1,
               'id_receptor': 2,
               'quantia': 1000.0,  # Assumindo que o remetente não tem saldo suficiente
               'key_validacao': gerar_chave_validacao(validadores_selecionados, id_transacao=9)
           }

           # Envie a transação para o servidor
           resposta = self.client.post('/trans', json=transacao_dados)
           
           # Verifique se a resposta indica saldo insuficiente
           self.assertEqual(resposta.status_code, 200)
           self.assertIn('Saldo insuficiente', resposta.json[0]['mensagem'])

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

    def teste_reativar_validador(self):
        dados = {
            'endereco': 'validador8',
            'stake': 150.0,
            'key': 'key8',
        }
        resposta = self.client.post('/seletor/registrar', json=dados)
        print(f"Resposta do servidor para teste_reativar_validador: {resposta.json}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi reativado', resposta.json['mensagem'])

    def teste_remover_validador(self):
        dados = {'endereco': 'validador3'}
        resposta = self.client.post('/seletor/remover', json=dados)
        print(f"Resposta do servidor para teste_remover_validador: {resposta.json}")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi expulso', resposta.json['mensagem'])

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