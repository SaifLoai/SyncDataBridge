import firebase_admin
from firebase_admin import credentials, db
from typing import Dict, Any
import logging
import traceback
import datetime
import json

# إعداد الـ logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def serialize_data(data):
    """تحويل جميع كائنات datetime إلى نص (isoformat) داخل dict أو list."""
    if isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_data(v) for v in data]
    elif isinstance(data, datetime.datetime):
        return data.isoformat()
    else:
        return data

def validate_project_id(config_path: str, db_url: str):
    """التحقق من تطابق project_id مع رابط قاعدة البيانات."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        project_id = config.get("project_id", "")
        if project_id and project_id not in db_url:
            logging.warning(f"⚠️ تحذير: project_id '{project_id}' لا يتطابق مع db_url '{db_url}'")
        else:
            logging.info("✅ تطابق project_id مع db_url تم بنجاح.")
    except Exception as e:
        logging.error(f"🛑 فشل في التحقق من project_id: {e}")
        traceback.print_exc()

class FirebaseWriter:
    def __init__(self, config_path: str, db_url: str):
        """تهيئة الاتصال بـ Firebase."""
        try:
            validate_project_id(config_path, db_url)
            if not firebase_admin._apps:
                cred = credentials.Certificate(config_path)
                firebase_admin.initialize_app(cred, {'databaseURL': db_url})
                logging.info("✅ تم تهيئة الاتصال بـ Firebase")
        except Exception as e:
            logging.error(f"🚫 فشل في التهيئة: {e}")
            traceback.print_exc()

    def test_connection(self) -> bool:
        """اختبار الاتصال بـ Firebase عن طريق كتابة وقراءة قيمة تجريبية."""
        try:
            path = "test_connection_check"
            test_data = {"status": "connected", "timestamp": datetime.datetime.now().isoformat()}
            ref = db.reference(path)
            ref.set(test_data)
            result = ref.get()
            if result and result.get("status") == "connected":
                logging.info("✅ الاتصال بـ Firebase يعمل بشكل صحيح.")
                return True
            else:
                logging.warning("⚠️ الاتصال تم لكن البيانات غير متطابقة.")
                return False
        except Exception as e:
            logging.error(f"🛑 فشل اختبار الاتصال: {e}")
            traceback.print_exc()
            return False

    def write_data(self, path: str, data: Dict[str, Any]) -> bool:
        try:
            if not isinstance(data, dict):
                raise ValueError("❌ البيانات يجب أن تكون من نوع dict")
            data = serialize_data(data)
            logging.info(f"📤 إرسال البيانات إلى ({path}): {data}")
            ref = db.reference(path)
            ref.set(data)
            logging.info(f"✅ تم كتابة البيانات إلى: {path}")
            return True
        except Exception as e:
            logging.error(f"🛑 خطأ في الكتابة: {e}")
            traceback.print_exc()
            return False

    def push_data(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not isinstance(data, dict):
                raise ValueError("❌ البيانات يجب أن تكون من نوع dict")
            data = serialize_data(data)
            ref = db.reference(path)
            new_ref = ref.push(data)
            logging.info(f"🆕 تم إنشاء سجل جديد بالمفتاح: {new_ref.key}")
            return {"key": new_ref.key, "data": data}
        except Exception as e:
            logging.error(f"🛑 خطأ في push: {e}")
            traceback.print_exc()
            return {}

    def update_data(self, path: str, data: Dict[str, Any]) -> bool:
        try:
            if not isinstance(data, dict):
                raise ValueError("❌ البيانات يجب أن تكون من نوع dict")
            data = serialize_data(data)
            ref = db.reference(path)
            ref.update(data)
            logging.info(f"🔄 تم تحديث البيانات في: {path}")
            return True
        except Exception as e:
            logging.error(f"🛑 خطأ في التحديث: {e}")
            traceback.print_exc()
            return False

    def delete_data(self, path: str) -> bool:
        try:
            ref = db.reference(path)
            ref.delete()
            logging.info(f"🗑️ تم حذف البيانات في: {path}")
            return True
        except Exception as e:
            logging.error(f"🛑 خطأ في الحذف: {e}")
            traceback.print_exc()
            return False

    def get_data(self, path: str) -> Dict[str, Any]:
        try:
            ref = db.reference(path)
            data = ref.get()
            if data is None:
                logging.info(f"📥 لا توجد بيانات في: {path}")
                return {}
            logging.info(f"📥 تم جلب البيانات من: {path}")
            return serialize_data(data)
        except Exception as e:
            logging.error(f"🛑 خطأ في جلب البيانات: {e}")
            traceback.print_exc()
            return {}

if __name__ == "__main__":
    config_path = "../firebase_key.json"  # عدل حسب مكان الملف
    db_url = "https://rawaat-almazaq-default-rtdb.firebaseio.com"
    writer = FirebaseWriter(config_path, db_url)

    if writer.test_connection():
        print("✅ الاتصال بـ Firebase ناجح.")
    else:
        print("❌ الاتصال بـ Firebase فشل.")

