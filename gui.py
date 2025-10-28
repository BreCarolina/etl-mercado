# -*- coding: utf-8 -*-
"""
GUI Desktop (Qt/PySide6) — preto/laranja.
Abas:
  - Extração: ativo, timeframe ("M5"), dias -> data/raw
  - Transformação: arquivo de entrada + janela_sr -> data/transformed
  - Pipeline: ativo, timeframe, dias, janela_sr
  - Arquivos: lista conteúdo de data/raw e data/transformed (abrir, revelar, copiar caminho)
Logs aparecem no painel inferior. Conexão: Enter no campo senha muda status.
"""

import sys
import io
import contextlib
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QTextEdit, QLabel, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox
)
from PySide6.QtGui import QIcon, QPalette, QColor, QDesktopServices
from PySide6.QtCore import Qt, QUrl
import main


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
TRANS_DIR = DATA_DIR / "transformed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
TRANS_DIR.mkdir(parents=True, exist_ok=True)


def _best_icon_path() -> Path | None:
    base = ROOT / "assets"
    icns = base / "icone.icns"
    png = base / "icone.png"
    if icns.exists():
        return icns
    if png.exists():
        return png
    return None


def _human_size(n: int) -> str:
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < step:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= step
    return f"{n:.2f} PB"


class ETLApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETL de Mercado — Desktop (Qt)")
        self.resize(900, 620)

        ipath = _best_icon_path()
        if ipath:
            self.setWindowIcon(QIcon(str(ipath)))

        root = QVBoxLayout(self)

        # ---------------- Credenciais ----------------
        cred_layout = QFormLayout()
        title = QLabel("Credenciais da corretora")
        title.setStyleSheet("color: orange; font-weight: bold; font-size: 13px;")
        cred_layout.addRow(title)

        self.email = QLineEdit()
        self.senha = QLineEdit()
        self.senha.setEchoMode(QLineEdit.Password)

        status_row = QHBoxLayout()
        self.conn_status = QLabel("Desconectado")
        self.conn_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.conn_status.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        status_row.addWidget(self.conn_status, 1)

        cred_layout.addRow("E-mail:", self.email)
        cred_layout.addRow("Senha:", self.senha)
        cred_layout.addRow(status_row)
        self.senha.returnPressed.connect(self.do_connect)  # Enter faz login

        root.addLayout(cred_layout)

        # ---------------- Abas ----------------
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # Extração
        self.ext_widget = QWidget()
        self.tabs.addTab(self.ext_widget, "Extração")
        self._build_extract_tab(self.ext_widget)

        # Transformação
        self.tr_widget = QWidget()
        self.tabs.addTab(self.tr_widget, "Transformação")
        self._build_transform_tab(self.tr_widget)

        # Pipeline
        self.pipe_widget = QWidget()
        self.tabs.addTab(self.pipe_widget, "Pipeline")
        self._build_pipeline_tab(self.pipe_widget)

        # Arquivos
        self.files_widget = QWidget()
        self.tabs.addTab(self.files_widget, "Arquivos")
        self._build_files_tab(self.files_widget)

        # Log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log)

        self._apply_dark_theme()

    # ---------------- Conexão ----------------
    def do_connect(self):
        email = self.email.text().strip()
        senha = self.senha.text().strip()
        if not email or not senha:
            QMessageBox.warning(self, "Atenção", "Informe e-mail e senha.")
            return
        ok = main.check_connection(email, senha)
        if ok:
            self.conn_status.setText("Conectado")
            self.conn_status.setStyleSheet("color: #00d97e; font-weight: bold;")
            self.log.append("✔ Conexão estabelecida com sucesso.")
        else:
            self.conn_status.setText("Falhou")
            self.conn_status.setStyleSheet("color: #ff5a5f; font-weight: bold;")
            QMessageBox.critical(self, "Erro", "Não foi possível conectar.")
            self.log.append("✖ Falha na conexão.")

    # ---------------- Extração ----------------
    def _build_extract_tab(self, w):
        form = QFormLayout(w)
        self.ext_ativo = QLineEdit("EURJPY")
        self.ext_timeframe = QLineEdit("M5")
        self.ext_dias = QSpinBox()
        self.ext_dias.setRange(1, 3650)
        self.ext_dias.setValue(360)
        form.addRow("Ativo:", self.ext_ativo)
        form.addRow("Timeframe:", self.ext_timeframe)
        form.addRow("Dias:", self.ext_dias)
        btn = QPushButton("Rodar extração (data/raw)")
        btn.clicked.connect(self.run_extract)
        form.addRow(btn)

    # --------------- Transformação ---------------
    def _build_transform_tab(self, w):
        form = QFormLayout(w)
        self.tr_input = QLineEdit()
        pick = QPushButton("Escolher…")
        pick.clicked.connect(self._pick_input_file)
        row = QHBoxLayout()
        row.addWidget(self.tr_input, 1)
        row.addWidget(pick, 0)
        self.tr_janela_sr = QSpinBox()
        self.tr_janela_sr.setRange(0, 100000)
        self.tr_janela_sr.setValue(48)
        form.addRow("Arquivo de entrada:", row)
        form.addRow("Janela SR (int):", self.tr_janela_sr)
        btn = QPushButton("Rodar transformação (data/transformed)")
        btn.clicked.connect(self.run_transform)
        form.addRow(btn)

    # ----------------- Pipeline ------------------
    def _build_pipeline_tab(self, w):
        form = QFormLayout(w)
        self.pipe_ativo = QLineEdit("EURJPY")
        self.pipe_timeframe = QLineEdit("M5")
        self.pipe_dias = QSpinBox()
        self.pipe_dias.setRange(1, 3650)
        self.pipe_dias.setValue(360)
        self.pipe_janela_sr = QSpinBox()
        self.pipe_janela_sr.setRange(0, 100000)
        self.pipe_janela_sr.setValue(48)
        form.addRow("Ativo:", self.pipe_ativo)
        form.addRow("Timeframe:", self.pipe_timeframe)
        form.addRow("Dias:", self.pipe_dias)
        form.addRow("Janela SR (int):", self.pipe_janela_sr)
        btn = QPushButton("Rodar pipeline")
        btn.clicked.connect(self.run_pipeline)
        form.addRow(btn)

    # ----------------- Arquivos ------------------
    def _build_files_tab(self, w):
        layout = QVBoxLayout(w)

        # Top bar: seletor de pasta + ações
        bar = QHBoxLayout()
        self.dir_selector = QComboBox()
        self.dir_selector.addItems(["data/raw", "data/transformed"])
        self.dir_selector.currentIndexChanged.connect(self.refresh_files)

        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.clicked.connect(self.refresh_files)

        btn_abrir_pasta = QPushButton("Abrir pasta")
        btn_abrir_pasta.clicked.connect(self.open_folder)

        btn_revelar = QPushButton("Mostrar no Finder")
        btn_revelar.clicked.connect(self.reveal_in_finder)

        btn_abrir_arquivo = QPushButton("Abrir arquivo")
        btn_abrir_arquivo.clicked.connect(self.open_selected_file)

        bar.addWidget(QLabel("Pasta:"))
        bar.addWidget(self.dir_selector, 1)
        bar.addWidget(btn_atualizar)
        bar.addWidget(btn_abrir_pasta)
        bar.addWidget(btn_revelar)
        bar.addWidget(btn_abrir_arquivo)
        layout.addLayout(bar)

        # Tabela
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nome", "Tipo", "Tamanho", "Modificado", "Caminho"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.doubleClicked.connect(self.open_selected_file)
        layout.addWidget(self.table)

        self.refresh_files()

    def _current_dir(self) -> Path:
        txt = self.dir_selector.currentText()
        return (ROOT / txt).resolve()

    def refresh_files(self):
        folder = self._current_dir()
        self.table.setRowCount(0)
        files = sorted([p for p in folder.glob("*") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            ext = p.suffix.lower().lstrip(".") or "-"
            size = _human_size(p.stat().st_size)
            mtime = p.stat().st_mtime
            when = Path(p).stat().st_mtime
            from datetime import datetime
            mod = datetime.fromtimestamp(when).strftime("%Y-%m-%d %H:%M:%S")

            self.table.setItem(row, 0, QTableWidgetItem(p.name))
            self.table.setItem(row, 1, QTableWidgetItem(ext))
            self.table.setItem(row, 2, QTableWidgetItem(size))
            self.table.setItem(row, 3, QTableWidgetItem(mod))
            self.table.setItem(row, 4, QTableWidgetItem(str(p)))

    def _selected_path(self) -> Path | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return Path(self.table.item(rows[0].row(), 4).text())

    def open_folder(self):
        folder = self._current_dir()
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def reveal_in_finder(self):
        p = self._selected_path()
        if not p:
            QMessageBox.information(self, "Arquivos", "Selecione um arquivo.")
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(p)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.parent)))

    def open_selected_file(self):
        p = self._selected_path()
        if not p:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    # ---------------- Helpers ----------------
    def _pick_input_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecione o arquivo", "", "CSV (*.csv);;Todos (*.*)")
        if path:
            self.tr_input.setText(path)

    def _append_log(self, txt: str):
        self.log.append(txt)

    @contextlib.contextmanager
    def _capture_to_log(self):
        class _QtWriter(io.StringIO):
            def __init__(self, append_fn):
                super().__init__()
                self._append = append_fn
            def write(self, s):
                if s.strip():
                    self._append(s.rstrip())
                return len(s)
        def _append_line(txt: str):
            self.log.append(txt)
        out = _QtWriter(_append_line)
        err = _QtWriter(_append_line)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield

    # ---------------- Actions ----------------
    def run_extract(self):
        try:
            params = {
                "email": self.email.text().strip(),
                "senha": self.senha.text().strip(),
                "ativo": self.ext_ativo.text().strip(),
                "timeframe": self.ext_timeframe.text().strip(),
                "dias": int(self.ext_dias.value()),
            }
            with self._capture_to_log():
                result = main.extract(params)
            self._append_log(f"Extração concluída: {result}")
            QMessageBox.information(self, "Extração", f"Concluída: {result}")
            self.tr_input.setText(str(result))
            # Atualiza aba Arquivos (raw)
            if self.dir_selector.currentText() != "data/raw":
                self.dir_selector.setCurrentText("data/raw")
            self.refresh_files()
        except Exception as e:
            self._append_log(f"Erro na extração: {e}")
            QMessageBox.critical(self, "Erro", str(e))

    def run_transform(self):
        try:
            input_path = self.tr_input.text().strip()
            if not input_path:
                QMessageBox.warning(self, "Atenção", "Informe o arquivo de entrada.")
                return
            params = {
                "email": self.email.text().strip(),
                "senha": self.senha.text().strip(),
                "janela_sr": int(self.tr_janela_sr.value()),
            }
            with self._capture_to_log():
                result = main.transform(Path(input_path), params)
            self._append_log(f"Transformação concluída: {result}")
            QMessageBox.information(self, "Transformação", f"Concluída: {result}")
            # Atualiza aba Arquivos (transformed)
            if self.dir_selector.currentText() != "data/transformed":
                self.dir_selector.setCurrentText("data/transformed")
            self.refresh_files()
        except Exception as e:
            self._append_log(f"Erro na transformação: {e}")
            QMessageBox.critical(self, "Erro", str(e))

    def run_pipeline(self):
        try:
            eparams = {
                "email": self.email.text().strip(),
                "senha": self.senha.text().strip(),
                "ativo": self.pipe_ativo.text().strip(),
                "timeframe": self.pipe_timeframe.text().strip(),
                "dias": int(self.pipe_dias.value()),
            }
            tparams = {
                "email": self.email.text().strip(),
                "senha": self.senha.text().strip(),
                "janela_sr": int(self.pipe_janela_sr.value()),
            }
            with self._capture_to_log():
                result = main.run_pipeline(eparams, tparams)
            self._append_log(f"Pipeline concluído: {result}")
            QMessageBox.information(self, "Pipeline", f"Concluído: {result}")
            # Atualiza lista de transformados
            if self.dir_selector.currentText() != "data/transformed":
                self.dir_selector.setCurrentText("data/transformed")
            self.refresh_files()
        except Exception as e:
            self._append_log(f"Erro no pipeline: {e}")
            QMessageBox.critical(self, "Erro", str(e))

    # ---------------- Tema ----------------
    def _apply_dark_theme(self):
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(18, 18, 18))
        pal.setColor(QPalette.Base, QColor(24, 24, 24))
        pal.setColor(QPalette.AlternateBase, QColor(32, 32, 32))
        pal.setColor(QPalette.Text, QColor(230, 230, 230))
        pal.setColor(QPalette.WindowText, QColor(230, 230, 230))
        pal.setColor(QPalette.Button, QColor(28, 28, 28))
        pal.setColor(QPalette.ButtonText, QColor(230, 230, 230))
        pal.setColor(QPalette.Highlight, QColor(255, 109, 0))
        pal.setColor(QPalette.BrightText, QColor(255, 255, 255))
        self.setPalette(pal)
        self.setStyleSheet("""
            QLabel { color: #e6e6e6; }
            QLineEdit, QSpinBox, QComboBox {
                background: #1f1f1f; color: #f0f0f0; border: 1px solid #333; padding: 4px;
            }
            QPushButton {
                background: #ff6d00; color: #111; font-weight: 600; border: none; padding: 6px 10px;
            }
            QPushButton:hover { background: #ff7f1a; }
            QTabBar::tab { background: #2a2a2a; padding: 6px 12px; margin-right: 4px; }
            QTabBar::tab:selected { background: #ff6d00; color: #111; }
            QTextEdit, QTableWidget { background: #151515; color: #dcdcdc; border: 1px solid #333; }
            QHeaderView::section { background: #222; color: #ddd; padding: 4px; border: 0px; }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ipath = _best_icon_path()
    if ipath:
        app.setWindowIcon(QIcon(str(ipath)))
    w = ETLApp()
    w.show()
    sys.exit(app.exec())
