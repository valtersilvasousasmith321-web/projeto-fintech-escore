# Deploy Público — Do VS Code até o Ar

Guia completo pra colocar o sistema na internet, disponível para qualquer
pessoa acessar. Vamos usar o **Render** (tem plano gratuito, não precisa
cartão de crédito pra começar) pra hospedar tanto o backend (API) quanto
o frontend (as telas HTML).

## Visão geral do que vamos fazer

```
Seu computador (VS Code)
        │
        │  1. Subir o código pro GitHub
        ▼
   GitHub (repositório)
        │
        │  2. Conectar o Render ao repositório
        ▼
   Render.com
   ├── Web Service (backend/API) → https://seu-app-api.onrender.com
   └── Static Site (frontend)    → https://seu-app.onrender.com
```

---

## Parte 1 — Subir o código pro GitHub

Se você ainda não tem Git instalado, baixe em https://git-scm.com/downloads
(marque a opção padrão na instalação).

No PowerShell, dentro da pasta `projeto-fintech-score`:

```powershell
git init
git add .
git commit -m "primeira versão do sistema"
```

Crie um repositório novo em https://github.com/new (pode ser privado ou
público — o Render funciona com os dois). Depois:

```powershell
git remote add origin https://github.com/SEU_USUARIO/projeto-fintech-score.git
git branch -M main
git push -u origin main
```

Se pedir login, o GitHub vai te guiar pra autenticar (token de acesso,
não mais senha direta — siga o que aparecer na tela).

---

## Parte 2 — Publicar o backend (API) no Render

1. Crie uma conta gratuita em https://render.com (dá pra entrar direto com GitHub)
2. No painel, clique em **New** → **Web Service**
3. Conecte sua conta do GitHub e escolha o repositório `projeto-fintech-score`
4. Configure:

| Campo | Valor |
|---|---|
| **Name** | `nome-limpo-api` (ou o nome que quiser) |
| **Root Directory** | `backend` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |

5. Antes de clicar em criar, vá em **Environment Variables** e adicione:

| Nome | Valor |
|---|---|
| `JWT_SECRET_KEY` | gere uma rodando localmente: `python -c "import secrets; print(secrets.token_urlsafe(64))"` e cole o resultado |
| `CORS_ALLOWED_ORIGINS` | por enquanto deixe `http://localhost:3000` — vamos voltar aqui na Parte 4 |
| `APP_ENV` | `production` — isso desliga o retorno do token de reset de senha na resposta da API (só aparece em `dev`) |
| `ADMIN_BOOTSTRAP_EMAIL` | o e-mail que você vai usar pra acessar o painel administrativo, ex: `voce@seudominio.com` |
| `ADMIN_BOOTSTRAP_SENHA` | uma senha forte (mín. 8 caracteres) — só é usada na primeira vez que o servidor sobe |

**Importante**: depois do primeiro deploy funcionar e você confirmar que consegue logar no painel admin (`/admin.html` no seu frontend), volte no Render e **remova** `ADMIN_BOOTSTRAP_EMAIL`/`ADMIN_BOOTSTRAP_SENHA` das variáveis de ambiente — elas só servem pra criar a conta a primeira vez, não precisam continuar expostas depois disso.

6. Clique em **Create Web Service**. O Render vai buildar e subir — acompanhe
   o log na tela. Ao final, você recebe uma URL do tipo:

   `https://nome-limpo-api.onrender.com`

7. Teste abrindo `https://nome-limpo-api.onrender.com/docs` no navegador —
   se aparecer a documentação interativa do Swagger, está no ar.

**Nota sobre o plano gratuito**: a instância "dorme" depois de 15 minutos
sem uso, e demora alguns segundos para "acordar" na primeira requisição
seguinte. Isso é normal no plano free — não é bug.

---

## Parte 3 — Publicar o frontend (as telas HTML)

1. No painel do Render, clique em **New** → **Static Site**
2. Escolha o mesmo repositório
3. Configure:

| Campo | Valor |
|---|---|
| **Name** | `nome-limpo-app` |
| **Root Directory** | `frontend` |
| **Build Command** | (deixe em branco — são arquivos estáticos, não precisa build) |
| **Publish Directory** | `.` |

4. Clique em **Create Static Site**. Você recebe uma URL do tipo:

   `https://nome-limpo-app.onrender.com`

---

## Parte 4 — Conectar as duas pontas

Agora que você tem as duas URLs, precisa apontar uma pra outra:

**4.1 — Atualizar o frontend para chamar a API certa**

Abra `frontend/index.html`, ache esta linha perto do fim do arquivo:

```javascript
const API_BASE_URL = "http://localhost:8000";
```

Troque pela URL real da sua API:

```javascript
const API_BASE_URL = "https://nome-limpo-api.onrender.com";
```

**4.2 — Atualizar o CORS do backend pra aceitar o frontend publicado**

Volte no painel do Render, na configuração do **Web Service** (backend) →
**Environment** → edite `CORS_ALLOWED_ORIGINS` pra:

