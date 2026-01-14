# Instalação (Windows)

Este repositório tem 2 formas de uso:

- `whisper-transcribe.py`: transcreve todos os áudios/vídeos da pasta atual e gera `.srt`.
- `gui-whisper-transcribe.py`: interface gráfica (Tkinter) com arrastar-e-soltar e geração de `.srt`.

## Comandos (PowerShell + Chocolatey)

Abra o **PowerShell como Administrador** e rode, na ordem:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
Import-Module $env:ChocolateyInstall\helpers\chocolateyProfile.psm1
refreshenv

choco install python -y
choco install ffmpeg -y
refreshenv

python --version
pip --version
ffmpeg -version

cd C:\Users\furih\Desktop\GitHub\Whisper-Transcriber
python -m venv .venv
Set-ExecutionPolicy Bypass -Scope Process -Force
. .\.venv\Scripts\Activate.ps1

python -m pip install -U pip setuptools wheel
python -m pip install openai-whisper tkinterdnd2
```

## O que você precisa instalar

### 1) Python (recomendado: 3.10+)

- Instale o Python pelo instalador oficial (python.org) e marque **Add Python to PATH**.
- Verifique:
  - `python --version`
  - `pip --version`

### 2) FFmpeg (obrigatório)

O Whisper usa o `ffmpeg` para ler áudio/vídeo. Ele precisa estar no `PATH`.

- Verifique:
  - `ffmpeg -version`

**Opção A — Chocolatey (recomendado)**

- Instalar Chocolatey: https://chocolatey.org/install
- Depois:
  - `choco install ffmpeg -y`

**Opção B — Manual**

- Baixe um build do FFmpeg para Windows, extraia e adicione a pasta `bin` (onde fica `ffmpeg.exe`) no `PATH`.

### 3) Dependências Python (obrigatório)

Crie (opcional, recomendado) um ambiente virtual e instale as bibliotecas:

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
python -m pip install openai-whisper
```

Para rodar a interface gráfica com arrastar-e-soltar, instale também:

```
python -m pip install tkinterdnd2
```

Observações:

- No Windows, o **Tkinter** normalmente já vem junto com o Python. Se o script reclamar de `tkinter`, reinstale o Python (python.org) e inclua os “tcl/tk and IDLE”.
- Se você preferir instalar o Whisper direto do GitHub (alternativa ao `openai-whisper`):
  - `python -m pip install git+https://github.com/openai/whisper.git`

## Como rodar

### Script em lote (CLI)

1. Coloque `whisper-transcribe.py` na mesma pasta dos vídeos/áudios.
2. No terminal, vá até a pasta e rode:
   - `python whisper-transcribe.py`

Ele gera um `.srt` ao lado de cada mídia e pula arquivos que já tiverem `.srt`.

### Interface gráfica (GUI)

- `python gui-whisper-transcribe.py`

Na janela, você pode arrastar arquivos/pastas ou selecionar uma pasta; o app gera `.srt` ao lado de cada mídia.
