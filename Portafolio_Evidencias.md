# Reporte de Proyecto Unidad 2
**Proyecto:** Sistema Inteligente de Reconocimiento de Matrículas  
**Equipo:** Jorge Gabriel Heredia Lara, Abdiel Gerardo Alonso Herrera, Geovani Coronado Cruz  
**Materia:** Proyecto Integrador  
**Fecha:** 13 de Junio de 2026  

---

## 1. INTRODUCCIÓN
El robo de vehículos y la inseguridad vial representan problemáticas crecientes en las zonas urbanas. Ante este panorama, nuestro equipo ha decidido desarrollar una solución tecnológica: un Sistema Inteligente de Reconocimiento de Matrículas (ANPR) diseñado para operar en tiempo real. 

Hasta el día de hoy, hemos avanzado fuertemente en el desarrollo, implementando el modelo YOLOv8 para la detección de objetos y PaddleOCR para la lectura de caracteres, además de sentar las bases de la aplicación cliente en Flutter. Si bien contamos con avances operativos significativos y una infraestructura sólida, somos conscientes de que aún nos falta pulir diversos detalles y optimizar el sistema en nuestras próximas iteraciones. El presente portafolio documenta el proceso que tuvimos durante la unidad 2 para el proceso de la creacion de nuestro proyecto y los avances tangibles logrados hasta este momento.

---

## 2. DESARROLLO

### 2.1. Técnica aplicable para la generación de ruta o plan de acción
Para estructurar nuestras actividades y garantizar entregas o avances que motivaran al equipo, hicimos que cada cierto tiempo se presentaran avances, pues hablamos que es gratificante sentir que avanzamos rápidamente y eso nos motivaba. Por ello, hemos optado por un **Enfoque Híbrido** combinando metodologías **Gantt (Predictivo)** y **Kanban (Ágil)**.

**Justificación:**
Decidimos usar el diagrama de Gantt para organizar el trabajo con la Inteligencia Artificial (es decir, la parte donde le enseñamos al programa a reconocer las placas). Usamos esta técnica porque necesitábamos seguir pasos en orden y con tiempos fijos antes de poder conectar la Inteligencia Artificial con el resto del sistema. Por otro lado, elegimos usar tableros Kanban para la creación de la pantalla principal (la aplicación visual) y el sistema de envío de alertas. Kanban nos resultó más fácil de entender porque nos permitía hacer cambios rápidos, corregir errores sobre la marcha y ver visualmente en equipo qué tareas estaban pendientes, cuáles en proceso y cuáles ya estaban terminadas.

**Ejemplo Visual:**
A continuación, se muestra el estado de flujo de nuestras tareas en el tablero Kanban:

![TABLERO KANBAN DEL PROYECTO](tablero_kanban.png)

---

### 2.2. Objetivos, metas, alcances y limitaciones del proyecto

**Objetivos:**
*   **Propósito general:** Desarrollar y lanzar un sistema integral de reconocimiento automático de matrículas basado en visión artificial capaz de emitir notificaciones de seguridad en tiempo real.

**Metas (Resultados específicos y medibles):**
*   Alcanzar una precisión de lectura de los números y letras de las placas superior al 95% en los próximos 2 meses.
*   Lograr que el programa procese y analice el video muy rápido, tardando menos de 50 milisegundos en revisar cada imagen o cuadro del video.
*   Integrar con éxito el envío de alertas automáticas vía Telegram con un tiempo de entrega de menos de 3 segundos después de detectar una placa sospechosa.

**Alcance:**
*   **Entregables y fronteras:** El proyecto abarca todo el proceso de funcionamiento del sistema de forma local (es decir, corriendo en nuestras propias computadoras sin depender de internet para funcionar de forma general). Esto incluye el modelo de Inteligencia Artificial ya entrenado (`yolo11n.pt`), el servidor o cerebro detrás de la aplicación (`main.py` y `database.py`), y la aplicación visual (Flutter) para gestionar los registros.

**Limitaciones:**
*   **Restricciones:** El desempeño del sistema depende fuertemente de contar con una buena tarjeta de video (GPU) instalada en la computadora para poder procesar la cámara sin que se trabe. Asimismo, existen limitaciones climáticas (baja visibilidad por lluvia intensa o poca luz) que restringen la capacidad de visión de las cámaras instaladas.

---

### 2.3. Recursos necesarios para el proyecto

Para lograr nuestros avances actuales, hemos requerido e identificado los siguientes recursos:

| Tipo | Detalle |
| :--- | :--- |
| **Humanos** | Equipo multidisciplinario con habilidades en: Inteligencia Artificial (para entrenar los modelos visuales con Python), Manejo de Datos (para guardar las placas en una base de datos local SQLite), y Desarrollo de Interfaces (creación de pantallas y botones de la aplicación en Flutter). |
| **Materiales** | Computadoras de escritorio o laptops con tarjetas de video dedicadas NVIDIA, programas gratuitos para escribir código (Jupyter/VS Code), y miles de fotografías de placas mexicanas para entrenar a la Inteligencia Artificial. |
| **Financieros** | Presupuesto estimado en **$30,000 MXN** distribuidos en: Computadora principal para correr el sistema ($20,000 MXN), renta de servidores en internet para entrenar la inteligencia artificial más rápido ($3,000 MXN), un par de cámaras de vigilancia de buena calidad ($6,000 MXN) y saldo para el sistema de envío de mensajes ($1,000 MXN). |

