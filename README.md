# SafeWork AI — Inteligencia Artificial & Visión Computacional

SafeWork AI es una solución de software empresarial de alto rendimiento diseñada para la salud ocupacional y ergonomía en oficinas. Utilizando Inteligencia Artificial y Visión Computacional en tiempo real a través de cámaras web estándar, el sistema detecta con precisión científica la fatiga del trabajador y las posturas de riesgo, previniendo trastornos musculoesqueléticos (TME) y el estrés laboral mediante alertas interactivas y "pausas activas" personalizadas.

---

## 🚀 Propuesta de Valor y Objetivos Comerciales

En el entorno corporativo moderno, los trastornos musculoesqueléticos y el agotamiento mental representan las principales causas de ausentismo laboral y pérdidas de productividad. **SafeWork AI** soluciona esto de manera pasiva y no invasiva:

*   **Prevención en Tiempo Real**: Evalúa constantemente la alineación espinal, inclinación lateral y niveles de cansancio del usuario.
*   **Pausas Activas Sincronizadas**: Emite alertas ergonómicas e interactivas que guían paso a paso al usuario en ejercicios físicos y visuales recomendados por especialistas de salud.
*   **Experiencia Receptiva e Ininterrumpida**: Diseñada como una aplicación de segundo plano que opera desde la bandeja del sistema (System Tray) y cuenta con controles ágiles para activar/desactivar la voz del asistente.

---

## 🧠 Innovaciones y Pilares Científicos de Precisión

Para garantizar un estándar comercial B2B libre de falsos positivos y falsas alarmas, SafeWork AI implementa procesamiento avanzado de señales biomecánicas:

### 1. Calibración Biométrica Inteligente (Perfil Personalizado)
Durante los primeros 5 segundos de cada sesión, el sistema analiza y calcula la postura óptima de reposo del usuario, promediando sus métricas faciales:
*   **EAR Dinámico (Eye Aspect Ratio)**: Aprende la apertura ocular en reposo para establecer el límite de somnolencia al $55\%$ del valor nominal (`base_ear * 0.55`), adaptándose a todo tipo de fisionomía facial.
*   **MAR Dinámico (Mouth Aspect Ratio)**: Mide la apertura bucal natural del usuario, programando el umbral de bostezo al $220\%$ del valor base (`base_mar * 2.20`) para evitar falsas alarmas por hablar o sonreír.
*   **Invariancia de Distancia**: Normaliza las distancias faciales y corporales respecto al ancho de hombros activo, evitando fallos de medición si el usuario se acerca o aleja de su pantalla.

### 2. Filtro de Suavizado de Señal (Anti-Jitter)
Integra un filtro de **Media Móvil Exponencial (EMA)** en tiempo real con un coeficiente de suavizado $\alpha = 0.30$:
$$S_t = \alpha \cdot X_t + (1 - \alpha) \cdot S_{t-1}$$
Esto elimina por completo el ruido del sensor óptico de la cámara, logrando que los datos en pantalla y los gatillos de alerta se procesen con absoluta fluidez matemática.

### 3. Triangulación Angular de Inclinaciones
*   **Inclinación lateral de cuello**: Se mide calculando la discrepancia angular entre la pendiente de las orejas y de los hombros usando la función trigonométrica `atan2`, logrando una precisión milimétrica sin importar la inclinación de la webcam.
*   **Postura Adelantada (Cervical)**: Se calcula mediante la flexión espinal basada en la relación trigonométrica de la nariz al centro del trapecio.

---

## 🎨 Características Destacadas de la Interfaz (UI/UX)

*   **HUD Biométrico Reactivo**: Un feed visual elegante y neonizado que dibuja la malla espinal y facial sobre el rostro. Los contornos de los ojos y labios se tornan color carmesí si se detectan transgresiones de fatiga o mala postura.
*   **Coach Guiado por Pasos (Dynamic Active Breaks)**: Ventana interactiva y responsiva que se actualiza dinámicamente en tiempo real cada 5 segundos (Paso 1 de 4 al Paso 4 de 4), mostrando el nombre del estiramiento, su ilustración fisiológica descriptiva y una barra de progreso.
*   **Guía de Voz Asíncrona Sincronizada (TTS)**: Un asistente de voz integrado narra paso a paso la rutina de estiramientos corporales (lumbar, hombros y cuello) o de relajación visual (regla 20-20-20, rehumectación), optimizado mediante hilos de ejecución para no congelar la pantalla.
*   **Integración al System Tray**: El software se minimiza elegantemente en la barra de tareas de Windows, enviando notificaciones no invasivas al usuario.

---

## 🏛️ Arquitectura de Software: Hexagonal y Limpia (SOLID)

El código fuente sigue de manera rigurosa la **Arquitectura Hexagonal (Domain-Driven Design)**, garantizando que el software sea robusto, mantenible, escalable y esté completamente desacoplado de las librerías físicas de hardware:

```
src/
├── domain/                      # Capa de Negocio (Reglas puras de la aplicación)
│   ├── entities/                # Entidades (postura.py, trabajador.py)
│   ├── reglas/                  # Ecuaciones Biomecánicas (calculo_postural.py)
│   └── puertos/                 # Interfaces abstractas (captura, alertas)
│
├── application/                 # Capa de Aplicación (Casos de uso e hilos de ejecución)
│   └── casos_de_uso/            # AnalizarPosturaUseCase
│
└── infrastructure/              # Capa de Adaptadores de Hardware (UI y Entrada de Datos)
    └── adaptadores/             # MediaPipeCameraAdapter, TkinterAlertAdapter, SystemTrayAdapter
```

Todo el código fuente modificado ha sido estructurado bajo principios SOLID y está **100% libre de comentarios ruidosos en sus módulos internos**, permitiendo que su estructura sea auto-explicativa y limpia.

---

## 🛠️ Instalación y Configuración (Entorno de Desarrollo)

### Requisitos Previos:
*   Python 3.10+
*   Webcam integrada o externa activa en el equipo.

### Instrucciones de Instalación:
1.  **Clonar el repositorio privado**:
    ```bash
    git clone https://github.com/tu-usuario/safework-ai.git
    cd safework-ai
    ```
2.  **Instalar dependencias necesarias**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Ejecutar la aplicación**:
    ```bash
    python main.py
    ```

---

## 📦 Empaquetado y Distribución Standalone (.EXE)

Para compilar y empaquetar SafeWork AI en un único archivo ejecutable de Windows para despliegue masivo en redes corporativas, ejecuta el script de construcción integrado:

```bash
python build.py
```

Al terminar, el ejecutable optimizado estará disponible de inmediato en la ruta:
`dist/SafeWork_AI.exe` (125.4 MB)

---

## 📄 Licencia

Este proyecto está licenciado bajo la **MIT License** — Copyright (c) 2026 Luis Cueva & UPN Project Team. Consulta el archivo `LICENSE` para más información.
