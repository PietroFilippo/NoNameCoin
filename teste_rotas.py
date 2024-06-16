import unittest
import logging
from datetime import datetime
from flask import current_app
from app import criar_app, db
from app.models import Usuario, Validador, Seletor, Transacao
from app.validador import generate_unique_key, selecionar_validadores, gerenciar_consenso

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
            seletor1 = Seletor(endereco='seletor1')
            db.session.add(seletor1)
            db.session.commit()
            
            validador1 = Validador(endereco='validador1', stake=200.0, key='key1', chave_seletor='1-validador1', seletor_id=seletor1.id)
            validador2 = Validador(endereco='validador2', stake=350.0, key='key2', chave_seletor='1-validador2', seletor_id=seletor1.id)
            validador4 = Validador(endereco='validador4', stake=250.0, key='key4', chave_seletor='1-validador4', seletor_id=seletor1.id)
            validador5 = Validador(endereco='validador5', stake=300.0, key='key5', chave_seletor='1-validador5', seletor_id=seletor1.id)
            validador6 = Validador(endereco='validador6', stake=250.0, key='key6', chave_seletor='1-validador6', seletor_id=seletor1.id)
            validador7 = Validador(endereco='validador7', stake=250.0, key='key7', chave_seletor='1-validador7', seletor_id=seletor1.id, status='on_hold')
            validador8 = Validador(endereco='validador8', stake=150.0, key='key8', chave_seletor='1-validador8', seletor_id=seletor1.id, status='expulso')
            validador9 = Validador(endereco='validador9', stake=100.0, key='key9', chave_seletor='1-validador9', seletor_id=seletor1.id)
            db.session.add_all([usuario1, usuario2, validador1, validador2, validador4, validador5, validador6, validador7, validador8, validador9])
            db.session.commit()

    def test_transacao_bem_sucedida(self):
        with self.app.app_context():
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados
    
            # Gerar chaves de validação para todos os validadores selecionados
            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            chaves_validacao = [generate_unique_key(seletor_id, v.endereco) for v in validadores_selecionados]
    
            transacao_dados = {
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 100.0,
                'keys_validacao': chaves_validacao[0]  # Usar a chave esperada pelo primeiro validador
            }
    
            resposta = self.client.post('/trans', json=transacao_dados)
            print(resposta.json)  # Adicionado para inspecionar a resposta
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('mensagem', resposta.json[0])  # Verifica se 'mensagem' está presente
            self.assertIn('Transação feita com sucesso', resposta.json[0]['mensagem'])
    
    def test_multiplas_transacoes(self):
        with self.app.app_context():
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados

            # Gerar chaves de validação para todos os validadores selecionados
            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            chaves_validacao_1 = [generate_unique_key(seletor_id, v.endereco) for v in validadores_selecionados]
            chaves_validacao_2 = [generate_unique_key(seletor_id, v.endereco) for v in validadores_selecionados]

            transacoes_dados = [
                {
                    'id_remetente': 1,
                    'id_receptor': 2,
                    'quantia': 50.0,
                    'keys_validacao': chaves_validacao_1[0]  # Usar a chave esperada pelo primeiro validador
                },
                {
                    'id_remetente': 2,
                    'id_receptor': 1,
                    'quantia': 30.0,
                    'keys_validacao': chaves_validacao_2[0]  # Usar a chave esperada pelo primeiro validador
                }
            ]

            resposta = self.client.post('/trans', json=transacoes_dados)
            print(resposta.json)  # Adicionado para inspecionar a resposta
            self.assertEqual(resposta.status_code, 200)
            for resultado in resposta.json:
                self.assertIn('mensagem', resultado) 
                self.assertIn('Transação feita com sucesso', resultado['mensagem'])

    def test_chave_invalida(self):
        with self.app.app_context():
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados

            transacao_dados = {
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 10.0,
                'keys_validacao': 'chave_invalida'
            }

            resposta = self.client.post('/trans', json=transacao_dados)
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('Chave de validação inválida', resposta.json[0]['mensagem'])

    def test_saldo_insuficiente(self):
        with self.app.app_context():
            validadores_selecionados = selecionar_validadores()
            current_app.config['validadores_selecionados'] = validadores_selecionados

            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            chave_validacao = generate_unique_key(seletor_id, validadores_selecionados[0].endereco)

            transacao_dados = {
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 1000.0,
                'keys_validacao': chave_validacao  # Usar a chave esperada pelo primeiro validador
            }

            resposta = self.client.post('/trans', json=transacao_dados)
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
            'seletor_id': 1
        }
        resposta = self.client.post('/validador/registrar', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi registrado', resposta.json['mensagem'])

    def teste_reativar_validador(self):
        dados = {
            'endereco': 'validador8',
            'stake': 150.0,
            'key': 'key8',
            'seletor_id': 1
        }
        resposta = self.client.post('/validador/registrar', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi reativado', resposta.json['mensagem'])

    def teste_expulsar_validador(self):
        dados = {'endereco': 'validador9'}
        resposta = self.client.post('/validador/expulsar', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi expulso', resposta.json['mensagem'])

    def teste_listar_validadores(self):
        resposta = self.client.get('/validador/listar')
        print(resposta.json) 
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue('validadores' in resposta.json)
        print("\nLista de Validadores:")
        for validador in resposta.json['validadores']:
            print(f"Endereço: {validador['endereco']}, Stake: {validador['stake']}, Key: {validador['key']}")

    def teste_flag_validador(self):
        dados = {'endereco': 'validador1', 'acao': 'add'}
        resposta = self.client.post('/validador/flag', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Flag do validador de endereço {dados["endereco"]} foi atualizado', resposta.json['mensagem'])

if __name__ == '__main__':
    unittest.main()