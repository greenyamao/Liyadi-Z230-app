import uuid
from PySide6.QtCore import Qt, Signal, QTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QTimeEdit
)
from qfluentwidgets import (
    CardWidget, SwitchButton, PushButton, PrimaryPushButton, TransparentPushButton,
    TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel,
    LineEdit, FluentIcon as FIF, InfoBar, InfoBarPosition
)
from ui.common_widgets import NoWheelSpinBox
from core.i18n import tr

class SchedulerView(QWidget):
    rules_changed = Signal(list)

    def __init__(self, scheduler_engine, initial_rules=None, parent=None):
        super().__init__(parent)
        self.engine = scheduler_engine
        self.rules = initial_rules or []
        self._init_ui()
        self._connect_engine()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # Header
        h_box = QHBoxLayout()
        t_box = QVBoxLayout()
        t_box.setSpacing(4)
        self.title = TitleLabel(tr("schedule_title"), self)
        self.desc = CaptionLabel(tr("schedule_desc"), self)
        self.desc.setStyleSheet("color: gray;")
        t_box.addWidget(self.title)
        t_box.addWidget(self.desc)
        h_box.addLayout(t_box)
        h_box.addStretch()
        main_layout.addLayout(h_box)

        # Scroll Area for rules and creator
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background: transparent; }")
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 16, 0)
        self.scroll_layout.setSpacing(16)

        # Container for active rule cards
        self.rules_container = QVBoxLayout()
        self.rules_container.setSpacing(12)
        self.scroll_layout.addLayout(self.rules_container)

        # Add Rule Card (Creator)
        self._create_add_rule_card()
        self.scroll_layout.addWidget(self.add_card)
        self.scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        self._render_rules()

    def _create_add_rule_card(self):
        self.add_card = CardWidget(self)
        c_layout = QVBoxLayout(self.add_card)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.setSpacing(16)

        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        self.c_title = SubtitleLabel(tr("card_new_rule"), self.add_card)
        self.c_desc = CaptionLabel(tr("card_new_rule_desc"), self.add_card)
        self.c_desc.setStyleSheet("color: gray;")
        header_box.addWidget(self.c_title)
        header_box.addWidget(self.c_desc)
        c_layout.addLayout(header_box)

        # Row 1: Name and Start Time
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        name_box = QVBoxLayout()
        self.lbl_name = BodyLabel(tr("lbl_rule_name"), self.add_card)
        name_box.addWidget(self.lbl_name)
        self.in_name = LineEdit(self.add_card)
        self.in_name.setText(tr("def_rule_piter"))
        name_box.addWidget(self.in_name)
        row1.addLayout(name_box, stretch=2)

        time_box = QVBoxLayout()
        self.lbl_time = BodyLabel(tr("lbl_start_time"), self.add_card)
        time_box.addWidget(self.lbl_time)
        self.in_time = QTimeEdit(self.add_card)
        self.in_time.setDisplayFormat("HH:mm")
        self.in_time.setTime(QTime(13, 0))
        time_box.addWidget(self.in_time)
        row1.addLayout(time_box, stretch=1)

        c_layout.addLayout(row1)

        # Row 2: Target Brightness and Target Kelvin (clamped to 6500K)
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        target_b_box = QVBoxLayout()
        self.lbl_tb = BodyLabel(tr("lbl_target_b"), self.add_card)
        target_b_box.addWidget(self.lbl_tb)
        self.in_target_b = NoWheelSpinBox(self.add_card)
        self.in_target_b.setRange(0, 100)
        self.in_target_b.setValue(80)
        target_b_box.addWidget(self.in_target_b)
        row2.addLayout(target_b_box)

        target_k_box = QVBoxLayout()
        self.lbl_tk = BodyLabel(tr("lbl_target_k"), self.add_card)
        target_k_box.addWidget(self.lbl_tk)
        self.in_target_k = NoWheelSpinBox(self.add_card)
        self.in_target_k.setRange(2700, 6500)
        self.in_target_k.setSingleStep(100)
        self.in_target_k.setValue(5600)
        target_k_box.addWidget(self.in_target_k)
        row2.addLayout(target_k_box)

        c_layout.addLayout(row2)

        # Row 3: Step Interval, Step Brightness, Step Kelvin
        row3 = QHBoxLayout()
        row3.setSpacing(16)

        interval_box = QVBoxLayout()
        self.lbl_int = BodyLabel(tr("lbl_interval"), self.add_card)
        interval_box.addWidget(self.lbl_int)
        self.in_interval = NoWheelSpinBox(self.add_card)
        self.in_interval.setRange(1, 120)
        self.in_interval.setValue(10)
        interval_box.addWidget(self.in_interval)
        row3.addLayout(interval_box)

        step_b_box = QVBoxLayout()
        self.lbl_sb = BodyLabel(tr("lbl_step_b"), self.add_card)
        step_b_box.addWidget(self.lbl_sb)
        self.in_step_b = NoWheelSpinBox(self.add_card)
        self.in_step_b.setRange(1, 50)
        self.in_step_b.setValue(5)
        step_b_box.addWidget(self.in_step_b)
        row3.addLayout(step_b_box)

        step_k_box = QVBoxLayout()
        self.lbl_sk = BodyLabel(tr("lbl_step_k"), self.add_card)
        step_k_box.addWidget(self.lbl_sk)
        self.in_step_k = NoWheelSpinBox(self.add_card)
        self.in_step_k.setRange(50, 1000)
        self.in_step_k.setSingleStep(50)
        self.in_step_k.setValue(200)
        step_k_box.addWidget(self.in_step_k)
        row3.addLayout(step_k_box)

        c_layout.addLayout(row3)

        # Button
        b_box = QHBoxLayout()
        b_box.addStretch()
        self.add_btn = PrimaryPushButton(FIF.ADD, tr("btn_add_rule"), self.add_card)
        self.add_btn.clicked.connect(self._on_add_rule)
        b_box.addWidget(self.add_btn)
        c_layout.addLayout(b_box)

    def _render_rules(self):
        # Clear existing cards in container
        while self.rules_container.count():
            item = self.rules_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for rule in self.rules:
            card = CardWidget(self)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(22, 16, 22, 16)
            card_layout.setSpacing(16)

            info_box = QVBoxLayout()
            info_box.setSpacing(6)
            title_row = QHBoxLayout()
            title_row.setSpacing(10)
            r_title = SubtitleLabel(rule["name"], card)
            r_badge = CaptionLabel(tr("rule_badge_time", rule["start_time"], rule.get("interval_min", 10)), card)
            r_badge.setStyleSheet("color: #0099FF; font-weight: bold;")
            title_row.addWidget(r_title)
            title_row.addWidget(r_badge)
            title_row.addStretch()
            info_box.addLayout(title_row)

            target_k = min(6500, rule.get("target_kelvin", 5600))
            details = BodyLabel(
                tr("rule_details", rule["target_brightness"], target_k, rule.get("step_brightness", 5), rule.get("step_kelvin", 200)),
                card
            )
            details.setStyleSheet("color: gray;")
            info_box.addWidget(details)

            status_lbl = CaptionLabel(tr("status_waiting"), card)
            status_lbl.setObjectName(f"status_{rule['id']}")
            info_box.addWidget(status_lbl)

            card_layout.addLayout(info_box, stretch=3)

            # Actions
            actions_box = QHBoxLayout()
            actions_box.setSpacing(12)

            # Test step button
            test_btn = PushButton(FIF.PLAY, tr("btn_test_step"), card)
            test_btn.clicked.connect(lambda _, rid=rule["id"]: self.engine.run_test_step(rid))
            actions_box.addWidget(test_btn)

            # Enable/Disable switch
            sw = SwitchButton(card)
            sw.setOnText(tr("val_on"))
            sw.setOffText(tr("val_off"))
            sw.setChecked(rule.get("enabled", True))
            sw.checkedChanged.connect(lambda chk, rid=rule["id"]: self._on_rule_toggled(rid, chk))
            actions_box.addWidget(sw)

            # Delete button
            del_btn = TransparentPushButton(FIF.DELETE, "", card)
            del_btn.clicked.connect(lambda _, rid=rule["id"]: self._on_rule_deleted(rid))
            actions_box.addWidget(del_btn)

            card_layout.addLayout(actions_box)
            self.rules_container.addWidget(card)

    def retranslate_ui(self):
        self.title.setText(tr("schedule_title"))
        self.desc.setText(tr("schedule_desc"))
        self.c_title.setText(tr("card_new_rule"))
        self.c_desc.setText(tr("card_new_rule_desc"))
        self.lbl_name.setText(tr("lbl_rule_name"))
        self.lbl_time.setText(tr("lbl_start_time"))
        self.lbl_tb.setText(tr("lbl_target_b"))
        self.lbl_tk.setText(tr("lbl_target_k"))
        self.lbl_int.setText(tr("lbl_interval"))
        self.lbl_sb.setText(tr("lbl_step_b"))
        self.lbl_sk.setText(tr("lbl_step_k"))
        self.add_btn.setText(tr("btn_add_rule"))
        self._render_rules()

    def _on_add_rule(self):
        name = self.in_name.text().strip() or "Custom Rule"
        start_time = self.in_time.time().toString("HH:mm")
        new_rule = {
            "id": f"rule_{uuid.uuid4().hex[:8]}",
            "name": name,
            "enabled": True,
            "start_time": start_time,
            "interval_min": self.in_interval.value(),
            "target_brightness": self.in_target_b.value(),
            "target_kelvin": min(6500, self.in_target_k.value()),
            "step_brightness": self.in_step_b.value(),
            "step_kelvin": self.in_step_k.value(),
            "turn_on_if_off": True
        }
        self.rules.append(new_rule)
        self.engine.update_rules(self.rules)
        self.rules_changed.emit(self.rules)
        self._render_rules()

        InfoBar.success(
            tr("rule_added_title"),
            tr("rule_added_msg", name, start_time),
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000
        )

    def _on_rule_toggled(self, rule_id, enabled):
        for r in self.rules:
            if r["id"] == rule_id:
                r["enabled"] = enabled
                break
        self.engine.update_rules(self.rules)
        self.rules_changed.emit(self.rules)

    def _on_rule_deleted(self, rule_id):
        self.rules = [r for r in self.rules if r["id"] != rule_id]
        self.engine.update_rules(self.rules)
        self.rules_changed.emit(self.rules)
        self._render_rules()

    def _connect_engine(self):
        self.engine.status_updated.connect(self._on_status_updated)

    def _on_status_updated(self, rule_id, text):
        lbl = self.findChild(CaptionLabel, f"status_{rule_id}")
        if lbl:
            lbl.setText(f"{text}")
            lbl.setStyleSheet("color: #2ECC71; font-weight: bold;")
