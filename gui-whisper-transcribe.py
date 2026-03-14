# gui-whisper-transcribe.py – Interface gráfica para transcrição com Whisper (PySide6)
# Requisitos:
#   pip install faster-whisper PySide6-Essentials
# Arraste vídeos ou escolha uma pasta: o script gera um .srt ao lado de cada vídeo.

import sys
import logging
import threading
import queue
import mimetypes
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QTextEdit, QFileDialog, QMessageBox,
    QAbstractItemView,
)
from PySide6.QtCore import Signal, Qt

try:
    from faster_whisper import WhisperModel
except ImportError:
    sys.exit("⚠️  Instale a dependência: pip install faster-whisper")

MODELO = 'large-v3'


def is_media_file(path: Path) -> bool:
    if not path.is_file():
        return False
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime.startswith("audio/") or mime.startswith("video/")
    return True


def ensure_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg não encontrado no PATH. Instale o ffmpeg e reabra o app.")


class SignalLogHandler(logging.Handler):
    """Redireciona mensagens de logging para um Signal do Qt."""

    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class DropListWidget(QListWidget):
    """QListWidget com suporte nativo a drag-and-drop de arquivos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.window().add_files(paths)
            event.acceptProposedAction()


class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whisper SRT – Interface")
        self.resize(700, 550)

        self.model = None
        self.file_queue: queue.Queue[Path] = queue.Queue()
        self.processing_thread = None
        self.cancel_event = threading.Event()

        self.log_signal.connect(self._append_log)
        self._build_ui()
        self.log("💡 Arraste arquivos ou clique em 'Pasta…' para começar.")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Lista de arquivos
        self.listbox = DropListWidget(self)
        layout.addWidget(self.listbox, stretch=1)

        # Botões
        btn_layout = QHBoxLayout()
        actions = [
            ("📁 Pasta…", self.choose_folder),
            ("▶ Processar seleção", self.process_next),
            ("▶▶ Processar todos", self.process_all),
            ("⏹ Cancelar", self.cancel_current),
            ("✕ Remover seleção", self.remove_selected),
            ("🗑 Limpar lista", self.remove_all),
            ("📋 Copiar Log", self.copy_log),
        ]
        for text, callback in actions:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        # Log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        layout.addWidget(self.log_text)

    def _append_log(self, msg: str):
        self.log_text.append(msg)
        self.log_text.ensureCursorVisible()

    def log(self, msg: str):
        self.log_signal.emit(msg)

    # -- Ações --

    def add_files(self, paths: list[str]):
        existing = set()
        for i in range(self.listbox.count()):
            existing.add(self.listbox.item(i).text())

        added = 0
        for pstr in paths:
            p = Path(pstr)
            if not p.exists():
                self.log(f"Arquivo não encontrado: {p}")
                continue
            if p.is_dir():
                files = [f for f in p.rglob('*') if is_media_file(f)]
            else:
                files = [p] if is_media_file(p) else []
            for f in files:
                f_str = str(f)
                if f_str not in existing:
                    self.listbox.addItem(f_str)
                    existing.add(f_str)
                    added += 1
        if added:
            self.log(f"➕ {added} arquivo(s) adicionados à lista.")

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolha uma pasta contendo vídeos")
        if folder:
            self.add_files([folder])

    def remove_selected(self):
        items = self.listbox.selectedItems()
        if not items:
            return
        for item in items:
            self.listbox.takeItem(self.listbox.row(item))
        self.log(f"🗑️ {len(items)} item(ns) removido(s) da lista.")

    def remove_all(self):
        self.listbox.clear()
        self.log("🗑️ Lista limpa.")

    def copy_log(self):
        text = self.log_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.log("📋 Log copiado para a área de transferência.")

    def process_next(self):
        if self.listbox.count() == 0:
            QMessageBox.information(self, "Nada a processar", "Adicione arquivos primeiro.")
            return
        self._start_processing(all_items=False)

    def process_all(self):
        if self.listbox.count() == 0:
            QMessageBox.information(self, "Nada a processar", "Adicione arquivos primeiro.")
            return
        self._start_processing(all_items=True)

    def cancel_current(self):
        if not self.processing_thread or not self.processing_thread.is_alive():
            return
        self.cancel_event.set()
        self.log("⏹️ Cancelamento solicitado. Será efetivado após o arquivo atual.")

    def _start_processing(self, all_items: bool):
        if self.processing_thread and self.processing_thread.is_alive():
            QMessageBox.warning(self, "Processamento em andamento", "Aguarde o término ou cancele.")
            return

        self.cancel_event.clear()
        self.file_queue.queue.clear()

        if all_items:
            items = [self.listbox.item(i).text() for i in range(self.listbox.count())]
        else:
            selected = self.listbox.selectedItems()
            if selected:
                items = [item.text() for item in selected]
            else:
                items = [self.listbox.item(0).text()]

        for it in items:
            self.file_queue.put(Path(it))

        self.processing_thread = threading.Thread(target=self._worker, daemon=True)
        self.processing_thread.start()

    def _worker(self):
        while not self.file_queue.empty() and not self.cancel_event.is_set():
            video: Path = self.file_queue.get()
            try:
                self._process_video(video)
            except Exception as e:
                self.log(f"❌ Erro ao processar {video.name}: {e}")
            finally:
                self.file_queue.task_done()
        self.log("🏁 Fila concluída ou cancelada.")

    def _load_model(self):
        if self.model is None:
            self.log(f"⬇️ Baixando/carregando modelo Whisper ({MODELO})… "
                     f"na primeira vez, o download pode levar vários minutos…")

            # Redireciona logs do huggingface_hub para a GUI
            handler = SignalLogHandler(self.log_signal)
            handler.setFormatter(logging.Formatter("  %(message)s"))
            for name in ("huggingface_hub", "faster_whisper"):
                logger = logging.getLogger(name)
                logger.setLevel(logging.INFO)
                logger.addHandler(handler)

            try:
                self.model = WhisperModel(MODELO, device="cuda", compute_type="int8")
            except Exception as e:
                self.log(f"⚠️ Falha ao carregar na GPU: {e}")
                self.log("Tentando carregar na CPU…")
                self.model = WhisperModel(MODELO, device="cpu", compute_type="int8")

            # Remove handlers após carregar para não poluir o log
            for name in ("huggingface_hub", "faster_whisper"):
                logging.getLogger(name).removeHandler(handler)

            self.log("✅ Modelo carregado.")

    def _process_video(self, video: Path):
        self.log(f"🎬 Processando: {video.name}")
        if not video.exists():
            self.log(f"Arquivo não encontrado: {video}")
            return

        srt_path = video.with_suffix('.srt')
        if srt_path.exists():
            self.log(f"⚠️ Pulando (SRT já existe): {srt_path.name}")
            return

        ensure_ffmpeg()
        self._load_model()

        try:
            segments, info = self.model.transcribe(str(video), beam_size=5)
        except Exception as e:
            cuda_keywords = ("libcublas", "libcudnn", "libcufft", "CUDA", "cuda")
            if any(k in str(e) for k in cuda_keywords):
                self.log(f"⚠️ Falha de CUDA durante transcrição: {e}")
                self.log("Recarregando modelo na CPU…")
                self.model = WhisperModel(MODELO, device="cpu", compute_type="int8")
                self.log("✅ Modelo recarregado na CPU.")
                segments, info = self.model.transcribe(str(video), beam_size=5)
            else:
                raise

        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments):
                start = segment.start
                end = segment.end
                text = segment.text.strip()

                def format_time(t):
                    h = int(t // 3600)
                    m = int((t % 3600) // 60)
                    s = int(t % 60)
                    ms = int((t - int(t)) * 1000)
                    return f"{h:02}:{m:02}:{s:02},{ms:03}"

                f.write(f"{i+1}\n{format_time(start)} --> {format_time(end)}\n{text}\n\n")

        self.log(f"✅ SRT gerado: {srt_path.name}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
