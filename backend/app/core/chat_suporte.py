"""
app/core/chat_suporte.py

Motor de chat de suporte PRÓPRIO — não chama nenhuma API externa de IA.
Classifica a intenção da mensagem por palavras-chave, responde com
conteúdo pré-definido (alinhado com docs/manual_usuario_operacao.md e
docs/guia_pratico_aumento_score.md), e decide quando oferecer o
redirecionamento pra um atendente humano.

Lógica pura — sem rede, sem banco. 100% testável.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum


class Intencao(str, Enum):
    SAUDACAO = "saudacao"
    PEDIDO_HUMANO = "pedido_humano"
    FRUSTRACAO = "frustracao"
    SCORE_EXPLICACAO = "score_explicacao"
    PRAZO = "prazo"
    NEGOCIACAO_DIVIDA = "negociacao_divida"
    CUSTO = "custo"
    MARKETPLACE_CREDITO = "marketplace_credito"
    SENHA = "senha"
    CONFIRMACAO_POSITIVA = "confirmacao_positiva"
    CONFIRMACAO_NEGATIVA = "confirmacao_negativa"
    DESPEDIDA = "despedida"
    DESCONHECIDA = "desconhecida"


# Ordem importa: intenções mais específicas/urgentes são checadas primeiro,
# senão uma mensagem como "quero falar com um humano sobre meu score" cairia
# em SCORE_EXPLICACAO em vez de PEDIDO_HUMANO.
_PALAVRAS_POR_INTENCAO: list[tuple[Intencao, list[str]]] = [
    (Intencao.PEDIDO_HUMANO, ["humano", "atendente", "pessoa de verdade", "falar com alguem", "suporte humano"]),
    (Intencao.FRUSTRACAO, ["nao funciona", "ruim", "pessimo", "reclamar", "reclamacao", "absurdo", "cansei", "irritado", "raiva"]),
    (Intencao.SAUDACAO, ["ola", "oi", "bom dia", "boa tarde", "boa noite", "eae", "opa"]),
    (Intencao.DESPEDIDA, ["tchau", "obrigado", "obrigada", "ate mais", "valeu"]),
    (Intencao.SENHA, ["senha", "esqueci a senha", "redefinir senha", "login"]),
    (Intencao.CUSTO, ["quanto custa", "preco", "valor", "comissao", "cobranca", "pagar", "gratis"]),
    (Intencao.NEGOCIACAO_DIVIDA, ["negociar", "divida", "boleto", "negativado", "negativada", "limpar nome", "quitar"]),
    (Intencao.MARKETPLACE_CREDITO, ["credito", "emprestimo", "aprovado", "aprovacao", "oferta", "financiamento"]),
    (Intencao.SCORE_EXPLICACAO, ["score", "pontuacao", "por que", "porque", "subir", "aumentar", "fator"]),
    (Intencao.PRAZO, ["quanto tempo", "prazo", "quando", "demora"]),
    (Intencao.CONFIRMACAO_POSITIVA, ["sim", "quero", "pode", "claro", "por favor", "gostaria"]),
    (Intencao.CONFIRMACAO_NEGATIVA, ["nao", "nao quero", "deixa", "obrigado mas nao"]),
]

_RESPOSTAS: dict[Intencao, str] = {
    Intencao.SAUDACAO: "Oi! Posso te ajudar a entender seu score, seu plano de ação ou como negociar suas dívidas. O que você quer saber?",
    Intencao.SCORE_EXPLICACAO: (
        "Seu score é calculado a partir de 5 fatores: histórico de pagamento (35%), utilização de crédito (30%), "
        "tempo de relacionamento (15%), diversidade de crédito (10%) e consultas recentes ao CPF (10%). "
        "No seu Dashboard, cada fator aparece detalhado com o motivo específico e uma ação recomendada."
    ),
    Intencao.PRAZO: (
        "O prazo varia por ação: reduzir uso do cartão costuma levar 30 a 45 dias pra refletir no score; "
        "quitar uma dívida negativada, entre 55 e 85 dias. Cada ação do seu Plano de Ação mostra o prazo "
        "estimado específico."
    ),
    Intencao.NEGOCIACAO_DIVIDA: (
        "Pra negociar uma dívida, vá até a lista de Pendências no app e toque em 'Negociar direto' ou "
        "'Ver oferta Limpa Nome'. A gente sempre mostra a opção gratuita primeiro."
    ),
    Intencao.CUSTO: (
        "Se existir oferta pública de desconto (ex: Serasa Limpa Nome), é grátis. Se você usar a negociação "
        "assistida, a comissão (10% a 15% sobre o desconto conseguido) só é cobrada depois que o acordo é "
        "confirmado no birô — nunca antes."
    ),
    Intencao.MARKETPLACE_CREDITO: (
        "O app mostra ofertas de crédito pré-qualificadas, com o percentual de critérios que você já atende. "
        "Isso não é uma aprovação — a decisão final é sempre do banco ou fintech parceiro."
    ),
    Intencao.SENHA: (
        "Na tela de login, toque em 'Esqueci minha senha' e informe seu e-mail. Você recebe um token de "
        "redefinição válido por 30 minutos."
    ),
    Intencao.DESPEDIDA: "De nada! Qualquer dúvida, é só voltar aqui. 🙂",
    Intencao.DESCONHECIDA: "Não tenho certeza se entendi sua pergunta.",
}

SUGESTAO_REDIRECIONAMENTO = " Quer que eu te conecte com um atendente humano de verdade?"
CONTATO_HUMANO = "Certo! Você pode falar com nosso suporte humano em suporte@nomelimpo.com.br, de segunda a sexta, das 9h às 18h."
CONFIRMACAO_SEM_REDIRECIONAMENTO = "Sem problemas, fico por aqui se precisar de mais alguma coisa."


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def classificar_intencao(mensagem: str) -> Intencao:
    mensagem_normalizada = _normalizar(mensagem)
    for intencao, palavras in _PALAVRAS_POR_INTENCAO:
        for palavra in palavras:
            if palavra in mensagem_normalizada:
                return intencao
    return Intencao.DESCONHECIDA


@dataclass
class RespostaChat:
    texto: str
    oferecer_redirecionamento: bool


def _assistente_ofereceu_redirecionamento(historico: list[dict]) -> bool:
    """Verifica se a ÚLTIMA mensagem do assistente no histórico terminou
    oferecendo redirecionamento — usado pra interpretar corretamente um
    'sim'/'não' isolado do usuário na mensagem seguinte."""
    mensagens_assistente = [m for m in historico if m.get("role") == "assistant"]
    if not mensagens_assistente:
        return False
    return SUGESTAO_REDIRECIONAMENTO.strip() in mensagens_assistente[-1].get("content", "")


def processar_mensagem(historico: list[dict]) -> RespostaChat:
    """
    Recebe o histórico completo da conversa (lista de {"role", "content"})
    e retorna a resposta do assistente pra última mensagem do usuário.
    """
    if not historico or historico[-1].get("role") != "user":
        raise ValueError("historico deve terminar com uma mensagem do usuário")

    mensagem_atual = historico[-1]["content"]
    intencao = classificar_intencao(mensagem_atual)

    assistente_tinha_oferecido = _assistente_ofereceu_redirecionamento(historico[:-1])

    if assistente_tinha_oferecido and intencao == Intencao.CONFIRMACAO_POSITIVA:
        return RespostaChat(texto=CONTATO_HUMANO, oferecer_redirecionamento=False)
    if assistente_tinha_oferecido and intencao == Intencao.CONFIRMACAO_NEGATIVA:
        return RespostaChat(texto=CONFIRMACAO_SEM_REDIRECIONAMENTO, oferecer_redirecionamento=False)

    if intencao == Intencao.PEDIDO_HUMANO:
        return RespostaChat(texto=CONTATO_HUMANO, oferecer_redirecionamento=False)

    if intencao == Intencao.FRUSTRACAO:
        texto = "Sinto muito que esteja passando por isso. Vou te conectar com alguém que pode ajudar melhor."
        return RespostaChat(texto=texto + SUGESTAO_REDIRECIONAMENTO, oferecer_redirecionamento=True)

    # conta quantas das últimas mensagens do usuário (excluindo a atual) foram DESCONHECIDA
    mensagens_usuario_anteriores = [m for m in historico[:-1] if m.get("role") == "user"]
    desconhecidas_consecutivas = 0
    for msg in reversed(mensagens_usuario_anteriores):
        if classificar_intencao(msg["content"]) == Intencao.DESCONHECIDA:
            desconhecidas_consecutivas += 1
        else:
            break

    texto_base = _RESPOSTAS.get(intencao, _RESPOSTAS[Intencao.DESCONHECIDA])

    deve_oferecer = intencao == Intencao.DESCONHECIDA and desconhecidas_consecutivas >= 1
    if deve_oferecer:
        return RespostaChat(texto=texto_base + SUGESTAO_REDIRECIONAMENTO, oferecer_redirecionamento=True)

    return RespostaChat(texto=texto_base, oferecer_redirecionamento=False)
