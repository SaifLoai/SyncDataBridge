from typing import List, Dict, Any

class DiffChecker:
    def __init__(self, key_field: str = "id"):
        self.key_field = key_field

    def compare_lists(self, old_data: List[Dict[str, Any]], new_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        يقارن قائمتين من القواميس ويرجع العناصر المضافة، المحذوفة، والمعدّلة.
        :param old_data: البيانات القديمة قبل التزامن
        :param new_data: البيانات الجديدة بعد التزامن
        :return: قاموس يحتوي على [added, removed, updated]
        """
        old_map = {item[self.key_field]: item for item in old_data}
        new_map = {item[self.key_field]: item for item in new_data}

        added = [item for key, item in new_map.items() if key not in old_map]
        removed = [item for key, item in old_map.items() if key not in new_map]

        updated = []
        for key in new_map:
            if key in old_map and new_map[key] != old_map[key]:
                updated.append({
                    "before": old_map[key],
                    "after": new_map[key]
                })

        return {
            "added": added,
            "removed": removed,
            "updated": updated
        }