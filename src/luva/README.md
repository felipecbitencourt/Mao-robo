# brain-glove

Program for 5DT glove with hand movement feedback and finger opening.

---

## Instruções de execução (melhoradas)

Este README descreve como preparar um ambiente virtual, instalar dependências mínimas e executar o programa Python que usa o executável `TestGlove64.exe` (gerado a partir de `testglove.cpp`). O executável já deve estar no local correto dentro do repositório.

### Visão geral

1. Os programas Python consomem o executável `TestGlove64.exe`.
2. O código Python principal está dentro da pasta `python-project`.

### Passo a passo

> Execute todos os comandos a partir da raiz do repositório (`brain-glove`).

#### 1) Criar e ativar um ambiente virtual

**Windows (CMD)**

```cmd
cd C:\caminho\para\brain-glove
python -m venv .venv
.venv\Scripts\activate
```

**Windows (PowerShell)**

```powershell
cd C:\caminho\para\brain-glove
python -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force  # se necessário
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
cd /caminho/para/brain-glove
python3 -m venv .venv
source .venv/bin/activate
```

Após ativar, o prompt deve exibir `(.venv)` no início da linha.

#### 2) Instalar dependências (mínimo necessário)

Como não há `requirements.txt` fornecido, instale pelo menos o Pillow (usado para `PIL`) e outras bibliotecas que o seu projeto utilizar (por exemplo `numpy`, `opencv-python`, etc.).

```bash
pip install --upgrade pip
pip install pillow
# pip install numpy opencv-python  # descomente se seu projeto usar essas libs
```

> Para conferir se o pacote foi instalado dentro do venv:

```bash
pip show pillow
# verifique se o campo Location aponta para .venv\Lib\site-packages (Windows) ou .venv/lib/ (Linux)
```

Se preferir gerar um `requirements.txt` para reprodução futura:

```bash
pip freeze > requirements.txt
```

#### 3) Executar o programa

Entre na pasta `python-project` e rode o script Python desejado. Exemplo:

```bash
cd python-project
python realtime_glove_feedback.py
```

> Substitua `realtime_glove_feedback.py` pelo nome do arquivo Python que você quiser executar.

---

## Solução de problemas comuns

* **`ModuleNotFoundError: No module named 'PIL'`**

  * Certifique-se de ter ativado o venv e rode `pip install pillow` dentro dele.

* **Ao ativar o venv no PowerShell: `execution policy` bloqueando scripts**

  * Abra PowerShell como Administrador e rode: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

* **PIP instalou globalmente em vez do venv**

  * Verifique qual `python` está sendo usado: `where python` (Windows) ou `which python` (Linux). Quando o venv está ativado, `python` deve apontar para `.venv`.
  * Alternativamente, use `python -m pip install ...` para garantir que o `pip` corresponde ao `python` ativo.

* **Criou o venv com estrutura `bin/` (estilo Linux) mas está no CMD/Windows**

  * Isso significa que provavelmente você usou um Python do WSL/Git Bash. Apague o venv e recrie usando o Python do Windows (por exemplo `py -3 -m venv .venv`).

* **Arquivo Python não encontrado ao executar**

  * Confirme que você está na pasta correta (`python-project`) antes de rodar o script.

---


