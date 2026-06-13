# Planificación del Proyecto "YOLO Plate Recognition"

**Proyecto:** YOLO Plate Recognition (AlertaVecinal)  
**Autor:** Abdiel2501  
**Estado del Proyecto:** Prototipo Funcional Integrado  

---

## 1. Introducción y Contextualización del Proyecto

En los entornos urbanos y corporativos modernos, la seguridad y el control de accesos vehiculares representan una prioridad crítica. Los sistemas de registro manual por parte de guardias de seguridad son propensos a errores humanos, cuellos de botella en horas pico y registros deficientes o manipulables. Ante esta problemática, la visión artificial y el aprendizaje profundo ofrecen soluciones eficientes y automatizadas. El proyecto **"YOLO Plate Recognition"** nace con el propósito de resolver estas ineficiencias mediante el diseño, desarrollo e implementación de un sistema automatizado de Reconocimiento Óptico de Caracteres (OCR) especializado en matrículas vehiculares.

El núcleo del sistema combina algoritmos avanzados de visión computacional mediante el uso del framework YOLOv8 (You Only Look Once) optimizado para la detección de la ubicación exacta de las placas, seguido de un motor de OCR que extrae el texto de la matrícula incluso bajo condiciones desafiantes de iluminación y ángulo. Para dotar al sistema de una operabilidad profesional y oportuna, se integra una base de datos relacional SQLite localmente encriptada y un sistema automático de notificaciones mediante bots de mensajería instantánea (Telegram y WhatsApp) que alertan sobre vehículos sospechosos en menos de 3 segundos. Adicionalmente, el proyecto incluye una aplicación móvil interactiva desarrollada en Flutter que permite a los administradores del sistema gestionar permisos, supervisar accesos en tiempo real, visualizar gráficos analíticos y recibir notificaciones push en dispositivos móviles y de escritorio.

---

## 2. Técnica Aplicada para la Planificación del Proyecto (Enfoque Híbrido)

La correcta gestión de proyectos que involucran investigación en Inteligencia Artificial y el desarrollo de software multiplataforma exige un marco ágil que garantice adaptabilidad sin perder de vista los plazos clave. Para este proyecto, se ha seleccionado un enfoque híbrido: la estructura temporal global se rige por un cronograma de hitos críticos, mientras que la ejecución técnica diaria y la distribución de tareas se gestionan bajo la metodología ágil Kanban.

### Justificación del uso de Kanban:
* **Visibilidad Absoluta del Flujo de Trabajo:** Dado que el proyecto se compone de múltiples módulos independientes pero interconectados (el backend en Python, la base de datos, los bots de mensajería y la aplicación móvil Flutter), Kanban permite rastrear exactamente en qué etapa de desarrollo se encuentra cada script u objeto técnico.
* **Control del Trabajo en Progreso (WIP):** Limitar el trabajo simultáneo a un máximo de 3 tareas por desarrollador previene la sobrecarga mental, minimiza el cambio de contexto y asegura que las tareas iniciadas se terminen y prueben exhaustivamente antes de comenzar otras.
* **Mitigación de Bloqueos (Bottlenecks):** Si un módulo de IA (por ejemplo, el OCR) experimenta problemas de precisión, se visualiza inmediatamente como una columna saturada o bloqueada en el tablero, permitiendo al equipo reasignar esfuerzos para resolver el cuello de botella rápidamente.

### Tablero Kanban del Proyecto (Ejemplo Visual)

| Por Hacer (Backlog) | En Proceso (WIP: 3) | En Pruebas / QA | Completado (Done) |
| :--- | :--- | :--- | :--- |
| - Desarrollar vista de streaming en la App Flutter.<br>- Implementar gráficos de estadísticas en panel de control.<br>- Integración con base de datos en la nube para redundancia. | - Refinar modelo de detección YOLOv8 para placas inclinadas.<br>- Configurar servicios de notificaciones locales en Flutter.<br>- Depuración de base de datos encriptada. | - Testear latencia en envío de fotos del bot de Telegram.<br>- Validar algoritmos de encriptación AES en base de datos local SQLite. | - Crear servidor HTTP para la IA.<br>- Implementar pantalla de Login y Registro en Flutter.<br>- Configurar exclusiones de archivos de sistema en `.gitignore`. |

