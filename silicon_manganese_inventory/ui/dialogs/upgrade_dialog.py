from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFileDialog, QMessageBox, QWidget,
)
from PySide6.QtCore import Qt, QThread, Signal
from silicon_manganese_inventory.services.upgrade_service import UpgradeService


class _UpgradeWorker(QThread):
    progress = Signal(str, int)
    finished = Signal(bool, str)

    def __init__(self, zip_path):
        super().__init__()
        self.zip_path = zip_path
        self.svc = UpgradeService()

    def run(self):
        try:
            self.progress.emit("正在验证升级包...", 10)
            self.svc.validate_zip(self.zip_path)

            version = self.svc.get_version_from_zip(self.zip_path)
            self.progress.emit(f"升级到版本 {version}，正在备份当前文件...", 30)

            self.progress.emit("正在替换文件...", 60)
            count = self.svc.extract_and_replace(self.zip_path)

            self.progress.emit(f"升级完成，共更新 {count} 个文件", 100)
            self.finished.emit(True, version)
        except Exception as e:
            self.finished.emit(False, str(e))


class UpgradeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统升级")
        self.setMinimumSize(480, 260)
        self.setStyleSheet("QDialog { background: #FFFFFF; }")
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("系统升级")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1D2939;")
        layout.addWidget(title)

        self._version_label = QLabel()
        self._version_label.setStyleSheet("font-size: 13px; color: #6B7280;")
        try:
            svc = UpgradeService()
            self._version_label.setText(f"当前版本: {svc.get_app_version()}")
        except Exception:
            self._version_label.setText("当前版本: 未知")
        layout.addWidget(self._version_label)

        hint = QLabel(
            "请选择从 GitHub 下载的最新 ZIP 升级包\n"
            "升级将保留数据库和已有业务数据"
        )
        hint.setStyleSheet("font-size: 13px; color: #374151; padding: 8px 0;")
        layout.addWidget(hint)

        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 13px; color: #2B579A; font-weight: bold;")
        layout.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar { border: 1px solid #D1D5DB; border-radius: 3px;
                           text-align: center; height: 22px; }
            QProgressBar::chunk { background: #2B579A; border-radius: 2px; }
        """)
        layout.addWidget(self._progress)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._select_btn = QPushButton("选择升级包...")
        self._select_btn.setStyleSheet("""
            QPushButton { background: #2B579A; color: white; border: none;
                          padding: 8px 20px; border-radius: 4px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #234881; }
            QPushButton:disabled { background: #95A5C2; }
        """)
        self._select_btn.clicked.connect(self._on_select)
        btn_layout.addWidget(self._select_btn)

        self._cancel_btn = QPushButton("关闭")
        self._cancel_btn.setStyleSheet("""
            QPushButton { background: #FFFFFF; color: #374151; border: 1px solid #D1D5DB;
                          padding: 8px 20px; border-radius: 4px; font-size: 13px; }
            QPushButton:hover { background: #F3F4F6; }
        """)
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    def _on_select(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择升级包", "", "ZIP 文件 (*.zip)")
        if not file_path:
            return

        self._select_btn.setEnabled(False)
        self._cancel_btn.setText("取消")
        self._progress.setVisible(True)
        self._progress.setValue(0)

        self._worker = _UpgradeWorker(file_path)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, msg, value):
        self._status.setText(msg)
        self._progress.setValue(value)

    def _on_finished(self, success, info):
        self._progress.setVisible(False)
        if success:
            self._status.setText(f"升级成功! 新版本: {info}")
            QMessageBox.information(
                self, "升级完成",
                f"已升级到版本 {info}。\n\n"
                "请手动重启程序以应用更新。\n"
                "数据库和业务数据已完整保留。")
            self.accept()
        else:
            self._status.setText(f"升级失败: {info}")
            self._select_btn.setEnabled(True)
            self._cancel_btn.setText("关闭")
            QMessageBox.warning(self, "升级失败", str(info))
