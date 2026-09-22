# SECURITY.md — Postura de Segurança do Backend

## Resumo do que está implementado neste pacote

| Área | O que foi feito | Onde |
|---|---|---|
| Hash de senha | PBKDF2-HMAC-SHA256, 600.000 iterações (recomendação OWASP 2023+), salt único de 16 bytes por senha | `app/core/security.py` |
| Comparação de senha | Tempo constante (`hmac.compare_digest`) — evita timing attack | `app/core/security.py` |
| Autenticação | JWT (HS256), access token de 15 min + refresh token de 7 dias | `app/auth.py` |
| Segredo do JWT | Obrigatoriamente vindo de variável de ambiente — a aplicação **recusa subir** sem `JWT_SECRET_KEY` definida | `app/auth.py` |
| SQL Injection | Todas as queries usam parâmetros (`?`), nunca concatenação de string | `app/database.py` |
| Validação de entrada | Pydantic valida tipo, faixa e formato de todo dado recebido antes de chegar na lógica de negócio | `app/schemas.py` |
| Validação de e-mail | `EmailStr` do Pydantic — rejeita formato inválido antes de qualquer processamento | `app/schemas.py` |
| Validação de CPF/CNPJ | Algoritmo oficial de dígito verificador — rejeita documentos inválidos antes de processar | `app/core/security.py` |
| **XSS armazenado (corrigido nesta auditoria)** | Campos de texto livre digitados pelo usuário (`credor`) nunca aceitam `<` ou `>` no backend (regex `^[^<>]*$`), **e** todo valor vindo da API é escapado antes de entrar via `innerHTML` no frontend (`escaparHtml()`) — duas camadas independentes | `app/schemas.py`, `frontend/admin.html`, `frontend/index.html` |
| Dados sensíveis em log | CPF nunca gravado em texto puro — hash para persistência, máscara (`123.***.**-45`) para logs legíveis | `app/core/security.py`, `app/main.py` |
| Autorização por recurso | Toda rota de negociação verifica se o recurso pertence ao usuário do token — usuário A não acessa negociação de usuário B (testado em `test_api.py`) | `app/main.py` |
| User enumeration | Login e recuperação de senha retornam a mesma mensagem para "não existe" e "está errado" | `app/main.py` |
| Rate limiting geral | 30 requisições/minuto por IP (lógica testada, `app/core/rate_limiter.py`, 8 testes) | `app/main.py` |
| Rate limiting reforçado para auth | 8 requisições/minuto por IP, específico para `/auth/login`, `/auth/cadastro`, `/auth/esqueci-senha` — reduz força bruta e spam de cadastro | `app/main.py` |
| Proteção contra payload gigante | Corpo de requisição maior que 1 MB é rejeitado (413) antes de processar | `app/main.py` |
| CORS | Lista explícita de origens permitidas — nunca `*` | `app/main.py` |
| Headers de segurança | `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy` em toda resposta; `Cache-Control: no-store` em rotas de auth/admin | `app/main.py` |
| Regra de negócio como código | Comissão de negociação só pode ser calculada com status `BAIXA_CONFIRMADA` — reforçado no código, não só na documentação | `app/core/negociacao.py` |
| Chat de suporte | Motor próprio de classificação de intenção por palavra-chave — nenhuma chamada a API externa, nenhum custo por mensagem, nenhuma chave de terceiro exposta | `app/core/chat_suporte.py` (19 testes) |
| Bloqueio de conta | Após 5 tentativas de senha incorretas, a conta trava por 15 minutos | `app/core/account_lockout.py` (7 testes) |
| Painel administrativo | Endpoints `/admin/*` exigem `is_admin=1` checado no banco a cada requisição — revogar admin de alguém funciona imediatamente. Não existe endpoint público para criar um admin | `app/auth.py` (`admin_atual`) |
| Negociações persistidas | Migradas de memória para a tabela `negociacoes` real — sobrevivem a reinício do servidor | `app/main.py` |
| Recuperação de senha | Token de uso único, hash SHA-256 armazenado, validade de 30 min | `app/core/password_reset.py` |
| Cobrança (Asaas) | Webhook validado por token de autenticação (comparação em tempo constante) — Asaas não oferece HMAC ainda, confirmado na doc oficial antes de implementar. Comissão só é cobrada depois de `BAIXA_CONFIRMADA`, reforçado em código | `app/core/billing.py` (13 testes), `app/integrations/asaas_client.py` |
| Consulta real de score/dívida (Serasa via SOA Web Services) | Score e dívidas negativadas extraídos de resposta real do CredNet (JSON de homologação da conta do usuário, não inventado) — adaptador testado (29 testes) | `app/core/serasa_adapter.py`, `app/integrations/serasa_client.py` |
| Cache de consulta ao birô (proteção de margem) | Cada consulta CredNet custa ~R$16 — resultado é cacheado por 30 dias por documento, testado com SQLite real (UPSERT confirmado não duplicar linha) | `app/core/cache_score.py` (6 testes), `tests/test_database.py` (3 testes de UPSERT) |
| Controle de gasto real com o Serasa | `/admin/gastos-serasa` conta consultas pagas de verdade (baseado no cache, nunca duplica contagem) e estima o custo total — testado com dado temporal real | `app/main.py`, `tests/test_database.py::TestContagemDeGastosSerasa` |
| Trava de custo por assinatura | `/score/diagnostico-serasa` (consulta real ao birô, ~R$16/chamada) exige assinatura Plus/Premium **ativa** — sem isso, retorna 402 antes de gastar qualquer dinheiro. Impede conta gratuita gerar custo sem receita — testado com SQLite real (5 testes) | `app/database.py::possui_assinatura_ativa`, `app/main.py` |
| Consulta avulsa (sem assinatura) | Pagamento único de R$24,90 libera uma consulta real — preço testado pra sempre ficar acima do custo real (~R$16,06), garantindo margem. Crédito é de uso único, consumido só quando a consulta de fato acontece | `app/core/billing.py`, `app/database.py::possui_credito_avulso_disponivel`/`consumir_credito_avulso` (7 testes com SQLite real) |
| Consulta manual do admin (estilo escritório) | `/admin/consulta-manual-serasa` — consulta o birô em nome de quem ligou/mandou mensagem, sem exigir cadastro/assinatura do cliente. Usa o MESMO cache de 30 dias do endpoint público, então não duplica custo se o CPF já foi consultado por qualquer via. Restrito ao admin (nunca exposto ao público) | `app/main.py`, `frontend/admin.html` (aba "Consulta Manual") |
| Erro de integração Serasa nunca expõe dado bruto ao cliente | `resp.text` da API nunca sobe até o usuário final via `HTTPException` — fica só em log do servidor, e mesmo aí a senha é mascarada antes de logar (defesa contra a API ecoar a requisição de volta num erro) | `app/integrations/serasa_client.py` (9 testes) |

