# -*- coding: utf-8 -*-
"""
MVP3 — GUI Desktop (Qt/PySide6) — tema preto/laranja


Dependências esperadas no projeto:
- scripts/extracao.py com função: extrair_dados(par, timeframe, dias, email, senha) -> (df, csv_path)
- scripts/transformacao.py com função: transformar_dados(par, timeframe, dias, horizon, janela_sr) -> out_csv
  e opcionalmente FEATURE_COLUMNS
- scripts/carga.py com função: load_transformed(par, timeframe, csv_path=None) -> dict(ex.: {"upserts": int, "max_ts": int})
- scripts/db_manager.py com get_last_timestamp(par, timeframe) e export_to_csv(...)
"""

import sys, io, time, contextlib, shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox, QTextEdit, QLabel, QSpinBox,
    QScrollArea, QCheckBox, QGridLayout, QFileDialog
)
from PySide6.QtGui import QIcon, QPalette, QColor
from PySide6.QtCore import Qt

# Garante que o diretório do projeto esteja no sys.path antes de importar 'scripts'
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Módulos do projeto
from scripts import extracao, transformacao, carga, db_manager as dm

# --------------------------------- Config / Paths ---------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
TRANS_DIR = DATA_DIR / "transformed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
TRANS_DIR.mkdir(parents=True, exist_ok=True)

# Features (fallback caso não existam no módulo transformacao)
try:
    from scripts.transformacao import FEATURE_COLUMNS as _FEATURE_COLUMNS
    FEATURE_COLUMNS = list(_FEATURE_COLUMNS)
except Exception:
    FEATURE_COLUMNS = [
        "corpo","pavio_superior","pavio_inferior",
        "pressao_compradora","pressao_vendedora",
        "EMA_7","EMA_21","resistencia","suporte",
        "dist_resistencia","dist_suporte",
        "retorno","volatilidade","RSI_14","target_class"
    ]

# --------------------------------- Utils ---------------------------------

def _best_icon_path() -> Path | None:
    base = ROOT / "assets"
    for cand in (base / "icone.icns", base / "icone.png"):
        if cand.exists():
            return cand
    return None

def _tf_to_seconds(txt: str) -> int:
    t = (txt or "").strip().upper()
    if t.startswith("M1"): return 60
    if t.startswith("M5"): return 300
    if t.startswith("M15"): return 900
    if t.startswith("M30"): return 1800
    if t.startswith("H1"): return 3600
    try: return int(t)
    except: return 300

def _tf_label(tf_s: int) -> str:
    return {60:"M1",300:"M5",900:"M15",1800:"M30",3600:"H1"}.get(int(tf_s), f"{int(tf_s)}s")

def fixed_raw_path(pair: str, tf_s: int) -> Path:
    return RAW_DIR / f"{pair}_{_tf_label(tf_s)}.csv"

def fixed_transformed_path(pair: str, tf_s: int) -> Path:
    return TRANS_DIR / f"{pair}_{_tf_label(tf_s)}.csv"

@contextlib.contextmanager
def capture_to_log(append_fn):
    class _QtWriter(io.StringIO):
        def __init__(self, append):
            super().__init__(); self._append = append
        def write(self, s):
            if s.strip(): self._append(s.rstrip())
            return len(s)
    out = _QtWriter(append_fn); err = _QtWriter(append_fn)
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield

