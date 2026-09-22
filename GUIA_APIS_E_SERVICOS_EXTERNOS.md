# Guia de APIs e Serviços Externos — O Que Baixar, Criar e Contratar

Este é o mapa completo de **tudo que existe fora do código** — cada
conta, cada API, cada serviço que o sistema usa ou vai usar, o que já
está pronto e o que falta você mesmo providenciar. Organizado em 3
níveis, do que não exige nada até o que exige empresa aberta.

---

## Nível 0 — Já está resolvido no código, você não precisa criar nada

| O quê | Onde está no projeto |
|---|---|
| Motor de cálculo de score | `backend/app/core/score_engine.py` — roda 100% local, sem depender de nenhuma API externa |
| Validação de CPF/CNPJ | `backend/app/core/security.py` — algoritmo matemático, não consulta nenhum serviço |
| Chat de suporte | `backend/app/core/chat_suporte.py` — motor próprio por palavra-chave, sem IA externa |
| Autenticação, senha, sessão | Tudo local (JWT + hash de senha) — nenhum serviço terceiro envolvido |
| Banco de dados | SQLite, é um arquivo — não precisa instalar nem contratar nada |

---

## Nível 1 — Grátis, você mesmo cria agora, sem precisar de CNPJ

Essas são as contas que você já usa nos guias de instalação e deploy.
Nenhuma delas pede documento de empresa — só e-mail.

### 1.1 GitHub (guarda o código)
- **Criar em**: https://github.com/signup
- **Custo**: grátis
- **Pra que serve**: guardar o código-fonte e conectar com Render/Vercel pra deploy automático

### 1.2 Render (hospeda o backend)
- **Criar em**: https://render.com
- **Custo**: grátis no plano inicial (com a limitação de "dormir" após 15 min sem uso)
- **Pra que serve**: rodar a API (FastAPI) 24 horas por dia, acessível por uma URL pública

### 1.3 Vercel (hospeda o frontend, alternativa/complemento ao Render)
- **Criar em**: https://vercel.com
- **Custo**: grátis pra site estático
- **Pra que serve**: hospedar os arquivos HTML (`index.html`, `admin.html`, etc.)

### 1.4 Pluggy — Open Finance (sandbox)
- **Criar em**: https://dashboard.pluggy.ai
- **Custo**: grátis no sandbox — **liberado na hora, sem aprovação** (confirmei isso na documentação oficial deles antes de escrever este guia)
- **Pra que serve**: testar a conexão de Open Finance (extratos, cartão de crédito) com dados fictícios de banco, sem tocar em dinheiro/dado real
- **Onde plugar no código**: variáveis de ambiente `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET`, usadas em `backend/app/integrations/pluggy_client.py`
- **Importante**: sandbox é só pra testar o código. Pra conectar o banco de um usuário de verdade, você precisa do Nível 2.4 abaixo

### 1.5 Domínio próprio (opcional, mas recomendado)
- **Onde comprar (.com.br)**: https://registro.br — custo de ~R$40/ano, exige CPF (não precisa de CNPJ)
- **Onde comprar (.com genérico)**: Namecheap, GoDaddy — R$40 a R$80/ano
- **Pra que serve**: trocar `seu-app.onrender.com` por `www.seuapp.com.br` — mais profissional, mais fácil de divulgar
- Depois de comprar, tanto Render quanto Vercel têm um passo de "Add Custom Domain" no painel — é só apontar o domínio pra lá

### 1.6 Cloudflare (opcional — proteção extra contra ataque)
- **Criar em**: https://www.cloudflare.com (plano Free)
- **Custo**: grátis
- **Pra que serve**: fica na frente do seu domínio filtrando tráfego malicioso antes de chegar no seu servidor — já mencionado em `backend/SECURITY.md`

### 1.7 Sentry (opcional — monitoramento de erro)
- **Criar em**: https://sentry.io (plano Free)
- **Custo**: grátis até um certo volume de eventos
- **Pra que serve**: te avisa automaticamente (e-mail/celular) se o backend começar a dar erro em massa — útil pra notar um ataque em andamento

