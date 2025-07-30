r"""
# 🎯 COMO USAR ESTE SCRIPT (100% via CMD do Windows)

## 1. Instale o Chocolatey (se ainda não tiver)
Abra o CMD como administrador e execute:
    @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin

Feche e reabra o CMD.

## 2. Instale o Python 3.10 com Chocolatey
    choco install python --version=3.10.11 -y

## 3. Instale o ffmpeg com Chocolatey
    choco install ffmpeg -y

## 4. Verifique se Python está no PATH (reinicie o terminal se necessário)
    python --version

## 5. (Opcional, mas recomendado) Crie e ative um ambiente virtual:
    python -m venv whisper_env
    whisper_env\Scripts\activate

## 6. Instale o Whisper da OpenAI e dependências
    pip install -U pip setuptools wheel
    pip install git+https://github.com/openai/whisper.git

## 7. Coloque este arquivo `transcrever.py` na mesma pasta que os vídeos (.ts, .mp4, .mkv...)

## 8. Rode o script:
    python transcrever.py

O script irá:
- Procurar arquivos de vídeo com extensões suportadas
- Ignorar vídeos que já possuem um .srt com mesmo nome
- Transcrever com Whisper (modo offline) e gerar o .srt
"""


import whisper
from pathlib import Path

# 🟡 Altere/extenda conforme suas necessidades:
EXTENSOES_SUPORTADAS = ['.ts', '.mp4', '.mkv']
MODELO = 'medium'  # Pode usar: tiny, base, small, medium, large

# Carrega o modelo Whisper
model = whisper.load_model(MODELO)

# Encontra arquivos com extensões suportadas
videos = [f for ext in EXTENSOES_SUPORTADAS for f in Path('.').glob(f'*{ext}')]

for video in videos:
    srt_path = video.with_suffix('.srt')
    
    if srt_path.exists():
        print(f"Pulando (SRT já existe): {video.name}")
        continue

    print(f"Transcrevendo: {video.name}")
    result = model.transcribe(str(video), fp16=False)
    
    # Salva como .srt
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(result['segments']):
            start = segment['start']
            end = segment['end']
            text = segment['text'].strip()

            def format_time(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                ms = int((t - int(t)) * 1000)
                return f"{h:02}:{m:02}:{s:02},{ms:03}"

            f.write(f"{i+1}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")

    print(f"✅ SRT gerado: {srt_path.name}")
