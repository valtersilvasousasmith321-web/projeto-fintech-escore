"""
tests/test_database.py

Testes de integração REAIS contra SQLite (não é mock — usa um arquivo
de banco temporário de verdade, criado e destruído a cada teste).
Isso é possível porque SQLite é local (sem rede), diferente da Pluggy
e do Asaas.
"""

import sys
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import (
    inicializar_banco, obter_conexao,
    inserir_evento_negociacao, listar_eventos_negociacao, possui_assinatura_ativa,
    possui_credito_avulso_disponivel, consumir_credito_avulso, resolver_caminho_banco,
)


class TestPersistenciaEventosNegociacao(unittest.TestCase):
    def setUp(self):
        self.arquivo_temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.caminho_db = Path(self.arquivo_temp.name)
        self.arquivo_temp.close()
        inicializar_banco(self.caminho_db)

        # cria um usuário e uma negociação mínima pra satisfazer a FK
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) "
                "VALUES ('u1', 'hash1', 'teste@teste.com', 'senhahash', '2026-01-01T00:00:00')"
            )
            conn.execute(
                "INSERT INTO negociacoes (id, usuario_id, credor, valor_original, status, criado_em) "
                "VALUES ('n1', 'u1', 'Credor X', 1000.0, 'iniciada', '2026-01-01T00:00:00')"
            )

    def tearDown(self):
        os.unlink(self.caminho_db)

    def test_inserir_e_listar_um_evento(self):
        with obter_conexao(self.caminho_db) as conn:
            inserir_evento_negociacao(conn, "n1", "iniciada", "negociação iniciada", "2026-01-01T00:00:00")

        with obter_conexao(self.caminho_db) as conn:
            eventos = listar_eventos_negociacao(conn, "n1")

        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["status"], "iniciada")

    def test_eventos_retornados_em_ordem_cronologica(self):
        with obter_conexao(self.caminho_db) as conn:
            inserir_evento_negociacao(conn, "n1", "iniciada", "passo 1", "2026-01-01T00:00:00")
            inserir_evento_negociacao(conn, "n1", "proposta_recebida", "passo 2", "2026-01-02T00:00:00")
            inserir_evento_negociacao(conn, "n1", "aceita_pelo_usuario", "passo 3", "2026-01-03T00:00:00")

        with obter_conexao(self.caminho_db) as conn:
            eventos = listar_eventos_negociacao(conn, "n1")

        self.assertEqual(len(eventos), 3)
        self.assertEqual([e["status"] for e in eventos], ["iniciada", "proposta_recebida", "aceita_pelo_usuario"])

    def test_eventos_de_negociacoes_diferentes_nao_se_misturam(self):
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO negociacoes (id, usuario_id, credor, valor_original, status, criado_em) "
                "VALUES ('n2', 'u1', 'Credor Y', 500.0, 'iniciada', '2026-01-01T00:00:00')"
            )
            inserir_evento_negociacao(conn, "n1", "iniciada", "n1 evento", "2026-01-01T00:00:00")
            inserir_evento_negociacao(conn, "n2", "iniciada", "n2 evento", "2026-01-01T00:00:00")

        with obter_conexao(self.caminho_db) as conn:
            eventos_n1 = listar_eventos_negociacao(conn, "n1")
            eventos_n2 = listar_eventos_negociacao(conn, "n2")

        self.assertEqual(len(eventos_n1), 1)
        self.assertEqual(len(eventos_n2), 1)
        self.assertEqual(eventos_n1[0]["detalhe"], "n1 evento")
        self.assertEqual(eventos_n2[0]["detalhe"], "n2 evento")

    def test_negociacao_sem_eventos_retorna_lista_vazia(self):
        with obter_conexao(self.caminho_db) as conn:
            eventos = listar_eventos_negociacao(conn, "n1")
        self.assertEqual(eventos, [])

    def test_fk_de_usuario_invalido_e_rejeitada(self):
        """Confirma que PRAGMA foreign_keys=ON está de fato ativo —
        sem isso, dado órfão entraria silenciosamente no banco."""
        with self.assertRaises(sqlite3.IntegrityError):
            with obter_conexao(self.caminho_db) as conn:
                conn.execute(
                    "INSERT INTO negociacoes (id, usuario_id, credor, valor_original, status, criado_em) "
                    "VALUES ('n3', 'usuario_que_nao_existe', 'X', 100.0, 'iniciada', '2026-01-01T00:00:00')"
                )

    def test_rollback_em_caso_de_erro_nao_deixa_dado_parcial(self):
        """Se uma exceção ocorrer dentro do 'with', nada deve ser persistido."""
        try:
            with obter_conexao(self.caminho_db) as conn:
                inserir_evento_negociacao(conn, "n1", "iniciada", "vai falhar depois", "2026-01-01T00:00:00")
                raise RuntimeError("erro simulado no meio da transação")
        except RuntimeError:
            pass

        with obter_conexao(self.caminho_db) as conn:
            eventos = listar_eventos_negociacao(conn, "n1")
        self.assertEqual(eventos, [])  # o INSERT foi desfeito pelo rollback


