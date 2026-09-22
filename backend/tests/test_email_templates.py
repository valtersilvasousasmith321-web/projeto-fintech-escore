import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.email_templates import montar_email_reset_senha, montar_email_boas_vindas


class TestMontarEmailResetSenha(unittest.TestCase):
    def test_link_contem_o_token(self):
        email = montar_email_reset_senha("token-abc-123", "https://seuapp.onrender.com")
        self.assertIn("token-abc-123", email.corpo_texto)
        self.assertIn("token-abc-123", email.corpo_html)

    def test_remove_barra_final_da_url_base(self):
        email = montar_email_reset_senha("tok", "https://seuapp.onrender.com/")
        self.assertNotIn("//index.html", email.corpo_texto)

    def test_validade_customizada_aparece_no_texto(self):
        email = montar_email_reset_senha("tok", "https://x.com", validade_minutos=15)
        self.assertIn("15 minutos", email.corpo_texto)

    def test_token_vazio_rejeitado(self):
        with self.assertRaises(ValueError):
            montar_email_reset_senha("", "https://x.com")

    def test_url_base_vazia_rejeitada(self):
        with self.assertRaises(ValueError):
            montar_email_reset_senha("tok", "")

    def test_html_contem_link_clicavel(self):
        email = montar_email_reset_senha("tok123", "https://x.com")
        self.assertIn("<a href=", email.corpo_html)


class TestMontarEmailBoasVindas(unittest.TestCase):
    def test_nome_aparece_na_saudacao(self):
        email = montar_email_boas_vindas("maria@exemplo.com")
        self.assertIn("maria@exemplo.com", email.corpo_texto)

    def test_tem_assunto(self):
        email = montar_email_boas_vindas("x@x.com")
        self.assertTrue(len(email.assunto) > 0)


if __name__ == "__main__":
    unittest.main()
