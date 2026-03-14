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
	touch $(VENV)/bin/activate

.PHONY: dev
dev: check-deps $(VENV)/bin/activate
	$(PYTHON) gui-whisper-transcribe.py

.PHONY: cli
cli: check-deps $(VENV)/bin/activate
	$(PYTHON) whisper-transcribe.py

.PHONY: clean
clean:
	rm -rf $(VENV)
