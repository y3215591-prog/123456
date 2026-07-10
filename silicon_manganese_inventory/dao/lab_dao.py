from silicon_manganese_inventory.dao.database import DatabaseManager


class LabDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_result(self, pre_inbound_id, **kwargs):
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO lab_results
                   (pre_inbound_id, mn_content, si_content, c_content,
                    s_content, p_content, mn_result, si_result, c_result,
                    s_result, p_result, overall_result, test_date, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(pre_inbound_id) DO UPDATE SET
                    mn_content=excluded.mn_content, si_content=excluded.si_content,
                    c_content=excluded.c_content, s_content=excluded.s_content,
                    p_content=excluded.p_content, mn_result=excluded.mn_result,
                    si_result=excluded.si_result, c_result=excluded.c_result,
                    s_result=excluded.s_result, p_result=excluded.p_result,
                    overall_result=excluded.overall_result, test_date=excluded.test_date,
                    remark=excluded.remark""",
                (pre_inbound_id, kwargs.get("mn_content"),
                 kwargs.get("si_content"), kwargs.get("c_content"),
                 kwargs.get("s_content"), kwargs.get("p_content"),
                 kwargs.get("mn_result", ""), kwargs.get("si_result", ""),
                 kwargs.get("c_result", ""), kwargs.get("s_result", ""),
                 kwargs.get("p_result", ""), kwargs.get("overall_result", ""),
                 kwargs.get("test_date", ""), kwargs.get("remark", "")),
            )
            conn.execute(
                "UPDATE pre_inbound_orders SET lab_status='tested', updated_at=datetime('now','localtime') WHERE id=?",
                (pre_inbound_id,),
            )
            return cursor.lastrowid

    def get_result(self, pre_inbound_id):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM lab_results WHERE pre_inbound_id=?",
                (pre_inbound_id,),
            ).fetchone()

    def list_results(self, overall_result=None):
        with self.db.get_connection() as conn:
            if overall_result:
                return conn.execute(
                    """SELECT lr.*, pio.batch_no, pio.date, pio.quantity, pio.location_code
                       FROM lab_results lr
                       JOIN pre_inbound_orders pio ON lr.pre_inbound_id=pio.id
                       WHERE lr.overall_result=?
                       ORDER BY lr.test_date DESC""",
                    (overall_result,),
                ).fetchall()
            return conn.execute(
                """SELECT lr.*, pio.batch_no, pio.date, pio.quantity, pio.location_code
                   FROM lab_results lr
                   JOIN pre_inbound_orders pio ON lr.pre_inbound_id=pio.id
                   ORDER BY lr.test_date DESC"""
            ).fetchall()

    def get_standards(self):
        with self.db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM lab_standards ORDER BY id"
            ).fetchall()

    def update_standard(self, element, min_value, max_value, remark=""):
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM lab_standards WHERE element=?",
                (element,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE lab_standards SET min_value=?, max_value=?, remark=? WHERE element=?",
                    (min_value, max_value, remark, element),
                )
            else:
                conn.execute(
                    "INSERT INTO lab_standards (element, min_value, max_value, remark) VALUES (?, ?, ?, ?)",
                    (element, min_value, max_value, remark),
                )