class TestCacheConsultaSerasaUpsert(unittest.TestCase):
    """Confirma que o padrão INSERT ... ON CONFLICT DO UPDATE usado no
    cache de consulta Serasa (app/main.py) realmente atualiza a linha
    existente em vez de duplicar — testado contra SQLite real."""

    def setUp(self):
        self.arquivo_temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.caminho_db = Path(self.arquivo_temp.name)
        self.arquivo_temp.close()
        inicializar_banco(self.caminho_db)
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) "
                "VALUES ('u1', 'hash1', 'teste@teste.com', 'senhahash', '2026-01-01T00:00:00')"
            )

    def tearDown(self):
        os.unlink(self.caminho_db)

    def _upsert(self, conn, doc_hash, valor_score, timestamp):
        conn.execute(
            "INSERT INTO cache_consulta_serasa (documento_hash, usuario_id, resposta_json, consultado_em) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(documento_hash) DO UPDATE SET "
            "usuario_id = excluded.usuario_id, resposta_json = excluded.resposta_json, "
            "consultado_em = excluded.consultado_em",
            (doc_hash, "u1", f'{{"score": {valor_score}}}', timestamp),
        )

    def test_upsert_nao_duplica_linha(self):
        with obter_conexao(self.caminho_db) as conn:
            self._upsert(conn, "doc1", 500, "2026-01-01T00:00:00+00:00")
        with obter_conexao(self.caminho_db) as conn:
            self._upsert(conn, "doc1", 700, "2026-01-02T00:00:00+00:00")

        with obter_conexao(self.caminho_db) as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM cache_consulta_serasa").fetchone()["c"]
        self.assertEqual(total, 1)

    def test_upsert_atualiza_o_valor(self):
        with obter_conexao(self.caminho_db) as conn:
            self._upsert(conn, "doc1", 500, "2026-01-01T00:00:00+00:00")
        with obter_conexao(self.caminho_db) as conn:
            self._upsert(conn, "doc1", 700, "2026-01-02T00:00:00+00:00")

        with obter_conexao(self.caminho_db) as conn:
            row = conn.execute("SELECT resposta_json FROM cache_consulta_serasa WHERE documento_hash='doc1'").fetchone()
        self.assertIn("700", row["resposta_json"])
        self.assertNotIn("500", row["resposta_json"])

    def test_documentos_diferentes_geram_linhas_diferentes(self):
        with obter_conexao(self.caminho_db) as conn:
            self._upsert(conn, "doc1", 500, "2026-01-01T00:00:00+00:00")
            self._upsert(conn, "doc2", 600, "2026-01-01T00:00:00+00:00")

        with obter_conexao(self.caminho_db) as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM cache_consulta_serasa").fetchone()["c"]
        self.assertEqual(total, 2)


class TestContagemDeGastosSerasa(unittest.TestCase):
    """Testa a query usada em /admin/gastos-serasa: contar consultas
    dentro/fora da janela de 30 dias, contra SQLite real."""

    def setUp(self):
        self.arquivo_temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.caminho_db = Path(self.arquivo_temp.name)
        self.arquivo_temp.close()
        inicializar_banco(self.caminho_db)
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) "
                "VALUES ('u1', 'hash1', 'teste@teste.com', 'senhahash', '2026-01-01T00:00:00')"
            )

    def tearDown(self):
        os.unlink(self.caminho_db)

    def test_conta_apenas_consultas_dentro_da_janela_de_30_dias(self):
        agora = datetime.now(timezone.utc)
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO cache_consulta_serasa (documento_hash, usuario_id, resposta_json, consultado_em) "
                "VALUES ('d1', 'u1', '{}', ?)", ((agora - timedelta(days=5)).isoformat(),),
            )
            conn.execute(
                "INSERT INTO cache_consulta_serasa (documento_hash, usuario_id, resposta_json, consultado_em) "
                "VALUES ('d2', 'u1', '{}', ?)", ((agora - timedelta(days=60)).isoformat(),),
            )

        with obter_conexao(self.caminho_db) as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM cache_consulta_serasa").fetchone()["c"]
            ultimos_30 = conn.execute(
                "SELECT COUNT(*) as c FROM cache_consulta_serasa WHERE consultado_em >= ?",
                ((agora - timedelta(days=30)).isoformat(),),
            ).fetchone()["c"]

        self.assertEqual(total, 2)
        self.assertEqual(ultimos_30, 1)


