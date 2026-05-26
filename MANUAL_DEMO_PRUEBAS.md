# Manual de demo y pruebas - SafeWork AI

Este manual sirve para grabar un video demo y validar que SafeWork AI funcione de forma clara, profesional y estable antes de presentarlo a un cliente, jurado o usuario final.

## 1. Objetivo del video demo

El video debe demostrar que SafeWork AI:

- Monitorea ergonomia y fatiga en tiempo real con camara web.
- Identifica postura, fatiga visual, distancia al monitor, bostezos, ausencia y reingreso.
- Reduce falsos positivos usando persistencia, calidad de lectura y estabilizacion.
- Permite configurar el perfil del usuario.
- Exporta reportes PDF de jornada y de historial global.
- Funciona localmente con arquitectura limpia y sin depender de internet.

Duracion recomendada del video: 5 a 8 minutos.

## 2. Preparacion antes de grabar

Ejecutar desde la raiz del proyecto:

```powershell
python main.py
```

Verificar antes de iniciar la grabacion:

- La camara se ve completa.
- El rostro y hombros aparecen dentro del encuadre.
- Hay luz frontal suficiente.
- El usuario aparece sentado de forma natural.
- El nombre y rol del usuario aparecen en el header.
- El boton `Perfil` abre el formulario correctamente.
- El panel lateral muestra `Insights IA` y `Resumen ergonomico (Hoy)`.
- El boton visible de reporte dice `Exportar reporte`.

No iniciar la demo con objetos tapando la cara, baja luz extrema o la camara fuera de foco.

## 3. Guion recomendado para el video

### Escena 1 - Presentacion del sistema

Duracion sugerida: 30 a 45 segundos.

Mostrar:

- Pantalla principal de SafeWork AI.
- Header con logo, estado del motor visual, usuario y rol.
- Panel de camara.
- Indicadores circulares.
- Panel de insights.
- Resumen ergonomico.

Texto sugerido:

> SafeWork AI es un sistema de monitoreo ergonomico en tiempo real que usa vision computacional para analizar postura, fatiga visual, distancia al monitor, bostezos y ausencias durante la jornada. El sistema trabaja localmente, registra indicadores y permite exportar reportes PDF de la jornada y del historial global.

Validacion esperada:

- La app abre sin errores visibles.
- No aparece mensaje tecnico de YOLO faltante en pantalla.
- El sistema muestra motor visual activo.

### Escena 2 - Perfil del usuario

Duracion sugerida: 30 segundos.

Accion:

- Clic en `Perfil`.
- Mostrar nombre, identificador, rol, tipo de usuario, empresa, area y puesto.
- Cerrar o guardar sin cambiar datos si ya estan correctos.

Texto sugerido:

> El sistema trabaja con un perfil local. Esto permite que las metricas y reportes indiquen a quien pertenece el monitoreo, cual es su rol y en que contexto se realiza la evaluacion.

Validacion esperada:

- Si el perfil ya existe, no se pide nuevamente al iniciar la app.
- El usuario puede editarlo desde el boton `Perfil`.

### Escena 3 - Monitoreo normal

Duracion sugerida: 45 segundos.

Accion:

- Sentarse recto y mirar al frente.
- Mantener postura estable.

Mostrar:

- Indicador de postura en verde o estable.
- Fatiga visual normal.
- Distancia adecuada.
- Atencion estable.
- Indice general alto.

Texto sugerido:

> En una postura normal, el sistema mantiene indicadores estables. El resumen ergonomico muestra un indice general y riesgos vivos de postura, distancia y fatiga visual.

Validacion esperada:

- No debe marcar `CABECEO`.
- No debe marcar `MALA POSTURA` por estar quieto y centrado.
- No debe marcar `FATIGA EXTREMA`.

### Escena 4 - Mala postura sostenida

Duracion sugerida: 45 a 60 segundos.

Accion:

- Inclinar el cuello o espalda de forma clara.
- Mantener la postura algunos segundos.

Mostrar:

- Indicador de postura baja o en amarillo/naranja.
- Estado de mala postura solo si el patron se sostiene.

