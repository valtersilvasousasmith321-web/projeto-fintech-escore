# Instalação no Windows

Guia passo a passo pra rodar o projeto inteiro no seu computador Windows,
depois de descompactar o zip.

## 1. Pré-requisitos

Verifique se já tem Python instalado. Abra o **PowerShell** (ou CMD) e digite:

```powershell
python --version
```

Se aparecer algo como `Python 3.11.x` ou mais novo, já tem. Se der erro
("não é reconhecido"), instale primeiro:

1. Baixe em https://www.python.org/downloads/
2. Na instalação, **marque a caixa "Add python.exe to PATH"** antes de clicar em Install — esse passo é o que mais gente esquece e trava tudo depois

## 2. Rodar a parte que já funciona sem instalar nada

Abra o PowerShell dentro da pasta que você descompactou:

```powershell
cd Downloads\projeto-fintech-score\backend
python -m unittest discover -s tests -v
```

Isso deve mostrar várias linhas terminando em `ok`, e no final:

```
Ran 85 tests ...
```

(vai dar 1 erro no `test_api` — isso é esperado nessa etapa, resolve no passo 4)

Pra ver o script de diagnóstico rodando no terminal:

```powershell
cd ..\src
python mock_analise_score.py
```

## 3. Ver as telas do app (HTML)

Não precisa instalar nada — é só abrir o arquivo direto:

```powershell
cd ..\frontend
start dashboard_score.html
```

Isso abre no seu navegador padrão. Mesma coisa pra `plano_acao.html`.

## 4. Instalar a API completa (FastAPI) e rodar de verdade

De volta na pasta `backend`:

```powershell
cd ..\backend

python -m venv venv
venv\Scripts\activate
```

Depois de rodar `venv\Scripts\activate`, o começo da linha do PowerShell
deve mudar pra mostrar `(venv)` — é o sinal de que funcionou.

```powershell
pip install -r requirements.txt
```

Definir a chave secreta (obrigatória — a API se recusa a subir sem isso):

```powershell
$env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Subir a API:

```powershell
uvicorn app.main:app --reload --port 8000
```

Abra no navegador: **http://localhost:8000/docs** — ali dá pra testar
cada rota da API direto, sem precisar escrever código.

## 5. Rodar os testes completos de API

Com o ambiente virtual ainda ativado (`(venv)` aparecendo), em outra
janela do PowerShell (deixe o `uvicorn` rodando na primeira):

```powershell
cd projeto-fintech-score\backend
venv\Scripts\activate
pytest tests\test_api.py -v
```

## Erros comuns no Windows

| Erro | Causa mais provável | Solução |
|---|---|---|
| `python : O termo 'python' não é reconhecido...` | Python não foi adicionado ao PATH na instalação | Reinstale marcando "Add python.exe to PATH" |
| `venv\Scripts\activate` não faz nada / dá erro de permissão | Política de execução do PowerShell bloqueando scripts | Rode uma vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e confirme com `S` |
| `JWT_SECRET_KEY não definida` ao subir o uvicorn | Você fechou e abriu uma nova janela do PowerShell, e a variável de ambiente não persiste entre janelas | Rode o comando do passo 4 de novo, na mesma janela onde vai rodar o uvicorn |
| `ModuleNotFoundError: No module named 'fastapi'` | Ambiente virtual não está ativado, ou o `pip install` não terminou | Confirme que `(venv)` aparece no início da linha antes de rodar qualquer comando |

## Sobre deixar isso acessível publicamente na internet

Rodando assim, o app só funciona no seu próprio computador (`localhost`).
Se a ideia é outras pessoas acessarem pela internet, isso é uma etapa
diferente — de hospedagem (Railway, Render, AWS, etc.), não de instalação
local. Se for isso que você quis dizer com "público", me fala que eu
te oriento nesse próximo passo específico.