---

### 2.4. Interesados/usuarios del proyecto

*   **Operadores de Seguridad Privada (Usuarios finales):** Necesitan una pantalla de control clara, fácil de usar y que mande alertas inmediatas. Esperan que el programa no se congele ni falle durante los turnos continuos de vigilancia.
*   **Propietarios de Vehículos / Residentes:** Requieren recibir alertas de seguridad precisas y confiables en sus celulares cuando su automóvil entra o sale de las instalaciones.
*   **Equipo de Desarrollo (Nosotros):** Requerimos computadoras bien configuradas, apuntes ordenados sobre los errores que vayan saliendo y buena comunicación para seguir mejorando el código sin descomponer lo que ya funciona.

---

### 2.5. Responsables en cada etapa del proyecto

Hemos asignado responsabilidades y roles claros dentro del equipo para el avance en cada fase:

| Fase | Roles Asignados y Tareas Específicas |
| :--- | :--- |
| **Iniciación** | **Encargado de Inteligencia Artificial:** Recopilación, recorte de imágenes, y organización de las miles de fotografías de placas vehiculares. |
| **Ejecución (Cerebro del Sistema e IA)** | **Programador Backend / Encargado de IA:** Enseñanza y ajustes del modelo visual YOLO, creación de la base de datos para guardar la información, y escritura del código principal que une todo (`main.py`). |
| **Ejecución (Pantallas de la App)** | **Programador Frontend:** Diseño y creación de las pantallas visuales de la aplicación que usarán los guardias de seguridad. |
| **Cierre y Revisión de Calidad** | **Revisor de Pruebas:** Hacer pruebas para ver cuánto tarda el programa en detectar placas, mandar muchos mensajes de prueba por Telegram para verificar que no falle, y revisar que todo el proyecto corra de forma fluida. |

---

### 2.6. Trabajos prioritarios por realizar

Para determinar qué tareas debíamos hacer primero y cuáles podíamos dejar para después, utilizamos la técnica de priorización **MoSCoW**. Si bien hemos abarcado las tareas más urgentes (lo que es obligatorio para que funcione), esta tabla guía nuestros esfuerzos para seguir puliendo el programa:

**Ejemplo Visual:**
![PRIORIZACIÓN DE TRABAJOS (Técnica MoSCoW)](priorizacion_moscow.png)

---

### 2.7. Duración de las tareas y/o actividades del proyecto

Hemos detallado un calendario de trabajo para asegurar que la parte visual y la inteligencia artificial se conecten a tiempo sin retrasar el proyecto:

*   **Inicio:** Identificar qué necesitábamos hacer y cómo íbamos a guardar la información (5 días).
*   **Desarrollo en Orden:** Enseñanza y ajustes de la Inteligencia Artificial (7 días), seguido de la conexión a la base de datos (5 días).
    *   **Primer Avance Importante:** El "cerebro" del sistema detecta placas y guarda la información sin errores.
*   **Desarrollo al Mismo Tiempo:** Creación de las pantallas visuales de la app (10 días) y conexión con los mensajes de Telegram (3 días).
    *   **Segundo Avance Importante:** La aplicación ya se puede usar visualmente.
*   **Cierre:** Hacer muchas pruebas forzando el sistema a equivocarse (4 días) seguidas de corrección de esos últimos errores (3 días).
    *   **Tercer Avance Importante:** Entrega Final del proyecto.

**Ejemplo Visual:**
![CRONOGRAMA DE ACTIVIDADES (Diagrama de Gantt)](cronograma_gantt.png)

---

## 3. CONCLUSIONES

A lo largo de este periodo de planificación y trabajo continuo, hemos corroborado que construir un sistema con Inteligencia Artificial exige mucha organización. Combinar dos formas de trabajo fue un acierto: nos ayudó a ser rigurosos con los tiempos al entrenar la Inteligencia Artificial (diagrama de Gantt), y al mismo tiempo nos permitió ser rápidos y adaptarnos fácilmente al construir las pantallas de la aplicación (tableros Kanban).

Hasta el día de hoy, hemos avanzado fuertemente asegurando las funciones obligatorias del proyecto, logrando que el sistema ya detecte placas de video y envíe notificaciones. Sin embargo, este proceso nos dejó como lección que programar siempre requiere ensayo y error; hacer que todo el programa funcione a la perfección y rápido en situaciones de la vida real toma más tiempo del que imaginamos al inicio. A futuro, nuestro esfuerzo en equipo se concentrará en pulir todos esos pequeños detalles técnicos para entregar un sistema altamente eficiente, rápido y fácil de usar.
