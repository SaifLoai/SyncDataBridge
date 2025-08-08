from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QListWidget, QMessageBox,
    QLabel, QGroupBox, QTextEdit
)
from PyQt5.QtCore import Qt, QDateTime, QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor
import json
import os
import pyodbc
import firebase_admin
from firebase_admin import credentials, db
import tempfile

class ConnectionCheckThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, db_config):
        super().__init__()
        self.db_config = db_config

    def run(self):
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.db_config['host']};"
                f"DATABASE={self.db_config['name']};"
                f"UID={self.db_config['username']};"
                f"PWD={self.db_config['password']}"
            )
            conn = pyodbc.connect(conn_str, timeout=5)
            conn.close()
            self.result.emit(True, "✅ اتصال SQL Server ناجح")
        except Exception as e:
            self.result.emit(False, f"❌ فشل اتصال SQL Server: {e}")

class ConfigWindow(QWidget):
    def __init__(self, config_path="config.json"):
        super().__init__()
        self.setWindowTitle("إعدادات الاتصال المتقدمة")
        self.setGeometry(300, 300, 700, 700)
        self.config_path = config_path
        self.config = {}

        self.layout = QVBoxLayout(self)
        self.db_list = QListWidget()
        self.db_list.currentRowChanged.connect(self.load_db_fields)
        self.layout.addWidget(QLabel("📃 قواعد البيانات:"))
        self.layout.addWidget(self.db_list)

        self.db_group = QGroupBox("📁 تفاصيل القاعدة المحددة")
        self.db_form = QFormLayout()
        self.db_group.setLayout(self.db_form)
        self.layout.addWidget(self.db_group)

        self.name_input = QLineEdit()
        self.host_input = QLineEdit()
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.db_form.addRow("ℹ️ الاسم:", self.name_input)
        self.db_form.addRow("🌐 المضيف:", self.host_input)
        self.db_form.addRow("👤 المستخدم:", self.user_input)
        self.db_form.addRow("🔐 كلمة المرور:", self.pass_input)

        self.tables_group = QGroupBox("🔗 ربط الجداول المحلية بـ Firebase")
        self.tables_form = QFormLayout()
        self.tables_group.setLayout(self.tables_form)
        self.layout.addWidget(self.tables_group)

        self.add_table_btn = QPushButton("➕ إضافة جدول جديد")
        self.add_table_btn.clicked.connect(self.add_table_row)
        self.layout.addWidget(self.add_table_btn)
        self.table_widgets = []

        db_btns = QHBoxLayout()
        self.add_db_btn = QPushButton("➕ إضافة قاعدة")
        self.delete_db_btn = QPushButton("❌ حذف المحددة")
        db_btns.addWidget(self.add_db_btn)
        db_btns.addWidget(self.delete_db_btn)
        self.layout.addLayout(db_btns)

        self.add_db_btn.clicked.connect(self.add_database)
        self.delete_db_btn.clicked.connect(self.delete_database)

        self.fb_group = QGroupBox("🔥 إعدادات Firebase الكاملة")
        self.firebase_form = QFormLayout()
        self.fb_group.setLayout(self.firebase_form)
        self.layout.addWidget(self.fb_group)

        self.fb_inputs = {}
        firebase_keys = [
            "type", "project_id", "private_key_id", "private_key",
            "client_email", "client_id", "auth_uri", "token_uri",
            "auth_provider_x509_cert_url", "client_x509_cert_url",
            "universe_domain", "database_url"
        ]
        for key in firebase_keys:
            inp = QLineEdit()
            self.fb_inputs[key] = inp
            self.firebase_form.addRow(f"🔧 {key.replace('_', ' ').title()}:", inp)

        btns = QHBoxLayout()
        self.save_btn = QPushButton("💾 حفظ")
        self.test_btn = QPushButton("🔍 فحص")
        btns.addWidget(self.save_btn)
        btns.addWidget(self.test_btn)
        self.layout.addLayout(btns)

        self.save_btn.clicked.connect(self.save_config)
        self.test_btn.clicked.connect(self.test_connection)

        self.layout.addWidget(QLabel("📜 سجل الأحداث:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)

        self.logger = None
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

        self.db_list.clear()
        for db in self.config.get("databases", []):
            self.db_list.addItem(db.get("name", "غير محدد"))

        for key, inp in self.fb_inputs.items():
            inp.setText(self.config.get("firebase", {}).get(key, ""))

        if self.config.get("databases"):
            self.db_list.setCurrentRow(0)

    def clear_table_rows(self):
        while self.tables_form.count():
            item = self.tables_form.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.table_widgets.clear()

    def load_db_fields(self, index):
        self.clear_table_rows()
        try:
            db = self.config["databases"][index]
            self.name_input.setText(db.get("name", ""))
            self.host_input.setText(db.get("host", ""))
            self.user_input.setText(db.get("username", ""))
            self.pass_input.setText(db.get("password", ""))
            for local, remote in db.get("tables", {}).items():
                self.add_table_row(local, remote)
        except Exception:
            self.name_input.clear()
            self.host_input.clear()
            self.user_input.clear()
            self.pass_input.clear()

    def add_table_row(self, local_val="", remote_val=""):
        local_input = QLineEdit(str(local_val))
        remote_input = QLineEdit(str(remote_val))
        remove_btn = QPushButton("❌")
        remove_btn.setFixedWidth(30)
        container = QHBoxLayout()
        container.addWidget(local_input)
        container.addWidget(remote_input)
        container.addWidget(remove_btn)
        row_widget = QWidget()
        row_widget.setLayout(container)
        self.tables_form.addRow(row_widget)
        self.table_widgets.append((local_input, remote_input, row_widget))
        remove_btn.clicked.connect(lambda: self.remove_table_row(row_widget))

    def remove_table_row(self, row_widget):
        for i, (_, _, widget) in enumerate(self.table_widgets):
            if widget == row_widget:
                self.tables_form.removeWidget(widget)
                widget.deleteLater()
                self.table_widgets.pop(i)
                break

    def save_config(self):
        try:
            index = self.db_list.currentRow()
            if index >= 0:
                tables_dict = {
                    local.text().strip(): remote.text().strip()
                    for local, remote, _ in self.table_widgets
                    if local.text().strip() and remote.text().strip()
                }
                db = {
                    "name": self.name_input.text(),
                    "host": self.host_input.text(),
                    "username": self.user_input.text(),
                    "password": self.pass_input.text(),
                    "tables": tables_dict
                }
                self.config["databases"][index] = db

            self.config["firebase"] = {
                key: inp.text().strip()
                for key, inp in self.fb_inputs.items()
            }

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)

            QMessageBox.information(self, "حفظ الإعدادات", "تم حفظ الإعدادات بنجاح!")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل في حفظ الإعدادات: {e}")
            print(f"فشل في حفظ الإعدادات: {e}")

    def add_database(self):
        new_db = {"name": "جديدة", "host": "", "username": "", "password": "", "tables": {}}
        self.config.setdefault("databases", []).append(new_db)
        self.load_config()
        self.db_list.setCurrentRow(self.db_list.count() - 1)

    def delete_database(self):
        index = self.db_list.currentRow()
        if index >= 0:
            reply = QMessageBox.question(self, "تأكيد الحذف", "هل أنت متأكد؟", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            del self.config["databases"][index]
            self.load_config()
            self.db_list.setCurrentRow(0 if self.db_list.count() else -1)

    def test_connection(self):
        index = self.db_list.currentRow()
        if index < 0:
            QMessageBox.warning(self, "تحذير", "اختر قاعدة بيانات أولاً.")
            return

        db_conf = self.config["databases"][index]
        self.append_log("🔍 بدء اختبار الاتصال...")

        self.check_thread = ConnectionCheckThread(db_conf)
        self.check_thread.result.connect(self.handle_db_check_result)
        self.check_thread.start()

    def handle_db_check_result(self, success, message):
        self.append_log(message)
        fb_creds = self.config.get("firebase", {})
        fb_ok, fb_msg = self.test_firebase_connection(fb_creds)
        self.append_log(fb_msg)

        if success and fb_ok:
            QMessageBox.information(self, "نجاح", "✅ تم الاتصال بنجاح بكل الأنظمة.")
        else:
            QMessageBox.warning(self, "فشل الاتصال", "❌ حدثت مشكلة. راجع السجل.")

    def test_firebase_connection(self, firebase_creds):
        try:
            # كتابة dict إلى ملف مؤقت ثم تمريره لـ Certificate
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False, encoding="utf-8") as tmp:
                json.dump(firebase_creds, tmp, ensure_ascii=False)
                tmp.flush()
                tmp_path = tmp.name
            if not firebase_admin._apps:
                cred = credentials.Certificate(tmp_path)
                firebase_admin.initialize_app(cred, {"databaseURL": firebase_creds.get("database_url", "")})
            db.reference("/").get()
            os.unlink(tmp_path)
            return True, "✅ اتصال Firebase ناجح"
        except Exception as e:
            return False, f"❌ فشل اتصال Firebase: {e}"

    def append_log(self, message):
        timestamp = QDateTime.currentDateTime().toString('hh:mm:ss')
        self.log_area.append(f"[{timestamp}] {message}")