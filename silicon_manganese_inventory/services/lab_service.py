from datetime import datetime
from silicon_manganese_inventory.dao.database import DatabaseManager
from silicon_manganese_inventory.dao.lab_dao import LabDAO


class LabService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.dao = LabDAO(db)
        self._standards = None

    def _get_standards(self):
        if self._standards is None:
            self._standards = self.dao.get_standards()
        return self._standards

    def record_result(self, pre_inbound_id, mn_content=None, si_content=None,
                      c_content=None, s_content=None, p_content=None,
                      overall_result="", remark=""):
        if overall_result:
            mn_r = si_r = c_r = s_r = p_r = overall_result
        else:
            mn_r = self._judge_element("Mn", mn_content)
            si_r = self._judge_element("Si", si_content)
            c_r = self._judge_element("C", c_content)
            s_r = self._judge_element("S", s_content)
            p_r = self._judge_element("P", p_content)
            all_results = [mn_r, si_r, c_r, s_r, p_r]
            overall_result = "合格" if all(r == "合格" for r in all_results) else "不合格"
        return self.dao.save_result(
            pre_inbound_id,
            mn_content=mn_content, si_content=si_content,
            c_content=c_content, s_content=s_content, p_content=p_content,
            mn_result=mn_r, si_result=si_r, c_result=c_r,
            s_result=s_r, p_result=p_r,
            overall_result=overall_result,
            test_date=datetime.now().strftime("%Y-%m-%d"),
            remark=remark,
        )

    def _judge_element(self, element, value):
        if value is None:
            return ""
        standards = self.dao.get_standards()
        std = next((s for s in standards if s["element"] == element), None)
        if not std:
            return ""
        if std["min_value"] <= value <= std["max_value"]:
            return "合格"
        return "不合格"

    def format_lab_string(self, pre_inbound_id):
        result = self.dao.get_result(pre_inbound_id)
        if not result:
            return ""
        parts = []
        for elem in ["Mn", "Si", "C", "S", "P"]:
            content_key = f"{elem.lower()}_content"
            result_key = f"{elem.lower()}_result"
            content = result[content_key]
            result_val = result[result_key]
            if content is not None:
                parts.append(f"{elem}含量:{content}%({result_val})")
        return " | ".join(parts)

    def get_result(self, pre_inbound_id):
        return self.dao.get_result(pre_inbound_id)

    def list_results(self, **kwargs):
        return self.dao.list_results(**kwargs)

    def get_standards(self):
        return self.dao.get_standards()

    def update_standard(self, element, min_value, max_value, remark=""):
        self.dao.update_standard(element, min_value, max_value, remark)
