# =============================================================================
# BUILD SCRIPT — SafeWork AI v1.0
# Fase A: Congelamiento con PyInstaller
# Ejecutar desde la raíz del proyecto: python build.py
# =============================================================================

import subprocess
import sys
import os


NOMBRE_EXE = "safework_ai"
ARCHIVO_ICONO = "assets/safework_icon.ico"


def ejecutar_empaquetado_pyinstaller() -> None:
    comando = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name={NOMBRE_EXE}",
        "--clean",
        "--add-data=assets;assets",
    ]

    if os.path.exists(ARCHIVO_ICONO):
        comando.append(f"--icon={ARCHIVO_ICONO}")

    comando.append("main.py")

    print("[SafeWork AI Build] Iniciando congelamiento con PyInstaller...")
    print(f"[SafeWork AI Build] Comando: {' '.join(comando)}")

    resultado = subprocess.run(comando, check=True)

    if resultado.returncode == 0:
        print(f"\n[SafeWork AI Build] ✓ Ejecutable generado: dist/{NOMBRE_EXE}.exe")
        print("[SafeWork AI Build] Fase A completada. Proceda con Inno Setup para Fase B.")
    else:
        print("[SafeWork AI Build] ✗ Error durante el empaquetado.")
        sys.exit(1)


if __name__ == "__main__":
    ejecutar_empaquetado_pyinstaller()
