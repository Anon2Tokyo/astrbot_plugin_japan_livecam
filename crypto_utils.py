import base64
import hashlib
import os
import platform
import subprocess
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

SALT_BYTE_LENGTH = 16
PBKDF2_ITERATIONS = 100_000


def get_machine_fingerprint() -> str:
    """Retrieve a unique, tamper-resistant machine fingerprint based on the OS.

    Returns:
        A unique machine identifier string prefixed with OS type.
    """
    sys_name = platform.system()
    if sys_name == "Linux":
        for path_str in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            path = Path(path_str)
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        return f"linux:{content}"
                except OSError:
                    pass
    elif sys_name == "Windows":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
            ) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    return f"win:{guid}"
        except OSError:
            pass
    elif sys_name == "Darwin":
        try:
            output = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                text=True,
                timeout=3,
            )
            for line in output.splitlines():
                if "IOPlatformUUID" in line:
                    uuid_str = line.split()[-1].strip('"')
                    return f"darwin:{uuid_str}"
        except (subprocess.SubprocessError, OSError):
            pass

    # Generic hardware fallback (MAC address + node name)
    return f"generic:{uuid.getnode()}:{platform.node()}"


def _derive_fernet_key(machine_id: str, salt: bytes) -> bytes:
    """Derive a URL-safe base64 32-byte Fernet key from machine ID and salt.

    Args:
        machine_id: Unique hardware identifier.
        salt: Cryptographic random salt bytes.

    Returns:
        Base64 urlsafe encoded key for Fernet.
    """
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        machine_id.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(derived)


def encrypt_machine_bound(data: str) -> bytes:
    """Encrypt plaintext string bound to the current physical/virtual machine.

    Args:
        data: Plaintext string to encrypt.

    Returns:
        Binary encrypted payload containing salt + ciphertext.
    """
    machine_id = get_machine_fingerprint()
    salt = os.urandom(SALT_BYTE_LENGTH)
    key = _derive_fernet_key(machine_id, salt)
    fernet = Fernet(key)
    ciphertext = fernet.encrypt(data.encode("utf-8"))
    return salt + ciphertext


def decrypt_machine_bound(payload: bytes) -> str | None:
    """Decrypt machine-bound payload using current machine fingerprint.

    Args:
        payload: Binary encrypted payload containing salt + ciphertext.

    Returns:
        Decrypted plaintext string, or None if machine ID does not match.
    """
    if len(payload) <= SALT_BYTE_LENGTH:
        return None

    salt = payload[:SALT_BYTE_LENGTH]
    ciphertext = payload[SALT_BYTE_LENGTH:]
    machine_id = get_machine_fingerprint()
    key = _derive_fernet_key(machine_id, salt)
    fernet = Fernet(key)

    try:
        decrypted_bytes = fernet.decrypt(ciphertext)
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        return None
