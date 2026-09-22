"""
app/main.py

API FastAPI que expõe o motor de score, o módulo de negociação e o
marketplace de crédito pré-qualificado.

Rodar localmente (após `pip install -r requirements.txt`):

    export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    uvicorn app.main:app --reload --port 8000

Documentação interativa gerada automaticamente em: http://localhost:8000/docs
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.score_engine import (
    DadosOpenFinance, DadosBiro, Divida, ErroValidacao, rodar_auditoria,
)
from app.core.negociacao import (
    Negociacao, StatusNegociacao, TransicaoInvalida, ErroValidacaoNegociacao,
)
from app.core.marketplace import (
    CriteriosParceiro, PerfilUsuario, rankear_ofertas, ErroValidacaoMarketplace,
)
from app.core.security import gerar_hash_senha, verificar_senha, mascarar_cpf, hash_deterministico_documento
from app.core.cache_score import cache_esta_valido, dias_restantes_ate_proxima_consulta
from app.core.password_reset import criar_token_reset, token_e_valido, TokenResetSenha
from app.core.chat_suporte import processar_mensagem
from app.core.account_lockout import deve_bloquear, calcular_fim_bloqueio, esta_bloqueado
from app.core.rate_limiter import permitir_requisicao
from app.core.billing import (
    PlanoAssinatura, obter_valor_plano, ErroCobranca,
    token_webhook_valido, interpretar_webhook_pagamento, TipoEventoAsaas,
    PRECO_CONSULTA_AVULSA,
)
from app.integrations.asaas_client import AsaasClient, ErroIntegracaoAsaas
from app.integrations.sendgrid_client import SendGridClient, ErroIntegracaoSendGrid
from app.integrations.serasa_client import SerasaClient, ErroIntegracaoSerasa
from app.core.email_templates import montar_email_reset_senha
from app.core.serasa_adapter import (
    extrair_score, extrair_dividas_negativadas, extrair_consultas_recentes,
    extrair_probabilidade_inadimplencia,
)
from app.schemas import (
    DiagnosticoRequest, NovaNegociacaoRequest, RegistrarPropostaRequest,
    TransicaoRequest, AvaliarMarketplaceRequest, CadastroRequest,
    EsqueciSenhaRequest, RedefinirSenhaRequest, SuporteChatRequest, CriarAssinaturaRequest, CobrarComissaoRequest,
    DiagnosticoSerasaRequest, ComprarConsultaAvulsaRequest, ConsultaManualAdminRequest,
)
from app.auth import criar_access_token, criar_refresh_token, usuario_atual, admin_atual
from app.database import (
    inicializar_banco, obter_conexao, inserir_log_auditoria,
    inserir_evento_negociacao, listar_eventos_negociacao, possui_assinatura_ativa,
    possui_credito_avulso_disponivel, consumir_credito_avulso,
)


app = FastAPI(
    title="Score Transparente & Plano de Evolução de Crédito — API",
    version="1.0.0",
    description=(
        "API do produto de diagnóstico de score, negociação de dívidas e "
        "marketplace de crédito pré-qualificado. Nunca aprova crédito — "
        "decisão final é sempre do parceiro financeiro."
    ),
)


# ---------------------------------------------------------------------------
# CORS — restrito a origens explícitas (nunca "*" em produção com credenciais)
# ---------------------------------------------------------------------------

ORIGENS_PERMITIDAS = [
    origem.strip()
    for origem in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origem.strip()
]
# Em produção, defina CORS_ALLOWED_ORIGINS com a URL real do frontend publicado,
# ex: https://seu-app.onrender.com — ver DEPLOY_PUBLICO.md

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Rate limiting simples em memória (para produção com múltiplas instâncias,
# usar Redis — ver SECURITY.md, seção "Rate limiting")
# ---------------------------------------------------------------------------

JANELA_RATE_LIMIT_SEGUNDOS = 60
LIMITE_REQUISICOES_POR_JANELA = 30
_contador_requisicoes: dict[str, list[float]] = defaultdict(list)

# Endpoints de autenticação recebem um limite MUITO mais rígido, porque são
# o alvo natural de ataques de força bruta (tentar muitas senhas) e de
# criação em massa de contas falsas (spam de cadastro). 30 req/min é
# aceitável pra uso geral do app, mas é generoso demais pra login.
CAMINHOS_SENSIVEIS_AUTH = ("/auth/login", "/auth/cadastro", "/auth/esqueci-senha")
LIMITE_REQUISICOES_AUTH_POR_JANELA = 8
_contador_requisicoes_auth: dict[str, list[float]] = defaultdict(list)

TAMANHO_MAXIMO_CORPO_BYTES = 1_000_000  # 1 MB — nenhuma rota deste app precisa de payload maior que isso


@app.middleware("http")
async def seguranca_middleware(request: Request, call_next):
    identificador = request.client.host if request.client else "desconhecido"
    agora = time.time()

    # Proteção contra payload gigante (DoS por corpo de requisição enorme)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > TAMANHO_MAXIMO_CORPO_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "Corpo da requisição excede o tamanho máximo permitido."},
        )

    # Rate limit geral
    permitido, nova_janela = permitir_requisicao(
        _contador_requisicoes[identificador], agora, JANELA_RATE_LIMIT_SEGUNDOS, LIMITE_REQUISICOES_POR_JANELA
    )
    _contador_requisicoes[identificador] = nova_janela
    if not permitido:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Muitas requisições. Tente novamente em instantes."},
        )

    # Rate limit adicional e mais rígido, específico pra rotas sensíveis de auth
    if request.url.path in CAMINHOS_SENSIVEIS_AUTH:
        permitido_auth, nova_janela_auth = permitir_requisicao(
            _contador_requisicoes_auth[identificador], agora,
            JANELA_RATE_LIMIT_SEGUNDOS, LIMITE_REQUISICOES_AUTH_POR_JANELA,
        )
        _contador_requisicoes_auth[identificador] = nova_janela_auth
        if not permitido_auth:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Muitas tentativas. Aguarde um minuto antes de tentar de novo."},
            )

    response = await call_next(request)

    # Headers de segurança em toda resposta
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    # Respostas de autenticação e admin nunca devem ser guardadas em cache
    # (nem pelo navegador, nem por um proxy no meio do caminho)
    if request.url.path.startswith("/auth") or request.url.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store"

    return response


@app.on_event("startup")
def startup() -> None:
    inicializar_banco()
    _bootstrap_admin_se_configurado()


def _bootstrap_admin_se_configurado() -> None:
    """
    Cria a conta de administrador inicial a partir de variáveis de
    ambiente, se elas estiverem definidas e a conta ainda não existir.

    Isso é o ÚNICO jeito de criar um admin — não existe endpoint público
    pra isso, de propósito (senão qualquer pessoa poderia se auto-promover).

    Depois do primeiro deploy com sucesso, recomenda-se REMOVER essas
    variáveis de ambiente do painel do Render, já que só são necessárias
    uma vez.
    """
    email_admin = os.environ.get("ADMIN_BOOTSTRAP_EMAIL")
    senha_admin = os.environ.get("ADMIN_BOOTSTRAP_SENHA")
    if not email_admin or not senha_admin:
        return

    with obter_conexao() as conn:
        existente = conn.execute("SELECT id, is_admin FROM usuarios WHERE email = ?", (email_admin,)).fetchone()
        if existente is not None:
            if not existente["is_admin"]:
                print(f"[bootstrap admin] e-mail {email_admin} já existe e NÃO é admin — não promovido automaticamente.")
            return

        usuario_id = str(uuid.uuid4())
        senha_hash = gerar_hash_senha(senha_admin)
        # documento_hash precisa ser único; pra conta de admin sem CPF real associado,
        # usamos um valor derivado do próprio id (não é um documento de verdade).
        documento_hash_admin = gerar_hash_senha(f"admin-bootstrap-{usuario_id}")
        conn.execute(
            "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em, is_admin) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (usuario_id, documento_hash_admin, email_admin, senha_hash, datetime.now(timezone.utc).isoformat()),
        )
    print(f"[bootstrap admin] conta de administrador criada para {email_admin}")


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

@app.post("/auth/cadastro", status_code=status.HTTP_201_CREATED, tags=["auth"])
def cadastrar_usuario(dados: CadastroRequest):
    usuario_id = str(uuid.uuid4())
    senha_hash = gerar_hash_senha(dados.senha)
    documento_hash = gerar_hash_senha(dados.documento)  # nunca guardamos o CPF em claro

    with obter_conexao() as conn:
        try:
            conn.execute(
                "INSERT INTO usuarios (id, documento_hash, email, senha_hash, criado_em) VALUES (?, ?, ?, ?, ?)",
                (usuario_id, documento_hash, dados.email, senha_hash, datetime.now(timezone.utc).isoformat()),
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="e-mail ou documento já cadastrado")

    return {"usuario_id": usuario_id, "documento_mascarado": mascarar_cpf(dados.documento)}


@app.post("/auth/login", tags=["auth"])
def login(email: str, senha: str):
    agora = datetime.now(timezone.utc)
    erro_a_lancar: HTTPException | None = None

    with obter_conexao() as conn:
        row = conn.execute(
            "SELECT id, senha_hash, tentativas_login_falhas, bloqueado_ate FROM usuarios WHERE email = ?", (email,)
        ).fetchone()

        if row is not None and row["bloqueado_ate"]:
            fim_bloqueio = datetime.fromisoformat(row["bloqueado_ate"])
            if esta_bloqueado(fim_bloqueio, agora):
                erro_a_lancar = HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Conta temporariamente bloqueada por várias tentativas de senha incorretas. "
                           "Tente novamente mais tarde ou use 'Esqueci minha senha'.",
                )

        if erro_a_lancar is None:
            senha_correta = row is not None and verificar_senha(senha, row["senha_hash"])

            if not senha_correta:
                if row is not None:
                    novas_tentativas = row["tentativas_login_falhas"] + 1
                    novo_bloqueio = calcular_fim_bloqueio(agora).isoformat() if deve_bloquear(novas_tentativas) else None
                    conn.execute(
                        "UPDATE usuarios SET tentativas_login_falhas = ?, bloqueado_ate = ? WHERE id = ?",
                        (novas_tentativas, novo_bloqueio, row["id"]),
                    )
                # Mesma mensagem de erro para "não existe" e "senha errada" — evita
                # que um atacante descubra quais e-mails estão cadastrados (user enumeration)
                erro_a_lancar = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="e-mail ou senha inválidos")
            else:
                # login certo: zera o contador de tentativas
                conn.execute(
                    "UPDATE usuarios SET tentativas_login_falhas = 0, bloqueado_ate = NULL WHERE id = ?", (row["id"],)
                )

    # o raise fica FORA do "with": se estivesse dentro, o context manager
    # trataria a exceção como motivo de rollback e desfaria a atualização
    # do contador de tentativas que acabamos de gravar.
    if erro_a_lancar is not None:
        raise erro_a_lancar

    return {
        "access_token": criar_access_token(row["id"]),
        "refresh_token": criar_refresh_token(row["id"]),
        "token_type": "bearer",
    }


@app.post("/auth/esqueci-senha", tags=["auth"])
def esqueci_senha(dados: EsqueciSenhaRequest):
    """
    Gera um token de recuperação e "envia" pro e-mail do usuário.

    IMPORTANTE: este endpoint sempre retorna a mesma mensagem de sucesso,
    exista ou não o e-mail no banco — isso evita user enumeration (um
    atacante descobrir quais e-mails estão cadastrados testando esse
    endpoint em massa).
    """
    with obter_conexao() as conn:
        row = conn.execute("SELECT id FROM usuarios WHERE email = ?", (dados.email,)).fetchone()

        if row is not None:
            token_bruto, registro = criar_token_reset(usuario_id=row["id"])
            conn.execute(
                "INSERT INTO tokens_reset_senha (token_hash, usuario_id, criado_em, expira_em, usado) "
                "VALUES (?, ?, ?, ?, 0)",
                (registro.token_hash, registro.usuario_id, registro.criado_em.isoformat(), registro.expira_em.isoformat()),
            )
            _enviar_email_reset_senha(dados.email, token_bruto)

    resposta = {"detail": "Se este e-mail estiver cadastrado, você vai receber as instruções em instantes."}
    # Em ambiente de desenvolvimento (sem serviço de e-mail configurado),
    # devolvemos o token direto na resposta pra dar pra testar o fluxo
    # sem precisar de um provedor de e-mail real. NUNCA fazer isso em produção.
    if os.environ.get("APP_ENV", "dev") == "dev" and row is not None:
        resposta["token_dev_apenas"] = token_bruto
    return resposta


@app.post("/auth/redefinir-senha", tags=["auth"])
def redefinir_senha(dados: RedefinirSenhaRequest):
    token_hash_recebido = hashlib.sha256(dados.token.encode("utf-8")).hexdigest()

    with obter_conexao() as conn:
        row = conn.execute(
            "SELECT * FROM tokens_reset_senha WHERE token_hash = ?", (token_hash_recebido,)
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=400, detail="token inválido")

        registro = TokenResetSenha(
            token_hash=row["token_hash"],
            usuario_id=row["usuario_id"],
            criado_em=datetime.fromisoformat(row["criado_em"]),
            expira_em=datetime.fromisoformat(row["expira_em"]),
            usado=bool(row["usado"]),
        )

        if not token_e_valido(registro, dados.token):
            raise HTTPException(status_code=400, detail="token inválido ou expirado")

        nova_senha_hash = gerar_hash_senha(dados.nova_senha)
        conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (nova_senha_hash, registro.usuario_id))
        conn.execute("UPDATE tokens_reset_senha SET usado = 1 WHERE token_hash = ?", (registro.token_hash,))

    return {"detail": "Senha redefinida com sucesso."}


def _enviar_email_reset_senha(email: str, token_bruto: str) -> None:
    """
    Envia o e-mail de recuperação de senha via SendGrid. Se
    SENDGRID_API_KEY não estiver configurada (ex: ambiente de
    desenvolvimento local sem essa variável), cai de volta pro log no
    console — o fluxo de "esqueci senha" continua funcionando pra
    testar localmente, só não manda e-mail de verdade.
    """
    url_frontend = os.environ.get("FRONTEND_URL", "http://localhost:5500")
    email_montado = montar_email_reset_senha(token_bruto, url_frontend)

    try:
        cliente_email = SendGridClient()
        cliente_email.enviar(
            destinatario=email, assunto=email_montado.assunto,
            corpo_texto=email_montado.corpo_texto, corpo_html=email_montado.corpo_html,
        )
    except ErroIntegracaoSendGrid as e:
        # Nunca loga o token completo, mesmo no fallback — só os primeiros
        # caracteres, suficiente pra debug sem virar um token usável se o
        # log for exposto.
        print(f"[SendGrid indisponível: {e}] E-mail não enviado de verdade para {email}. "
              f"Token (truncado): {token_bruto[:8]}...")


# ---------------------------------------------------------------------------
# Diagnóstico de score
# ---------------------------------------------------------------------------

@app.post("/score/diagnostico", tags=["score"])
def diagnostico(dados: DiagnosticoRequest, usuario_id: str = Depends(usuario_atual)):
    try:
        dados_of = DadosOpenFinance(
            utilizacao_credito_atual=dados.utilizacao_credito_atual,
            utilizacao_credito_meta=dados.utilizacao_credito_meta,
            meses_historico_disponivel=dados.meses_historico_disponivel,
            pontualidade_pagamentos_24m=dados.pontualidade_pagamentos_24m,
        )
        dividas = [
            Divida(
                credor=d.credor, valor=d.valor, dias_atraso=d.dias_atraso,
                origem=d.origem, negativado=d.negativado, linha_digitavel=d.linha_digitavel,
            )
            for d in dados.dividas_ativas
        ]
        dados_biro = DadosBiro(
            score_atual=dados.score_atual,
            tempo_relacionamento_credito_meses=dados.tempo_relacionamento_credito_meses,
            quantidade_tipos_credito_ativos=dados.quantidade_tipos_credito_ativos,
            dividas_ativas=dividas,
            consultas_cpf_ultimos_30_dias=dados.consultas_cpf_ultimos_30_dias,
        )
    except ErroValidacao as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    resultado = rodar_auditoria(dados_of, dados_biro)

    log_payload = {
        "fatores": resultado.fatores,
        "alertas": resultado.alertas,
        "confianca_modelo": resultado.confianca_modelo,
        "documento_mascarado": mascarar_cpf(dados.documento) if len(dados.documento.replace(".", "").replace("-", "")) == 11 else dados.documento,
    }
    with obter_conexao() as conn:
        inserir_log_auditoria(
            conn, usuario_id, datetime.now(timezone.utc).isoformat(),
            resultado.score_atual, resultado.score_estimado_apos_plano,
            json.dumps(log_payload, ensure_ascii=False),
        )

    return {
        "score_atual": resultado.score_atual,
        "score_estimado_apos_plano": resultado.score_estimado_apos_plano,
        "confianca_modelo": resultado.confianca_modelo,
        "fatores": resultado.fatores,
        "alertas": resultado.alertas,
        "plano_acao": [
            {
                "descricao": a.descricao,
                "impacto_estimado_min": a.impacto_estimado_min,
                "impacto_estimado_max": a.impacto_estimado_max,
                "prazo_estimado_dias": a.prazo_estimado_dias,
                "esforco": a.esforco,
                "status": a.status.value,
            }
            for a in resultado.plano_acao
        ],
        "aviso_legal": (
            "Estimativas baseadas em modelo estatístico interno. O score oficial é "
            "calculado exclusivamente pelo birô de crédito."
        ),
    }


def _consultar_serasa_com_cache(documento: str, usuario_id_para_registro: str) -> tuple[dict, str, int]:
    """
    Lógica compartilhada de cache + consulta real ao CredNet — usada
    tanto pelo endpoint público (/score/diagnostico-serasa) quanto pelo
    endpoint manual do admin (/admin/consulta-manual-serasa). Extraída
    pra um só lugar de propósito: a regra de "não gastar de novo dentro
    de 30 dias" precisa valer igual nos dois caminhos, senão um deles
    vira um jeito de furar o cache do outro.

    Retorna (resposta_crednet, fonte, dias_restantes_ate_nova_consulta).
    """
    doc_hash = hash_deterministico_documento(documento)
    agora = datetime.now(timezone.utc)

    with obter_conexao() as conn:
        cache_row = conn.execute(
            "SELECT resposta_json, consultado_em FROM cache_consulta_serasa WHERE documento_hash = ?",
            (doc_hash,),
        ).fetchone()

    usar_cache = False
    if cache_row is not None:
        consultado_em = datetime.fromisoformat(cache_row["consultado_em"])
        if cache_esta_valido(consultado_em, agora):
            usar_cache = True

    if usar_cache:
        resposta_crednet = json.loads(cache_row["resposta_json"])
        dias_restantes = dias_restantes_ate_proxima_consulta(consultado_em, agora)
        fonte = "serasa_crednet_cache"
    else:
        try:
            cliente_serasa = SerasaClient()
            resposta_crednet = cliente_serasa.consultar_crednet(documento=documento)
        except ErroIntegracaoSerasa as e:
            raise HTTPException(status_code=503, detail=f"Consulta ao birô indisponível: {e}")

        with obter_conexao() as conn:
            conn.execute(
                "INSERT INTO cache_consulta_serasa (documento_hash, usuario_id, resposta_json, consultado_em) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(documento_hash) DO UPDATE SET "
                "usuario_id = excluded.usuario_id, resposta_json = excluded.resposta_json, "
                "consultado_em = excluded.consultado_em",
                (doc_hash, usuario_id_para_registro, json.dumps(resposta_crednet), agora.isoformat()),
            )
        dias_restantes = dias_restantes_ate_proxima_consulta(agora, agora)
        fonte = "serasa_crednet_real"

    return resposta_crednet, fonte, dias_restantes


@app.post("/score/diagnostico-serasa", tags=["score"])
def diagnostico_com_serasa_real(dados: DiagnosticoSerasaRequest, usuario_id: str = Depends(usuario_atual)):
    """
    Igual ao /score/diagnostico, mas consulta o score e as dívidas
    negativadas DE VERDADE no birô (Serasa CredNet via SOA Web
    Services) em vez de recebê-los manualmente no corpo da requisição.

    IMPORTANTE — CUSTO: cada consulta ao CredNet é cobrada pelo
    provedor (~R$16, confirmado no painel da conta). Por isso este
    endpoint usa CACHE de 30 dias por documento: se já consultamos
    esse CPF/CNPJ recentemente, devolve o resultado salvo em vez de
    pagar por uma nova consulta. Ver app/core/cache_score.py.

    TRAVA DE CUSTO: exige assinatura Plus/Premium ATIVA **ou** um
    crédito de consulta avulsa pago e não usado — sem nenhum dos dois,
    retorna 402 antes de gastar qualquer dinheiro. Ver
    possui_assinatura_ativa / possui_credito_avulso_disponivel em
    app/database.py, ambos testados com SQLite real.

    Requer SOA_EMAIL e SOA_SENHA configuradas.
    """
    with obter_conexao() as conn:
        tem_assinatura = possui_assinatura_ativa(conn, usuario_id)
        tem_credito_avulso = possui_credito_avulso_disponivel(conn, usuario_id) if not tem_assinatura else False

    if not tem_assinatura and not tem_credito_avulso:
        raise HTTPException(
            status_code=402,
            detail="Esta consulta usa dado real do birô e tem custo — disponível para "
                   "assinantes Plus/Premium ou mediante consulta avulsa paga. Assine em "
                   "/pagamentos/assinatura ou compre uma consulta avulsa em "
                   "/pagamentos/consulta-avulsa. O diagnóstico manual (/score/diagnostico) "
                   "continua gratuito.",
        )

    resposta_crednet, fonte, dias_restantes = _consultar_serasa_com_cache(dados.documento, usuario_id)

    # Se foi crédito avulso (não assinatura) que liberou, consome o
    # crédito agora que a consulta de fato aconteceu (mesmo se veio do
    # cache — o usuário pediu a consulta, o crédito dele é consumido
    # de qualquer forma, senão ele nunca gastaria o crédito comprado).
    if tem_credito_avulso:
        with obter_conexao() as conn:
            consumir_credito_avulso(conn, usuario_id)

    score_atual = extrair_score(resposta_crednet)
    if score_atual is None:
        raise HTTPException(
            status_code=422,
            detail="O birô não retornou uma pontuação de score para este documento "
                   "(comum quando o CPF/CNPJ não tem histórico suficiente).",
        )

    dividas = extrair_dividas_negativadas(resposta_crednet)
    consultas_recentes = extrair_consultas_recentes(resposta_crednet)

    try:
        dados_of = DadosOpenFinance(
            utilizacao_credito_atual=dados.utilizacao_credito_atual,
            utilizacao_credito_meta=dados.utilizacao_credito_meta,
            meses_historico_disponivel=dados.meses_historico_disponivel,
            pontualidade_pagamentos_24m=dados.pontualidade_pagamentos_24m,
        )
        dados_biro = DadosBiro(
            score_atual=score_atual,
            # NOTA: o CredNet não retorna tempo de relacionamento nem
            # diversidade de crédito nesses campos exatos — usando
            # valores conservadores até identificarmos o campo certo
            # na doc completa da SOA (ou outra fonte). Ver SECURITY.md.
            tempo_relacionamento_credito_meses=0,
            quantidade_tipos_credito_ativos=1,
            dividas_ativas=dividas,
            consultas_cpf_ultimos_30_dias=consultas_recentes,
        )
    except ErroValidacao as e:
        raise HTTPException(status_code=422, detail=str(e))

    resultado = rodar_auditoria(dados_of, dados_biro)

    log_payload = {
        "fonte": fonte,
        "fatores": resultado.fatores,
        "alertas": resultado.alertas,
        "confianca_modelo": resultado.confianca_modelo,
        "documento_mascarado": mascarar_cpf(dados.documento),
    }
    with obter_conexao() as conn:
        inserir_log_auditoria(
            conn, usuario_id, datetime.now(timezone.utc).isoformat(),
            resultado.score_atual, resultado.score_estimado_apos_plano,
            json.dumps(log_payload, ensure_ascii=False),
        )

    return {
        "fonte": fonte,
        "dias_restantes_ate_nova_consulta_real": dias_restantes,
        "score_atual": resultado.score_atual,
        "score_estimado_apos_plano": resultado.score_estimado_apos_plano,
        "confianca_modelo": resultado.confianca_modelo,
        "fatores": resultado.fatores,
        "alertas": resultado.alertas,
        "plano_acao": [
            {
                "descricao": a.descricao,
                "impacto_estimado_min": a.impacto_estimado_min,
                "impacto_estimado_max": a.impacto_estimado_max,
                "prazo_estimado_dias": a.prazo_estimado_dias,
                "esforco": a.esforco,
                "status": a.status.value,
            }
            for a in resultado.plano_acao
        ],
        "aviso_legal": (
            "Score e dívidas consultados em tempo real no birô de crédito. "
            "O plano de ação continua sendo uma estimativa do nosso modelo."
        ),
    }


# ---------------------------------------------------------------------------
# Negociação (armazenamento em memória neste exemplo — trocar por tabela
# dedicada em produção, seguindo o schema de app/database.py)
# ---------------------------------------------------------------------------

@app.post("/negociacao", status_code=status.HTTP_201_CREATED, tags=["negociacao"])
def criar_negociacao(dados: NovaNegociacaoRequest, usuario_id: str = Depends(usuario_atual)):
    if dados.usuario_id != usuario_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="usuario_id não corresponde ao token autenticado")
    try:
        neg = Negociacao(
            negociacao_id=str(uuid.uuid4()), usuario_id=dados.usuario_id,
            credor=dados.credor, valor_original=dados.valor_original,
        )
    except ErroValidacaoNegociacao as e:
        raise HTTPException(status_code=422, detail=str(e))

    with obter_conexao() as conn:
        conn.execute(
            "INSERT INTO negociacoes (id, usuario_id, credor, valor_original, valor_com_desconto, status, criado_em) "
            "VALUES (?, ?, ?, ?, NULL, ?, ?)",
            (neg.negociacao_id, neg.usuario_id, neg.credor, neg.valor_original, neg.status.value,
             datetime.now(timezone.utc).isoformat()),
        )
        inserir_evento_negociacao(
            conn, neg.negociacao_id, neg.status.value, "negociação iniciada",
            datetime.now(timezone.utc).isoformat(),
        )
    return {"negociacao_id": neg.negociacao_id, "status": neg.status.value}


@app.post("/negociacao/{negociacao_id}/proposta", tags=["negociacao"])
def registrar_proposta(negociacao_id: str, dados: RegistrarPropostaRequest, usuario_id: str = Depends(usuario_atual)):
    neg = _carregar_negociacao_do_usuario(negociacao_id, usuario_id)
    try:
        neg.registrar_proposta(dados.valor_com_desconto)
    except ErroValidacaoNegociacao as e:
        raise HTTPException(status_code=422, detail=str(e))

    with obter_conexao() as conn:
        conn.execute(
            "UPDATE negociacoes SET valor_com_desconto = ?, status = ? WHERE id = ?",
            (neg.valor_com_desconto, neg.status.value, negociacao_id),
        )
        inserir_evento_negociacao(
            conn, negociacao_id, neg.status.value, f"proposta de R$ {dados.valor_com_desconto:.2f}",
            datetime.now(timezone.utc).isoformat(),
        )
    return {"status": neg.status.value, "valor_com_desconto": neg.valor_com_desconto}


@app.post("/negociacao/{negociacao_id}/transicao", tags=["negociacao"])
def transicionar_negociacao(negociacao_id: str, dados: TransicaoRequest, usuario_id: str = Depends(usuario_atual)):
    neg = _carregar_negociacao_do_usuario(negociacao_id, usuario_id)
    try:
        novo_status = StatusNegociacao(dados.novo_status)
        neg.transicionar(novo_status, detalhe=dados.detalhe)
    except (TransicaoInvalida, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    resposta = {"status": neg.status.value}
    if neg.status == StatusNegociacao.BAIXA_CONFIRMADA:
        resposta["comissao_devida"] = neg.calcular_comissao()

    with obter_conexao() as conn:
        conn.execute("UPDATE negociacoes SET status = ? WHERE id = ?", (neg.status.value, negociacao_id))
        inserir_evento_negociacao(
            conn, negociacao_id, neg.status.value, dados.detalhe,
            datetime.now(timezone.utc).isoformat(),
        )
    return resposta


@app.get("/negociacao/{negociacao_id}/historico", tags=["negociacao"])
def historico_negociacao(negociacao_id: str, usuario_id: str = Depends(usuario_atual)):
    """Retorna a linha do tempo completa da negociação — cada
    transição de status, com detalhe e timestamp."""
    _carregar_negociacao_do_usuario(negociacao_id, usuario_id)  # valida posse e existência
    with obter_conexao() as conn:
        eventos = listar_eventos_negociacao(conn, negociacao_id)
    return {
        "eventos": [
            {"status": e["status"], "detalhe": e["detalhe"], "timestamp": e["timestamp"]}
            for e in eventos
        ]
    }


def _carregar_negociacao_do_usuario(negociacao_id: str, usuario_id: str) -> Negociacao:
    """
    Carrega a negociação do banco e reconstrói o objeto Negociacao pra
    aplicar as regras da máquina de estados. O histórico completo de
    eventos é persistido separadamente (tabela negociacao_eventos) —
    ver historico_negociacao() para consultá-lo.
    """
    with obter_conexao() as conn:
        row = conn.execute("SELECT * FROM negociacoes WHERE id = ?", (negociacao_id,)).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="negociação não encontrada")
    if row["usuario_id"] != usuario_id:
        raise HTTPException(status_code=403, detail="negociação não pertence ao usuário autenticado")

    neg = Negociacao(
        negociacao_id=row["id"], usuario_id=row["usuario_id"], credor=row["credor"],
        valor_original=row["valor_original"], valor_com_desconto=row["valor_com_desconto"],
    )
    neg.status = StatusNegociacao(row["status"])
    return neg


# ---------------------------------------------------------------------------
# Marketplace
# ---------------------------------------------------------------------------

@app.post("/marketplace/ofertas", tags=["marketplace"])
def listar_ofertas(dados: AvaliarMarketplaceRequest, usuario_id: str = Depends(usuario_atual)):
    try:
        perfil = PerfilUsuario(
            score_atual=dados.score_atual, tem_restricao_ativa=dados.tem_restricao_ativa,
            renda_declarada=dados.renda_declarada,
            tempo_relacionamento_bancario_meses=dados.tempo_relacionamento_bancario_meses,
        )
        lista_criterios = [
            CriteriosParceiro(
                parceiro_id=c.parceiro_id, produto=c.produto, score_minimo=c.score_minimo,
                sem_restricao_ativa=c.sem_restricao_ativa, renda_minima_declarada=c.renda_minima_declarada,
                tempo_minimo_relacionamento_bancario_meses=c.tempo_minimo_relacionamento_bancario_meses,
            )
            for c in dados.ofertas_disponiveis
        ]
    except ErroValidacaoMarketplace as e:
        raise HTTPException(status_code=422, detail=str(e))

    ranking = rankear_ofertas(perfil, lista_criterios)
    return {
        "ofertas": [
            {
                "parceiro_id": r.parceiro_id, "produto": r.produto,
                "percentual_aderencia": r.percentual_aderencia,
                "detalhamento": r.detalhamento,
            }
            for r in ranking
        ],
        "aviso_legal": "Pré-qualificação baseada em critérios públicos. A decisão final é sempre do parceiro financeiro.",
    }


@app.post("/suporte/chat", tags=["suporte"])
def chat_suporte(dados: SuporteChatRequest, usuario_id: str = Depends(usuario_atual)):
    """
    Motor de chat de suporte PRÓPRIO — classificação de intenção por
    palavra-chave, sem chamada a nenhuma API externa de IA. Ver
    app/core/chat_suporte.py para a lógica completa (testada, 19 testes).
    """
    historico = [{"role": m.role, "content": m.content} for m in dados.mensagens]
    try:
        resultado = processar_mensagem(historico)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"resposta": resultado.texto, "oferecer_redirecionamento": resultado.oferecer_redirecionamento}


@app.get("/health", tags=["infra"])
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Cobrança (Asaas) — assinatura mensal e comissão de negociação.
# Requer ASAAS_API_KEY configurada. Sem isso, retorna 503 em vez de quebrar
# o resto do app.
# ---------------------------------------------------------------------------

def _obter_ou_criar_cliente_asaas(conn, usuario_id: str, nome: str, documento: str, email: str) -> str:
    """
    Reaproveita o customer_id do Asaas se o usuário já tiver um — evita
    criar cliente duplicado a cada nova cobrança. O `documento` (CPF/CNPJ
    real) só é usado nesta chamada, pra criar o cliente no Asaas — nunca
    é persistido no nosso banco em texto puro (só o hash, em `usuarios.documento_hash`).
    """
    existente = conn.execute(
        "SELECT asaas_customer_id FROM clientes_asaas WHERE usuario_id = ?", (usuario_id,)
    ).fetchone()
    if existente:
        return existente["asaas_customer_id"]

    cliente_asaas = AsaasClient()
    resposta = cliente_asaas.criar_cliente(nome=nome, cpf_cnpj=documento, email=email)
    customer_id = resposta["id"]

    conn.execute(
        "INSERT INTO clientes_asaas (usuario_id, asaas_customer_id, criado_em) VALUES (?, ?, ?)",
        (usuario_id, customer_id, datetime.now(timezone.utc).isoformat()),
    )
    return customer_id


@app.post("/pagamentos/assinatura", status_code=status.HTTP_201_CREATED, tags=["pagamentos"])
def criar_assinatura(dados: CriarAssinaturaRequest, usuario_id: str = Depends(usuario_atual)):
    try:
        plano = PlanoAssinatura(dados.plano)
        valor = obter_valor_plano(plano)
    except (ValueError, ErroCobranca) as e:
        raise HTTPException(status_code=422, detail=str(e))

    with obter_conexao() as conn:
        usuario = conn.execute("SELECT id, email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if usuario is None:
            raise HTTPException(status_code=404, detail="usuário não encontrado")

        try:
            customer_id = _obter_ou_criar_cliente_asaas(
                conn, usuario_id, nome=usuario["email"], documento=dados.documento, email=usuario["email"],
            )
        except ErroIntegracaoAsaas as e:
            raise HTTPException(status_code=503, detail=f"Gateway de pagamento indisponível: {e}")

        proximo_vencimento = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        try:
            cliente_asaas = AsaasClient()
            assinatura_asaas = cliente_asaas.criar_assinatura(
                customer_id=customer_id, valor=valor,
                proximo_vencimento_iso=proximo_vencimento, tipo=dados.tipo_pagamento,
            )
        except ErroIntegracaoAsaas as e:
            raise HTTPException(status_code=503, detail=f"Gateway de pagamento indisponível: {e}")

        assinatura_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO assinaturas (id, usuario_id, plano, asaas_customer_id, asaas_subscription_id, status, criado_em) "
            "VALUES (?, ?, ?, ?, ?, 'pendente', ?)",
            (assinatura_id, usuario_id, plano.value, customer_id, assinatura_asaas["id"],
             datetime.now(timezone.utc).isoformat()),
        )

    return {
        "assinatura_id": assinatura_id, "valor": valor,
        "link_pagamento": assinatura_asaas.get("invoiceUrl") or assinatura_asaas.get("bankSlipUrl"),
        "status": "pendente",
    }


@app.post("/pagamentos/consulta-avulsa", status_code=status.HTTP_201_CREATED, tags=["pagamentos"])
def comprar_consulta_avulsa(dados: ComprarConsultaAvulsaRequest, usuario_id: str = Depends(usuario_atual)):
    """
    Pagamento único (sem assinatura) que libera UMA consulta real ao
    Serasa. Alternativa mais barata de entrada pra quem não quer
    compromisso mensal — preço fixo em PRECO_CONSULTA_AVULSA
    (app/core/billing.py), sempre acima do custo real da consulta
    (~R$16,06), garantindo margem.
    """
    with obter_conexao() as conn:
        usuario = conn.execute("SELECT id, email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if usuario is None:
            raise HTTPException(status_code=404, detail="usuário não encontrado")

        try:
            customer_id = _obter_ou_criar_cliente_asaas(
                conn, usuario_id, nome=usuario["email"], documento=dados.documento, email=usuario["email"],
            )
            cliente_asaas = AsaasClient()
            vencimento = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
            cobranca = cliente_asaas.criar_cobranca_unica(
                customer_id=customer_id, valor=PRECO_CONSULTA_AVULSA,
                vencimento_iso=vencimento, tipo=dados.tipo_pagamento,
            )
        except ErroIntegracaoAsaas as e:
            raise HTTPException(status_code=503, detail=f"Gateway de pagamento indisponível: {e}")

        credito_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO creditos_consulta_avulsa (id, usuario_id, asaas_payment_id, status, criado_em) "
            "VALUES (?, ?, ?, 'pendente', ?)",
            (credito_id, usuario_id, cobranca["id"], datetime.now(timezone.utc).isoformat()),
        )

    return {
        "credito_id": credito_id, "valor": PRECO_CONSULTA_AVULSA,
        "link_pagamento": cobranca.get("invoiceUrl"),
        "status": "pendente",
        "aviso": "Depois de pago, o crédito libera UMA consulta real em /score/diagnostico-serasa.",
    }


@app.post("/pagamentos/webhook", tags=["pagamentos"])
async def webhook_asaas(request: Request):
    """
    Recebe notificações do Asaas. Valida o token de autenticação
    configurado no painel deles (ver GUIA_APIS_E_SERVICOS_EXTERNOS.md) —
    NÃO usa assinatura HMAC porque a Asaas não oferece esse recurso hoje
    (confirmado na documentação oficial deles).
    """
    token_esperado = os.environ.get("ASAAS_WEBHOOK_TOKEN")
    if not token_esperado:
        raise HTTPException(status_code=503, detail="Webhook do Asaas não configurado neste ambiente.")

    token_recebido = request.headers.get("asaas-access-token")
    if not token_webhook_valido(token_recebido, token_esperado):
        raise HTTPException(status_code=401, detail="token de webhook inválido")

    payload = await request.json()
    evento = interpretar_webhook_pagamento(payload)

    if evento.tipo in (TipoEventoAsaas.PAGAMENTO_CONFIRMADO, TipoEventoAsaas.PAGAMENTO_RECEBIDO):
        with obter_conexao() as conn:
            # Pode ser pagamento de comissão de negociação...
            conn.execute(
                "UPDATE negociacoes SET comissao_paga = 1 WHERE asaas_payment_id = ?",
                (evento.asaas_payment_id,),
            )
            # ...ou de crédito de consulta avulsa (identificado pelo
            # payment_id específico daquela cobrança única, igual comissão)...
            conn.execute(
                "UPDATE creditos_consulta_avulsa SET status = 'pago' WHERE asaas_payment_id = ?",
                (evento.asaas_payment_id,),
            )
            # ...ou de assinatura (identificado pelo customer, já que a
            # cobrança recorrente gera um payment novo a cada ciclo, com
            # id diferente do subscription_id original).
            conn.execute(
                "UPDATE assinaturas SET status = 'ativa' WHERE asaas_customer_id = ?",
                (evento.asaas_customer_id,),
            )

    return {"detail": "recebido"}


@app.post("/negociacao/{negociacao_id}/cobrar-comissao", tags=["pagamentos"])
def cobrar_comissao_negociacao(negociacao_id: str, dados: CobrarComissaoRequest, usuario_id: str = Depends(usuario_atual)):
    """
    Gera a cobrança da comissão no Asaas — só pode ser chamado depois que
    a negociação está em BAIXA_CONFIRMADA (a mesma regra de
    Negociacao.calcular_comissao é respeitada aqui, não é contornada).
    """
    neg = _carregar_negociacao_do_usuario(negociacao_id, usuario_id)
    try:
        valor_comissao = neg.calcular_comissao()
    except ErroValidacaoNegociacao as e:
        raise HTTPException(status_code=422, detail=str(e))

    if valor_comissao <= 0:
        return {"detail": "Nenhuma comissão devida (sem desconto obtido nesta negociação)."}

    with obter_conexao() as conn:
        usuario = conn.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        try:
            customer_id = _obter_ou_criar_cliente_asaas(
                conn, usuario_id, nome=usuario["email"], documento=dados.documento, email=usuario["email"],
            )
            cliente_asaas = AsaasClient()
            vencimento = (datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat()
            cobranca = cliente_asaas.criar_cobranca_unica(
                customer_id=customer_id, valor=valor_comissao, vencimento_iso=vencimento, tipo="PIX",
            )
        except ErroIntegracaoAsaas as e:
            raise HTTPException(status_code=503, detail=f"Gateway de pagamento indisponível: {e}")

        conn.execute(
            "UPDATE negociacoes SET asaas_payment_id = ? WHERE id = ?", (cobranca["id"], negociacao_id)
        )

    return {
        "valor_comissao": valor_comissao,
        "link_pagamento": cobranca.get("invoiceUrl"),
        "pix_qr_disponivel_em": f"consulte o payment {cobranca['id']} no painel do Asaas",
    }


# ---------------------------------------------------------------------------
# Painel administrativo — acesso exclusivo a contas com is_admin=1.
# Não existe endpoint público para criar admin — ver _bootstrap_admin_se_configurado.
# ---------------------------------------------------------------------------

@app.get("/admin/usuarios", tags=["admin"])
def admin_listar_usuarios(limit: int = 50, _admin_id: str = Depends(admin_atual)):
    limit = min(max(limit, 1), 200)
    with obter_conexao() as conn:
        linhas = conn.execute(
            "SELECT id, email, criado_em, is_admin, tentativas_login_falhas, bloqueado_ate "
            "FROM usuarios ORDER BY criado_em DESC LIMIT ?",
            (limit,),
        ).fetchall()
    # nunca expõe documento_hash nem senha_hash — não há utilidade de suporte
    # nisso e é exatamente o tipo de dado que não deve viajar numa resposta HTTP
    return {
        "usuarios": [
            {
                "id": r["id"], "email": r["email"], "criado_em": r["criado_em"],
                "is_admin": bool(r["is_admin"]), "tentativas_login_falhas": r["tentativas_login_falhas"],
                "bloqueado_ate": r["bloqueado_ate"],
            }
            for r in linhas
        ]
    }


@app.get("/admin/auditoria", tags=["admin"])
def admin_listar_auditoria(limit: int = 50, usuario_id: str | None = None, _admin_id: str = Depends(admin_atual)):
    limit = min(max(limit, 1), 200)
    with obter_conexao() as conn:
        if usuario_id:
            linhas = conn.execute(
                "SELECT * FROM log_auditoria WHERE usuario_id = ? ORDER BY id DESC LIMIT ?",
                (usuario_id, limit),
            ).fetchall()
        else:
            linhas = conn.execute("SELECT * FROM log_auditoria ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return {
        "eventos": [
            {
                "usuario_id": r["usuario_id"], "timestamp": r["timestamp"],
                "score_anterior": r["score_anterior"], "score_novo": r["score_novo"],
                "payload": json.loads(r["payload_json"]),
            }
            for r in linhas
        ]
    }


@app.get("/admin/negociacoes", tags=["admin"])
def admin_listar_negociacoes(limit: int = 50, usuario_id: str | None = None, _admin_id: str = Depends(admin_atual)):
    limit = min(max(limit, 1), 200)
    with obter_conexao() as conn:
        if usuario_id:
            linhas = conn.execute(
                "SELECT * FROM negociacoes WHERE usuario_id = ? ORDER BY criado_em DESC LIMIT ?",
                (usuario_id, limit),
            ).fetchall()
        else:
            linhas = conn.execute("SELECT * FROM negociacoes ORDER BY criado_em DESC LIMIT ?", (limit,)).fetchall()
    return {
        "negociacoes": [
            {
                "id": r["id"], "usuario_id": r["usuario_id"], "credor": r["credor"],
                "valor_original": r["valor_original"], "valor_com_desconto": r["valor_com_desconto"],
                "status": r["status"], "criado_em": r["criado_em"],
            }
            for r in linhas
        ]
    }


@app.post("/admin/usuarios/{usuario_id_alvo}/forcar-reset-senha", tags=["admin"])
def admin_forcar_reset_senha(usuario_id_alvo: str, _admin_id: str = Depends(admin_atual)):
    """
    Uso de suporte: cliente ligou/mandou mensagem dizendo que perdeu acesso
    ao e-mail e não consegue usar o fluxo normal de 'esqueci minha senha'.
    O admin gera o token aqui e passa manualmente pro usuário (telefone,
    WhatsApp) depois de confirmar a identidade dele por outro canal.
    """
    with obter_conexao() as conn:
        existe = conn.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id_alvo,)).fetchone()
        if existe is None:
            raise HTTPException(status_code=404, detail="usuário não encontrado")

        token_bruto, registro = criar_token_reset(usuario_id=usuario_id_alvo)
        conn.execute(
            "INSERT INTO tokens_reset_senha (token_hash, usuario_id, criado_em, expira_em, usado) "
            "VALUES (?, ?, ?, ?, 0)",
            (registro.token_hash, registro.usuario_id, registro.criado_em.isoformat(), registro.expira_em.isoformat()),
        )
    return {"token": token_bruto, "expira_em": registro.expira_em.isoformat()}


@app.post("/admin/usuarios/{usuario_id_alvo}/desbloquear", tags=["admin"])
def admin_desbloquear_usuario(usuario_id_alvo: str, _admin_id: str = Depends(admin_atual)):
    with obter_conexao() as conn:
        existe = conn.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id_alvo,)).fetchone()
        if existe is None:
            raise HTTPException(status_code=404, detail="usuário não encontrado")
        conn.execute(
            "UPDATE usuarios SET tentativas_login_falhas = 0, bloqueado_ate = NULL WHERE id = ?",
            (usuario_id_alvo,),
        )
    return {"detail": "conta desbloqueada"}


@app.post("/admin/consulta-manual-serasa", tags=["admin"])
def admin_consulta_manual_serasa(dados: ConsultaManualAdminRequest, admin_id: str = Depends(admin_atual)):
    """
    Consulta manual ao Serasa, feita pelo admin em nome de alguém que
    ligou/mandou mensagem — modelo "escritório" tradicional, sem
    passar pelo cadastro/assinatura pública. Ainda usa o MESMO cache
    de 30 dias que o endpoint público (via _consultar_serasa_com_cache),
    então não gera custo duplicado se o CPF já foi consultado
    recentemente por qualquer via.

    Não tem trava de assinatura (é o admin quem decide cobrar ou não,
    por fora do sistema — ex: dinheiro na mão, Pix pessoal) — por isso
    fica restrito só ao admin, nunca exposto ao público.
    """
    resposta_crednet, fonte, dias_restantes = _consultar_serasa_com_cache(dados.documento, admin_id)

    score_atual = extrair_score(resposta_crednet)
    dividas = extrair_dividas_negativadas(resposta_crednet)
    consultas_recentes = extrair_consultas_recentes(resposta_crednet)
    probabilidade_inadimplencia = extrair_probabilidade_inadimplencia(resposta_crednet)

    with obter_conexao() as conn:
        inserir_log_auditoria(
            conn, admin_id, datetime.now(timezone.utc).isoformat(),
            score_atual or 0, score_atual or 0,
            json.dumps({
                "fonte": fonte, "tipo": "consulta_manual_admin",
                "documento_mascarado": mascarar_cpf(dados.documento),
                "observacao": dados.observacao,
            }, ensure_ascii=False),
        )

    return {
        "fonte": fonte,
        "dias_restantes_ate_nova_consulta_real": dias_restantes,
        "score": score_atual,
        "probabilidade_inadimplencia": probabilidade_inadimplencia,
        "dividas_negativadas": [
            {
                "credor": d.credor, "valor": d.valor, "dias_atraso": d.dias_atraso,
                "origem": d.origem,
            }
            for d in dividas
        ],
        "consultas_cpf_ultimos_30_dias": consultas_recentes,
        "aviso_legal": "Dado consultado em tempo real no birô. Uso interno — atendimento manual.",
    }


# Preço confirmado na tela de "Preços" do painel da conta do usuário na
# SOA Web Services (produto CREDNET) — não é estimativa, é o valor real
# cobrado por consulta no momento em que essa tela foi conferida.
PRECO_CONSULTA_CREDNET_REAIS = 16.06


@app.get("/admin/gastos-serasa", tags=["admin"])
def admin_gastos_serasa(_admin_id: str = Depends(admin_atual)):
    """
    Painel de controle de custo: cada linha em cache_consulta_serasa
    representa uma consulta CredNet que foi PAGA de verdade (o cache
    de 30 dias garante que reconsultas dentro da janela não geram
    nova linha nem novo custo — ver app/core/cache_score.py). Contar
    linhas dessa tabela é, portanto, uma contagem real de gasto, não
    uma estimativa de uso do endpoint.
    """
    with obter_conexao() as conn:
        total_consultas = conn.execute("SELECT COUNT(*) as c FROM cache_consulta_serasa").fetchone()["c"]
        consultas_30_dias = conn.execute(
            "SELECT COUNT(*) as c FROM cache_consulta_serasa WHERE consultado_em >= ?",
            ((datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),),
        ).fetchone()["c"]
        ultimas = conn.execute(
            "SELECT documento_hash, usuario_id, consultado_em FROM cache_consulta_serasa "
            "ORDER BY consultado_em DESC LIMIT 20"
        ).fetchall()

    return {
        "preco_unitario_crednet": PRECO_CONSULTA_CREDNET_REAIS,
        "total_consultas_pagas_historico": total_consultas,
        "gasto_total_estimado_historico": round(total_consultas * PRECO_CONSULTA_CREDNET_REAIS, 2),
        "consultas_ultimos_30_dias": consultas_30_dias,
        "gasto_estimado_ultimos_30_dias": round(consultas_30_dias * PRECO_CONSULTA_CREDNET_REAIS, 2),
        "ultimas_consultas": [
            {
                "documento_hash": u["documento_hash"][:12] + "...",  # nunca expõe o hash completo nem o CPF
                "usuario_id": u["usuario_id"],
                "consultado_em": u["consultado_em"],
            }
            for u in ultimas
        ],
    }