---

## 3. Objetivos, Metas, Alcance y Limitaciones del Proyecto

### Objetivos:

* **Objetivo General:**
  Diseñar, implementar y evaluar un sistema integral de reconocimiento de matrículas vehiculares automatizado mediante visión por computadora e inteligencia artificial, conectado a una base de datos segura y encriptada, con capacidad de notificar alertas de seguridad de forma instantánea y administrable a través de una aplicación móvil multiplataforma.

* **Objetivos Específicos:**
  1. Desarrollar un backend de visión artificial en Python usando YOLOv8 capaz de aislar placas y procesar su contenido alfanumérico.
  2. Implementar una base de datos local basada en SQLite protegida por encriptación avanzada AES para salvaguardar la privacidad de las matrículas registradas.
  3. Programar e integrar sistemas automáticos de envío de alertas instantáneas de seguridad mediante el desarrollo de bots interactivos de Telegram y WhatsApp.
  4. Construir una interfaz de usuario móvil responsiva y moderna con Flutter que permita la consulta de registros, estadísticas y configuraciones del servidor de IA.

### Metas (Métricas de Éxito):
* **Precisión de Reconocimiento:** Lograr un porcentaje de aciertos igual o superior al 95% en la detección e interpretación de caracteres de placas en condiciones óptimas e iluminación artificial estándar.
* **Latencia de Alertas:** Asegurar que el tiempo transcurrido entre la detección física de un vehículo no autorizado por la cámara y el arribo de la notificación (con foto del vehículo) al bot de Telegram sea inferior a 3.0 segundos.
* **Rendimiento de la Aplicación Móvil:** Garantizar tiempos de carga inicial inferiores a 1.5 segundos en la visualización de registros históricos almacenados localmente.

### Alcance (Fronteras y Entregables):
El proyecto abarca el desarrollo del software de IA y la aplicación móvil cliente. Los entregables clave incluyen:
* **Servidor de IA Local (Backend):** Pipeline de visión por computadora en Python que procesa transmisiones de video RTSP de cámaras, aislando placas y aplicando OCR.
* **Módulo de Base de Datos Encriptada:** Base de datos local segura con cifrado a nivel de registro para cumplir con regulaciones de protección de datos personales.
* **App de Administración (Flutter):** Aplicación instalable para Android, Windows y Web que proporciona el panel de control central del sistema, permitiendo configurar listas blancas/negras.
* **Bots de Telegram y WhatsApp:** Canales automatizados de comunicación en dos vías para control remoto y entrega de alertas con soporte multimedia.

### Limitaciones y Restricciones:
* **Limitación de Procesamiento Local:** El procesamiento del modelo YOLOv8 depende directamente de los recursos del hardware disponible. Si se utiliza un servidor sin GPU dedicada, los fotogramas por segundo (FPS) analizados se verán reducidos.
* **Calidad y Ángulo de la Imagen:** Cámaras con resoluciones inferiores a 720p o instaladas a ángulos superiores a 45 grados respecto al eje del vehículo pueden deteriorar severamente el desempeño de la detección y lectura.
* **Restricciones de Proveedores de Mensajería:** El bot de WhatsApp depende de la política de uso y cuotas de APIs de terceros (como Twilio o Meta APIs), lo que limita la gratuidad del envío masivo de imágenes de alerta.

---

## 4. Recursos Necesarios para la Implementación del Proyecto

| Categoría | Recurso Requerido | Descripción / Especificación Técnica | Costo / Disponibilidad |
| :--- | :--- | :--- | :--- |
| **Recursos Humanos** | - Desarrollador Python e IA<br>- Desarrollador Flutter<br>- Ingeniero de QA y Despliegue | 1 Programador encargado del modelo YOLOv8 y lógica backend.<br>1 Programador para la UI y servicios de Flutter.<br>1 Integrador encargado del testing de seguridad. | Interno (Disponibilidad completa para el ciclo del proyecto) |
| **Recursos Tecnológicos (Software)** | - Python 3.10+<br>- SDK Flutter / Dart<br>- YOLOv8 (Ultralytics)<br>- SQLite3 y SQLCipher | Lenguajes de programación, framework multiplataforma, modelo preentrenado de visión artificial y motor de base de datos cifrada local. | Software Libre y de Código Abierto (Sin costo de licenciamiento) |
| **Recursos Materiales (Hardware)** | - Mini PC Servidor de IA<br>- Cámara IP Externa 1080p<br>- Computadora de desarrollo | Mini PC con procesador Intel i7 y aceleración de hardware para IA.<br>Cámara de seguridad con conectividad RTSP y LED infrarrojo para visión nocturna. | Inversión inicial estimada:<br>- Mini PC: $450 USD<br>- Cámara: $80 USD<br>- Accesorios: $15 USD<br>**Total: $545 USD** |

