import sys
import hashlib
import platform
import subprocess
import uuid
import requests

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QCheckBox, QLineEdit, QDoubleSpinBox,
                             QScrollArea, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QGuiApplication
from pynput import keyboard

import config_manager
import window_manager
from macro_engine import MacroEngine

GOOGLE_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwwdL9JlLM0V7qsDIuJv_ZwTWAdF-tjymdGFYnJyCYjTLFfK-zPm3_U5LqB1n-9qbYX/exec"

def get_hwid():
    info = [platform.node(), platform.machine(), platform.processor()]
    try:
        if platform.system() == "Windows":
            cmd = "wmic csproduct get uuid"
            output = subprocess.check_output(cmd, shell=True).decode().splitlines()
            if len(output) > 1:
                info.append(output[1].strip())
        elif platform.system() == "Darwin":
            cmd = "ioreg -d2 -c IOPlatformExpertDevice | grep IOPlatformUUID"
            output = subprocess.check_output(cmd, shell=True).decode().split("=")[1]
            info.append(output.replace('"', '').strip())
    except Exception:
        info.append(str(uuid.getnode()))
    return hashlib.sha256("|".join(info).encode()).hexdigest()[:16].upper()

def verify_license(app):
    hwid = get_hwid()
    try:
        res = requests.get(f"{GOOGLE_WEB_APP_URL}?hwid={hwid}", timeout=5).json()
        if res.get("approved"):
            return True

        clipboard = app.clipboard()
        clipboard.setText(hwid)

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("승인 필요")
        msg.setText("❌ 승인되지 않은 기기입니다.")
        msg.setInformativeText(
            f"고유 코드: [{hwid}]\n\n"
            "(코드가 클립보드에 자동 복사되었습니다.\n"
            "todaysharam 님에게 코드를 전달해주세요)"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        return False
    except Exception as e:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("연결 오류")
        msg.setText("인터넷 연결 상태를 확인한 후 다시 실행해주세요.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
        return False

class SignalHandler(QObject):
    toggle_macro = Signal()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("하람매크로")
        self.resize(500, 750)
        self.slots_data = config_manager.load_all_slots()
        self.current_slot = "1"
        self.engine = MacroEngine()
        self.windows_list = []

        self.signal_handler = SignalHandler()
        self.signal_handler.toggle_macro.connect(self.toggle_macro)

        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

        self.init_ui()
        self.load_config_to_ui(self.slots_data[self.current_slot])

    def on_press(self, key):
        if key == keyboard.Key.f1:
            self.signal_handler.toggle_macro.emit()

    def on_release(self, key):
        pass

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        slot_layout = QHBoxLayout()
        for i in range(1, 6):
            btn = QPushButton(f"저장 {i}")
            btn.clicked.connect(lambda checked=False, s=str(i): self.switch_slot(s))
            slot_layout.addWidget(btn)

        btn_save = QPushButton("설정 저장")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_save.clicked.connect(self.save_current_config)
        slot_layout.addWidget(btn_save)

        btn_help = QPushButton("설치방법(권한)")
        btn_help.setStyleSheet("background-color: #2196F3; color: white;")
        btn_help.clicked.connect(self.show_help)
        slot_layout.addWidget(btn_help)

        main_layout.addLayout(slot_layout)

        win_group = QGroupBox("타겟 창 선택 (대상 프로그램)")
        win_layout = QHBoxLayout()
        self.cb_windows = QComboBox()
        self.cb_windows.setMinimumWidth(250)
        win_layout.addWidget(self.cb_windows)

        btn_refresh = QPushButton("새로고침")
        btn_refresh.clicked.connect(self.refresh_windows)
        win_layout.addWidget(btn_refresh)

        btn_verify = QPushButton("창 확인")
        btn_verify.clicked.connect(self.verify_window)
        win_layout.addWidget(btn_verify)

        win_group.setLayout(win_layout)
        main_layout.addWidget(win_group)

        text_group = QGroupBox("메모 / 추가 텍스트 입력 (15자 내외)")
        text_layout = QHBoxLayout()
        self.chk_custom_text = QCheckBox("사용")
        self.edit_custom_text = QLineEdit()
        self.edit_custom_text.setMaxLength(15)
        self.edit_custom_text.setPlaceholderText("15자 내외로 입력하세요")
        text_layout.addWidget(self.chk_custom_text)
        text_layout.addWidget(self.edit_custom_text)
        text_group.setLayout(text_layout)
        main_layout.addWidget(text_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.keys_layout = QVBoxLayout(scroll_content)

        self.fixed_inputs = {}
        fixed_group = QGroupBox("고정 키 세팅 (1 ~ 0)")
        fixed_layout = QVBoxLayout()
        for k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            row = QHBoxLayout()
            chk = QCheckBox(f"사용 (키: {k})")
            spin = QDoubleSpinBox()
            spin.setRange(0.01, 300)
            spin.setSingleStep(0.01)
            spin.setSuffix(" 초")
            row.addWidget(chk)
            row.addWidget(spin)
            fixed_layout.addLayout(row)
            self.fixed_inputs[k] = {"chk": chk, "spin": spin}
        fixed_group.setLayout(fixed_layout)
        self.keys_layout.addWidget(fixed_group)

        self.custom_inputs = {}
        custom_group = QGroupBox("커스텀 키 세팅 (6개)")
        custom_layout = QVBoxLayout()
        for i in range(1, 7):
            row = QHBoxLayout()
            chk = QCheckBox("사용")
            key_edit = QLineEdit()
            key_edit.setPlaceholderText("키 입력 (a, b 등)")
            key_edit.setMaximumWidth(100)
            spin = QDoubleSpinBox()
            spin.setRange(0.01, 300)
            spin.setSingleStep(0.01)
            spin.setSuffix(" 초")
            row.addWidget(chk)
            row.addWidget(key_edit)
            row.addWidget(spin)
            custom_layout.addLayout(row)
            self.custom_inputs[f"custom_{i}"] = {"chk": chk, "key": key_edit, "spin": spin}
        custom_group.setLayout(custom_layout)
        self.keys_layout.addWidget(custom_group)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        status_layout = QHBoxLayout()
        self.lbl_status = QLabel("상태: 정지됨")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.lbl_status)

        lbl_info = QLabel("시작/정지 단축키: F1")
        status_layout.addWidget(lbl_info)

        self.btn_toggle = QPushButton("시작")
        self.btn_toggle.clicked.connect(self.toggle_macro)
        status_layout.addWidget(self.btn_toggle)

        main_layout.addLayout(status_layout)
        self.refresh_windows()

    def refresh_windows(self):
        self.cb_windows.clear()
        self.windows_list = window_manager.get_window_list()
        self.cb_windows.addItem("선택 안함 (글로벌 입력)")
        for w in self.windows_list:
            self.cb_windows.addItem(w["title"])

    def verify_window(self):
        idx = self.cb_windows.currentIndex() - 1
        if idx >= 0 and idx < len(self.windows_list):
            window_manager.bring_window_to_front(self.windows_list[idx])

    def switch_slot(self, slot):
        self.update_config_from_ui()
        self.current_slot = slot
        self.setWindowTitle(f"하람매크로 - 슬롯 {slot}")
        self.load_config_to_ui(self.slots_data[slot])

    def update_config_from_ui(self):
        conf = self.slots_data[self.current_slot]
        conf["custom_text_enabled"] = self.chk_custom_text.isChecked()
        conf["custom_text"] = self.edit_custom_text.text()
        for k, v in self.fixed_inputs.items():
            conf["fixed_keys"][k]["enabled"] = v["chk"].isChecked()
            conf["fixed_keys"][k]["interval"] = v["spin"].value()
        for k, v in self.custom_inputs.items():
            conf["custom_keys"][k]["enabled"] = v["chk"].isChecked()
            conf["custom_keys"][k]["key"] = v["key"].text()
            conf["custom_keys"][k]["interval"] = v["spin"].value()

    def load_config_to_ui(self, config):
        self.chk_custom_text.setChecked(config.get("custom_text_enabled", False))
        self.edit_custom_text.setText(config.get("custom_text", ""))
        fixed_keys = config.get("fixed_keys", {})
        for k, v in self.fixed_inputs.items():
            info = fixed_keys.get(k, {})
            v["chk"].setChecked(info.get("enabled", False))
            v["spin"].setValue(info.get("interval", 1.0))
        custom_keys = config.get("custom_keys", {})
        for k, v in self.custom_inputs.items():
            info = custom_keys.get(k, {})
            v["chk"].setChecked(info.get("enabled", False))
            v["key"].setText(info.get("key", ""))
            v["spin"].setValue(info.get("interval", 1.0))

    def save_current_config(self):
        self.update_config_from_ui()
        config_manager.save_all_slots(self.slots_data)
        messagebox.showinfo("저장 완료", "현재 설정을 저장하였습니다.")

    def show_help(self):
        messagebox.showinfo("도움말", "macOS 권한 설정: 손쉬운 사용(Accessibility) 및 화면 기록 권한을 부여해야 타겟 입력이 가능합니다.")

    def toggle_macro(self):
        if self.engine.is_running:
            self.engine.stop()
            self.lbl_status.setText("상태: 정지됨")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
            self.btn_toggle.setText("시작")
        else:
            self.update_config_from_ui()
            conf = self.slots_data[self.current_slot]
            idx = self.cb_windows.currentIndex() - 1
            target = self.windows_list[idx] if 0 <= idx < len(self.windows_list) else None
            self.engine.start(conf, target)
            self.lbl_status.setText("상태: 작동 중...")
            self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
            self.btn_toggle.setText("정지")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if not verify_license(app):
        sys.exit()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