## Vulnerabilidade real encontrada e corrigida nesta auditoria

**XSS armazenado no painel administrativo.** O código anterior inseria `email` (do cadastro de usuário) e `credor` (nome digitado livremente ao criar uma negociação) direto via `innerHTML` nas tabelas de `admin.html`. Como esses dois campos são preenchidos por qualquer usuário do sistema — não só pelo admin — alguém poderia ter cadastrado uma conta com um e-mail contendo `<script>` (tecnicamente inválido como e-mail, mas o campo não validava formato antes) ou criado uma negociação com um nome de credor malicioso, e esse script executaria **no navegador do administrador** na próxima vez que ele abrisse o painel — um clássico "stored XSS" que rouba a sessão de quem tem mais privilégio no sistema.

Corrigido em duas camadas independentes (defesa em profundidade — mesmo se uma falhar, a outra segura):
1. **Backend**: `credor` agora rejeita `<` e `>` na validação (Pydantic `pattern`); `email` agora usa `EmailStr`, que valida formato real
2. **Frontend**: toda inserção via `innerHTML` em `admin.html` e `index.html` passa por `escaparHtml()`, que usa `textContent` do DOM pra neutralizar qualquer tag antes de virar HTML

## O que ainda falta — separado em duas categorias diferentes

Isso é importante: **nem tudo que falta é código**. Algumas coisas só
uma ação sua no mundo real resolve — nenhuma linha de código muda isso,
por mais que eu escreva. Separei as duas categorias pra ficar claro
onde cada pendência realmente mora.

### Categoria A — Era código, e AGORA ESTÁ RESOLVIDO nesta rodada

