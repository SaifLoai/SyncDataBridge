from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QTextEdit, QMenuBar, QAction, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from ui.config_window import ConfigWindow

import os
import json
import traceback
from sync.sql_reader import SQLReader
from sync.firebase_writer import FirebaseWriter
from sync.diff_checker import DiffChecker

class MainWindow(QMainWindow):
    def __init__(self, config=None, logger=None):
        super().__init__()
        self.config = config or {}
        self.logger = logger

        self.setWindowTitle("SyncDataBridge - مزامنة البيانات")
        self.setGeometry(200, 200, 600, 400)

        self.status_label = QLabel("الحالة: غير متصل")
        self.last_sync_label = QLabel("آخر مزامنة: لا يوجد")
        self.records_label = QLabel("عدد التغييرات: 0")
        self.sync_button = QPushButton("بدء المزامنة الآن")
        self.sync_button.clicked.connect(self.manual_sync)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.last_sync_label)
        layout.addWidget(self.records_label)
        layout.addWidget(self.sync_button)
        layout.addWidget(self.log_area)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # القائمة العلوية
        menu_bar = QMenuBar()
        settings_action = QAction("⚙️ إعدادات الاتصال", self)
        settings_action.triggered.connect(self.open_config_window)
        menu_bar.addAction(settings_action)
        self.setMenuBar(menu_bar)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        # مؤقت المزامنة التلقائية كل 10 ثواني
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.auto_sync)
        self.sync_timer.start(10000)

        # تهيئة FirebaseWriter
        fb_conf = self.config.get("firebase", {})
        self.firebase_writer = None
        if fb_conf and fb_conf.get("database_url"):
            fb_key_path = "firebase_key.json"
            with open(fb_key_path, "w", encoding="utf-8") as f:
                json.dump(fb_conf, f, ensure_ascii=False)
            self.firebase_writer = FirebaseWriter(fb_key_path, fb_conf["database_url"])

            # اختبار الاتصال
            if self.firebase_writer and not self.firebase_writer.test_connection():
                self.append_log("⚠️ فشل اختبار الاتصال بـ Firebase. تحقق من الرابط أو ملف الخدمة.")
                self.status_label.setText("الحالة: غير متصل ❌")
                self.firebase_writer = None
            else:
                self.status_label.setText("الحالة: متصل ✅")

        self.diff_checker = DiffChecker()
        self.last_data = {}

    def update_time(self):
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.statusBar().showMessage(f"الوقت الحالي: {now}")

    def manual_sync(self):
        self.sync_data(is_manual=True)

    def auto_sync(self):
        self.sync_data(is_manual=False)

    def sync_data(self, is_manual=False):
        if is_manual:
            self.append_log("بدأت عملية المزامنة اليدوية...")
            if self.logger:
                self.logger.info("بدأت عملية المزامنة اليدوية.")
        else:
            self.append_log("بدأت المزامنة التلقائية...")

        total_changes = 0
        try:
            db_configs = self.config.get("databases", [])
            if not db_configs:
                self.append_log("لم يتم العثور على قواعد بيانات في الإعدادات.")
                return

            if not self.firebase_writer:
                self.append_log("إعدادات Firebase غير مكتملة أو الاتصال فشل.")
                return

            for db_conf in db_configs:
                db_name = db_conf.get("name")
                db_host = db_conf.get("host")
                db_user = db_conf.get("username")
                db_pass = db_conf.get("password")
                tables = db_conf.get("tables", {})

                sql_reader = SQLReader(db_name, db_host, db_user, db_pass)
                for local_table, remote_table in tables.items():
                    query = f"SELECT * FROM {local_table}"
                    new_data = sql_reader.fetch_query(query)
                    key = f"{db_name}:{local_table}"

                    if not new_data:
                        self.append_log(f"⚠️ قاعدة [{db_name}] - جدول [{local_table}]: الجدول غير موجود أو فارغ.")
                        continue

                    old_data = self.last_data.get(key, [])
                    diff = self.diff_checker.compare_lists(old_data, new_data)
                    changes = diff["added"] + [u["after"] for u in diff["updated"]]

                    if changes:
                        path = f"{remote_table}/{db_name}"
                        success = self.firebase_writer.write_data(path, {str(i): row for i, row in enumerate(new_data)})
                        if success:
                            self.append_log(f"📤 قاعدة [{db_name}] - جدول [{local_table}]: تم رفع {len(changes)} سجل إلى [{remote_table}] ✅")
                            total_changes += len(changes)
                        else:
                            self.append_log(f"❌ قاعدة [{db_name}] - جدول [{local_table}]: فشل رفع البيانات إلى Firebase.")
                    else:
                        self.append_log(f"🟡 قاعدة [{db_name}] - جدول [{local_table}]: لا يوجد بيانات جديدة للرفع.")

                    self.last_data[key] = new_data

            self.last_sync_label.setText("آخر مزامنة: الآن")
            self.records_label.setText(f"عدد التغييرات: {total_changes}")
            if total_changes > 0:
                self.append_log("✔️ تمت المزامنة بنجاح.")
                if self.logger:
                    self.logger.info("تمت المزامنة بنجاح.")
            else:
                self.append_log("لا يوجد تغييرات جديدة.")
                if self.logger:
                    self.logger.info("لا يوجد تغييرات جديدة.")
        except Exception as e:
            self.append_log(f"❌ خطأ أثناء المزامنة: {e}")
            self.append_log(traceback.format_exc())
            if self.logger:
                self.logger.error(f"خطأ أثناء المزامنة: {e}")

    def append_log(self, message):
        timestamp = QDateTime.currentDateTime().toString('hh:mm:ss')
        self.log_area.append(f"[{timestamp}] {message}")

    def open_config_window(self):
        self.config_window = ConfigWindow()
        self.config_window.show()