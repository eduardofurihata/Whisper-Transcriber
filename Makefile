VENV := .venv
PY := python3.12
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: check-deps
check-deps:
	@echo "🔍 Verificando dependências do sistema..."
	@command -v $(PY) >/dev/null 2>&1 || { \
		echo "📦 Instalando $(PY)..."; \
		sudo dnf install -y $(PY); \
	}
	@$(PY) -c "import venv" 2>/dev/null || { \
		echo "📦 Instalando $(PY)-devel..."; \
		sudo dnf install -y $(PY)-devel; \
	}
	@command -v ffmpeg >/dev/null 2>&1 || { \
		echo "📦 Instalando ffmpeg..."; \
		sudo dnf install -y ffmpeg; \
	}
	@echo "✅ Dependências do sistema OK."

$(VENV)/bin/activate: requirements.txt
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	@if command -v nvidia-smi >/dev/null 2>&1; then \
		echo "🎮 GPU NVIDIA detectada — instalando bibliotecas CUDA…"; \
		$(PIP) install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12; \
	fi
	touch $(VENV)/bin/activate

# Coleta caminhos das libs NVIDIA instaladas via pip (vazio se não houver)
NVIDIA_LIB_DIRS := $(shell find $(VENV) -path "*/nvidia/*/lib" -type d 2>/dev/null | paste -sd:)

.PHONY: dev
dev: check-deps $(VENV)/bin/activate
	LD_LIBRARY_PATH="$(NVIDIA_LIB_DIRS)$${LD_LIBRARY_PATH:+:$$LD_LIBRARY_PATH}" $(PYTHON) gui-whisper-transcribe.py

.PHONY: cli
cli: check-deps $(VENV)/bin/activate
	LD_LIBRARY_PATH="$(NVIDIA_LIB_DIRS)$${LD_LIBRARY_PATH:+:$$LD_LIBRARY_PATH}" $(PYTHON) whisper-transcribe.py

.PHONY: clean
clean:
	rm -rf $(VENV)
