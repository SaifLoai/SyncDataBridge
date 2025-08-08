import sys
import json
import logging
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import setup_logger

# تحميل إعدادات البرنامج
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"فشل في تحميل ملف الإعدادات: {e}")
        return {}

def main():
    # تعديل ترميز stdout لدعم اللغة العربية في الـ logging
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

    config = load_config()
    logger = setup_logger()

    logger.info("تشغيل البرنامج...")

    app = QApplication(sys.argv)
    window = MainWindow(config=config, logger=logger)
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()