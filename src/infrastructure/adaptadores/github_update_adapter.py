import os
import sys
import subprocess
import requests

class GitHubUpdateAdapter:
    def __init__(self, version_actual: str = "1.0.0") -> None:
        self.version_actual = version_actual
        self.url_version = "https://raw.githubusercontent.com/LuisCueva12/SafeWork_AI/main/version.txt"
        self.url_instalador = "https://github.com/LuisCueva12/SafeWork_AI/releases/latest/download/Instalador_SafeWork_AI.exe"

    def verificar_actualizacion(self) -> bool:
        try:
            respuesta = requests.get(self.url_version, timeout=5)
            if respuesta.status_code == 200:
                version_servidor = respuesta.text.strip()
                return self._es_version_mayor(self.version_actual, version_servidor)
            return False
        except requests.RequestException:
            return False

    def ejecutar_auto_actualizacion(self) -> None:
        carpeta_temp = os.environ.get("TEMP")
        if not carpeta_temp:
            return
            
        ruta_guardado = os.path.join(carpeta_temp, "update_setup.exe")
        
        try:
            with requests.get(self.url_instalador, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(ruta_guardado, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            subprocess.Popen([ruta_guardado, "/SILENT", "/SUPPRESSMSGBOXES"])
            sys.exit(0)
        except (requests.RequestException, OSError):
            pass

    def _es_version_mayor(self, local: str, server: str) -> bool:
        try:
            partes_local = [int(x) for x in local.split(".")]
            partes_server = [int(x) for x in server.split(".")]
            return partes_server > partes_local
        except ValueError:
            return server > local

if __name__ == "__main__":
    adaptador = GitHubUpdateAdapter("1.0.0")
    print(f"Versión local: {adaptador.version_actual}")
    print("Verificando actualizaciones...")
    
    if adaptador.verificar_actualizacion():
        print("¡Nueva versión disponible! Iniciando auto-actualización silenciosa...")
        adaptador.ejecutar_auto_actualizacion()
    else:
        print("El sistema está en la última versión o no se pudo verificar.")
