import os
import sys
from pathlib import Path

# Ensure local imports work when executing directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crypto_utils import encrypt_machine_bound, get_machine_fingerprint


def main() -> None:
    """Run interactive machine-bound cookie encryption tool."""
    plugin_dir = Path(__file__).resolve().parent
    cookies_txt = plugin_dir / "cookies.txt"
    cookies_enc = plugin_dir / "cookies.enc"

    machine_id = get_machine_fingerprint()
    print("=" * 60)
    print("🔒 AstrBot 日本实况街景 - 机器绑定 Cookie 加密工具")
    print(f"🖥️ 当前机器唯一硬件指纹: {machine_id}")
    print("💡 说明: 加密后的文件离开这台机器将彻底无法解密，零密码心智负担。")
    print("=" * 60)

    raw_cookie = ""
    if cookies_txt.exists():
        print(f"\n检测到同目录下存在明文文件: {cookies_txt.name}")
        choice = (
            input("是否直接加密现有的 cookies.txt 文件？(y/n, 默认 y): ")
            .strip()
            .lower()
        )
        if choice in ("", "y", "yes"):
            try:
                raw_cookie = cookies_txt.read_text(encoding="utf-8").strip()
            except OSError as exc:
                print(f"❌ 读取 cookies.txt 失败: {exc}")

    if not raw_cookie:
        print(
            "\n请直接粘贴你的 YouTube Cookie（从浏览器 F12 或扩展导出的内容），输入完成后按回车："
        )
        try:
            raw_cookie = input().strip()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消操作。")
            return

    if not raw_cookie:
        print("❌ 未输入任何 Cookie 内容，操作中止。")
        return

    print("\n⏳ 正在使用本机硬件指纹执行 PBKDF2 + AES 机器绑定加密...")
    try:
        encrypted_bytes = encrypt_machine_bound(raw_cookie)
        cookies_enc.write_bytes(encrypted_bytes)

        # On POSIX systems (Linux / macOS), set 0600 permissions
        if os.name == "posix":
            try:
                cookies_enc.chmod(0o600)
            except OSError:
                pass

        print(
            f"✅ 成功生成加密凭证文件: {cookies_enc.name} (大小: {len(encrypted_bytes)} 字节)"
        )

        # Offer to clean up plaintext cookies.txt
        if cookies_txt.exists():
            cleanup = (
                input(
                    "⚠️ 是否删除原始明文 cookies.txt 以确保磁盘绝对安全？(y/n, 默认 y): "
                )
                .strip()
                .lower()
            )
            if cleanup in ("", "y", "yes"):
                try:
                    cookies_txt.unlink()
                    print(f"🗑️ 已安全删除明文文件: {cookies_txt.name}")
                except OSError as exc:
                    print(f"⚠️ 删除明文文件失败: {exc}")

        print("\n🎉 加密配置完成！现在你可以安心启动 AstrBot，插件会自动无感解密运行。")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 加密过程中发生错误: {exc}")


if __name__ == "__main__":
    main()
