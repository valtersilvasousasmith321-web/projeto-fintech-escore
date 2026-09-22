# Guia Completo — Do VS Code até o Ar

Passo a passo único, na ordem certa, do zero até o sistema publicado. Cada
passo tem o comando exato e o que você deve ver de resultado, pra você
saber se deu certo antes de ir pro próximo.

**Tempo estimado total**: 2 a 3 horas na primeira vez (a maior parte é
espera de download/build, não trabalho manual).

---

## PARTE 1 — Abrir o projeto no VS Code

### 1.1 Extrair o zip

Extraia `projeto-fintech-score.zip` em um lugar fácil de achar, por
exemplo `C:\Projetos\projeto-fintech-score`.

### 1.2 Abrir no VS Code

Abra o VS Code → **Arquivo** → **Abrir Pasta** → selecione a pasta
`projeto-fintech-score` (a de fora, que contém `backend/`, `frontend/`,
`docs/` etc.).

### 1.3 Instalar a extensão Python (se ainda não tiver)

No VS Code, vá na aba de Extensões (ícone de blocos na barra lateral,
ou `Ctrl+Shift+X`), busque **"Python"** (da Microsoft) e clique em
**Instalar**. Isso te dá realce de sintaxe, autocompletar, e o botão de
"Run" nos arquivos `.py`.

### 1.4 Abrir o terminal integrado

`Ctrl + '` (crase) ou menu **Terminal** → **Novo Terminal**. Todos os
comandos abaixo rodam **dentro desse terminal**, não no CMD do Windows
separado.

Confirme que o terminal abriu como **PowerShell** (é o padrão do VS
Code no Windows) — o prompt deve terminar em `PS C:\...>`.

---

## PARTE 2 — Verificar o Python instalado

```powershell
python --version
```

**Esperado**: algo como `Python 3.11.x` ou mais novo.

**Se der erro** ("não é reconhecido"): baixe em
https://www.python.org/downloads/ — na instalação, **marque a caixa
"Add python.exe to PATH"** antes de clicar em Install. Depois, feche e
reabra o VS Code inteiro (não só o terminal) e repita o comando.

---

## PARTE 3 — Validar a lógica de negócio (sem instalar nada ainda)

Isso prova que o núcleo do sistema (cálculo de score, negociação,
segurança) está correto, antes de você instalar qualquer dependência.

```powershell
cd backend
python -m unittest discover -s tests -v
```

**Esperado**: várias linhas terminando em `ok`, e no final:

```
Ran 128 tests in 1.4s
FAILED (errors=1)
```

O `FAILED (errors=1)` **é esperado nesta etapa** — é só o `test_api`
avisando que falta instalar `fastapi`/`pytest`, o que resolvemos na
Parte 4. Se aparecer qualquer outro erro além desse, pare e me avise.

---

## PARTE 4 — Criar o ambiente virtual e instalar as dependências

Ainda dentro de `backend`:

```powershell
python -m venv venv
```

Isso cria uma pasta `venv/` — demora alguns segundos.

```powershell
venv\Scripts\activate
```

**Esperado**: o prompt do terminal muda para começar com `(venv)`.
Se aparecer um erro de "política de execução" (`cannot be loaded
because running scripts is disabled`), rode isto uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Confirme com `S` (sim) quando perguntado, depois repita
`venv\Scripts\activate`.

Com `(venv)` aparecendo, instale as dependências:

```powershell
pip install -r requirements.txt
```

Demora 1 a 2 minutos. **Esperado**: várias linhas de `Successfully
installed ...` no final, sem `ERROR`.

---

## PARTE 5 — Rodar o backend localmente

Ainda com `(venv)` ativo, gere e defina a chave secreta:

```powershell
$env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Marque também que está em ambiente de desenvolvimento (isso deixa o
token de "esqueci senha" visível na resposta da API, só pra facilitar
teste local):

```powershell
$env:APP_ENV = "dev"
```

Agora suba a API:

```powershell
uvicorn app.main:app --reload --port 8000
```

**Esperado**: várias linhas terminando em algo como
`Application startup complete.` e `Uvicorn running on http://127.0.0.1:8000`.

**Deixe esse terminal rodando** — não feche. Abra o navegador em:

```
http://localhost:8000/docs
```

