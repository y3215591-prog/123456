import hashlib
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QWidget, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from silicon_manganese_inventory.dao.database import DatabaseManager


class LoginDialog(QDialog):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.setWindowTitle("硅锰合金库存管理系统 - 登录")
        self.setFixedSize(420, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._setup_ui()
        self._init_admin_if_needed()
        self._center()

    def _center(self):
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QWidget()
        card.setObjectName("loginCard")
        card.setStyleSheet("""
            #loginCard {
                background: rgba(255, 255, 255, 0.92);
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.3);
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 36, 40, 30)
        layout.setSpacing(12)

        title = QLabel("硅锰合金库存管理")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("PingFang SC, Microsoft YaHei", 20, QFont.Bold))
        title.setStyleSheet("color: #1d1d1f; margin-bottom: 4px;")
        layout.addWidget(title)

        subtitle = QLabel("Silicon Manganese Inventory")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont("PingFang SC, Microsoft YaHei", 11))
        subtitle.setStyleSheet("color: #86868b; margin-bottom: 16px;")
        layout.addWidget(subtitle)

        self.stack = QStackedWidget()

        self.stack.addWidget(self._login_page())
        self.stack.addWidget(self._recover_page())
        self.stack.addWidget(self._reset_page())

        layout.addWidget(self.stack)
        outer.addWidget(card)

        close_btn = QPushButton("X")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,0.06); border-radius: 14px;
                color: #86868b; font-weight: bold; font-size: 13px; border: none;
            }
            QPushButton:hover { background: rgba(0,0,0,0.12); color: #1d1d1f; }
        """)
        close_btn.clicked.connect(self.reject)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        layout.insertLayout(0, close_row)

    def _login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self._style_input(self.username_input)
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self._style_input(self.password_input)
        layout.addWidget(self.password_input)

        self.login_error = QLabel("")
        self.login_error.setStyleSheet("color: #ff3b30; font-size: 12px;")
        self.login_error.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.login_error)

        login_btn = QPushButton("登 录")
        self._style_primary_btn(login_btn)
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)

        recover_btn = QPushButton("忘记密码？")
        recover_btn.setStyleSheet("""
            QPushButton { border: none; color: #007aff; font-size: 12px;
                background: transparent; }
            QPushButton:hover { color: #0056b3; text-decoration: underline; }
        """)
        recover_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(recover_btn, alignment=Qt.AlignCenter)

        layout.addStretch()
        return page

    def _recover_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        title = QLabel("找回密码")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("PingFang SC, Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet("color: #1d1d1f;")
        layout.addWidget(title)

        self.recover_user = QLineEdit()
        self.recover_user.setPlaceholderText("输入用户名")
        self._style_input(self.recover_user)
        layout.addWidget(self.recover_user)

        self.recover_answer = QLineEdit()
        self.recover_answer.setPlaceholderText("输入安全问题答案")
        self._style_input(self.recover_answer)
        layout.addWidget(self.recover_answer)

        self.recover_error = QLabel("")
        self.recover_error.setStyleSheet("color: #ff3b30; font-size: 12px;")
        self.recover_error.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.recover_error)

        verify_btn = QPushButton("验 证")
        self._style_primary_btn(verify_btn)
        verify_btn.clicked.connect(self._verify_recovery)
        layout.addWidget(verify_btn)

        back_btn = QPushButton("返回登录")
        back_btn.setStyleSheet("""
            QPushButton { border: none; color: #007aff; font-size: 12px;
                background: transparent; }
            QPushButton:hover { color: #0056b3; }
        """)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back_btn, alignment=Qt.AlignCenter)

        layout.addStretch()
        return page

    def _reset_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        title = QLabel("重置密码")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("PingFang SC, Microsoft YaHei", 16, QFont.Bold))
        title.setStyleSheet("color: #1d1d1f;")
        layout.addWidget(title)

        self.reset_new_pw = QLineEdit()
        self.reset_new_pw.setPlaceholderText("新密码")
        self.reset_new_pw.setEchoMode(QLineEdit.Password)
        self._style_input(self.reset_new_pw)
        layout.addWidget(self.reset_new_pw)

        self.reset_confirm = QLineEdit()
        self.reset_confirm.setPlaceholderText("确认新密码")
        self.reset_confirm.setEchoMode(QLineEdit.Password)
        self._style_input(self.reset_confirm)
        layout.addWidget(self.reset_confirm)

        self.reset_error = QLabel("")
        self.reset_error.setStyleSheet("color: #ff3b30; font-size: 12px;")
        self.reset_error.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.reset_error)

        reset_btn = QPushButton("确认重置")
        self._style_primary_btn(reset_btn)
        reset_btn.clicked.connect(self._do_reset)
        layout.addWidget(reset_btn)

        layout.addStretch()
        return page

    def _style_input(self, widget):
        widget.setFixedHeight(40)
        widget.setStyleSheet("""
            QLineEdit {
                border: 1px solid rgba(0,0,0,0.1); border-radius: 10px;
                padding: 0 14px; font-size: 14px; background: rgba(0,0,0,0.03);
                color: #1d1d1f;
            }
            QLineEdit:focus { border-color: #007aff; background: rgba(0,122,255,0.04); }
        """)

    def _style_primary_btn(self, btn):
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton {
                background: #007aff; color: white; border: none;
                border-radius: 10px; font-size: 15px; font-weight: bold;
            }
            QPushButton:hover { background: #0062cc; }
            QPushButton:pressed { background: #004999; }
        """)

    def _init_admin_if_needed(self):
        with self.db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    security_question TEXT DEFAULT '',
                    security_answer_hash TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
                )
            """)
            row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
            if row[0] == 0:
                pw_salt = os.urandom(16).hex()
                ans_salt = os.urandom(16).hex()
                pw_hash = self._hash_pw("admin", pw_salt)
                ans_hash = self._hash_pw("硅锰合金", ans_salt)
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt, security_question, security_answer_hash) VALUES (?, ?, ?, ?, ?)",
                    ("admin", pw_hash, pw_salt, "公司主营产品是？", f"{ans_salt}:{ans_hash}"),
                )

    @staticmethod
    def _hash_pw(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.login_error.setText("请输入用户名和密码")
            return
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT password_hash, salt FROM users WHERE username=?",
                (username,),
            ).fetchone()
        if not row:
            self.login_error.setText("用户名或密码错误")
            return
        if self._hash_pw(password, row["salt"]) != row["password_hash"]:
            self.login_error.setText("用户名或密码错误")
            return
        self.accept()

    def _verify_recovery(self):
        username = self.recover_user.text().strip()
        answer = self.recover_answer.text().strip()
        if not username or not answer:
            self.recover_error.setText("请填写完整信息")
            return
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT security_answer_hash FROM users WHERE username=?",
                (username,),
            ).fetchone()
        if not row:
            self.recover_error.setText("用户名不存在")
            return
        ans_stored = row["security_answer_hash"]
        if ":" in ans_stored:
            ans_salt, ans_hash = ans_stored.split(":", 1)
        else:
            ans_salt = ""
            ans_hash = ans_stored
        if not ans_salt or self._hash_pw(answer, ans_salt) != ans_hash:
            self.recover_error.setText("安全问题答案错误")
            return
        self._reset_username = username
        self.recover_error.setText("")
        self.stack.setCurrentIndex(2)

    def _do_reset(self):
        pw1 = self.reset_new_pw.text()
        pw2 = self.reset_confirm.text()
        if not pw1 or len(pw1) < 4:
            self.reset_error.setText("密码不能少于4位")
            return
        if pw1 != pw2:
            self.reset_error.setText("两次密码不一致")
            return
        salt = os.urandom(16).hex()
        pw_hash = self._hash_pw(pw1, salt)
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash=?, salt=? WHERE username=?",
                (pw_hash, salt, self._reset_username),
            )
        QMessageBox.information(self, "成功", "密码重置成功，请返回登录")
        self.stack.setCurrentIndex(0)
