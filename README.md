# SafeWork AI — Inteligencia Artificial & Visión Computacional

SafeWork AI es una solución de software empresarial de alto rendimiento diseñada para la salud ocupacional y ergonomía en oficinas. Utilizando Inteligencia Artificial y Visión Computacional híbrida en tiempo real a través de cámaras web estándar, el sistema detecta con precisión científica la fatiga del trabajador y las posturas de riesgo, previniendo trastornos musculoesqueléticos (TME) y el estrés laboral mediante alertas interactivas, síntesis de voz activa y un sistema completo de "pausas activas" y reportes ocupacionales.

---

## 🚀 Propuesta de Valor y Objetivos Comerciales

En el entorno corporativo moderno, los trastornos musculoesqueléticos y el agotamiento mental representan las principales causas de ausentismo laboral y pérdidas de productividad. **SafeWork AI** soluciona esto de manera pasiva y no invasiva:

*   **Prevención Híbrida en Tiempo Real**: Fusión inteligente de redes neuronales YOLO para clasificación de gestos/fatiga y MediaPipe para biometría tridimensional.
*   **Pausas Activas Programadas e Interactivas**: Emite alertas ergonómicas guiadas visualmente paso a paso (lumbar, hombros, cuello y visual 20-20-20) con barra de progreso interactiva.
*   **Arquitectura Multi-Hilo de Alto Rendimiento**: Procesamiento de IA (QThread), voz y GUI (PyQt6) desacoplados para garantizar fluidez absoluta de 60 FPS sin ralentizar el equipo.
*   **Reportes Corporativos Exportables**: Genera estadísticas completas del desempeño ergonómico en reportes interactivos HTML y documentos oficiales listos para imprimir en formato PDF.

---

## 🧠 Innovaciones y Pilares Científicos de Precisión

Para garantizar un estándar comercial B2B libre de falsos positivos y falsas alarmas, SafeWork AI implementa procesamiento avanzado de señales biomecánicas y machine learning:

### 1. Fusión de Sensores (YOLO + MediaPipe)
*   **MediaPipe Landmarks**: Obtiene coordenadas 3D precisas de rostro y tren superior para mediciones trigonométricas de inclinación de orejas, nariz, ojos, labios y hombros.
*   **YOLO Classification**: Identifica estados cognitivos complejos (bostezos activos, ojos cerrados por somnolencia prolongada o fatiga facial).
*   **Lógica de Coexistencia y Oclusión**: Si el usuario se frota la cara o apoya la mano sobre su rostro (oclusión), el sistema lo detecta inteligentemente para suspender momentáneamente el cálculo de fatiga y evitar falsas alertas.

### 2. Calibración Biométrica Inteligente (Perfil Personalizado)
Durante los primeros segundos de cada sesión, el sistema analiza y calcula la postura óptima de reposo del usuario, adaptándose a su fisonomía:
*   **EAR Dinámico (Eye Aspect Ratio)**: Determina la apertura ocular de base para estimar con exactitud el nivel de somnolencia individual.
*   **MAR Dinámico (Mouth Aspect Ratio)**: Mide la apertura bucal natural en reposo para calibrar el umbral de bostezo, ignorando gestos naturales de conversación o sonrisa.
*   **Invariancia de Distancia y Zoom**: Normaliza la relación del rostro respecto al ancho de hombros tridimensional, impidiendo fallas de perspectiva cuando el trabajador se aleja o se acerca a la webcam.

### 3. Filtro de Suavizado Biomecánico (Anti-Jitter)
Integra un filtro de **Media Móvil Exponencial (EMA)** en tiempo real con un coeficiente de suavizado $\alpha = 0.30$:
$$S_t = \alpha \cdot X_t + (1 - \alpha) \cdot S_{t-1}$$
Esto elimina por completo el temblor o ruido del sensor óptico en condiciones de baja iluminación, estabilizando los cálculos en pantalla.

