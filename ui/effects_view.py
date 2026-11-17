from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame
)
from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton,
    TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel,
    ComboBox, FluentIcon as FIF, InfoBar
)
from ui.common_widgets import NoWheelSlider
from core.fx_engine import FXEngine
from core.i18n import tr

WORKING_HW_EFFECTS = [
    (3, "TV"),
    (1, "Flash"),
    (2, "Flash 2 (Burst)"),
    (12, "Strobe"),
    (4, "Candle"),
    (5, "Flame")
]

class EffectsView(QWidget):
    effect_triggered = Signal(int, int, int, int)
    stop_effect_requested = Signal()

    def __init__(self, ble_manager, parent=None):
        super().__init__(parent)
        self.ble = ble_manager
        self.fx_engine = FXEngine(ble_manager, self)
        
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # Header
        h_box = QHBoxLayout()
        t_box = QVBoxLayout()
        t_box.setSpacing(4)
        self.title_lbl = TitleLabel(tr("fx_title"), self)
        self.desc_lbl = CaptionLabel(tr("fx_desc"), self)
        self.desc_lbl.setStyleSheet("color: gray;")
        t_box.addWidget(self.title_lbl)
        t_box.addWidget(self.desc_lbl)
        h_box.addLayout(t_box)
        h_box.addStretch()

        self.stop_btn = PrimaryPushButton(FIF.CANCEL, tr("btn_stop_fx"), self)
        self.stop_btn.clicked.connect(self._on_stop)
        h_box.addWidget(self.stop_btn)
        main_layout.addLayout(h_box)

        # Transparent Scroll Area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background: transparent; }")
        c_layout = QVBoxLayout(scroll_content)
        c_layout.setContentsMargins(0, 0, 16, 0)
        c_layout.setSpacing(18)

        # 1. Hardware Effects Card
        hw_card = CardWidget(scroll_content)
        hw_layout = QVBoxLayout(hw_card)
        hw_layout.setContentsMargins(24, 20, 24, 20)
        hw_layout.setSpacing(16)

        self.hw_title = SubtitleLabel(tr("hw_fx_title"), hw_card)
        self.hw_desc = CaptionLabel(tr("hw_fx_desc"), hw_card)
        self.hw_desc.setStyleSheet("color: gray;")
        hw_layout.addWidget(self.hw_title)
        hw_layout.addWidget(self.hw_desc)

        # Sliders for hardware speed & freq
        sliders_row = QHBoxLayout()
        sliders_row.setSpacing(24)

        # Speed
        s_box = QVBoxLayout()
        s_box.setSpacing(6)
        s_header = QHBoxLayout()
        self.lbl_speed_title = BodyLabel(tr("lbl_speed"), hw_card)
        s_header.addWidget(self.lbl_speed_title)
        self.speed_val_label = BodyLabel("100%", hw_card)
        self.speed_val_label.setStyleSheet("color: #0099FF; font-weight: bold;")
        s_header.addWidget(self.speed_val_label)
        s_box.addLayout(s_header)

        self.speed_slider = NoWheelSlider(Qt.Horizontal, hw_card)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(lambda v: self.speed_val_label.setText(f"{v}%"))
        s_box.addWidget(self.speed_slider)
        sliders_row.addLayout(s_box)

        # Frequency
        f_box = QVBoxLayout()
        f_box.setSpacing(6)
        f_header = QHBoxLayout()
        self.lbl_freq_title = BodyLabel(tr("lbl_freq"), hw_card)
        f_header.addWidget(self.lbl_freq_title)
        self.freq_val_label = BodyLabel("1", hw_card)
        self.freq_val_label.setStyleSheet("color: #0099FF; font-weight: bold;")
        f_header.addWidget(self.freq_val_label)
        f_box.addLayout(f_header)

        self.freq_slider = NoWheelSlider(Qt.Horizontal, hw_card)
        self.freq_slider.setRange(0, 20)
        self.freq_slider.setValue(1)
        self.freq_slider.valueChanged.connect(lambda v: self.freq_val_label.setText(str(v)))
        f_box.addWidget(self.freq_slider)
        sliders_row.addLayout(f_box)

        hw_layout.addLayout(sliders_row)

        # Hardware buttons grid (3 columns)
        hw_grid = QGridLayout()
        hw_grid.setSpacing(12)
        cols = 3
        for i, (fx_id, title) in enumerate(WORKING_HW_EFFECTS):
            btn = PushButton(FIF.PLAY, title, hw_card)
            btn.setFixedHeight(42)
            btn.clicked.connect(lambda _, fid=fx_id: self._on_play_hw_fx(fid))
            hw_grid.addWidget(btn, i // cols, i % cols)
        hw_layout.addLayout(hw_grid)

        c_layout.addWidget(hw_card)

        # 2. Software Dynamic Effects Card
        sw_card = CardWidget(scroll_content)
        sw_layout = QVBoxLayout(sw_card)
        sw_layout.setContentsMargins(24, 20, 24, 20)
        sw_layout.setSpacing(16)

        self.sw_title = SubtitleLabel(tr("sw_fx_title"), sw_card)
        self.sw_desc = CaptionLabel(tr("sw_fx_desc"), sw_card)
        self.sw_desc.setStyleSheet("color: gray;")
        sw_layout.addWidget(self.sw_title)
        sw_layout.addWidget(self.sw_desc)

        sw_grid = QHBoxLayout()
        sw_grid.setSpacing(12)

        self.btn_storm = PushButton(FIF.PLAY, tr("btn_storm"), sw_card)
        self.btn_storm.setFixedHeight(44)
        self.btn_storm.clicked.connect(lambda: self._on_play_sw_fx("lightning", tr("btn_storm")))
        sw_grid.addWidget(self.btn_storm)

        self.btn_bulb = PushButton(FIF.PLAY, tr("btn_bulb"), sw_card)
        self.btn_bulb.setFixedHeight(44)
        self.btn_bulb.clicked.connect(lambda: self._on_play_sw_fx("bad_bulb", tr("btn_bulb")))
        sw_grid.addWidget(self.btn_bulb)

        self.btn_breath = PushButton(FIF.PLAY, tr("btn_breathing"), sw_card)
        self.btn_breath.setFixedHeight(44)
        self.btn_breath.clicked.connect(lambda: self._on_play_sw_fx("breathing", tr("btn_breathing")))
        sw_grid.addWidget(self.btn_breath)

        sw_layout.addLayout(sw_grid)
        c_layout.addWidget(sw_card)

        # 3. Effect Constructor Card (DIY Generator)
        diy_card = CardWidget(scroll_content)
        diy_layout = QVBoxLayout(diy_card)
        diy_layout.setContentsMargins(24, 20, 24, 20)
        diy_layout.setSpacing(16)

        self.diy_title = SubtitleLabel(tr("diy_title"), diy_card)
        self.diy_desc = CaptionLabel(tr("diy_desc"), diy_card)
        self.diy_desc.setStyleSheet("color: gray;")
        diy_layout.addWidget(self.diy_title)
        diy_layout.addWidget(self.diy_desc)

        # Range row: Brightness min/max
        b_range_box = QHBoxLayout()
        b_range_box.setSpacing(20)

        min_b_box = QVBoxLayout()
        self.lbl_diy_min_b = BodyLabel(tr("lbl_min_b", 10), diy_card)
        self.slider_diy_min_b = NoWheelSlider(Qt.Horizontal, diy_card)
        self.slider_diy_min_b.setRange(1, 100)
        self.slider_diy_min_b.setValue(10)
        self.slider_diy_min_b.valueChanged.connect(lambda v: self.lbl_diy_min_b.setText(tr("lbl_min_b", v)))
        min_b_box.addWidget(self.lbl_diy_min_b)
        min_b_box.addWidget(self.slider_diy_min_b)
        b_range_box.addLayout(min_b_box)

        max_b_box = QVBoxLayout()
        self.lbl_diy_max_b = BodyLabel(tr("lbl_max_b", 80), diy_card)
        self.slider_diy_max_b = NoWheelSlider(Qt.Horizontal, diy_card)
        self.slider_diy_max_b.setRange(1, 100)
        self.slider_diy_max_b.setValue(80)
        self.slider_diy_max_b.valueChanged.connect(lambda v: self.lbl_diy_max_b.setText(tr("lbl_max_b", v)))
        max_b_box.addWidget(self.lbl_diy_max_b)
        max_b_box.addWidget(self.slider_diy_max_b)
        b_range_box.addLayout(max_b_box)

        diy_layout.addLayout(b_range_box)

        # Range row: Kelvin min/max (clamped to 6500K max)
        k_range_box = QHBoxLayout()
        k_range_box.setSpacing(20)

        min_k_box = QVBoxLayout()
        self.lbl_diy_min_k = BodyLabel(tr("lbl_min_k", 2700), diy_card)
        self.slider_diy_min_k = NoWheelSlider(Qt.Horizontal, diy_card)
        self.slider_diy_min_k.setRange(2700, 6500)
        self.slider_diy_min_k.setSingleStep(100)
        self.slider_diy_min_k.setValue(2700)
        self.slider_diy_min_k.valueChanged.connect(lambda v: self.lbl_diy_min_k.setText(tr("lbl_min_k", v)))
        min_k_box.addWidget(self.lbl_diy_min_k)
        min_k_box.addWidget(self.slider_diy_min_k)
        k_range_box.addLayout(min_k_box)

        max_k_box = QVBoxLayout()
        self.lbl_diy_max_k = BodyLabel(tr("lbl_max_k", 5600), diy_card)
        self.slider_diy_max_k = NoWheelSlider(Qt.Horizontal, diy_card)
        self.slider_diy_max_k.setRange(2700, 6500)
        self.slider_diy_max_k.setSingleStep(100)
        self.slider_diy_max_k.setValue(5600)
        self.slider_diy_max_k.valueChanged.connect(lambda v: self.lbl_diy_max_k.setText(tr("lbl_max_k", v)))
        max_k_box.addWidget(self.lbl_diy_max_k)
        max_k_box.addWidget(self.slider_diy_max_k)
        k_range_box.addLayout(max_k_box)

        diy_layout.addLayout(k_range_box)

        # Options: Waveform and Speed
        opts_row = QHBoxLayout()
        opts_row.setSpacing(20)

        wave_box = QVBoxLayout()
        self.lbl_wave = BodyLabel(tr("lbl_wave"), diy_card)
        wave_box.addWidget(self.lbl_wave)
        self.combo_wave = ComboBox(diy_card)
        self._populate_wave_combo()
        wave_box.addWidget(self.combo_wave)
        opts_row.addLayout(wave_box)

        speed_box = QVBoxLayout()
        self.lbl_diy_speed = BodyLabel(tr("lbl_period", 3.0), diy_card)
        self.slider_diy_speed = NoWheelSlider(Qt.Horizontal, diy_card)
        self.slider_diy_speed.setRange(5, 100)
        self.slider_diy_speed.setValue(30)
        self.slider_diy_speed.valueChanged.connect(lambda v: self.lbl_diy_speed.setText(tr("lbl_period", v/10.0)))
        speed_box.addWidget(self.lbl_diy_speed)
        speed_box.addWidget(self.slider_diy_speed)
        opts_row.addLayout(speed_box)

        diy_layout.addLayout(opts_row)

        # DIY Start Button
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_run_diy = PrimaryPushButton(FIF.PLAY, tr("btn_run_diy"), diy_card)
        self.btn_run_diy.clicked.connect(self._on_run_diy)
        btn_box.addWidget(self.btn_run_diy)
        diy_layout.addLayout(btn_box)

        c_layout.addWidget(diy_card)
        c_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _populate_wave_combo(self):
        curr_idx = self.combo_wave.currentIndex() if self.combo_wave.count() > 0 else 0
        self.combo_wave.clear()
        self.combo_wave.addItems([tr("wave_sine"), tr("wave_pulse"), tr("wave_chaos")])
        self.combo_wave.setCurrentIndex(max(0, curr_idx))

    def retranslate_ui(self):
        self.title_lbl.setText(tr("fx_title"))
        self.desc_lbl.setText(tr("fx_desc"))
        self.stop_btn.setText(tr("btn_stop_fx"))
        self.hw_title.setText(tr("hw_fx_title"))
        self.hw_desc.setText(tr("hw_fx_desc"))
        self.lbl_speed_title.setText(tr("lbl_speed"))
        self.lbl_freq_title.setText(tr("lbl_freq"))
        self.sw_title.setText(tr("sw_fx_title"))
        self.sw_desc.setText(tr("sw_fx_desc"))
        self.btn_storm.setText(tr("btn_storm"))
        self.btn_bulb.setText(tr("btn_bulb"))
        self.btn_breath.setText(tr("btn_breathing"))
        self.diy_title.setText(tr("diy_title"))
        self.diy_desc.setText(tr("diy_desc"))
        self.lbl_diy_min_b.setText(tr("lbl_min_b", self.slider_diy_min_b.value()))
        self.lbl_diy_max_b.setText(tr("lbl_max_b", self.slider_diy_max_b.value()))
        self.lbl_diy_min_k.setText(tr("lbl_min_k", self.slider_diy_min_k.value()))
        self.lbl_diy_max_k.setText(tr("lbl_max_k", self.slider_diy_max_k.value()))
        self.lbl_wave.setText(tr("lbl_wave"))
        self.lbl_diy_speed.setText(tr("lbl_period", self.slider_diy_speed.value() / 10.0))
        self.btn_run_diy.setText(tr("btn_run_diy"))
        self._populate_wave_combo()

    def _connect_signals(self):
        self.fx_engine.fx_stopped.connect(self._on_engine_stopped)

    def _on_play_hw_fx(self, fx_id):
        self.fx_engine.stop()
        speed = self.speed_slider.value()
        freq = self.freq_slider.value()
        self.fx_engine.start_hardware_fx(fx_id, speed, freq)
        InfoBar.success(tr("fx_title"), f"Hardware Mode #{fx_id}", parent=self, duration=1500)

    def _on_play_sw_fx(self, fx_type, name):
        self.fx_engine.start_software_fx(fx_type)
        InfoBar.success(tr("fx_title"), f"{name}", parent=self, duration=1500)

    def _on_run_diy(self):
        idx = self.combo_wave.currentIndex()
        wave = "sine" if idx == 0 else ("pulse" if idx == 1 else "chaos")
        params = {
            "min_b": min(self.slider_diy_min_b.value(), self.slider_diy_max_b.value()),
            "max_b": max(self.slider_diy_min_b.value(), self.slider_diy_max_b.value()),
            "min_k": min(self.slider_diy_min_k.value(), self.slider_diy_max_k.value()),
            "max_k": max(self.slider_diy_min_k.value(), self.slider_diy_max_k.value()),
            "speed_sec": self.slider_diy_speed.value() / 10.0,
            "wave": wave
        }
        self.fx_engine.start_software_fx("custom", params)
        InfoBar.success(tr("diy_title"), tr("btn_run_diy"), parent=self, duration=1500)

    def _on_stop(self):
        self.fx_engine.stop()
        self.stop_effect_requested.emit()
        InfoBar.info(tr("fx_stopped_title"), tr("fx_stopped_msg"), parent=self, duration=1500)

    def _on_engine_stopped(self):
        pass