---

## 5. Interesados y Usuarios del Proyecto (Stakeholders)

El análisis de los interesados del proyecto garantiza que el desarrollo responda directamente a las necesidades reales de los usuarios operativos, técnicos y patrocinadores, mitigando la brecha de diseño.

| Interesado | Clasificación | Necesidades / Expectativas | Impacto / Rol en el Proyecto |
| :--- | :--- | :--- | :--- |
| **Vigilantes y Operadores de Seguridad** | Usuario Final Directo | Desean una interfaz simple y alertas instantáneas visuales cuando una placa no permitida ingrese al rango de la cámara. | Alto. Son quienes operan la app en el día a día y validan las alertas generadas. |
| **Comité de Administración Residencial/Corporativo** | Cliente y Patrocinador | Busca automatizar los registros de accesos, erradicar las bitácoras físicas de papel y contar con reportes de analítica sobre horas pico de vehículos. | Muy Alto. Financian el equipamiento de hardware y dictan los requerimientos de negocio. |
| **Equipo de Soporte de TI / Desarrolladores** | Usuario Técnico | Requiere código documentado, pruebas unitarias estandarizadas y control de versiones transparente en GitHub para aplicar actualizaciones y corregir bugs. | Medio. Aseguran la estabilidad técnica y el mantenimiento evolutivo del sistema. |

---

## 6. Responsabilidades en Cada Etapa del Proyecto

Para garantizar una ejecución sin retrasos y un control de calidad óptimo, las responsabilidades se distribuyen de acuerdo con las fases metodológicas del proyecto:

* **1. Etapa de Iniciación e Investigación (Semanas 1-2):**  
  El Analista y Diseñador UX-UI definen los requisitos de software del sistema, diseñan el esquema físico de la base de datos SQLite y desarrollan el mockup interactivo de la app en Flutter. Se realiza la configuración inicial de los repositorios en GitHub.
* **2. Etapa de Desarrollo Backend e IA (Semanas 3-4):**  
  El Programador Python & IA programa la lógica de detección de YOLOv8, ajusta los hiperparámetros de precisión y optimiza OpenCV. Integra la lógica de cifrado SQLCipher y desarrolla el servidor HTTP/RTSP local.
* **3. Etapa de Desarrollo de la Aplicación Cliente (Semana 4-5):**  
  El Programador Flutter construye las vistas de dashboard, el panel de cámaras y la lógica de login local/remota. Conecta la app con el backend local a través de servicios HTTP REST y WebSockets.
* **4. Etapa de Cierre, Integración y Pruebas (Semana 6):**  
  El Especialista en QA ejecuta pruebas unitarias, de rendimiento e integración de las alertas (mensajes automáticos en Telegram/WhatsApp). Se realiza el despliegue del ejecutable del servidor local y se entrega el manual de operación técnica.

---

## 7. Trabajos Prioritarios por Realizar (Técnica MoSCoW)

La técnica MoSCoW es una herramienta clave de priorización que ayuda al equipo a enfocarse en entregar valor en fases tempranas, asegurando el desarrollo de un Producto Mínimo Viable (MVP) funcional y pulido.