**Esperado**: uma página com o título "Score Transparente & Plano de
Evolução de Crédito — API" e a lista de todos os endpoints. Se isso
apareceu, seu backend está funcionando.

---

## PARTE 6 — Rodar os testes completos de API

Abra **um segundo terminal** no VS Code (ícone de `+` na aba do
terminal, ou `Ctrl + Shift + '`) — deixe o primeiro com o `uvicorn`
rodando.

No terminal novo:

```powershell
cd backend
venv\Scripts\activate
pytest tests\test_api.py -v
```

**Esperado**: todas as linhas terminando em `PASSED`, e no final
`== X passed in Y.Ys ==` sem nenhum `FAILED`.

---

## PARTE 7 — Testar o frontend local, conectado no backend local

Os arquivos HTML já vêm configurados para `http://localhost:8000` por
padrão — não precisa mudar nada agora.

No VS Code, clique com o botão direito em `frontend/index.html` no
painel de arquivos → **Copiar Caminho** (ou simplesmente dê duplo-clique
nele no Explorer do Windows depois de achar a pasta). Isso abre no seu
navegador padrão.

**Teste o fluxo completo**:
1. Clique em "Não tenho conta — cadastrar", preencha com um CPF válido
   (ex: `111.444.777-35` é um CPF de teste com dígito verificador
   correto), um e-mail, e uma senha com 8+ caracteres
2. Volte pro login e entre com esse e-mail/senha
3. **Esperado**: aparece o Dashboard com o score de exemplo (530) e os
   5 fatores detalhados

Se aparecer erro de "Failed to fetch", confirme que o terminal da Parte
5 (com o `uvicorn`) ainda está rodando.

**Teste o painel admin também** — mas antes, você precisa criar a conta
de admin (isso só é possível via variável de ambiente, nunca por
cadastro público, de propósito). Pare o `uvicorn` (`Ctrl+C` no terminal
dele) e suba de novo assim:

```powershell
$env:ADMIN_BOOTSTRAP_EMAIL = "seu-email-admin@exemplo.com"
$env:ADMIN_BOOTSTRAP_SENHA = "umaSenhaForte123"
uvicorn app.main:app --reload --port 8000
```

Abra `frontend/admin.html` no navegador e entre com esse e-mail/senha.
**Esperado**: painel escuro com as abas Usuários, Auditoria,
Negociações, populado com os dados de teste que você criou na Parte 7.

---

## PARTE 8 — Subir o código pro GitHub

### 8.1 Instalar o Git (se ainda não tiver)

```powershell
git --version
```

Se der erro, baixe em https://git-scm.com/downloads (aceite as opções
padrão da instalação).

### 8.2 Criar o repositório no GitHub

Acesse https://github.com/new no navegador:
- **Repository name**: `projeto-fintech-score` (ou o nome que preferir)
- Deixe **Private** marcado se não quiser que o código fique público
- Não marque nenhuma opção de "Initialize with README" (o projeto já tem um)
- Clique em **Create repository**

### 8.3 Enviar o código

De volta no VS Code, num terminal na **pasta raiz do projeto** (não
dentro de `backend`):

```powershell
cd ..
git init
git add .
git commit -m "primeira versão do sistema"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/projeto-fintech-score.git
git push -u origin main
```

Na primeira vez, o GitHub vai abrir uma janela pra você autenticar —
siga o que aparecer na tela (login pelo navegador).

**Esperado**: linhas de progresso de upload, terminando sem erro.
Atualize a página do repositório no navegador — os arquivos devem
aparecer lá.

**Importante**: o arquivo `.gitignore` em `backend/` já impede que
`venv/` e `dados_app.db` sejam enviados — isso é intencional, esses
arquivos não devem ir pro GitHub.

---

## PARTE 9 — Publicar o backend no Render

1. Crie conta gratuita em https://render.com (pode entrar direto com GitHub)
2. **New** → **Web Service** → conecte o repositório `projeto-fintech-score`
3. Configure:

