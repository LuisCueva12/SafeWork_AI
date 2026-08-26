from __future__ import annotations

import base64

_CLAVE_XOR = 0x5A


def ofuscar(texto: str) -> str:
    try:
        codificado = bytearray(texto.encode("utf-8"))
        for i in range(len(codificado)):
            codificado[i] ^= _CLAVE_XOR
        return base64.b64encode(codificado).decode("utf-8")
    except Exception:
        return texto


def desofuscar(texto_ofuscado: str) -> str:
    texto_limpio = texto_ofuscado.strip()
    if not texto_limpio:
        return ""
    if texto_limpio.startswith(("{", "[")):
        return texto_ofuscado
    try:
        decodificado = bytearray(base64.b64decode(texto_limpio.encode("utf-8")))
        for i in range(len(decodificado)):
            decodificado[i] ^= _CLAVE_XOR
        return decodificado.decode("utf-8")
    except Exception:
        return texto_ofuscado
