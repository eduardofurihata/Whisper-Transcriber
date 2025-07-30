# whisper_gui.py – Interface gráfica simples e gratuita usando Tkinter + tkinterdnd2
# Requisitos:
#   pip install openai-whisper tkinterdnd2
# Em Windows o Tkinter já vem incluso.
# Arraste vídeos ou escolha uma pasta: o script gera um .srt ao lado de cada vídeo.
# Não carrega todos os vídeos na memória – processa um de cada vez.

import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # pip install tkinterdnd2
except ImportError:
    raise SystemExit("⚠️  Instale a dependência: pip install tkinterdnd2")

try:
    import whisper
except ImportError:
    raise SystemExit("⚠️  Instale a dependência: pip install openai-whisper")

# 🟡 Altere/extenda conforme suas necessidades:
EXTENSOES_SUPORTADAS = {'.ts', '.mp4', '.mkv'}
MODELO = 'medium'    # tiny, base, small, medium, large

model = None                 # instanciado lazily no 1.º processamento
afila: "queue.Queue[Path]" = queue.Queue()
processing_thread = None
cancel_event = threading.Event()

# ------------- Funções auxiliares ------------------

def load_model_once():
    global model
    if model is None:
        log("Carregando modelo Whisper (%s)… isso pode levar alguns segundos…" % MODELO)
        model = whisper.load_model(MODELO)
        log("✅ Modelo carregado.")


def sufixo_srt(video_path: Path) -> Path:
    return video_path.with_suffix('.srt')


def log(msg: str):
    log_text.configure(state='normal')
    log_text.insert('end', msg + "\n")
    log_text.see('end')
    log_text.configure(state='disabled')


def add_files(paths):
    """Adiciona caminhos na fila (evita duplicados)."""
    added = 0
    for pstr in paths:
        p = Path(pstr)
        if p.is_dir():
            vids = [f for f in p.rglob('*') if f.suffix.lower() in EXTENSOES_SUPORTADAS]
        else:
            vids = [p]
        for v in vids:
            if v.suffix.lower() not in EXTENSOES_SUPORTADAS:
                continue
            if v not in listbox.get(0, 'end'):
                listbox.insert('end', v)
                added += 1
    if added:
        log(f"➕ {added} arquivo(s) adicionados à lista.")


def choose_folder():
    folder = filedialog.askdirectory(title="Escolha uma pasta contendo vídeos")
    if folder:
        add_files([folder])


def on_drop(event):
    # event.data é string com paths separadas por espaços; paths com espaços vêm entre { }
    raw = event.data
    # Divide respeitando chaves
    files = []
    current = ''
    inside_brace = False
    for char in raw:
        if char == '{':
            inside_brace = True
            current = ''
        elif char == '}':
            inside_brace = False
            files.append(current)
            current = ''
        elif char == ' ' and not inside_brace:
            if current:
                files.append(current)
                current = ''
        else:
            current += char
    if current:
        files.append(current)
    add_files(files)
    return 'break'


def remove_selected():
    sel = list(listbox.curselection())
    sel.reverse()
    for idx in sel:
        listbox.delete(idx)
    log(f"🗑️  {len(sel)} item(ns) removido(s) da lista.")


def remove_all():
    listbox.delete(0, 'end')
    log("🗑️  Lista limpa.")


def process_next():
    if listbox.size() == 0:
        messagebox.showinfo("Nada a processar", "Adicione arquivos primeiro.")
        return
    start_processing(all_items=False)


def process_all():
    if listbox.size() == 0:
        messagebox.showinfo("Nada a processar", "Adicione arquivos primeiro.")
        return
    start_processing(all_items=True)


def start_processing(all_items: bool):
    global processing_thread
    if processing_thread and processing_thread.is_alive():
        messagebox.showwarning("Processamento em andamento", "Aguarde o término ou cancele.")
        return
    cancel_event.clear()
    # Preenche a fila
    afila.queue.clear()
    items = listbox.get(0, 'end')
    if not all_items:  # só o selecionado ou o primeiro
        if listbox.curselection():
            items = [items[listbox.curselection()[0]]]
        else:
            items = [items[0]]
    for it in items:
        afila.put(Path(it))
    # Thread para processamento
    processing_thread = threading.Thread(target=worker, daemon=True)
    processing_thread.start()


def worker():
    while not afila.empty() and not cancel_event.is_set():
        video: Path = afila.get()
        try:
            process_video(video)
        except Exception as e:
            log(f"❌ Erro ao processar {video.name}: {e}")
        finally:
            afila.task_done()
    log("🏁 Fila concluída ou cancelada.")


def cancel_current():
    if not processing_thread or not processing_thread.is_alive():
        return
    cancel_event.set()
    log("⏹️  Cancelamento solicitado. Será efetivado após o arquivo atual.")


def process_video(video: Path):
    log(f"🎬 Processando: {video.name}")
    srt_path = sufixo_srt(video)
    if srt_path.exists():
        log(f"⚠️  Pulando (SRT já existe): {srt_path.name}")
        return
    load_model_once()
    result = model.transcribe(str(video), fp16=False)
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

            f.write(f"{i+1}\n{format_time(start)} --> {format_time(end)}\n{text}\n\n")
    log(f"✅ SRT gerado: {srt_path.name}")

# ------------- GUI ------------------

root = TkinterDnD.Tk()
root.title("Whisper SRT – Interface")
root.geometry("650x500")

# Frame principal
frame = ttk.Frame(root, padding=10)
frame.pack(fill='both', expand=True)

# Listbox com scroll
list_frame = ttk.Frame(frame)
list_frame.pack(fill='both', expand=True)
listbox = tk.Listbox(list_frame, selectmode='extended')
scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=listbox.yview)
listbox.configure(yscrollcommand=scrollbar.set)
listbox.pack(side='left', fill='both', expand=True)
scrollbar.pack(side='right', fill='y')

# Drag‑and‑drop
listbox.drop_target_register(DND_FILES)
listbox.dnd_bind('<<Drop>>', on_drop)

# Botões
btn_frame = ttk.Frame(frame)
btn_frame.pack(fill='x', pady=5)

actions = [
    ("➕ Pasta…", choose_folder),
    ("➡️ Processar seleção", process_next),
    ("▶️ Processar todos", process_all),
    ("⏹️ Cancelar atual", cancel_current),
    ("❌ Remover seleção", remove_selected),
    ("🗑️ Limpar lista", remove_all),
]
for txt, cmd in actions:
    ttk.Button(btn_frame, text=txt, command=cmd).pack(side='left', padx=2, pady=2)

# Log
log_text = tk.Text(frame, height=10, state='disabled', wrap='word')
log_text.pack(fill='both', expand=False, pady=(10,0))

log("💡 Arraste arquivos ou clique em ➕ Pasta… para começar.")
root.mainloop()
