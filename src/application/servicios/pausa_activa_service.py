from __future__ import annotations

from dataclasses import asdict, dataclass

from ...domain.entities.postura import EstadoAlerta


@dataclass(frozen=True)
class PausaActiva:
    tipo: str
    titulo: str
    duracion_segundos: int
    instrucciones: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["instrucciones"] = list(self.instrucciones)
        return payload

    def texto_corto(self) -> str:
        pasos = " ".join(self.instrucciones[:2])
        return f"Pausa activa: {self.titulo}. {pasos}"


class PausaActivaService:
    def recomendar(self, estado: EstadoAlerta, reincidencias: int = 0) -> PausaActiva | None:
        if estado == EstadoAlerta.MALA_POSTURA:
            return self._postura(reincidencias)
        if estado == EstadoAlerta.CERCANIA_MONITOR:
            return self._distancia_visual(reincidencias)
        if estado == EstadoAlerta.ADVERTENCIA_SUENO:
            return self._fatiga_visual(reincidencias)
        if estado in {EstadoAlerta.FATIGA_EXTREMA, EstadoAlerta.CABECEO}:
            return self._recuperacion_somnolencia(reincidencias)
        return None

    @staticmethod
    def _postura(reincidencias: int) -> PausaActiva:
        duracion = 45 if reincidencias < 2 else 75
        return PausaActiva(
            tipo="ergonomia",
            titulo="Reajuste de cuello y hombros",
            duracion_segundos=duracion,
            instrucciones=(
                "Apoya la espalda en la silla y baja los hombros.",
                "Mira al frente y alinea orejas, hombros y cadera.",
                "Gira suavemente el cuello a cada lado durante cinco segundos.",
            ),
        )

    @staticmethod
    def _distancia_visual(reincidencias: int) -> PausaActiva:
        duracion = 30 if reincidencias < 2 else 60
        return PausaActiva(
            tipo="distancia_visual",
            titulo="Distancia segura al monitor",
            duracion_segundos=duracion,
            instrucciones=(
                "Aleja el rostro de la pantalla hasta una distancia comoda.",
                "Relaja la mandibula y apoya ambos pies en el piso.",
                "Mantén el borde superior del monitor cerca de la altura de los ojos.",
            ),
        )

    @staticmethod
    def _fatiga_visual(reincidencias: int) -> PausaActiva:
        duracion = 60 if reincidencias < 2 else 90
        return PausaActiva(
            tipo="fatiga",
            titulo="Descanso visual 20-20",
            duracion_segundos=duracion,
            instrucciones=(
                "Mira un punto lejano durante veinte segundos.",
                "Parpadea lento cinco veces para lubricar los ojos.",
                "Respira profundo antes de volver a la pantalla.",
            ),
        )

    @staticmethod
    def _recuperacion_somnolencia(reincidencias: int) -> PausaActiva:
        duracion = 120 if reincidencias < 2 else 180
        return PausaActiva(
            tipo="somnolencia",
            titulo="Pausa de recuperacion",
            duracion_segundos=duracion,
            instrucciones=(
                "Deten la actividad y retira la vista del monitor.",
                "Ponte de pie, estira brazos y respira profundo.",
                "Toma agua antes de continuar.",
            ),
        )
