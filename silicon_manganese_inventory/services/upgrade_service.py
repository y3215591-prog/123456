import os
import sys
import shutil
import zipfile
import tempfile
from pathlib import Path


def get_app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def get_backup_dir():
    backup = get_app_root() / "_upgrade_backup"
    backup.mkdir(exist_ok=True)
    return backup


class UpgradeService:

    def is_frozen(self):
        return getattr(sys, "frozen", False)

    def validate_zip(self, zip_path):
        if not zipfile.is_zipfile(zip_path):
            raise ValueError("不是有效的 ZIP 文件")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            has_main = any("main.py" in n or "main_window.py" in n for n in names)
            if not has_main:
                raise ValueError("ZIP 中未找到程序模块，请确认选择了正确的升级包")

    def get_version_from_zip(self, zip_path):
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("config.py"):
                    content = zf.read(name).decode("utf-8", errors="ignore")
                    for line in content.split("\n"):
                        if "APP_VERSION" in line and "=" in line:
                            return line.split("=")[-1].strip().strip('"').strip("'")
        return "未知"

    def backup_current(self, app_root):
        backup = get_backup_dir()
        patterns_to_skip = {"*.db", "_upgrade_backup", "__pycache__", ".git", "upgrade_log.txt"}
        for item in app_root.iterdir():
            should_skip = False
            for pat in patterns_to_skip:
                if item.match(pat):
                    should_skip = True
                    break
            if should_skip:
                continue
            dest = backup / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    def extract_and_replace(self, zip_path):
        app_root = get_app_root()
        self.backup_current(app_root)

        log_lines = []
        log_lines.append(f"升级时间: {__import__('datetime').datetime.now()}")
        log_lines.append(f"升级包: {zip_path}")
        log_lines.append("")

        replaced_files = []
        has_error = False
        error_msg = ""

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                members = zf.namelist()
                log_lines.append(f"ZIP 包含 {len(members)} 个文件/目录")

                for member in members:
                    if member.endswith("/"):
                        continue
                    parts = member.replace("\\", "/").split("/")
                    for i in range(len(parts)):
                        if parts[i] in ("123456-master", "123456-main", parts[0]):
                            if i + 1 < len(parts):
                                parts = parts[i + 1:]
                                break

                    # Zip Slip protection: block path traversal
                    for p in parts:
                        if p == ".." or p.startswith("../") or p.startswith("~"):
                            log_lines.append(f"  安全阻止(路径穿越): {member}")
                            has_error = True
                            error_msg = f"非法路径: {member}"
                            break
                    if has_error:
                        break

                    rel_path = "/".join(parts)
                    dest = app_root / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)

                    if dest.name.endswith(".db"):
                        log_lines.append(f"  跳过数据库: {rel_path}")
                        continue
                    if dest.name == "_upgrade_backup":
                        log_lines.append(f"  跳过备份目录: {rel_path}")
                        continue

                    try:
                        content = zf.read(member)
                        with open(dest, "wb") as f:
                            f.write(content)
                        replaced_files.append(str(dest))
                        log_lines.append(f"  更新: {rel_path}")
                    except Exception as e:
                        has_error = True
                        error_msg = f"{rel_path}: {e}"
                        log_lines.append(f"  失败: {error_msg}")
                        break

            if has_error:
                log_lines.append("")
                log_lines.append("升级过程中出现错误，正在自动回滚...")
                for fpath in reversed(replaced_files):
                    try:
                        backup_f = get_backup_dir() / Path(fpath).relative_to(app_root)
                        if backup_f.exists():
                            shutil.copy2(str(backup_f), fpath)
                            log_lines.append(f"  回滚: {Path(fpath).relative_to(app_root)}")
                    except Exception as re:
                        log_lines.append(f"  回滚失败: {re}")
                log_lines.append("已回滚到升级前版本")
        except Exception as e:
            has_error = True
            error_msg = str(e)
            log_lines.append(f"升级异常: {e}")
            log_lines.append("正在自动回滚...")
            for fpath in reversed(replaced_files):
                try:
                    backup_f = get_backup_dir() / Path(fpath).relative_to(app_root)
                    if backup_f.exists():
                        shutil.copy2(str(backup_f), fpath)
                        log_lines.append(f"  回滚: {Path(fpath).relative_to(app_root)}")
                except Exception:
                    pass
            log_lines.append("已回滚到升级前版本")

        log_lines.append("")
        log_lines.append("升级完成" if not has_error else f"升级失败: {error_msg}")
        log_path = app_root / "upgrade_log.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

        if has_error:
            raise RuntimeError(error_msg)

        return len(members)

    def rollback(self):
        app_root = get_app_root()
        backup = get_backup_dir()
        if not backup.exists() or not list(backup.iterdir()):
            raise ValueError("没有找到备份文件，无法回滚")

        for item in backup.iterdir():
            dest = app_root / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    def get_app_version(self):
        from silicon_manganese_inventory import config
        return config.APP_VERSION