class TestPossuiAssinaturaAtiva(unittest.TestCase):
    """Testa a checagem que trava /score/diagnostico-serasa (~R$16 por
    chamada) atrás de assinatura paga — contra SQLite real."""

    def setUp(self):
        self.arquivo_temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.caminho_db = Path(self.arquivo_temp.name)
        self.arquivo_temp.close()
        inicializar_banco(self.caminho_db)
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) "
                "VALUES ('u1', 'hash1', 'teste@teste.com', 'senhahash', '2026-01-01T00:00:00')"
            )

    def tearDown(self):
        os.unlink(self.caminho_db)

    def _inserir_assinatura(self, conn, usuario_id, status, plano="plus"):
        conn.execute(
            "INSERT INTO assinaturas (id, usuario_id, plano, status, criado_em) VALUES (?, ?, ?, ?, ?)",
            (f"assinatura-{status}-{plano}", usuario_id, plano, status, "2026-01-01T00:00:00"),
        )

    def test_sem_nenhuma_assinatura_retorna_falso(self):
        with obter_conexao(self.caminho_db) as conn:
            self.assertFalse(possui_assinatura_ativa(conn, "u1"))

    def test_com_assinatura_ativa_retorna_verdadeiro(self):
        with obter_conexao(self.caminho_db) as conn:
            self._inserir_assinatura(conn, "u1", "ativa")
        with obter_conexao(self.caminho_db) as conn:
            self.assertTrue(possui_assinatura_ativa(conn, "u1"))

    def test_com_assinatura_pendente_retorna_falso(self):
        """Assinatura criada mas ainda não paga (webhook não confirmou) não libera o endpoint pago."""
        with obter_conexao(self.caminho_db) as conn:
            self._inserir_assinatura(conn, "u1", "pendente")
        with obter_conexao(self.caminho_db) as conn:
            self.assertFalse(possui_assinatura_ativa(conn, "u1"))

    def test_assinatura_de_outro_usuario_nao_libera(self):
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) "
                "VALUES ('u2', 'hash2', 'outro@teste.com', 'senhahash', '2026-01-01T00:00:00')"
            )
            self._inserir_assinatura(conn, "u2", "ativa")
        with obter_conexao(self.caminho_db) as conn:
            self.assertFalse(possui_assinatura_ativa(conn, "u1"))

    def test_uma_assinatura_pendente_e_outra_ativa_retorna_verdadeiro(self):
        with obter_conexao(self.caminho_db) as conn:
            self._inserir_assinatura(conn, "u1", "pendente", plano="plus")
            self._inserir_assinatura(conn, "u1", "ativa", plano="premium")
        with obter_conexao(self.caminho_db) as conn:
            self.assertTrue(possui_assinatura_ativa(conn, "u1"))


