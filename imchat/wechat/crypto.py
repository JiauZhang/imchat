from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import math


def encrypt_aes_ecb(plaintext: bytes, key: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    padded = _pkcs7_pad(plaintext, 16)
    return encryptor.update(padded) + encryptor.finalize()


def decrypt_aes_ecb(ciphertext: bytes, key: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return _pkcs7_unpad(padded)


def aes_ecb_padded_size(plaintext_size: int) -> int:
    return math.ceil((plaintext_size + 1) / 16) * 16


def _pkcs7_pad(data: bytes, block_size: int) -> bytes:
    padding_len = block_size - (len(data) % block_size)
    if padding_len == 0:
        padding_len = block_size
    return data + bytes([padding_len] * padding_len)


def _pkcs7_unpad(data: bytes) -> bytes:
    padding_len = data[-1]
    if padding_len > len(data):
        return data
    return data[:-padding_len]


def parse_aes_key(aes_key_base64: str) -> bytes:
    """CDNMedia.aes_key: base64(raw 16 bytes) | base64(hex string of 16 bytes)"""
    import base64
    decoded = base64.b64decode(aes_key_base64)
    if len(decoded) == 16:
        return decoded
    if len(decoded) == 32:
        hex_str = decoded.decode("ascii")
        if all(c in "0123456789abcdefABCDEF" for c in hex_str):
            return bytes.fromhex(hex_str)
    raise ValueError(
        f"aes_key must decode to 16 raw bytes or 32-char hex string, "
        f"got {len(decoded)} bytes (base64='{aes_key_base64}')"
    )