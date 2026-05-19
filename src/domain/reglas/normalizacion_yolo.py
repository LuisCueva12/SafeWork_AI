from __future__ import annotations

CLASES_NORMAL = frozenset(
    {
        "normal",
        "awake",
        "alert",
        "open",
        "open eyes",
        "eyes open",
        "no yawn",
        "not yawn",
        "no drowsy",
        "not drowsy",
        "no fatigue",
    }
)
CLASES_BOSTEZO = frozenset({"yawn", "bostezo"})
CLASES_FATIGA = frozenset({"drowsy", "fatiga"})


def normalizar_clase_yolo(clase: str | None) -> str:
    texto = str(clase or "").strip().lower().replace("_", " ").replace("-", " ")
    texto = " ".join(texto.split())
    if not texto or texto in CLASES_NORMAL:
        return "normal"
    if "bostezo" in texto or "bostez" in texto or "yawn" in texto:
        return "yawn"
    if (
        "fatiga" in texto
        or "drowsy" in texto
        or "sleepy" in texto
        or "somnol" in texto
        or "microsleep" in texto
        or "closed eye" in texto
        or "eyes closed" in texto
        or "closed eyes" in texto
        or "ojos cerrados" in texto
    ):
        return "drowsy"
    return texto


def es_clase_bostezo(clase: str | None) -> bool:
    return normalizar_clase_yolo(clase) in CLASES_BOSTEZO


def es_clase_fatiga(clase: str | None) -> bool:
    return normalizar_clase_yolo(clase) in CLASES_FATIGA


def es_clase_sueno_o_bostezo(clase: str | None) -> bool:
    clase_normalizada = normalizar_clase_yolo(clase)
    return clase_normalizada in CLASES_BOSTEZO or clase_normalizada in CLASES_FATIGA
