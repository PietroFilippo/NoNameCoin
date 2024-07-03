import unittest
import logging
from flask import current_app
from app import criar_app, db
from app.models import Usuario, Validador, Seletor, Transacao
from app.validacao import gerar_chave

# Configuração do logger para depuração
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class TesteRotas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configura o app para testes
        cls.app = criar_app('app.config.TestesConfig')
        cls.app.testing = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            # Limpa e cria o banco de dados
            db.drop_all()
            db.create_all()
            # Criação de 2 usuários e do seletor
            usuario1 = Usuario(nome='usuario1', saldo=600.0)
            usuario2 = Usuario(nome='usuario2', saldo=200.0)
            usuario3 = Usuario(nome='usuario3', saldo=100.0)
            seletor1 = Seletor(endereco='seletor1', saldo=100.0)
            db.session.add(seletor1)
            db.session.commit()
            
            # Criação de alguns validadores
            validador1 = Validador(endereco='validador1', stake=200.0, key='key1', chave_seletor='1-validador1', seletor_id=seletor1.id)
            validador2 = Validador(endereco='validador2', stake=350.0, key='key2', chave_seletor='1-validador2', seletor_id=seletor1.id, flag=1, transacoes_coerentes=9999)
            validador4 = Validador(endereco='validador4', stake=250.0, key='key4', chave_seletor='1-validador4', seletor_id=seletor1.id)
            validador5 = Validador(endereco='validador5', stake=300.0, key='key5', chave_seletor='1-validador5', seletor_id=seletor1.id)
            validador6 = Validador(endereco='validador6', stake=250.0, key='key6', chave_seletor='malicioso', seletor_id=seletor1.id)
            validador7 = Validador(endereco='validador7', stake=250.0, key='key7', chave_seletor='1-validador7', seletor_id=seletor1.id, status='on_hold')
            validador8 = Validador(endereco='validador8', stake=150.0, key='key8', chave_seletor='1-validador8', seletor_id=seletor1.id, status='expulso')
            validador9 = Validador(endereco='validador9', stake=100.0, key='key9', chave_seletor='1-validador9', seletor_id=seletor1.id)
            validador10 = Validador(endereco='validador10', stake=100.0, key='key10', chave_seletor='1-validador10', seletor_id=seletor1.id)
            validador11 = Validador(endereco='validador11', stake=10.0, key='key11', chave_seletor='1-validador11', seletor_id=seletor1.id)
            db.session.add_all([usuario1, usuario2, usuario3, validador1, validador2, validador4, validador5, validador6, validador7, validador8, validador9, validador10, validador11])
            db.session.commit()

    def obter_seletor(self):
        with self.app.app_context():
            # Obtém o seletor do banco de dados
            seletor = Seletor.query.first()
            return seletor.id if seletor else None

    def selecionar_validadores(self):
        seletor_id = self.obter_seletor()
        if not seletor_id:
            self.fail("Seletor não encontrado.")
        
        resposta_selecao = self.client.post(f'/seletor/{seletor_id}/selecionar_validadores')
        self.assertEqual(resposta_selecao.status_code, 200, "Erro ao selecionar validadores")
        
        validadores_ids = resposta_selecao.json['validadores']
        validadores = Validador.query.filter(Validador.id.in_(validadores_ids)).all()
        current_app.config['validadores_selecionados'] = validadores
        return validadores

    def teste_transacao_bem_sucedida(self):
        with self.app.app_context():
            validadores_selecionados = self.selecionar_validadores()
            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            chaves_validacao = [gerar_chave(seletor_id, v.endereco) for v in validadores_selecionados]

            transacao_dados = {
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 100.0,
                'keys_validacao': chaves_validacao
            }

            resposta = self.client.post('/trans', json=transacao_dados)
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('mensagem', resposta.json[0])
            self.assertIn('Transação feita com sucesso', resposta.json[0]['mensagem'])
    
    def teste_multiplas_transacoes(self):
        with self.app.app_context():
            validadores_selecionados = self.selecionar_validadores()
            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            chaves_validacao_1 = [gerar_chave(seletor_id, v.endereco) for v in validadores_selecionados]
            chaves_validacao_2 = [gerar_chave(seletor_id, v.endereco) for v in validadores_selecionados]

            transacoes_dados = [
                {
                    'id_remetente': 1,
                    'id_receptor': 2,
                    'quantia': 50.0,
                    'keys_validacao': chaves_validacao_1
                },
                {
                    'id_remetente': 2,
                    'id_receptor': 1,
                    'quantia': 30.0,
                    'keys_validacao': chaves_validacao_2
                }
            ]

            resposta = self.client.post('/trans', json=transacoes_dados)
            self.assertEqual(resposta.status_code, 200)
            for resultado in resposta.json:
                self.assertIn('mensagem', resultado)
                self.assertIn('Transação feita com sucesso', resultado['mensagem'])


    def teste_saldo_insuficiente(self):
        with self.app.app_context():
            validadores_selecionados = self.selecionar_validadores()
            seletor_id = validadores_selecionados[0].seletor_id if validadores_selecionados else None
            chaves_validacao = [gerar_chave(seletor_id, v.endereco) for v in validadores_selecionados]

            transacao_dados = {
                'id_remetente': 1,
                'id_receptor': 2,
                'quantia': 1000.0,
                'keys_validacao': chaves_validacao
            }

            resposta = self.client.post('/trans', json=transacao_dados)
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('Transação rejeitada', resposta.json[0]['mensagem'])

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

    def teste_editar_validador(self):
        dados = {
            'stake': 500.0
        }
        resposta = self.client.post('/validador/editar/10', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador com ID 10 foi atualizado', resposta.json['mensagem'])

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

    def teste_remover_validador(self):
        dados = {'endereco': 'validador10'}
        resposta = self.client.post('/validador/remover', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Validador de endereço {dados["endereco"]} foi removido', resposta.json['mensagem'])
        
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

    def teste_registrar_usuario(self):
        dados = {
            'nome': 'usuario4',
            'saldo': 300.0
        }
        resposta = self.client.post('/usuario/registrar', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Usuário {dados["nome"]} foi registrado', resposta.json['mensagem'])

    def teste_editar_usuario(self):
        dados = {
            'id': 1,
            'nome': 'ABC',
        }
        resposta = self.client.post('/usuario/editar/1', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Usuário {dados["nome"]} foi atualizado', resposta.json['mensagem'])

    def teste_remover_usuario(self):
        dados = {
            'nome': 'usuario3'
        }
        resposta = self.client.post('/usuario/remover', json=dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(f'Usuário {dados["nome"]} foi removido', resposta.json['mensagem'])

if __name__ == '__main__':
    unittest.main()