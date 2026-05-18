import subprocess
import sys
import os
import shutil

NOMBRE_EXE       = "SafeWork_AI"
ARCHIVO_MAIN     = "main.py"
ARCHIVO_ICONO    = os.path.join("assets", "safework_icon.ico")
CARPETA_ASSETS   = "assets"
CARPETA_SRC      = "src"
CARPETA_DIST     = "dist"
CARPETA_BUILD    = "build"


def limpiar_builds_anteriores() -> None:
    for carpeta in [CARPETA_BUILD, "__pycache__"]:
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
            print(f"[BUILD] Limpiado: {carpeta}/")
    spec = f"{NOMBRE_EXE}.spec"
    if os.path.exists(spec):
        os.remove(spec)


def construir_ejecutable() -> None:
    comando = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name={NOMBRE_EXE}",
        "--clean",
        f"--add-data={CARPETA_ASSETS}{os.pathsep}{CARPETA_ASSETS}",
        "--hidden-import=mediapipe",
        "--hidden-import=mediapipe.tasks",
        "--hidden-import=mediapipe.tasks.python",
        "--hidden-import=mediapipe.tasks.python.vision",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=qdarktheme",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--hidden-import=pyttsx3",
        "--hidden-import=pyttsx3.drivers",
        "--hidden-import=pyttsx3.drivers.sapi5",
        "--hidden-import=requests",
        "--hidden-import=onnxruntime",
        "--hidden-import=ultralytics",
        "--collect-all=mediapipe",
        "--collect-all=PyQt6",
        "--collect-all=qdarktheme",
        "--collect-all=ultralytics",
    ]

    if os.path.exists(ARCHIVO_ICONO):
        comando.append(f"--icon={ARCHIVO_ICONO}")
        print(f"[BUILD] Icono: {ARCHIVO_ICONO}")

    comando.append(ARCHIVO_MAIN)

    print("[BUILD] Iniciando PyInstaller...")
    print(f"[BUILD] Comando: {' '.join(comando)}\n")

    resultado = subprocess.run(comando)

    if resultado.returncode == 0:
        exe_path = os.path.join(CARPETA_DIST, f"{NOMBRE_EXE}.exe")
        if os.path.exists(exe_path):
            tam = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n[BUILD] Ejecutable generado: {exe_path} ({tam:.1f} MB)")
        print("[BUILD] Fase A completa. Ejecute Inno Setup para generar el instalador.")
    else:
        print("[BUILD] Error en el empaquetado. Revise los mensajes anteriores.")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("  SAFEWORK AI v1.0.0 — Softech Perú — Build Script")
    print("=" * 60)
    limpiar_builds_anteriores()
    construir_ejecutable()