Texto sugerido:

> Para evitar falsos positivos, el sistema no reacciona por un movimiento corto. Solo registra mala postura cuando detecta un patron sostenido.

Validacion esperada:

- Un movimiento rapido no debe activar alerta.
- Una inclinacion sostenida si debe afectar el indicador de postura.
- El estado no debe cambiar a cabeceo si los ojos estan abiertos y no hay somnolencia.

### Escena 5 - Mirar al teclado

Duracion sugerida: 30 a 45 segundos.

Accion:

- Mirar hacia abajo como si se estuviera escribiendo.
- Mantener ojos abiertos.

Texto sugerido:

> El sistema diferencia mirar al teclado de un cabeceo real. Para marcar cabeceo necesita evidencia de somnolencia, no solo una inclinacion de cabeza.

Validacion esperada:

- No debe marcar `CABECEO`.
- Puede afectar postura, pero no debe escalar a somnolencia si no hay ojos cerrados.

### Escena 6 - Cabeceo real

Duracion sugerida: 45 a 60 segundos.

Accion:

- Simular cabeza caida con ojos cerrados durante varios segundos.
- Evitar salir del encuadre.

Texto sugerido:

> El cabeceo se considera un evento mas critico. Por eso el sistema exige cabeza caida, ojos cerrados o evidencia sostenida de somnolencia antes de registrar la alerta.

Validacion esperada:

- Debe aparecer `CABECEO` solo cuando el patron es sostenido.
- No debe activarse por una inclinacion breve.
- No debe activarse si el usuario sale parcialmente de camara.

### Escena 7 - Bostezo

Duracion sugerida: 30 a 45 segundos.

Accion:

- Simular un bostezo abriendo la boca de forma sostenida.
- No tapar la boca con la mano.

Texto sugerido:

> El sistema puede detectar bostezos usando MediaPipe incluso cuando no hay modelo YOLO activo. La validacion se basa en apertura bucal sostenida y no en un solo frame.

Validacion esperada:

- Debe detectar advertencia de bostezo si la apertura es sostenida.
- No debe marcar bostezo por hablar normal o abrir la boca rapidamente.

### Escena 8 - Ausencia y reingreso

Duracion sugerida: 45 segundos.

Accion:

- Salir del encuadre.
- Esperar unos segundos.
- Volver a sentarse.

Texto sugerido:

> Cuando el usuario sale de camara, el sistema registra ausencia o lectura inestable. Al volver, aplica una ventana de estabilizacion para evitar falsos cabeceos al sentarse.

Validacion esperada:

- Al salir debe indicar ausencia o lectura no valida.
- Al volver no debe marcar cabeceo inmediato.
- Debe estabilizar antes de evaluar riesgos.

### Escena 9 - Reportes

Duracion sugerida: 60 segundos.

Accion:

- Clic en `Exportar reporte`.
- Mostrar que se abre el PDF de jornada.
- Mostrar la carpeta donde se guardaron los reportes.

Texto sugerido:

> SafeWork AI genera dos documentos PDF: un reporte de jornada para el dia evaluado y un historial global para seguimiento acumulado. Ambos se guardan localmente y el sistema muestra la carpeta de salida.

Validacion esperada:

- No debe generarse HTML.
- Deben existir dos PDFs:
  - `safework_reporte_jornada_...pdf`
  - `safework_historial_global_...pdf`
- Debe existir un JSON tecnico interno.
- El PDF debe tener logo, margenes, tarjetas, tabla e informacion organizada.

Ruta esperada por defecto:

```text
C:\Users\luisc\Documents\SafeWork AI Reports
```

Ruta alternativa si no hay permisos:

```text
C:\Users\luisc\OneDrive\Desktop\Proyectos CV\EXPOINNOVA\reportes_safework
```

## 4. Checklist funcional antes de grabar

### Arranque

- La app abre con `python main.py`.
- No aparecen errores rojos en la interfaz.
- No aparece mensaje de modelo YOLO faltante en pantalla.
- El motor visual se muestra activo.
- El perfil del usuario esta cargado.

### Camara