class TestCreditoConsultaAvulsa(unittest.TestCase):
    """Testa o crédito de consulta avulsa (pagamento único, sem
    assinatura) contra SQLite real."""

    def setUp(self):
        self.arquivo_temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.caminho_db = Path(self.arquivo_temp.name)
        self.arquivo_temp.close()
        inicializar_banco(self.caminho_db)
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) "
                "VALUES ('u1', 'hash1', 'teste@teste.com', 'senhahash', '2026-01-01T00:00:00')"
            )

    def tearDown(self):
        os.unlink(self.caminho_db)

    def _inserir_credito(self, conn, credito_id, status, criado_em="2026-01-01T00:00:00"):
        conn.execute(
            "INSERT INTO creditos_consulta_avulsa (id, usuario_id, status, criado_em) VALUES (?, 'u1', ?, ?)",
            (credito_id, status, criado_em),
        )

    def test_sem_credito_retorna_falso(self):
        with obter_conexao(self.caminho_db) as conn:
            self.assertFalse(possui_credito_avulso_disponivel(conn, "u1"))

    def test_credito_pendente_nao_libera(self):
        """Crédito comprado mas cujo pagamento ainda não foi confirmado pelo webhook não libera consulta."""
        with obter_conexao(self.caminho_db) as conn:
            self._inserir_credito(conn, "c1", "pendente")
        with obter_conexao(self.caminho_db) as conn:
            self.assertFalse(possui_credito_avulso_disponivel(conn, "u1"))

    def test_credito_pago_libera(self):
        with obter_conexao(self.caminho_db) as conn:
            self._inserir_credito(conn, "c1", "pago")
        with obter_conexao(self.caminho_db) as conn:
            self.assertTrue(possui_credito_avulso_disponivel(conn, "u1"))

    def test_consumir_credito_marca_como_usado(self):
        with obter_conexao(self.caminho_db) as conn:
            self._inserir_credito(conn, "c1", "pago")
        with obter_conexao(self.caminho_db) as conn:
            consumido = consumir_credito_avulso(conn, "u1")
            self.assertTrue(consumido)
        with obter_conexao(self.caminho_db) as conn:
            # depois de consumido, não deve mais aparecer como disponível
            self.assertFalse(possui_credito_avulso_disponivel(conn, "u1"))
            status = conn.execute("SELECT status FROM creditos_consulta_avulsa WHERE id='c1'").fetchone()["status"]
            self.assertEqual(status, "usado")

    def test_consumir_sem_credito_disponivel_retorna_falso(self):
        with obter_conexao(self.caminho_db) as conn:
            consumido = consumir_credito_avulso(conn, "u1")
        self.assertFalse(consumido)

    def test_consumir_pega_o_mais_antigo_primeiro(self):
        with obter_conexao(self.caminho_db) as conn:
            self._inserir_credito(conn, "c_novo", "pago", criado_em="2026-03-01T00:00:00")
            self._inserir_credito(conn, "c_antigo", "pago", criado_em="2026-01-01T00:00:00")

        with obter_conexao(self.caminho_db) as conn:
            consumir_credito_avulso(conn, "u1")

        with obter_conexao(self.caminho_db) as conn:
            status_antigo = conn.execute("SELECT status FROM creditos_consulta_avulsa WHERE id='c_antigo'").fetchone()["status"]
            status_novo = conn.execute("SELECT status FROM creditos_consulta_avulsa WHERE id='c_novo'").fetchone()["status"]

        self.assertEqual(status_antigo, "usado")
        self.assertEqual(status_novo, "pago")  # o mais novo continua disponível

    def test_credito_de_outro_usuario_nao_libera(self):
        with obter_conexao(self.caminho_db) as conn:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) "
                "VALUES ('u2', 'hash2', 'outro@teste.com', 'senhahash', '2026-01-01T00:00:00')"
            )
            conn.execute(
                "INSERT INTO creditos_consulta_avulsa (id, usuario_id, status, criado_em) "
                "VALUES ('c1', 'u2', 'pago', '2026-01-01T00:00:00')"
            )
        with obter_conexao(self.caminho_db) as conn:
            self.assertFalse(possui_credito_avulso_disponivel(conn, "u1"))


class TestResolverCaminhoBanco(unittest.TestCase):
    """Testa a escolha do caminho do arquivo de banco — o que permite
    apontar pro disco persistente do Render via DATABASE_PATH, sem
    quebrar quem roda local (onde essa variável não existe)."""

    def setUp(self):
        os.environ.pop("DATABASE_PATH", None)

    def tearDown(self):
        os.environ.pop("DATABASE_PATH", None)

    def test_sem_variavel_usa_caminho_local_padrao(self):
        caminho = resolver_caminho_banco()
        self.assertTrue(str(caminho).endswith("dados_app.db"))
        # confirma que é o caminho relativo ao próprio pacote, não um caminho arbitrário
        self.assertIn("backend", str(caminho))

    def test_com_variavel_usa_o_caminho_customizado(self):
        os.environ["DATABASE_PATH"] = "/caminho/customizado/no/disco/persistente.db"
        caminho = resolver_caminho_banco()
        self.assertEqual(str(caminho), "/caminho/customizado/no/disco/persistente.db")

    def test_variavel_vazia_cai_no_padrao(self):
        os.environ["DATABASE_PATH"] = ""
        caminho = resolver_caminho_banco()
        self.assertTrue(str(caminho).endswith("dados_app.db"))
        self.assertNotEqual(str(caminho), "")


if __name__ == "__main__":
    unittest.main()