### 4. Máquina de Estados con Histéresis
Las alertas ergonómicas y transiciones de estados (Óptimo ↔ Cabeceo ↔ Mala Postura) están reguladas por un módulo de histéresis temporal. Esto evita alertas parpadeantes debido a movimientos rápidos del cuerpo.

---

## 🎨 Características Destacadas de la Interfaz (UI/UX Premium)

*   **HUD Biométrico Neonizado (HUD View)**: Un feed visual premium desarrollado en PyQt6 con overlay en vivo. Dibuja la malla tridimensional facial y del torso sobre el trabajador con colores reactivos que transicionan al rojo si se superan los umbrales seguros.
*   **Coach Guiado por Pasos (Dynamic Active Breaks)**: Ventana interactiva y responsiva que guía paso a paso al usuario en ejercicios fisiológicos y visuales con descripciones y barra de progreso.
*   **Guía de Voz Asíncrona Sincronizada (TTS)**: Un asistente de voz integrado narra en tiempo real los ejercicios de estiramiento y relajación corporal de manera asíncrona sin bloquear la GUI.
*   **Dashboard de Métricas**: Indicadores visuales en tiempo real del nivel de fatiga, calidad de detección lumínica/óptica, postura y cercanía al monitor.
*   **Integración con System Tray (Bandeja del Sistema)**: El software se ejecuta silenciosamente en segundo plano en la barra de tareas de Windows, enviando notificaciones no invasivas y brindando accesos rápidos mediante un menú contextual.

---

## 🏛️ Arquitectura de Software: Hexagonal y Limpia (SOLID)

El código fuente sigue de manera rigurosa la **Arquitectura Hexagonal (Domain-Driven Design)**, estructurado bajo los principios SOLID para garantizar mantenibilidad, escalabilidad y desacoplamiento absoluto de las dependencias externas:

```
src/
├── domain/                      # Capa de Dominio (Reglas puras de la aplicación)
│   ├── entities/                # Entidades puras (postura.py, trabajador.py)
│   ├── reglas/                  # Ecuaciones Biomecánicas (calculo_postural.py, normalizacion_yolo.py)
│   └── puertos/                 # Interfaces de contratos (captura, persistencia, voz)
│
├── application/                 # Capa de Aplicación (Orquestación y Servicios)
│   └── servicios/               # monitor_safework_service.py, fusion_sensores_service.py,
│                                # pausa_activa_service.py, reporte_analisis_service.py,
│                                # perfil_biometrico_service.py, reporte_export_service.py,
│                                # reporte_html_renderer.py, reporte_pdf_renderer.py
│
└── infrastructure/              # Capa de Infraestructura (Adaptadores y Frameworks)
    ├── config/                  # Ajustes locales (safework_settings.py)
    └── adaptadores/             # GUI PyQt6 (safework_app.py), Hilo IA (motor_vision_hibrido_qthread.py),
                                 # Hilo Voz (voz_qthread_adapter.py), Persistencia (memoria_usuario_json_adapter.py),
                                 # Captura de video (captura_hibrida_adapter.py), Actualización (github_update_adapter.py)
```

---

## 🛠️ Instalación y Configuración (Entorno de Desarrollo)

### Requisitos Previos:
*   Python 3.10+
*   Webcam integrada o externa activa en el equipo.

### Instrucciones de Instalación:
1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/LuisCueva12/SafeWork_AI.git
    cd SafeWork_AI
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

Para compilar y empaquetar SafeWork AI en un único archivo ejecutable de Windows optimizado para redes corporativas B2B, puedes ejecutar el script de empaquetado automático:

```bash
python build.py
```

Al terminar, el ejecutable empaquetado estará disponible en la ruta:
`dist/SafeWork_AI.exe`

---

## 📄 Licencia

Este proyecto está licenciado bajo la **MIT License** — Copyright (c) 2026 Luis Cueva & UPN Project Team. Consulta el archivo `LICENSE` para más información.
