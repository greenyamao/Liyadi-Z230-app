from datetime import datetime, time
from PySide6.QtCore import QObject, QTimer, Signal
from core.i18n import tr

class SchedulerEngine(QObject):
    apply_state = Signal(bool, int, int)              # power, brightness, kelvin
    status_updated = Signal(str, str)                # rule_id, status_text
    rule_triggered = Signal(str, str)                # rule_name, message

    def __init__(self, ble_manager, rules=None, plug_manager=None):
        super().__init__()
        self.ble_manager = ble_manager
        self.rules = rules or []
        self.plug_manager = plug_manager
        
        # State tracking: {rule_id: {"last_triggered_date": "YYYY-MM-DD", "active": bool, "next_step_time": datetime}}
        self.runtime_state = {}
        for r in self.rules:
            self.runtime_state[r["id"]] = {
                "last_triggered_date": None,
                "is_running": False,
                "last_step_time": None
            }

        self.timer = QTimer(self)
        self.timer.setInterval(5000)  # Check every 5 seconds
        self.timer.timeout.connect(self._check_schedules)
        self.timer.start()

    def update_rules(self, rules):
        self.rules = rules
        for r in self.rules:
            if r["id"] not in self.runtime_state:
                self.runtime_state[r["id"]] = {
                    "last_triggered_date": None,
                    "is_running": False,
                    "last_step_time": None
                }

    def _check_schedules(self):
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M")

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue

            r_id = rule["id"]
            state = self.runtime_state.get(r_id, {})
            start_time = rule.get("start_time", "12:00")
            action_type = rule.get("action_type", "gradual")

            # Check if rule should trigger its start
            if current_time_str == start_time and state.get("last_triggered_date") != today_str:
                state["last_triggered_date"] = today_str
                
                if action_type == "turn_off":
                    state["is_running"] = False
                    self.runtime_state[r_id] = state
                    self.ble_manager.set_cct(False, 0, self.ble_manager.kelvin)
                    if self.plug_manager and self.plug_manager.enabled and self.plug_manager.auto_power_off:
                        self.plug_manager.start_cooldown()
                    self.status_updated.emit(r_id, tr("status_done"))
                    self.rule_triggered.emit(rule["name"], f"{rule['name']}: {tr('schedule_badge_turn_off')}")
                elif action_type == "instant":
                    state["is_running"] = False
                    self.runtime_state[r_id] = state
                    if self.plug_manager:
                        self.plug_manager.cancel_cooldown()
                        if self.plug_manager.enabled and self.plug_manager.auto_power_on and not self.plug_manager.is_on():
                            self.plug_manager.turn_on()
                    self.ble_manager.wake_and_connect()
                    target_b = max(0, min(100, rule.get("target_brightness", 50)))
                    target_k = min(6500, max(2700, rule.get("target_kelvin", 4500)))
                    self.ble_manager.set_cct(target_b > 0, target_b, target_k)
                    self.ble_manager.wake_and_connect()
                    self.status_updated.emit(r_id, tr("status_done"))
                    self.rule_triggered.emit(rule["name"], f"{rule['name']}: {target_b}%, {target_k}K")
                else:
                    # gradual transition
                    state["is_running"] = True
                    state["last_step_time"] = now
                    self.runtime_state[r_id] = state
                    
                    if self.plug_manager:
                        self.plug_manager.cancel_cooldown()
                        if self.plug_manager.enabled and self.plug_manager.auto_power_on and not self.plug_manager.is_on():
                            self.plug_manager.turn_on()
                    self.ble_manager.wake_and_connect()

                    target_k = min(6500, max(2700, rule.get("target_kelvin", 5600)))
                    self.rule_triggered.emit(
                        rule["name"],
                        f"{rule['name']} -> {rule['target_brightness']}%, {target_k}K"
                    )
                    
                    if rule.get("turn_on_if_off", True) and not self.ble_manager.is_on:
                        self.ble_manager.set_power(True)

                    self._execute_step(rule)

            # If rule is currently running its gradual transition
            elif state.get("is_running", False) and action_type == "gradual":
                last_step = state.get("last_step_time")
                interval_sec = rule.get("interval_min", 10) * 60
                
                if (now - last_step).total_seconds() >= interval_sec:
                    state["last_step_time"] = now
                    is_complete = self._execute_step(rule)
                    if is_complete:
                        state["is_running"] = False
                        self.status_updated.emit(r_id, tr("status_done"))
                        self.rule_triggered.emit(rule["name"], f"{rule['name']}: {tr('status_done')}")

    def _execute_step(self, rule) -> bool:
        """Executes one step of gradual transition. Returns True if target reached."""
        curr_b = self.ble_manager.brightness
        curr_k = self.ble_manager.kelvin
        
        target_b = max(0, min(100, rule.get("target_brightness", 50)))
        target_k = min(6500, max(2700, rule.get("target_kelvin", 5600)))
        step_b = rule.get("step_brightness", 5)
        step_k = rule.get("step_kelvin", 200)

        # Calculate new brightness
        new_b = curr_b
        if curr_b < target_b:
            new_b = min(target_b, curr_b + abs(step_b))
        elif curr_b > target_b:
            new_b = max(target_b, curr_b - abs(step_b))

        # Calculate new kelvin
        new_k = curr_k
        if curr_k < target_k:
            new_k = min(target_k, curr_k + abs(step_k))
        elif curr_k > target_k:
            new_k = max(target_k, curr_k - abs(step_k))

        # Apply to lamp
        self.ble_manager.set_cct(new_b > 0, new_b, new_k)
        
        reached_b = (new_b == target_b)
        reached_k = (new_k == target_k)
        
        status = tr("status_running", new_b, new_k)
        self.status_updated.emit(rule["id"], status)

        return reached_b and reached_k

    def run_test_step(self, rule_id):
        """Immediately executes test for this rule"""
        for r in self.rules:
            if r["id"] == rule_id:
                action_type = r.get("action_type", "gradual")
                if action_type == "turn_off":
                    self.ble_manager.set_cct(False, 0, self.ble_manager.kelvin)
                    self.status_updated.emit(rule_id, tr("status_done"))
                elif action_type == "instant":
                    target_b = max(0, min(100, r.get("target_brightness", 50)))
                    target_k = min(6500, max(2700, r.get("target_kelvin", 4500)))
                    self.ble_manager.set_cct(target_b > 0, target_b, target_k)
                    self.status_updated.emit(rule_id, tr("status_done"))
                else:
                    if not self.ble_manager.is_on:
                        self.ble_manager.set_power(True)
                    self._execute_step(r)
                break