- La imagen se ve completa.
- No se corta la cabeza.
- No se cortan hombros.
- El overlay no tapa zonas criticas.
- El video mantiene fluidez aceptable.

### Indicadores

- Postura cambia cuando hay inclinacion real.
- Fatiga visual cambia cuando se cierran ojos.
- Distancia cambia al acercarse al monitor.
- Atencion cambia cuando hay bostezo o apertura bucal.
- Indice general se actualiza con las metricas vivas.

### Alertas

- Mala postura requiere persistencia.
- Cabeceo requiere evidencia de somnolencia.
- Bostezo requiere apertura sostenida.
- Salir del encuadre no debe generar cabeceo.
- Reingreso no debe generar alerta inmediata.

### Reportes

- Un solo boton visible: `Exportar reporte`.
- Se abre el PDF de jornada.
- Se guarda tambien el PDF global.
- Se muestra la carpeta en la barra inferior.
- No se generan archivos `.html`.

## 5. Checklist visual para el video

- Usar buena iluminacion.
- Limpiar el fondo si es posible.
- Mantener el rostro centrado.
- No usar gorra o mascarilla durante la demo.
- Evitar tapar boca y ojos.
- No grabar con la ventana parcialmente fuera de pantalla.
- Mostrar brevemente la carpeta de reportes.
- Abrir el PDF y mostrar las secciones principales.

## 6. Fallas que deben revisarse si aparecen

### Falso cabeceo

Revisar:

- Si el rostro esta saliendo del encuadre.
- Si los hombros no se detectan.
- Si hay baja luz.
- Si se esta mirando al teclado con ojos semicerrados.
- Si el estado esta en cooldown reteniendo una alerta anterior.

Resultado esperado:

- El sistema no debe marcar cabeceo por movimiento breve.

### Bostezo no detectado

Revisar:

- Si la boca esta visible.
- Si la apertura fue sostenida.
- Si la camara tiene suficiente luz.
- Si la mano tapa parte del rostro.

Resultado esperado:

- Un bostezo claro y sostenido debe marcar advertencia.

### Mala postura demasiado sensible

Revisar:

- Si la postura fue sostenida.
- Si el usuario esta muy cerca del monitor.
- Si el fondo o la camara deforman la perspectiva.

Resultado esperado:

- No debe alertar por una inclinacion corta.

### PDF mal generado

Revisar:

- Que exista `assets/logo.png`.
- Que la carpeta de salida tenga permisos.
- Que el PDF no este abierto/bloqueado por otro programa.

Resultado esperado:

- PDF con logo, tarjetas, tablas y margenes correctos.

## 7. Explicacion tecnica corta para la demo

SafeWork AI esta organizado con arquitectura hexagonal:

- Dominio: reglas de postura, fatiga, calidad de lectura y estados.
- Aplicacion: servicios de monitoreo, perfil biometrico, pausas activas y reportes.
- Infraestructura: camara, MediaPipe, PyQt6, voz, almacenamiento local y exportacion PDF.

El sistema usa:

- MediaPipe para puntos faciales y corporales.
- Calibracion biometrica para adaptar EAR, MAR y postura base.
- Rachas temporales para evitar alertas por un frame aislado.
- Histeresis para evitar parpadeos de estado.
- Reportes PDF locales para jornada e historial global.

## 8. Orden sugerido para grabar

1. Abrir la app.
2. Mostrar perfil.
3. Mostrar estado normal.
4. Probar mala postura sostenida.
5. Probar mirar al teclado.
6. Probar cabeceo real.
7. Probar bostezo.
8. Probar ausencia y reingreso.
9. Exportar reporte.
10. Mostrar PDF de jornada.
11. Mostrar carpeta con PDF global.
12. Cerrar con resumen de beneficios.

## 9. Cierre sugerido para el video

> SafeWork AI permite monitorear ergonomia y fatiga en tiempo real, reducir falsos positivos mediante validacion temporal, registrar eventos locales y exportar reportes PDF para seguimiento diario y global. El objetivo es apoyar la prevencion ergonomica en entornos de oficina sin hardware especializado.