| Prioridad | Tareas / Funcionalidades Incluidas | Justificación Estratégica |
| :--- | :--- | :--- |
| **Must Have (Obligatorio)** | - Detección y localización exacta de placas.<br>- Cifrado AES en la base de datos de matrículas.<br>- Pantalla de login e historial de ingresos en la App. | Constituye el núcleo del sistema de seguridad. Sin precisión en la IA y protección de datos, el producto no es funcional ni legal. |
| **Should Have (Deseable)** | - Bot automatizado en Telegram para alertas con foto.<br>- Gestión y control de cámaras (alta/baja) desde la App móvil. | Mejora significativamente la experiencia del usuario operativo al recibir alertas multimedia de inmediato en sus móviles sin estar frente a una PC. |
| **Could Have (Opcional)** | - Alertas avanzadas a través de mensajes de WhatsApp.<br>- Reportes analíticos descargables (PDF/Excel) desde la app. | Son funcionalidades complementarias de alta conveniencia que añaden valor pero cuya ausencia no paraliza la operación del sistema. |
| **Won't Have (No en esta fase)** | - Reconocimiento facial del conductor del vehículo.<br>- Control domótico físico del portón vehicular. | Se excluyen de la planificación inicial para limitar el alcance técnico, controlar el presupuesto y evitar la desviación del objetivo principal. |

---

## 8. Duración de las Tareas y Actividades del Proyecto (Cronograma)

| ID | Fase / Actividad | Duración | Fecha Inicio | Fecha Fin | Hito Clave Relacionado |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F1** | Análisis e Ingeniería de Requisitos | 5 días | 01/Jun/2026 | 05/Jun/2026 | Especificación de Requisitos Aprobada |
| **F2** | Diseño de Base de Datos y Prototipos UX-UI | 5 días | 06/Jun/2026 | 10/Jun/2026 | Estructura de Base de Datos y Mockups Listos |
| **F3** | Desarrollo del Backend, Servidor IA e Integración de YOLOv8 | 8 días | 11/Jun/2026 | 18/Jun/2026 | **Hito 1: Prototipo IA Funcional** |
| **F4** | Desarrollo de la App Multiplataforma en Flutter | 10 días | 19/Jun/2026 | 28/Jun/2026 | **Hito 2: App Flutter Base Operativa** |
| **F5** | Integración de Sistemas de Alertas (Bots de Telegram/WhatsApp) | 4 días | 29/Jun/2026 | 02/Jul/2026 | Canales de Mensajería Vinculados |
| **F6** | Fase de Pruebas Integrales de Seguridad y QA | 4 días | 03/Jul/2026 | 06/Jul/2026 | Pruebas de Carga y Estrés Finalizadas |
| **F7** | Entrega del Sistema, Cierre y Documentación | 4 días | 07/Jul/2026 | 10/Jul/2026 | **Hito 3: Entrega de Proyecto a Producción** |

---

## 9. Conclusiones y Lecciones Aprendidas

La planificación metódica y estructurada es el pilar fundamental para mitigar la incertidumbre en el desarrollo de software de vanguardia. Tras el análisis detallado del proyecto "YOLO Plate Recognition", se extraen las siguientes conclusiones clave:

1. **Sinergia Metodológica:** El uso combinado de Kanban para el control diario de actividades y la técnica de priorización MoSCoW permite mantener al equipo altamente enfocado en entregar valor funcional continuo. Esta disciplina previene la dispersión del alcance y asegura que los esfuerzos se concentren en el núcleo de seguridad del sistema (Must Have).
2. **Mitigación del Riesgo Tecnológico:** Al planificar y documentar detalladamente las limitaciones y dependencias físicas del hardware, se evitan falsas expectativas en el cliente y se estructuran respuestas proactivas (como la recomendación de aceleración por GPU para evitar la caída en la tasa de FPS analizada).
3. **Importancia de la Seguridad desde el Diseño:** La integración de base de datos encriptada con SQLite y SQLCipher es una decisión de planificación estratégica. Resguarda los datos sensibles en cumplimiento con las regulaciones de privacidad actuales, transformando un simple proyecto técnico en un producto maduro, seguro y listo para la implantación residencial y comercial.

---

## 10. Anexos y Referencias Técnicas

### Enlaces de Referencia del Repositorio y Herramientas:
* **Repositorio Oficial de GitHub:** [https://github.com/Abdiel2501/yolo-plate-recognition](https://github.com/Abdiel2501/yolo-plate-recognition)
* **Documentación Oficial de YOLOv8 por Ultralytics:** [https://docs.ultralytics.com](https://docs.ultralytics.com)
* **Flutter SDK Documentation:** [https://docs.flutter.dev](https://docs.flutter.dev)