### 1.8 SendGrid — envio de e-mail real (para "esqueci minha senha")
- **Criar em**: https://sendgrid.com (plano Free: 100 e-mails/dia)
- **Custo**: grátis até 100 e-mails/dia, depois é pago
- **Pra que serve**: hoje `_enviar_email_reset_senha()` em `backend/app/main.py` só imprime no console — pra virar e-mail de verdade, você cria conta aqui, pega uma API Key, e troca aquela função pra chamar a API do SendGrid
- **Alternativas**: AWS SES (mais barato em volume alto, mas configuração mais técnica), Postmark (mais caro, mais simples)

### 1.9 Gateway de pagamento — como você recebe o dinheiro de verdade
Isso é uma peça que faltava no guia: nem a assinatura (R$19,90/mês) nem
a comissão de negociação caem na sua conta por mágica — precisa de um
gateway de pagamento processando Pix/boleto/cartão em nome do seu CNPJ.

- **Recomendado pra esse caso — Asaas**: https://www.asaas.com — forte
  em cobrança recorrente (assinatura) e boleto/Pix, comum entre SaaS e
  prestadores de serviço brasileiros. Taxas aproximadas: ~2,99% no
  cartão, R$0,49 no Pix, R$1,99 no boleto compensado (varia por
  volume/negociação)
- **Alternativas**: Pagar.me (forte em split de pagamento pra
  marketplace, mas com limitação de recorrência em alguns planos),
  Mercado Pago (ecossistema mais popular, bom pra split também), Stripe
  (se algum dia expandir pra cobrança internacional)
- **Pré-requisito**: CNPJ ativo + conta bancária PJ vinculada — se você
  já tem CNPJ LTDA, isso é só abrir a conta no gateway escolhido e
  vincular a conta bancária da empresa
- **Onde plugar no código**: ainda não implementado neste pacote — o
  `modelo_negocios_monetizacao.md` documenta as regras de cobrança
  (comissão só após confirmação, assinatura mensal), mas a integração
  técnica com o gateway escolhido é o próximo passo de desenvolvimento,
  não algo que já está no `backend/app/`

---

## Nível 2 — Precisa de empresa aberta (CNPJ) e/ou contrato comercial

Isso é o que separa "sistema funcionando com dado de teste" de "sistema
operando com dado real de crédito de gente de verdade". Nenhum desses
tem um botão de "criar conta e pegar API key" simples — todos exigem
processo comercial.

### 2.1 Abrir o CNPJ (pré-requisito pra quase tudo abaixo)
- Você precisa de um contador pra abrir a empresa — não é um passo que se faz sozinho num site
- Tipo de empresa comum pra esse negócio: sociedade limitada (LTDA) ou, se for só você, SLU (Sociedade Limitada Unipessoal)
- **Isso não é opcional** se você quer negociar dívida em nome de clientes ou receber comissão de parceiros financeiros — o mercado de crédito exige CNPJ pra qualquer contrato B2B

### 2.2 Pluggy — Open Finance (produção)
- Depois de ter CNPJ, você cria uma "aplicação de produção" dentro do mesmo painel do sandbox (dashboard.pluggy.ai)
- **Custo**: têm planos pagos por volume (não divulgam preço público — é sob consulta comercial)
- **O que muda no código**: nada — é a mesma API, só troca de credencial de sandbox pra produção

### 2.3 Birôs de crédito — Serasa Experian, Quod, Boa Vista
Aqui não existe "criar conta e pegar chave" — é sempre contrato comercial.
Dois caminhos possíveis:

**Caminho A — direto com o birô**
- Serasa Experian: portal de desenvolvedor em https://developer.serasaexperian.com.br — mas o acesso real de API só libera depois de contrato comercial (o portal serve pra consultar documentação e pedir contato de vendas)
- Quod e Boa Vista: processo parecido — precisa entrar em contato com o time comercial de cada um
- **Isso demora** — geralmente semanas de negociação, análise de compliance da sua empresa, e costuma exigir volume mínimo de consultas mensais

