from app import criar_app
from app.models import db, Usuario, Transacao, Validador
import unittest

class teste_rotas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = criar_app('app.config.TestesConfig')
        cls.app.testing = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
            usuario1 = Usuario(nome = 'usuario1', saldo = 500.0)
            usuario2 = Usuario(nome = 'usuario2', saldo = 200.0)
            validador1 = Validador(endereco = 'validador1', stake = 200.0, key = 'key1')
            validador2 = Validador(endereco = 'validador2', stake = 100.0, key = 'key2')
            db.session.add_all([usuario1, usuario2, validador1, validador2])
            db.session.commit()
    
    def teste_transacao(self):
        transacao_dados = {
            'id_remetente': 1,
            'id_receptor': 2,
            'quantia': 20.0,
            'key': 'key2'
        }
        resposta = self.client.post('/trans', json=transacao_dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Transação feita com sucesso', resposta.json['mensagem'])

        # Verifica se os dados dos usuarios foram atualizados corretamente
        with self.app.app_context():
            remetente = db.session.get(Usuario, 1)
            receptor = db.session.get(Usuario, 2)
            self.assertEqual(remetente.saldo, 480.0)
            self.assertEqual(receptor.saldo, 220.0)

    def teste_transacao_insuficiente(self):
        transacao_dados = {
            'id_remetente': 2,
            'id_receptor': 1,
            'quantia': 300.0,
            'key': 'key2'
        }
        resposta = self.client.post('/trans', json = transacao_dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('Saldo insuficiente', resposta.json['mensagem'])

    def teste_transacao_chave_invalida(self):
        transacao_dados = {
            'id_remetente': 1,
            'id_receptor': 2,
            'quantia': 300.0,
            'key': 'chave_invalida'
        }
        resposta = self.client.post('/trans', json = transacao_dados)
        self.assertEqual(resposta.status_code, 500)
        self.assertIn('Erro na verificação da chave', resposta.json['mensagem'])

    def teste_get_hora(self):
        resposta = self.client.get('/hora')
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('tempo_atual', resposta.json)       

    def teste_registrar_validador(self):
        dados = {
            'endereco': 'validador3',
            'stake': 150.0,
            'key': 'key3'
        }
        resposta = self.client.post('/seletor/registrar', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi registrado', resposta.json['mensagem'])

    def teste_remover_validador(self):
        dados = {'endereco': 'validador3'}
        resposta = self.client.post('/seletor/remover', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi removido', resposta.json['mensagem'])

    def teste_listar_validadores(self):
        resposta = self.client.get('/seletor/listar')
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue('validadores' in resposta.json)

    def teste_flag_validador(self):
        dados = {'endereco': 'validador1', 'acao': 'add'}
        resposta = self.client.post('/seletor/flag', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Flag de validador atualizado', resposta.json['mensagem'])

    def teste_hold_validador(self):
        dados = {'endereco': 'validador1'}
        resposta = self.client.post('/seletor/hold', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} está on hold', resposta.json['mensagem'])

if __name__ == '__main__':
    unittest.main()