| Campo | Valor |
|---|---|
| **Root Directory** | `backend` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Starter` (plano pago, a partir de ~US$7/mês — necessário pro disco persistente, ver 9.1 abaixo. **Não use `Free`**: ele apaga o banco de dados a cada reinício) |

4. Em **Environment Variables**, adicione:

| Nome | Valor |
|---|---|
| `JWT_SECRET_KEY` | gere de novo: `python -c "import secrets; print(secrets.token_urlsafe(64))"` — use uma chave DIFERENTE da que você usou localmente |
| `APP_ENV` | `production` |
| `ADMIN_BOOTSTRAP_EMAIL` | seu e-mail de admin de produção |
| `ADMIN_BOOTSTRAP_SENHA` | uma senha forte, diferente da que você testou localmente |
| `CORS_ALLOWED_ORIGINS` | deixe `http://localhost:3000` por enquanto — voltamos aqui na Parte 11 |
| `ASAAS_API_KEY` | sua chave de API do Asaas (painel Asaas → Integrações → Chaves de API) |
| `ASAAS_SANDBOX` | `true` pra testar com dinheiro fictício antes de cobrar de verdade |
| `ASAAS_WEBHOOK_TOKEN` | gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"` e cole esse MESMO valor na configuração de webhook do painel Asaas (Integrações → Webhooks → Token de autenticação, header `asaas-access-token`) |
| `SOA_EMAIL` | o e-mail que você usa pra logar no painel soawebservices.com.br |
| `SOA_SENHA` | a senha da sua conta lá (trate como senha de banco — nunca comite no código) |
| `SOA_AMBIENTE` | `homologacao` (padrão, mais seguro pra testar) ou `producao` (quando quiser gastar seu saldo de verdade) — muda automaticamente pra `https://producao.soawebservices.com.br`, já confirmada |
| `DATABASE_PATH` | `/var/data/dados_app.db` — só funciona depois de anexar o disco persistente, ver passo 9.1 logo abaixo |

5. **Create Web Service** e acompanhe o log de build. Ao final, você
   recebe uma URL: `https://SEU-APP.onrender.com`

6. Teste abrindo `https://SEU-APP.onrender.com/health` — esperado:
   `{"status":"ok"}`

### 9.1 Anexar o disco persistente (CRÍTICO — sem isso o banco reseta sozinho)

Sem essa etapa, todo cadastro e negociação de todo usuário **some**
sempre que o serviço reinicia (acontece automaticamente depois de
15 minutos sem uso, no plano Free — no Starter, reinicia com menos
frequência, mas ainda assim acontece em deploys e manutenções do
Render).

1. No painel do seu Web Service no Render, vá em **Disks** (menu lateral)
2. **Add Disk**
3. Configure:

| Campo | Valor |
|---|---|
| **Name** | `dados-persistentes` (ou o nome que quiser) |
| **Mount Path** | `/var/data` |
| **Size** | `1 GB` já é bastante pra começar |

4. Salve — o Render reinicia o serviço automaticamente pra montar o disco
5. Confirme que a variável `DATABASE_PATH` (passo 4 acima) está
   configurada como `/var/data/dados_app.db` — é esse "/var/data" que
   precisa bater exatamente com o **Mount Path** que você configurou aqui

**Como confirmar que funcionou**: cadastre um usuário de teste, force
um redeploy manual (no painel, **Manual Deploy** → **Deploy latest
commit**), e confira se aquele usuário ainda existe depois (via
`/admin/usuarios`). Se ainda estiver lá, o disco está funcionando.

### 9.2 Configurar o webhook do Asaas

No painel do Asaas (sandbox.asaas.com ou api.asaas.com, dependendo de
onde você está testando) → **Integrações** → **Webhooks** → criar um
novo:

- **URL**: `https://SEU-APP.onrender.com/pagamentos/webhook`
- **Token de autenticação**: cole o mesmo valor que você colocou em
  `ASAAS_WEBHOOK_TOKEN` no Render (Parte 9, passo 4)
- **Eventos**: marque pelo menos `PAYMENT_CONFIRMED`, `PAYMENT_RECEIVED`,
  `PAYMENT_OVERDUE`

Isso é o que avisa seu sistema quando alguém paga a assinatura ou a
comissão de negociação.

---

## PARTE 10 — Publicar o frontend

Escolha **uma** das duas opções (ambas gratuitas):

### Opção A — Render Static Site