**Caminho B — via revendedor/parceiro (mais rápido pra começar pequeno)**
- Empresas como SOA Web Services e Connect S/A revendem acesso à API da Serasa sem você precisar negociar direto com a Serasa
- Custo por consulta, sem contrato de volume mínimo tão alto — mais acessível pra fase inicial
- Isso é uma alternativa real e usada por muitas fintechs pequenas no Brasil pra não travar o produto esperando contrato direto

### 2.4 Open Finance — conectar banco de usuário real
Depois que sua Pluggy estiver em produção (2.2), o usuário final ainda
precisa conseguir autorizar a conexão com o banco dele — isso já é
coberto pela própria Pluggy (ela é uma Iniciadora de Transação de
Pagamento regulada pelo Banco Central), então não tem um passo adicional
seu aqui além de estar em produção.

### 2.5 Correspondente bancário / parceria de crédito (marketplace)
Se você quiser que bancos/fintechs parceiros paguem comissão pelos leads
do seu marketplace (`docs/esteira_credito_pre_qualificado.md`), isso
também é contrato comercial direto com cada parceiro — não existe
"cadastro de API" pra isso. Normalmente começa por indicação/network ou
participando de eventos do setor (ex: Febraban Tech).

---

## Resumo — se você JÁ TEM CNPJ (LTDA), como é o seu caso

Isso já resolve o problema de enquadramento que eu tinha levantado
antes: o MEI tem uma lista fechada de atividades permitidas, e
Correspondente Bancário (CNAE 6619-3/02) está fora dela — mas essa
restrição é **só do MEI**. Uma LTDA pode registrar praticamente
qualquer CNAE, incluindo esse. Ainda vale confirmar com seu contador
qual CNAE exato descreve melhor o seu serviço (negociação de dívida
assistida é diferente de correspondente bancário formal — o contador
sabe qual se aplica), mas você não está mais travado pela restrição de
regime que travaria um MEI.

```
JÁ FEITO (segundo você):
  ✓ CNPJ LTDA aberto
  ✓ Conta no GitHub
  ✓ Conta no Vercel

FALTA — infraestrutura (grátis/rápido, faça primeiro):
  → Conta no Render                → hospedar o backend (Vercel não é bom pra isso, ver Parte 9 do GUIA_COMPLETO_VSCODE_AO_AR.md)
  → Variáveis de ambiente no Render → JWT_SECRET_KEY, ADMIN_BOOTSTRAP_*, CORS_ALLOWED_ORIGINS
  → SendGrid                       → e-mail de "esqueci senha" de verdade
  → Domínio próprio (opcional)     → pode registrar em nome da empresa agora

FALTA — dinheiro de verdade (precisa integrar, ver 1.9 acima):
  → Conta em gateway de pagamento (Asaas recomendado) → receber assinatura/comissão
  → Integração técnica do gateway no backend            → ainda não existe no código, é próximo passo

FALTA — dado real de crédito (agora liberado, mas ainda leva tempo):
  → Pluggy produção                → já pode aplicar, tem CNPJ
  → Contato comercial com birô     → inicia a conversa agora, mas negociação ainda leva semanas
```

## O que isso significa pro seu lançamento

Você **pode** lançar o app agora, no Lançamento 1 apenas — as pessoas
se cadastram, o app funciona ponta a ponta com o motor de score e o
plano de ação, e a parte de dívida mostra as opções **gratuitas** de
negociação (Serasa Limpa Nome, negociar direto com o credor). Isso já
entrega valor real: diagnóstico completo, plano de ação com prazo,
orientação de onde resolver cada pendência — sem cobrar nada e sem
precisar de CNPJ.

O Lançamento 2 é o que adiciona duas coisas de uma vez: puxar dado
automaticamente do banco/birô do usuário (em vez dele digitar), e
cobrar comissão pela negociação assistida. As duas dependem de CNPJ e
negociação comercial — não são um passo de fim de semana, então não
precisam travar o lançamento inicial.
