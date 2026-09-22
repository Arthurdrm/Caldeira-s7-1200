"""Interface Gráfica HMI / SCADA para Simulação da Caldeira Siemens S7-1200.
Desenvolvida com PySide6 e componentes visuais industriais.
"""

import sys
import time
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QCheckBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QFrame, QGroupBox, QSplitter
)

from src.simulador.plc_s7_1200 import PLCS71200Caldeira
from src.simulador.boiler_physics import BoilerPhysics

class BoilerVesselWidget(QWidget):
    """Widget de renderização visual personalizada do vaso de pressão da caldeira."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 380)
        self.water_level: float = 0.0
        self.temperature: float = 0.0
        self.pressure: float = 0.0
        self.valvula_agua: bool = False
        self.valvula_vapor: bool = False
        self.valvula_alivio: bool = False
        self.queimadores: list[bool] = [False] * 6

    def update_states(self, water: float, temp: float, pres: float,
                      v_agua: bool, v_vapor: bool, v_alivio: bool, burners: list[bool]):
        self.water_level = water
        self.temperature = temp
        self.pressure = pres
        self.valvula_agua = v_agua
        self.valvula_vapor = v_vapor
        self.valvula_alivio = v_alivio
        self.queimadores = burners
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Fundo do sinótico
        painter.fillRect(0, 0, w, h, QColor(22, 25, 30))

        # Coordenadas do tambor/cilindro da caldeira
        cx = int(w * 0.22)
        cy = int(h * 0.18)
        cw = int(w * 0.56)
        ch = int(h * 0.60)

        # 1. LINHA DE ENTRADA DE ÁGUA (Esquerda)
        pipe_y = cy + int(ch * 0.70)
        water_color = QColor(41, 128, 185) if self.valvula_agua else QColor(70, 75, 80)
        painter.setPen(QPen(water_color, 12))
        painter.drawLine(15, pipe_y, cx, pipe_y)

        # Indicador Válvula de Água Q0.0
        vx = (15 + cx) // 2
        self._draw_valve(painter, vx, pipe_y, self.valvula_agua, "Q0.0 ÁGUA")

        # 2. LINHA DE SAÍDA DE VAPOR (Direita)
        steam_y = cy + int(ch * 0.15)
        steam_color = QColor(0, 210, 255) if self.valvula_vapor else QColor(70, 75, 80)
        painter.setPen(QPen(steam_color, 14))
        painter.drawLine(cx + cw, steam_y, w - 15, steam_y)

        # Indicador Válvula de Vapor Q0.1
        svx = (cx + cw + w - 15) // 2
        self._draw_valve(painter, svx, steam_y, self.valvula_vapor, "Q0.1 VAPOR", QColor(0, 200, 255))

        # 3. VÁLVULA DE ALÍVIO Q0.2 (Topo Central)
        relief_x = cx + cw // 2
        relief_color = QColor(231, 76, 60) if self.valvula_alivio else QColor(70, 75, 80)
        painter.setPen(QPen(relief_color, 10))
        painter.drawLine(relief_x, cy, relief_x, cy - 35)
        self._draw_valve(painter, relief_x, cy - 35, self.valvula_alivio, "Q0.2 ALÍVIO", QColor(255, 70, 70))

        # 4. CASCO DE AÇO DA CALDEIRA (TAMBOR CILÍNDRICO)
        drum_gradient = QLinearGradient(cx, cy, cx + cw, cy)
        drum_gradient.setColorAt(0.0, QColor(45, 52, 60))
        drum_gradient.setColorAt(0.5, QColor(75, 85, 96))
        drum_gradient.setColorAt(1.0, QColor(45, 52, 60))

        painter.setPen(QPen(QColor(120, 130, 145), 3))
        painter.setBrush(QBrush(drum_gradient))
        painter.drawRoundedRect(cx, cy, cw, ch, 28, 28)

        # 5. VISOR INTERNO DE NÍVEL DE ÁGUA E VAPOR
        inner_margin = 8
        ix = cx + inner_margin
        iy = cy + inner_margin
        iw = cw - 2 * inner_margin
        ih = ch - 2 * inner_margin

        # Fundo do vapor interno
        vapor_gradient = QLinearGradient(ix, iy, ix, iy + ih)
        vapor_gradient.setColorAt(0.0, QColor(30, 45, 55, 230))
        vapor_gradient.setColorAt(1.0, QColor(20, 30, 40, 230))
        painter.fillRect(ix, iy, iw, ih, QBrush(vapor_gradient))

        # Volume de Água
        water_height = int((self.water_level / 100.0) * ih)
        wy = iy + ih - water_height

        water_gradient = QLinearGradient(ix, wy, ix, iy + ih)
        water_gradient.setColorAt(0.0, QColor(41, 128, 185, 220))
        water_gradient.setColorAt(1.0, QColor(24, 80, 130, 250))
        painter.fillRect(ix, wy, iw, water_height, QBrush(water_gradient))

        # Linha de marcação de setpoint: 50% (Liga Água) e 75% (Desliga Água)
        y50 = iy + ih - int(0.50 * ih)
        painter.setPen(QPen(QColor(241, 196, 15, 180), 1, Qt.DashLine))
        painter.drawLine(ix, y50, ix + iw, y50)
        painter.drawText(ix + 10, y50 - 4, "MÍN: 50%")

        y75 = iy + ih - int(0.75 * ih)
        painter.setPen(QPen(QColor(46, 204, 113, 180), 1, Qt.DashLine))
        painter.drawLine(ix, y75, ix + iw, y75)
        painter.drawText(ix + 10, y75 - 4, "MÁX: 75%")

        # 6. BANNER DE INFORMAÇÃO NO CORPO DA CALDEIRA
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        info_txt = f"NÍVEL: {self.water_level:.1f}%  |  TEMP: {self.temperature:.1f}%  |  PRESSÃO: {self.pressure:.1f}%"
        painter.drawText(ix + 15, iy + 25, info_txt)

        # 7. OS 6 QUEIMADORES NA BASE DA CALDEIRA (Q0.3 a Q1.0)
        burner_y = cy + ch + 12
        burner_w = cw // 6
        for i, ativo in enumerate(self.queimadores):
            bx = cx + i * burner_w + (burner_w - 24) // 2
            self._draw_burner(painter, bx, burner_y, ativo, f"B{i+1}")

    def _draw_valve(self, painter: QPainter, x: int, y: int, is_open: bool, label: str, color_on=QColor(46, 204, 113)):
        color = color_on if is_open else QColor(100, 105, 115)
        # Triângulos da válvula
        p1 = [(x - 14, y - 10), (x, y), (x - 14, y + 10)]
        p2 = [(x + 14, y - 10), (x, y), (x + 14, y + 10)]
        painter.setPen(QPen(QColor(30, 30, 30), 1))
        painter.setBrush(QBrush(color))
        painter.drawPolygon([QPoint(px, py) for px, py in p1])
        painter.drawPolygon([QPoint(px, py) for px, py in p2])

        # Rótulo
        painter.setPen(QColor(200, 210, 220))
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        status = "ABERTA" if is_open else "FECHADA"
        painter.drawText(x - 28, y + 24, f"{label}")
        painter.drawText(x - 22, y + 36, f"[{status}]")

    def _draw_burner(self, painter: QPainter, x: int, y: int, ativo: bool, label: str):
        # Bocal do queimador
        painter.setPen(QPen(QColor(50, 55, 60), 2))
        painter.setBrush(QBrush(QColor(80, 85, 95)))
        painter.drawRect(x + 2, y + 25, 20, 10)

        # Chama quando ativo
        if ativo:
            flame_grad = QRadialGradient(x + 12, y + 12, 16)
            flame_grad.setColorAt(0.0, QColor(255, 255, 180, 240))
            flame_grad.setColorAt(0.4, QColor(255, 140, 0, 230))
            flame_grad.setColorAt(1.0, QColor(220, 20, 60, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(flame_grad))
            painter.drawEllipse(x - 2, y - 2, 28, 30)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(40, 45, 50)))
            painter.drawEllipse(x + 4, y + 8, 16, 16)

        painter.setPen(QColor(180, 190, 200))
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        painter.drawText(x + 3, y + 48, label)


class MainWindowSimulador(QMainWindow):
    """Janela principal do Simulador de Caldeira Siemens S7-1200."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Siemens SIMATIC S7-1200 — Simulador de Caldeira Industrial")
        self.resize(1180, 780)

        self.plc = PLCS71200Caldeira()
        self.physics = BoilerPhysics()

        self._init_ui()
        self._apply_dark_theme()

        # Timer de Scan do CLP (50ms = 20Hz, padrão de automação)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step_simulation)
        self.timer.start(50)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. CABEÇALHO COM STATUS DO CLP
        header = QFrame()
        header.setStyleSheet("background-color: #1e2229; border-radius: 8px; padding: 10px;")
        h_layout = QHBoxLayout(header)

        title = QLabel("SIEMENS S7-1200  |  SISTEMA DE CONTROLE DE CALDEIRA")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setStyleSheet("color: #00d2ff;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        self.lbl_status_cpu = QLabel("● CPU S7-1200: RUN")
        self.lbl_status_cpu.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 13px;")
        h_layout.addWidget(self.lbl_status_cpu)

        self.lbl_sistema_operacao = QLabel("ESTADO: REPOUSO")
        self.lbl_sistema_operacao.setStyleSheet("color: #f39c12; font-weight: bold; font-size: 13px; margin-left: 20px;")
        h_layout.addWidget(self.lbl_sistema_operacao)

        main_layout.addWidget(header)

        # 2. CONTEÚDO PRINCIPAL (SPLITTER: SINÓTICO / PAINEL DE CONTROLE)
        content_splitter = QSplitter(Qt.Horizontal)

        # Lado Esquerdo: Sinótico da Caldeira + Mesa de Botoeiras
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Sinótico Animado
        self.vessel_widget = BoilerVesselWidget()
        left_layout.addWidget(self.vessel_widget, 4)

        # Mesa de Botoeiras Industriais (Entradas Digitais)
        panel_group = QGroupBox("MESA DE COMANDO INDUSTRIAL (ENTRADAS %I0.0 .. %I0.3)")
        panel_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ecf0f1; border: 1px solid #34495e; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        panel_layout = QHBoxLayout(panel_group)

        # Botão LIGA I0.0 (NA)
        self.btn_liga = QPushButton("▶ LIGA (I0.0)")
        self.btn_liga.setMinimumHeight(44)
        self.btn_liga.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; font-size: 12px; border-radius: 6px;")
        self.btn_liga.pressed.connect(lambda: self._set_button("liga", True))
        self.btn_liga.released.connect(lambda: self._set_button("liga", False))
        panel_layout.addWidget(self.btn_liga)

        # Botão DESLIGA I0.1 (NF)
        self.btn_desliga = QPushButton("⏹ DESLIGA (I0.1)")
        self.btn_desliga.setMinimumHeight(44)
        self.btn_desliga.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; font-size: 12px; border-radius: 6px;")
        self.btn_desliga.pressed.connect(lambda: self._set_button("desliga", False))
        self.btn_desliga.released.connect(lambda: self._set_button("desliga", True))
        panel_layout.addWidget(self.btn_desliga)

        # Botão RESET I0.2 (NF)
        self.btn_reset = QPushButton("🔄 RESET (I0.2)")
        self.btn_reset.setMinimumHeight(44)
        self.btn_reset.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; font-size: 12px; border-radius: 6px;")
        self.btn_reset.pressed.connect(lambda: self._set_button("reset", False))
        self.btn_reset.released.connect(lambda: self._set_button("reset", True))
        panel_layout.addWidget(self.btn_reset)

        # Botão EMERGÊNCIA I0.3 (NF Trava)
        self.btn_emergencia = QPushButton("🚨 EMERGÊNCIA (I0.3)")
        self.btn_emergencia.setMinimumHeight(44)
        self.btn_emergencia.setCheckable(True)
        self.btn_emergencia.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; font-size: 12px; border-radius: 6px; } QPushButton:checked { background-color: #7f1d1d; border: 3px solid #ff0000; }")
        self.btn_emergencia.toggled.connect(self._toggle_emergencia)
        panel_layout.addWidget(self.btn_emergencia)

        # Lâmpadas Piloto
        self.lbl_lamp_operacao = QLabel("EM OPERAÇÃO")
        self.lbl_lamp_operacao.setAlignment(Qt.AlignCenter)
        self.lbl_lamp_operacao.setStyleSheet("background-color: #2c3e50; color: #7f8c8d; font-weight: bold; border-radius: 18px; min-width: 100px; padding: 10px;")
        panel_layout.addWidget(self.lbl_lamp_operacao)

        self.lbl_lamp_emergencia = QLabel("EMERGÊNCIA")
        self.lbl_lamp_emergencia.setAlignment(Qt.AlignCenter)
        self.lbl_lamp_emergencia.setStyleSheet("background-color: #2c3e50; color: #7f8c8d; font-weight: bold; border-radius: 18px; min-width: 100px; padding: 10px;")
        panel_layout.addWidget(self.lbl_lamp_emergencia)

        left_layout.addWidget(panel_group, 1)
        content_splitter.addWidget(left_box)

        # Lado Direito: Sliders de Injeção de Falhas + Tabela de Tags + Console de Eventos
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Seletor de Modo Físico
        ctrl_group = QGroupBox("MODO DE SIMULAÇÃO / INJEÇÃO DE FALHAS")
        ctrl_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ecf0f1; border: 1px solid #34495e; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self.chk_auto_physics = QCheckBox("Simulação Física Automática (Balanço Térmico & Fluido)")
        self.chk_auto_physics.setChecked(True)
        self.chk_auto_physics.toggled.connect(self._toggle_auto_physics)
        ctrl_layout.addWidget(self.chk_auto_physics)

        # Slider Nível
        h_sl1 = QHBoxLayout()
        h_sl1.addWidget(QLabel("Nível H2O (%):"))
        self.sl_nivel = QSlider(Qt.Horizontal)
        self.sl_nivel.setRange(0, 100)
        self.sl_nivel.setValue(int(self.physics.water_level))
        self.sl_nivel.valueChanged.connect(self._on_slider_nivel)
        h_sl1.addWidget(self.sl_nivel)
        self.lbl_val_nivel = QLabel(f"{self.physics.water_level:.1f}%")
        h_sl1.addWidget(self.lbl_val_nivel)
        ctrl_layout.addLayout(h_sl1)

        # Slider Pressão
        h_sl2 = QHBoxLayout()
        h_sl2.addWidget(QLabel("Pressão (%):"))
        self.sl_pressao = QSlider(Qt.Horizontal)
        self.sl_pressao.setRange(0, 100)
        self.sl_pressao.setValue(int(self.physics.pressure))
        self.sl_pressao.valueChanged.connect(self._on_slider_pressao)
        h_sl2.addWidget(self.sl_pressao)
        self.lbl_val_pressao = QLabel(f"{self.physics.pressure:.1f}%")
        h_sl2.addWidget(self.lbl_val_pressao)
        ctrl_layout.addLayout(h_sl2)

        # Slider Temperatura
        h_sl3 = QHBoxLayout()
        h_sl3.addWidget(QLabel("Temp (%):"))
        self.sl_temp = QSlider(Qt.Horizontal)
        self.sl_temp.setRange(0, 100)
        self.sl_temp.setValue(int(self.physics.temperature))
        self.sl_temp.valueChanged.connect(self._on_slider_temp)
        h_sl3.addWidget(self.sl_temp)
        self.lbl_val_temp = QLabel(f"{self.physics.temperature:.1f}%")
        h_sl3.addWidget(self.lbl_val_temp)
        ctrl_layout.addLayout(h_sl3)

        right_layout.addWidget(ctrl_group)

        # Tabela de Tags S7-1200
        tag_group = QGroupBox("TAGS DO CLP SIEMENS (%I, %IW, %Q)")
        tag_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ecf0f1; border: 1px solid #34495e; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        tag_layout = QVBoxLayout(tag_group)

        self.tag_table = QTableWidget(7, 3)
        self.tag_table.setHorizontalHeaderLabels(["Endereço", "Nome da Tag", "Valor"])
        self.tag_table.verticalHeader().setVisible(False)
        self.tag_table.setStyleSheet("background-color: #1a1d24; color: #ecf0f1; gridline-color: #2c3e50;")
        tag_layout.addWidget(self.tag_table)
        right_layout.addWidget(tag_group, 2)

        # Console de Eventos do CLP
        log_group = QGroupBox("LOG DE EVENTOS & INTERTRAVAMENTOS DO S7-1200")
        log_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ecf0f1; border: 1px solid #34495e; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        log_layout = QVBoxLayout(log_group)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #121418; color: #2ecc71; font-family: monospace; font-size: 11px;")
        log_layout.addWidget(self.txt_log)
        right_layout.addWidget(log_group, 2)

        content_splitter.addWidget(right_box)
        content_splitter.setSizes([680, 480])

        main_layout.addWidget(content_splitter)

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #16191f; }
            QLabel { color: #ecf0f1; }
            QSlider::groove:horizontal { height: 6px; background: #34495e; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #00d2ff; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ecf0f1; width: 16px; margin-top: -5px; margin-bottom: -5px; border-radius: 8px; }
            QCheckBox { color: #ecf0f1; font-weight: bold; }
        """)

    def _set_button(self, btn_name: str, state: bool):
        if btn_name == "liga":
            self.plc.botao_liga = state
        elif btn_name == "desliga":
            self.plc.botao_desliga = state
        elif btn_name == "reset":
            self.plc.botao_reset = state

    def _toggle_emergencia(self, checked: bool):
        # Botão com retenção: Pressionado -> Contato NF abre (False)
        self.plc.botao_emergencia = not checked

    def _toggle_auto_physics(self, checked: bool):
        self.physics.auto_mode = checked

    def _on_slider_nivel(self, val: int):
        if not self.physics.auto_mode:
            self.physics.water_level = float(val)

    def _on_slider_pressao(self, val: int):
        if not self.physics.auto_mode:
            self.physics.pressure = float(val)

    def _on_slider_temp(self, val: int):
        if not self.physics.auto_mode:
            self.physics.temperature = float(val)

    def _step_simulation(self):
        dt = 0.05  # 50ms

        # 1. Executa física da caldeira
        self.physics.update(
            dt=dt,
            valvula_agua=self.plc.valvula_agua,
            valvula_vapor=self.plc.valvula_vapor,
            valvula_alivio=self.plc.valvula_alivio,
            qtd_queimadores=self.plc.qtd_queimadores_ativos
        )

        # 2. Converte estados físicos para palavras analógicas brutas do S7
        raw_n, raw_p, raw_t = self.physics.get_raw_signals()
        self.plc.ai_nivel_raw = raw_n
        self.plc.ai_pressao_raw = raw_p
        self.plc.ai_temp_raw = raw_t

        # 3. Executa Scan Cycle do CLP Siemens
        events = self.plc.scan_cycle()

        for ev in events:
            timestamp = time.strftime("%H:%M:%S")
            self.txt_log.append(f"[{timestamp}] {ev}")

        # 4. Atualiza Sliders se estiver no modo automático
        if self.physics.auto_mode:
            self.sl_nivel.blockSignals(True)
            self.sl_nivel.setValue(int(self.physics.water_level))
            self.sl_nivel.blockSignals(False)

            self.sl_pressao.blockSignals(True)
            self.sl_pressao.setValue(int(self.physics.pressure))
            self.sl_pressao.blockSignals(False)

            self.sl_temp.blockSignals(True)
            self.sl_temp.setValue(int(self.physics.temperature))
            self.sl_temp.blockSignals(False)

        self.lbl_val_nivel.setText(f"{self.physics.water_level:.1f}%")
        self.lbl_val_pressao.setText(f"{self.physics.pressure:.1f}%")
        self.lbl_val_temp.setText(f"{self.physics.temperature:.1f}%")

        # 5. Atualiza Sinótico Gráfico
        self.vessel_widget.update_states(
            water=self.physics.water_level,
            temp=self.physics.temperature,
            pres=self.physics.pressure,
            v_agua=self.plc.valvula_agua,
            v_vapor=self.plc.valvula_vapor,
            v_alivio=self.plc.valvula_alivio,
            burners=self.plc.queimadores
        )

        # 6. Atualiza Lâmpadas Piloto
        if self.plc.lamp_em_operacao:
            self.lbl_lamp_operacao.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; border-radius: 18px; min-width: 100px; padding: 10px;")
            self.lbl_sistema_operacao.setText("ESTADO: EM OPERAÇÃO")
            self.lbl_sistema_operacao.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 13px; margin-left: 20px;")
        elif self.plc.lamp_emergencia:
            # Efeito piscante de emergência
            blink = int(time.time() * 3) % 2 == 0
            bg = "#e74c3c" if blink else "#7f1d1d"
            self.lbl_lamp_emergencia.setStyleSheet(f"background-color: {bg}; color: white; font-weight: bold; border-radius: 18px; min-width: 100px; padding: 10px;")
            self.lbl_sistema_operacao.setText("ESTADO: 🚨 PARADA DE EMERGÊNCIA!")
            self.lbl_sistema_operacao.setStyleSheet("color: #ff3838; font-weight: bold; font-size: 13px; margin-left: 20px;")
        else:
            self.lbl_lamp_operacao.setStyleSheet("background-color: #2c3e50; color: #7f8c8d; font-weight: bold; border-radius: 18px; min-width: 100px; padding: 10px;")
            self.lbl_lamp_emergencia.setStyleSheet("background-color: #2c3e50; color: #7f8c8d; font-weight: bold; border-radius: 18px; min-width: 100px; padding: 10px;")
            self.lbl_sistema_operacao.setText("ESTADO: REPOUSO / PARADO")
            self.lbl_sistema_operacao.setStyleSheet("color: #f39c12; font-weight: bold; font-size: 13px; margin-left: 20px;")

        # 7. Atualiza Tabela de Tags
        tags_data = [
            ("%IW64", "AI_Nivel_Raw", f"{self.plc.ai_nivel_raw} ({self.plc.nivel_perc:.1f}%)"),
            ("%IW66", "AI_Pressao_Raw", f"{self.plc.ai_pressao_raw} ({self.plc.pressao_perc:.1f}%)"),
            ("%IW68", "AI_Temp_Raw", f"{self.plc.ai_temp_raw} ({self.plc.temp_perc:.1f}%)"),
            ("%Q0.0", "Valvula_Agua", "1 (LIGADA)" if self.plc.valvula_agua else "0 (DESLIGADA)"),
            ("%Q0.1", "Valvula_Vapor", "1 (ABERTA)" if self.plc.valvula_vapor else "0 (FECHADA)"),
            ("%Q0.2", "Valvula_Alivio", "1 (ALÍVIO!)" if self.plc.valvula_alivio else "0 (NORMAL)"),
            ("%Q0.3..Q1.0", "Queimadores (1..6)", f"{self.plc.qtd_queimadores_ativos} / 6 ATIVOS"),
        ]

        for row, (addr, name, val) in enumerate(tags_data):
            self.tag_table.setItem(row, 0, QTableWidgetItem(addr))
            self.tag_table.setItem(row, 1, QTableWidgetItem(name))
            self.tag_table.setItem(row, 2, QTableWidgetItem(val))