| Item | O que foi feito |
|---|---|
| Histórico de negociação | Antes só o status atual persistia. Agora cada transição vira uma linha na tabela `negociacao_eventos`, com timestamp — testado com SQLite real (6 testes, `tests/test_database.py`), não é mock |
| Envio de e-mail | Antes era só um `print()`. Agora chama a API real do SendGrid (`app/integrations/sendgrid_client.py`) — se a chave não estiver configurada, cai de volta pro log, sem quebrar o resto do app |
| Rate limiter distribuído | Implementado (`app/core/rate_limiter_redis.py`), pronto pra usar quando você tiver mais de uma instância do backend — ver Categoria B abaixo sobre por que não é o padrão ativo |
| Caminho do banco configurável (disco persistente) | `DATABASE_PATH` (variável de ambiente) permite apontar o SQLite pro disco persistente do Render, evitando que o banco resete a cada reinício do serviço no plano free/sem disco — testado (3 testes, `TestResolverCaminhoBanco`). Sem a variável, comportamento local não muda em nada |

### Categoria B — Ainda é código, mas com uma ressalva honesta

| Item | Por que não dá pra marcar 100% concluído |
|---|---|
| Rate limiter Redis | O código está escrito e a parte que não depende de rede está testada, mas a chamada real ao Redis não pôde ser testada aqui (não há servidor Redis neste ambiente). Por isso o rate limiter em memória continua sendo o ativo por padrão em `app/main.py` — trocar por Redis sem poder testar a troca seria arriscado num componente de segurança |
| Integração Asaas / Pluggy | O cliente HTTP de cada um está escrito seguindo a documentação oficial (confirmada antes de escrever), mas nenhuma chamada de rede real foi testada aqui — teste no sandbox de cada um antes de usar com dinheiro/dado real |
| PostgreSQL em vez de SQLite | Não reescrevi isso nesta rodada — trocar de banco é uma migração de dado real (exportar, importar, validar integridade), não só trocar uma linha de código, e eu não tenho um Postgres real pra testar essa migração aqui. `app/database.py` já isola todo acesso a banco num só arquivo, o que torna essa troca localizada quando for feita |

### Categoria C — NÃO é código, é um processo do mundo real que só você resolve

Nenhuma quantidade de código fecha esses itens. Marcá-los como "concluído"
seria mentira, então não vou fazer isso:

- **Contrato com birô de crédito (Serasa/Quod/Boa Vista)** — não existe API pública documentada pra isso, é sempre negociação comercial direta ou via revendedor (ver `GUIA_APIS_E_SERVICOS_EXTERNOS.md`). Isso não é uma tarefa de programação, é uma reunião de vendas que só você (ou seu time comercial) pode fazer
- **Pentest profissional** — precisa de uma pessoa ou empresa especializada rodando ataques controlados contra o sistema no ar. Eu posso (e já fiz) auditoria de código; um pentest de verdade testa o sistema publicado, em produção, com ferramentas que simulam ataque real
- **Cofre de segredos gerenciado** (AWS Secrets Manager, Vault) — é uma decisão de qual serviço de nuvem contratar e como configurá-lo, não uma função Python. O código já lê tudo de variável de ambiente, que é compatível com qualquer cofre que você escolher depois
- **WAF/Cloudflare, backup do banco, monitoramento de erro (Sentry)** — são contas e configurações que você cria fora do código, listadas em detalhe na seção seguinte

## Notas específicas sobre a integração Serasa (CredNet)

- **`tempo_relacionamento_credito_meses` e `quantidade_tipos_credito_ativos` usam valores conservadores (0 e 1)** — o retorno do CredNet que vimos até agora não tem um campo claro pra esses dois dados. Se a documentação completa da SOA tiver esses campos em outro lugar (ex: dentro de `sinteseCadastral` ou outro endpoint), me avise e eu ajusto o adaptador.
- **URL de produção confirmada**: `https://producao.soawebservices.com.br` — achada direto no dropdown da própria documentação da SOA (a caixa "Server" tinha 3 opções escondidas). Configure `SOA_AMBIENTE=producao` quando for usar de verdade.
- **O campo `"adicionais": [1]`** no corpo da requisição foi copiado do exemplo da própria documentação deles — não sabemos ainda o que esse código representa exatamente (parece ser um seletor de informações extras a incluir na consulta). Vale confirmar com o suporte antes de operar em produção, caso o valor `1` não seja o que você espera.
- **Autenticação é login/senha no corpo, não uma chave de API** — diferente de Pluggy e Asaas. Isso significa que `SOA_SENHA` precisa ser tratada com o mesmo cuidado que qualquer senha de conta (nunca commitada no código, sempre variável de ambiente).