```
https://nome-limpo-app.onrender.com
```

**4.3 — Subir a mudança**

```powershell
git add .
git commit -m "conectar frontend com API publicada"
git push
```

O Render redeploya automaticamente sempre que você faz `git push` — não
precisa repetir os passos de criação, só esperar o novo build terminar
(acompanha na aba **Events** do serviço).

---

## Parte 5 — Testar de ponta a ponta

1. Abra `https://nome-limpo-app.onrender.com` no navegador do celular
2. Cadastre uma conta (o CPF precisa ser válido — o sistema valida o dígito
   verificador de verdade)
3. Faça login
4. Deve aparecer o diagnóstico de score carregando da API real

Se der erro de "Failed to fetch" ou similar, quase sempre é CORS
desalinhado — confira se a URL em `CORS_ALLOWED_ORIGINS` no Render é
**exatamente igual** à URL do frontend (sem barra `/` no final).

---

## Sobre o botão de "Instalar" no celular

O `index.html` já vem com:
- `manifest.json` (nome, ícone, cor do app)
- `service-worker.js` (obrigatório pra virar instalável)
- Um aviso automático ("Instalar o app na tela inicial") que aparece
  quando o navegador detecta que o app pode ser instalado

**Android (Chrome)**: o aviso aparece automaticamente depois de alguns
segundos de uso, ou a pessoa pode tocar no menu (⋮) → "Instalar app".

**iPhone (Safari)**: o iOS não dispara o aviso automático — a pessoa
precisa tocar em **Compartilhar** (ícone de quadrado com seta) →
**Adicionar à Tela de Início**. Isso é uma limitação do próprio Safari,
não do nosso código — todo PWA funciona assim no iPhone.

Depois de instalado, o app abre em tela cheia, com ícone próprio, sem
barra de endereço do navegador — visualmente igual a um app nativo.

---

## Alternativa: publicar o frontend no Vercel (em vez do Render)

O Vercel é ótimo pra **arquivos estáticos** (HTML/CSS/JS) — que é exatamente o que está em `frontend/`. Mas ele roda como *serverless* (cada requisição pode subir num processo novo, sem disco persistente), o que **não combina bem com o backend** deste projeto, porque o backend usa SQLite (um arquivo de banco que precisa continuar existindo entre requisições). Por isso a recomendação é:

- **Frontend** (`index.html`, `admin.html`, `suporte.html`, etc.) → Vercel
- **Backend** (API FastAPI) → continua no Render, como nas Partes 1 e 2

### Passo a passo no Vercel

1. Já tendo o código no GitHub (Parte 1 acima), acesse https://vercel.com e entre com sua conta do GitHub
2. No dashboard, clique em **Add New...** → **Project**
3. Selecione o repositório `projeto-fintech-score` e clique em **Import**
4. Configure:

| Campo | Valor |
|---|---|
| **Framework Preset** | `Other` (é HTML puro, sem framework) |
| **Root Directory** | `frontend` |
| **Build Command** | deixe em branco |
| **Output Directory** | deixe em branco (ou `.`) |

5. Clique em **Deploy**. Em menos de um minuto você recebe uma URL do tipo:

   `https://projeto-fintech-score.vercel.app`

6. Repita a Parte 4 (conectar as duas pontas) usando essa URL do Vercel no lugar da URL do Render Static Site — tanto no `API_BASE_URL` dos arquivos HTML quanto no `CORS_ALLOWED_ORIGINS` do backend.

### Deploys automáticos

Assim como o Render, o Vercel fica de olho no seu repositório: todo `git push` pra branch `main` gera um novo deploy automaticamente, sem precisar repetir nenhum passo de configuração.

### Se um dia quiser levar o backend pro Vercel também

Precisaria trocar o SQLite por um banco hospedado externamente (ex: Postgres no Supabase, Neon, ou Vercel Postgres) — o backend já está estruturado com toda a lógica de acesso a dado isolada em `app/database.py`, então essa troca é localizada, não exige reescrever a lógica de negócio. Isso fica como próximo passo, não é necessário pra ir ao ar agora.

---

## Checklist final antes de divulgar pro público

- [ ] Backend no ar e respondendo em `/health`
- [ ] Frontend no ar e carregando o dashboard
- [ ] CORS alinhado entre as duas URLs
- [ ] `JWT_SECRET_KEY` configurada (nunca deixe em branco)
- [ ] `ADMIN_BOOTSTRAP_EMAIL`/`ADMIN_BOOTSTRAP_SENHA` configuradas, testado login em `admin.html`, e depois REMOVIDAS do painel do Render
- [ ] Testado cadastro + login + diagnóstico num celular real
- [ ] Testado o botão "Instalar app" tanto em `index.html` quanto em `admin.html`
- [ ] Ler `backend/SECURITY.md` — ainda faltam itens antes de operar com
      dinheiro/dado real de muita gente (banco de dados real em vez de
      SQLite, rate limiting distribuído, etc.) — o app já funciona
      ponta a ponta, mas em escala pequena/piloto, não em volume nacional ainda