def safe_overwrite_from_src(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    tmp.replace(dst)

def safe_overwrite_from_df(df, dst: Path):
    # Evita dependência de timestamp: salva diretamente no caminho fixo
    import pandas as pd
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    # garante cabeçalho quando df está vazio mas com colunas
    if getattr(df, "empty", False) and len(getattr(df, "columns", [])) == 0:
        # cria um DF com colunas mínimas para não quebrar leitura a jusante
        df = pd.DataFrame(columns=["ts","abertura","maxima","minima","fechamento","volume"])  # fallback
    df.to_csv(tmp, index=False)
    tmp.replace(dst)

def purge_transformed_dir():
    if TRANS_DIR.exists():
        for p in TRANS_DIR.glob("*.csv"):
            try: p.unlink()
            except: pass

def _csv_has_columns(p: Path) -> bool:
    try:
        if not p.exists() or p.stat().st_size == 0:
            return False
        import pandas as pd
        pd.read_csv(p, nrows=0)  # dispara se não houver cabeçalho
        return True
    except Exception:
        return False

# --------------------------------- GUI ---------------------------------
class MVP3App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETL de Mercado — MVP3 (Qt)")
        self.resize(960, 640)
        ipath = _best_icon_path()
        if ipath: self.setWindowIcon(QIcon(str(ipath)))

        self.connected = False  # estado de conexão

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # ---- Aba: Credenciais ----
        self.tab_creds = QWidget(); self.tabs.addTab(self.tab_creds, "Credenciais")
        self._build_tab_creds(self.tab_creds)

        # ---- Aba: Pipeline ----
        self.tab_pipeline = QWidget(); self.tabs.addTab(self.tab_pipeline, "Pipeline")
        self._build_tab_pipeline(self.tab_pipeline)

        # ---- Aba: Exportar Dados (a partir do DB) ----
        self.tab_export = QWidget(); self.tabs.addTab(self.tab_export, "Exportar Dados")
        self._build_tab_export(self.tab_export)

        # ---- Log ----
        self.log = QTextEdit(); self.log.setReadOnly(True)
        root.addWidget(self.log)

        self._apply_dark_theme()

    # ----------------------- ABA: Credenciais -----------------------
    def _build_tab_creds(self, w: QWidget):
        form = QFormLayout(w)
        lbl = QLabel("Informe suas credenciais da corretora.")
        lbl.setStyleSheet("color: orange; font-weight: 600;")
        self.lbl_email = QLabel("E-mail:")
        self.email = QLineEdit()
        self.lbl_senha = QLabel("Senha:")
        self.senha = QLineEdit(); self.senha.setEchoMode(QLineEdit.Password)
        self.conn_status = QLabel("Desconectado")
        self.conn_status.setStyleSheet("color: #AAAAAA; font-weight: 600;")
        self.btn_connect = QPushButton("CONECTAR")
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        # Enter para conectar
        self.email.returnPressed.connect(self.on_connect_clicked)
        self.senha.returnPressed.connect(self.on_connect_clicked)

        form.addRow(lbl)
        form.addRow(self.lbl_email, self.email)
        form.addRow(self.lbl_senha, self.senha)
        form.addRow(self.btn_connect)
        form.addRow(self.conn_status)

    def on_connect_clicked(self):
        if not self.connected:
            # Tentar conectar
            email = self.email.text().strip()
            senha = self.senha.text().strip()
            if not email or not senha:
                QMessageBox.warning(self, "Atenção", "Informe e-mail e senha.")
                return
            try:
                api = extracao.conectar_api(email, senha)
                try:
                    if hasattr(api, "disconnect"): api.disconnect()
                    elif hasattr(api, "close"): api.close()
                except: pass
                # Sucesso
                self.connected = True
                self.conn_status.setText("Conectado")
                self.conn_status.setStyleSheet("color: #00d97e; font-weight: 700;")
                self.btn_connect.setText("DESCONECTAR")
                # Ocultar campos enquanto conectado
                for w in (self.lbl_email, self.email, self.lbl_senha, self.senha):
                    w.setVisible(False)
                self.log.append("✔ Conexão estabelecida com sucesso.")
                # Fechar aba Credenciais e ir para Pipeline
                idx_pipe = self.tabs.indexOf(self.tab_pipeline)
                if idx_pipe != -1:
                    self.tabs.setCurrentIndex(idx_pipe)
                idx_creds = self.tabs.indexOf(self.tab_creds)
                if idx_creds != -1:
                    self.tabs.removeTab(idx_creds)
            except Exception as e:
                self.connected = False
                self.conn_status.setText("Falhou")
                self.conn_status.setStyleSheet("color: #ff5a5f; font-weight: 700;")
                QMessageBox.critical(self, "Erro", f"Não foi possível conectar: {e}")
                self.log.append(f"✖ Falha na conexão: {e}")
        else:
            # Toggle de desconexão quando a aba ainda estiver visível
            self.disconnect(quiet=True)

    def disconnect(self, quiet: bool=False):
        # Reset do estado de conexão e restauração da aba de credenciais
        self.connected = False
        try:
            self.conn_status.setText("Desconectado")
            self.conn_status.setStyleSheet("color: #AAAAAA; font-weight: 600;")
        except Exception:
            pass
        try:
            self.btn_connect.setText("CONECTAR")
        except Exception:
            pass
        # Se a aba de credenciais não existir mais, recria e reanexa
        if not hasattr(self, 'tab_creds') or self.tabs.indexOf(self.tab_creds) == -1:
            self.tab_creds = QWidget()
            self._build_tab_creds(self.tab_creds)
            self.tabs.insertTab(0, self.tab_creds, "Credenciais")
        # Garantir que campos fiquem visíveis
        for w in (getattr(self, 'lbl_email', None), getattr(self, 'email', None), getattr(self, 'lbl_senha', None), getattr(self, 'senha', None)):
            try:
                if w is not None:
                    w.setVisible(True)
            except Exception:
                pass
        if not quiet:
            self.log.append("ℹ️ Sessão desconectada pelo usuário.")
            idx_creds = self.tabs.indexOf(self.tab_creds)
            if idx_creds != -1:
                self.tabs.setCurrentIndex(idx_creds)

    def on_disconnect_clicked(self):
        self.disconnect(quiet=False)

    # ----------------------- ABA: Pipeline -----------------------
    def _build_tab_pipeline(self, w: QWidget):
        outer = QVBoxLayout(w)

        # Parâmetros únicos do pipeline
        form = QFormLayout()
        self.p_par = QLineEdit("EURJPY")
        self.p_tf = QLineEdit("M5")
        self.p_dias = QSpinBox(); self.p_dias.setRange(1, 3650); self.p_dias.setValue(360)
        self.p_janela_sr = QSpinBox(); self.p_janela_sr.setRange(0, 100000); self.p_janela_sr.setValue(48)

        form.addRow("Par:", self.p_par)
        form.addRow("Timeframe:", self.p_tf)
        form.addRow("Dias (histórico):", self.p_dias)
        form.addRow("Janela SR:", self.p_janela_sr)
        outer.addLayout(form)

        # Botões empilhados: Extração, Transformação, Carga
        btn_extr = QPushButton("Rodar Extração → data/raw (sobrescreve)")
        btn_extr.clicked.connect(self.run_extracao)
        btn_tr = QPushButton("Rodar Transformação → data/transformed (sobrescreve)")
        btn_tr.clicked.connect(self.run_transformacao)
        btn_carga = QPushButton("Rodar Carga (data/transformed → DB e limpar)")
        btn_carga.clicked.connect(self.run_carga)

        outer.addWidget(btn_extr)
        outer.addWidget(btn_tr)
        outer.addWidget(btn_carga)

        # Play do pipeline completo
        btn_play = QPushButton("Rodar Pipeline Completo (Extração → Transformação → Carga)")
        btn_play.clicked.connect(self.run_pipeline)
        outer.addWidget(btn_play)

        # Botão DESCONECTAR visível na Pipeline (cinza)
        self.btn_disconnect = QPushButton("DESCONECTAR")
        self.btn_disconnect.clicked.connect(self.on_disconnect_clicked)
        self.btn_disconnect.setStyleSheet("background: #474747; color: #dddddd; font-weight: 600; border: none; padding: 6px 10px;")
        outer.addWidget(self.btn_disconnect)

        outer.addStretch(1)

    # ----------------------- ABA: Exportar Dados -----------------------
    def _build_tab_export(self, w: QWidget):
        form = QFormLayout(w)
        self.exp_par = QLineEdit("EURJPY")
        self.exp_tf = QLineEdit("M5")
        self.exp_dias = QSpinBox(); self.exp_dias.setRange(1, 3650); self.exp_dias.setValue(30)

        form.addRow("Par:", self.exp_par)
        form.addRow("Timeframe:", self.exp_tf)
        form.addRow("Dias (para trás):", self.exp_dias)

        # Features (checkboxes dinâmicos)
        self._features_area = QScrollArea(); self._features_area.setWidgetResizable(True)
        _feat_container = QWidget(); grid = QGridLayout(_feat_container)
        self._feat_checks = []
        cols = 3
        for i, name in enumerate(FEATURE_COLUMNS):
            cb = QCheckBox(name); self._feat_checks.append(cb)
            grid.addWidget(cb, i // cols, i % cols)
        self._features_area.setWidget(_feat_container)
        form.addRow("Features:", self._features_area)

        btn = QPushButton("Exportar Dados (a partir do DB)")
        btn.clicked.connect(self.run_exportar_dados)
        form.addRow(btn)

    # ----------------------- Ações: Extração / Transformação / Carga -----------------------
    def _params(self):
        pair = self.p_par.text().strip().upper()
        tf_s = _tf_to_seconds(self.p_tf.text())
        dias = int(self.p_dias.value())
        janela_sr = int(self.p_janela_sr.value())
        return pair, tf_s, dias, janela_sr

    def run_extracao(self):
        pair, tf_s, dias_ui, _ = self._params()
        with capture_to_log(self.log.append):
            try:
                last = dm.get_last_timestamp(pair, tf_s)
                if last is not None:
                    now_aligned = (int(time.time()) // tf_s) * tf_s
                    delta_days = max(1, (now_aligned - int(last)) // 86400)
                    dias = int(delta_days)
                    self.log.append(f"Extração incremental detectada: {dias} dia(s) adicionais.")
                else:
                    dias = max(1, dias_ui)

                df, src_csv = extracao.extrair_dados(
                    par=pair, timeframe=tf_s, dias=dias,
                    email=self.email.text().strip(), senha=self.senha.text().strip()
                )

                # Validação rápida da resposta
                if getattr(df, "empty", False):
                    raise RuntimeError("Nenhum candle retornado pela extração. Verifique o 'Par' (ex.: use USDCAD em vez de CADUSD) e o período.")

                # Salvar em nome fixo, sobrescrevendo
                dst = fixed_raw_path(pair, tf_s)
                try:
                    safe_overwrite_from_src(Path(src_csv), dst)
                except Exception:
                    safe_overwrite_from_df(df, dst)

                # Verificação do CSV final
                if not _csv_has_columns(dst):
                    raise RuntimeError(f"CSV inválido em {dst}. O provedor pode não suportar o par informado.")

                self.log.append(f"✔ Extração concluída e salva em: {dst}")
                QMessageBox.information(self, "Extração", f"Concluída: {dst}")
            except Exception as e:
                self.log.append(f"Erro na extração: {e}")
                QMessageBox.critical(self, "Erro", str(e))

    def run_transformacao(self):
        pair, tf_s, _, janela_sr = self._params()
        with capture_to_log(self.log.append):
            try:
                raw_csv = fixed_raw_path(pair, tf_s)
                if not _csv_has_columns(raw_csv):
                    raise RuntimeError(
                        f"Base bruta inválida para transformação: {raw_csv}. Execute a Extração novamente com um PAR suportado (ex.: USDCAD, EURUSD, USDJPY)."
                    )

                out_csv = transformacao.transformar_dados(
                    par=pair, timeframe=tf_s, dias=0, horizon=1, janela_sr=janela_sr
                )
                dst = fixed_transformed_path(pair, tf_s)
                try:
                    safe_overwrite_from_src(Path(out_csv), dst)
                except Exception:
                    pass

                if not _csv_has_columns(dst):
                    raise RuntimeError(f"Saída transformada inválida em {dst}. Verifique o script de transformação.")

                self.log.append(f"✔ Transformação concluída e salva em: {dst}")
                QMessageBox.information(self, "Transformação", f"Concluída: {dst}")
            except Exception as e:
                self.log.append(f"Erro na transformação: {e}")
                QMessageBox.critical(self, "Erro", str(e))

    def run_carga(self):
        pair, tf_s, _, _ = self._params()
        with capture_to_log(self.log.append):
            try:
                # Preferir o caminho fixo da transformação
                trans_csv = fixed_transformed_path(pair, tf_s)
                csv_arg = trans_csv if trans_csv.exists() else None
                result = carga.load_transformed(pair, tf_s, csv_path=csv_arg)
                up = result.get("upserts", 0); mxts = result.get("max_ts")
                self.log.append(f"✔ Carga concluída: upserts={up}, max_ts={mxts}")

                # Limpeza dos temporários transformados
                purge_transformed_dir()
                self.log.append("🧹 Diretório data/transformed limpo (temporários removidos).")

                QMessageBox.information(self, "Carga", f"Upserts: {up}\nMAX(ts): {mxts}")
            except Exception as e:
                self.log.append(f"Erro na carga: {e}")
                QMessageBox.critical(self, "Erro", str(e))

    def run_pipeline(self):
        pair, tf_s, dias_ui, janela_sr = self._params()
        with capture_to_log(self.log.append):
            try:
                # 1) Extração
                last = dm.get_last_timestamp(pair, tf_s)
                if last is not None:
                    now_aligned = (int(time.time()) // tf_s) * tf_s
                    dias = max(1, (now_aligned - int(last)) // 86400)
                    self.log.append(f"Extração incremental detectada: {dias} dia(s) adicionais.")
                else:
                    dias = max(1, dias_ui)

                df, src_csv = extracao.extrair_dados(
                    par=pair, timeframe=tf_s, dias=dias,
                    email=self.email.text().strip(), senha=self.senha.text().strip()
                )
                if getattr(df, "empty", False):
                    raise RuntimeError("Nenhum candle retornado. Verifique o 'Par' (ex.: use USDCAD em vez de CADUSD) e o período.")

                raw_dst = fixed_raw_path(pair, tf_s)
                try:
                    safe_overwrite_from_src(Path(src_csv), raw_dst)
                except Exception:
                    safe_overwrite_from_df(df, raw_dst)
                if not _csv_has_columns(raw_dst):
                    raise RuntimeError(f"CSV inválido em {raw_dst} após extração.")
                self.log.append(f"✔ Extração: {raw_dst}")

                # 2) Transformação
                out_csv = transformacao.transformar_dados(pair, tf_s, dias=0, horizon=1, janela_sr=janela_sr)
                trans_dst = fixed_transformed_path(pair, tf_s)
                try:
                    safe_overwrite_from_src(Path(out_csv), trans_dst)
                except Exception:
                    pass
                if not _csv_has_columns(trans_dst):
                    raise RuntimeError(f"Saída transformada inválida em {trans_dst}.")
                self.log.append(f"✔ Transformação: {trans_dst}")

                # 3) Carga
                result = carga.load_transformed(pair, tf_s, csv_path=trans_dst if trans_dst.exists() else None)
                self.log.append(f"✔ Carga: upserts={result.get('upserts')}, max_ts={result.get('max_ts')}")

                # 4) Limpeza de temporários
                purge_transformed_dir()
                self.log.append("🧹 Temporários removidos em data/transformed.")

                QMessageBox.information(self, "Pipeline", "Pipeline concluído com sucesso.")
            except Exception as e:
                self.log.append(f"Erro no pipeline: {e}")
                QMessageBox.critical(self, "Erro", str(e))

    # ----------------------- Exportar dados -----------------------
    def _export_selected_features(self):
        return [cb.text() for cb in getattr(self, "_feat_checks", []) if cb.isChecked()]

    def run_exportar_dados(self):
        pair = self.exp_par.text().strip().upper()
        tf_s = _tf_to_seconds(self.exp_tf.text())
        dias = int(self.exp_dias.value())
        feats = self._export_selected_features() or None

        # Sugestão de nome padrão
        default_name = f"{pair}_{tf_s}_{dias}d.csv"
        default_dir = (ROOT / "data" / "exported").resolve()
        default_dir.mkdir(parents=True, exist_ok=True)
        suggested = str(default_dir / default_name)

        # Diálogo nativo para escolher onde salvar
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar dados como...",
            suggested,
            "CSV Files (*.csv)"
        )
        if not save_path:
            return  # usuário cancelou

        with capture_to_log(self.log.append):
            try:
                # Tenta chamar export_to_csv com out_path se suportado
                out_path = None
                try:
                    import inspect
                    if hasattr(dm, "export_to_csv"):
                        sig = inspect.signature(dm.export_to_csv)
                        if "out_path" in sig.parameters:
                            out_path = dm.export_to_csv(pair=pair, timeframe_s=tf_s, dias=dias, features=feats, out_path=save_path)
                        else:
                            tmp_path = dm.export_to_csv(pair=pair, timeframe_s=tf_s, dias=dias, features=feats)
                            # copia para o destino escolhido
                            shutil.copy2(tmp_path, save_path)
                            out_path = save_path
                    else:
                        dm_path = getattr(dm, "__file__", "<desconhecido>")
                        raise RuntimeError(f"db_manager.export_to_csv() não encontrado. Módulo carregado de: {dm_path}")
                except Exception as inner:
                    raise

                self.log.append(f"✔ Exportação concluída: {out_path}")
                QMessageBox.information(self, "Exportar Dados", f"Concluída: {out_path}")
            except Exception as e:
                self.log.append(f"Erro na exportação: {e}")
                QMessageBox.critical(self, "Erro", str(e))

    # ----------------------- Tema -----------------------
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
        self.setStyleSheet(
            """
            QLabel { color: #e6e6e6; }
            QLineEdit, QSpinBox {
                background: #1f1f1f; color: #f0f0f0; border: 1px solid #333; padding: 4px;
            }
            QPushButton {
                background: #ff6d00; color: #111; font-weight: 600; border: none; padding: 6px 10px;
            }
            QPushButton:hover { background: #ff7f1a; }
            QTabBar::tab { background: #2a2a2a; padding: 6px 12px; margin-right: 4px; }
            QTabBar::tab:selected { background: #ff6d00; color: #111; }
            QTextEdit { background: #151515; color: #dcdcdc; border: 1px solid #333; }
            """
        )

# --------------------------------- Bootstrap ---------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ipath = _best_icon_path()
    if ipath: app.setWindowIcon(QIcon(str(ipath)))
    w = MVP3App()
    w.show()
    sys.exit(app.exec())