## Notas específicas sobre o painel administrativo e o PWA

Isso é informação sobre o código que construí, não recomendação genérica —
por isso fica separado da lista de infraestrutura abaixo:

- **`admin.html` não tem nenhuma proteção de rede** — ele é servido publicamente junto com o resto do frontend (qualquer um pode abrir a URL). A segurança real está inteiramente no backend: sem ser admin no banco, os endpoints `/admin/*` retornam 403.
- **Bootstrap de admin via variável de ambiente é single-shot.** Depois de criar o primeiro admin, `ADMIN_BOOTSTRAP_EMAIL`/`ADMIN_BOOTSTRAP_SENHA` não fazem mais nada (o código não promove uma conta já existente) — remova-as do Render depois do primeiro deploy.
- **Instalabilidade do app admin (PWA) não é uma barreira de segurança — é só conveniência de acesso.** Qualquer visitante que abra `admin.html` recebe o mesmo evento `beforeinstallprompt` do navegador; isso acontece antes de qualquer login, é assim que todo PWA funciona. O que protege de fato: o botão "Instalar app" só é revelado depois que o backend confirma que a conta é admin, e mesmo instalado, o app não faz nada sem login válido de admin (403 em `/admin/*`).

## Recomendações de infraestrutura (não é código — é configuração da hospedagem)

Estas não estão implementadas neste pacote porque são decisões de infraestrutura, não de código-fonte. Mas são igualmente importantes contra ataques cibernéticos, e vale aplicá-las antes de divulgar o sistema:

- **WAF / proteção DDoS na frente da API** — considere colocar o Cloudflare (plano gratuito já ajuda muito) na frente do domínio, tanto pelo frontend quanto pelo backend. Isso filtra boa parte de tráfego malicioso antes de chegar no seu servidor.
- **HTTPS obrigatório** — Render e Vercel já servem com HTTPS automaticamente e redirecionam HTTP → HTTPS por padrão; confirme que isso está ativo antes de divulgar a URL.
- **Backup do banco de dados** — o SQLite (`dados_app.db`) hoje não tem backup automático. Enquanto estiver em SQLite, programe um backup manual periódico (copiar o arquivo) até migrar para um banco gerenciado com backup automático (Postgres no Render/Supabase, por exemplo).
- **Monitoramento de dependências vulneráveis** — rode `pip install pip-audit && pip-audit` periodicamente (ou configure o Dependabot do GitHub, que já roda isso automaticamente em repositórios públicos e privados) pra saber quando uma biblioteca usada aqui (FastAPI, python-jose, etc.) tiver uma vulnerabilidade conhecida corrigida numa versão mais nova.
- **Alertas de erro em produção** — considere um serviço como Sentry (tem plano gratuito) pra ser avisado automaticamente se o backend começar a gerar erros 500 em massa — isso costuma ser o primeiro sinal visível de um ataque em andamento (ex: tentativa de SQL injection gerando exceção, scanner automatizado testando endpoints inexistentes).
- **Revisão periódica dos logs de acesso** do Render/Vercel — picos anormais de tráfego de um mesmo IP, ou muitas respostas 401/403 em sequência, são sinais de tentativa de invasão em andamento.

## LGPD — pontos de atenção específicos

- O schema de `consentimentos` em `app/database.py` já prevê `concedido_em` e `revogado_em` — a lógica de aplicação (bloquear consultas a fontes cujo consentimento foi revogado) precisa ser implementada antes de conectar qualquer fonte real de dados.
- Direito de exclusão (art. 18 da LGPD): não há endpoint de exclusão de conta implementado neste pacote — precisa ser adicionado, com exclusão em cascata de negociações e logs, antes de operar com usuários reais.
- Nenhum dado é usado para decisão automatizada de crédito — isso é uma decisão de arquitetura deliberada que reduz a exposição ao art. 20 da LGPD (ver `docs/arquitetura_dados.md`).

## Como testar a segurança localmente

```bash
# Testes de lógica de negócio (rodam sem nenhuma dependência instalada)
python3 -m unittest discover -s tests -v

# Testes de API (após pip install -r requirements.txt)
pytest tests/test_api.py -v

# Checagem estática de tipos (opcional, recomendado)
pip install mypy --break-system-packages
mypy app/
```