1. **New** → **Static Site** → mesmo repositório
2. **Root Directory**: `frontend`
3. **Build Command**: em branco
4. **Publish Directory**: `.`
5. **Create Static Site** → você recebe `https://SEU-FRONTEND.onrender.com`

### Opção B — Vercel

1. Acesse https://vercel.com, entre com GitHub
2. **Add New...** → **Project** → selecione o repositório
3. **Framework Preset**: `Other`
4. **Root Directory**: `frontend`
5. **Deploy** → você recebe `https://SEU-FRONTEND.vercel.app`

---

## PARTE 11 — Conectar as duas pontas

### 11.1 Atualizar a URL da API nos arquivos HTML

No VS Code, abra `frontend/index.html`, `frontend/admin.html` e
`frontend/suporte.html`. Em cada um, ache a linha:

```javascript
const API_BASE_URL = "http://localhost:8000";
```

Troque pela URL real do Render (da Parte 9):

```javascript
const API_BASE_URL = "https://SEU-APP.onrender.com";
```

### 11.2 Atualizar o CORS no backend

No painel do Render, no **Web Service** (backend) → **Environment** →
edite `CORS_ALLOWED_ORIGINS` para a URL do frontend publicado (da
Parte 10):

```
https://SEU-FRONTEND.onrender.com
```

(ou a URL do Vercel, se escolheu a Opção B)

### 11.3 Subir as mudanças

De volta no VS Code, na pasta raiz:

```powershell
git add .
git commit -m "conectar frontend com API publicada"
git push
```

O Render e o Vercel redeployam automaticamente a cada `git push` —
espere 1 a 2 minutos e acompanhe na aba **Events**/**Deployments** de
cada painel.

---

## PARTE 12 — Teste final de ponta a ponta

1. Abra a URL do frontend publicado **no navegador do celular**
2. Cadastre uma conta com CPF válido
3. Faça login → confirme que o dashboard carrega
4. Toque no menu do navegador → **Instalar app** (ou espere o aviso
   automático aparecer)
5. Abra a URL do admin (`/admin.html`) e entre com o e-mail/senha do
   `ADMIN_BOOTSTRAP_EMAIL`/`ADMIN_BOOTSTRAP_SENHA` — confirme que o
   painel carrega e mostra o usuário que você acabou de cadastrar

---

## PARTE 13 — Depois que tudo funcionar: um passo de segurança final

Volte no Render, no backend → **Environment** → **remova**
`ADMIN_BOOTSTRAP_EMAIL` e `ADMIN_BOOTSTRAP_SENHA`. Elas só servem pra
criar a primeira conta de admin — depois disso, não precisam continuar
expostas nas variáveis de ambiente.

---

## Checklist final

- [ ] Testes de lógica pura passando localmente (Parte 3)
- [ ] `pytest tests/test_api.py` passando localmente (Parte 6)
- [ ] Login/cadastro/dashboard funcionando local (Parte 7)
- [ ] Painel admin funcionando local (Parte 7)
- [ ] Código no GitHub (Parte 8)
- [ ] Backend no ar no Render, `/health` respondendo (Parte 9)
- [ ] Frontend no ar (Parte 10)
- [ ] CORS e `API_BASE_URL` alinhados entre as duas URLs (Parte 11)
- [ ] Testado no celular real: cadastro, login, instalar app (Parte 12)
- [ ] Testado o painel admin publicado (Parte 12)
- [ ] `ADMIN_BOOTSTRAP_EMAIL`/`SENHA` removidas do Render (Parte 13)

## Se algo der errado

- **Erro de CORS no navegador** ("blocked by CORS policy"): a URL em
  `CORS_ALLOWED_ORIGINS` no Render precisa ser **idêntica**, sem barra
  `/` no final, à URL real do frontend.
- **"Failed to fetch"**: confirme que `API_BASE_URL` nos arquivos HTML
  aponta pra URL certa, e que o backend está de fato no ar
  (`/health`).
- **Erro 401 mesmo com senha certa**: confira se não passou pelo limite
  de 5 tentativas erradas (a conta trava por 15 min — ver
  `backend/SECURITY.md`).
- **Qualquer outro erro**: volte no `backend/SECURITY.md` e
  `STATUS_DO_PROJETO.md` — a maioria das limitações conhecidas já está
  documentada ali.
