import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.rate_limiter import limpar_janela, permitir_requisicao


class TestLimparJanela(unittest.TestCase):
    def test_remove_timestamps_antigos(self):
        resultado = limpar_janela([0.0, 5.0, 59.0], agora=61.0, janela_segundos=60.0)
        self.assertEqual(resultado, [5.0, 59.0])

    def test_lista_vazia_permanece_vazia(self):
        self.assertEqual(limpar_janela([], agora=100.0, janela_segundos=60.0), [])

    def test_todos_dentro_da_janela_permanecem(self):
        resultado = limpar_janela([10.0, 20.0], agora=25.0, janela_segundos=60.0)
        self.assertEqual(resultado, [10.0, 20.0])


class TestPermitirRequisicao(unittest.TestCase):
    def test_primeira_requisicao_sempre_permitida(self):
        permitido, nova_lista = permitir_requisicao([], agora=0.0, janela_segundos=60.0, limite=5)
        self.assertTrue(permitido)
        self.assertEqual(nova_lista, [0.0])

    def test_permite_ate_o_limite(self):
        timestamps = [0.0, 1.0, 2.0, 3.0]  # 4 requisições
        permitido, nova_lista = permitir_requisicao(timestamps, agora=4.0, janela_segundos=60.0, limite=5)
        self.assertTrue(permitido)
        self.assertEqual(len(nova_lista), 5)

    def test_bloqueia_ao_atingir_o_limite(self):
        timestamps = [0.0, 1.0, 2.0, 3.0, 4.0]  # já são 5, limite é 5
        permitido, nova_lista = permitir_requisicao(timestamps, agora=5.0, janela_segundos=60.0, limite=5)
        self.assertFalse(permitido)
        self.assertEqual(len(nova_lista), 5)  # não adiciona a que foi negada

    def test_timestamps_fora_da_janela_nao_contam_pro_limite(self):
        # 5 timestamps, mas todos fora da janela de 60s
        timestamps = [0.0, 1.0, 2.0, 3.0, 4.0]
        permitido, nova_lista = permitir_requisicao(timestamps, agora=100.0, janela_segundos=60.0, limite=5)
        self.assertTrue(permitido)
        self.assertEqual(nova_lista, [100.0])

    def test_janela_deslizante_libera_espaco_conforme_tempo_passa(self):
        # simula 5 chamadas seguidas atingindo o limite, depois espera passar
        # da janela e confirma que libera de novo
        timestamps: list[float] = []
        limite = 3
        janela = 10.0

        for t in [0.0, 1.0, 2.0]:
            permitido, timestamps = permitir_requisicao(timestamps, agora=t, janela_segundos=janela, limite=limite)
            self.assertTrue(permitido)

        # quarta chamada ainda dentro da janela -> bloqueada
        permitido, timestamps = permitir_requisicao(timestamps, agora=3.0, janela_segundos=janela, limite=limite)
        self.assertFalse(permitido)

        # chamada bem depois da janela (todas as 3 anteriores expiraram) -> permitida
        permitido, timestamps = permitir_requisicao(timestamps, agora=15.0, janela_segundos=janela, limite=limite)
        self.assertTrue(permitido)


if __name__ == "__main__":
    unittest.main()
