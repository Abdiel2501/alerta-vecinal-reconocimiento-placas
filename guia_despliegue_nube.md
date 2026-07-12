# Guía de Despliegue en la Nube (Frontend PWA e IA V14 Server GPU T4)

Esta guía explica paso a paso cómo subir todo el ecosistema de **AlertaVecinal** a la nube para garantizar un funcionamiento continuo (24/7), a alta velocidad (60 FPS gracias a aceleración GPU) y sin consumir batería ni procesador del dispositivo del usuario.

---

## PARTE 1: Desplegar la Aplicación Web (PWA Frontend)

Para que tu interfaz móvil (PWA) esté siempre en línea de forma gratuita, sigue una de estas dos opciones:

### Opción A: Activar GitHub Pages (Recomendado por su simplicidad)
1. Entra a tu repositorio en GitHub: `https://github.com/Abdiel2501/alerta-vecinal-reconocimiento-placas`
2. Ve a **Settings** (Configuración) > **Pages** (en el menú de la izquierda).
3. En la sección **Build and deployment**:
   * **Source**: Selecciona `Deploy from a branch`.
   * **Branch**: Selecciona `main` y la carpeta `/ (root)`.
   * Haz clic en **Save** (Guardar).
4. Espera 1 o 2 minutos. GitHub generará tu URL:
   ```text
   https://abdiel2501.github.io/alerta-vecinal-reconocimiento-placas/web_pwa/
   ```

### Opción B: Desplegar en Vercel (Para URL limpia)
1. Regístrate en [vercel.com](https://vercel.com/) vinculando tu cuenta de **GitHub**.
2. Haz clic en **Add New** > **Project** e importa `alerta-vecinal-reconocimiento-placas`.
3. En **Project Settings**:
   * Cambia el **Root Directory** a `web_pwa`.
4. Haz clic en **Deploy**. Obtendrás una URL única como `https://tu-proyecto.vercel.app`.

---

## PARTE 2: Desplegar la IA V14 Server (`servidor_ia_v14.py` en GPU T4)

Para procesar el flujo de video a 60 FPS y ejecutar YOLOv11 + PaddleOCR con aceleración por hardware, debes desplegar el servidor en una máquina virtual de la nube con soporte GPU (NVIDIA T4 es la opción con mejor relación costo/beneficio).

### 1. Proveedores Recomendados de GPU
* **Económicos e Instantáneos (Recomendado)**: [RunPod.io](https://www.runpod.io/) o [Vast.ai](https://vast.ai/). Ofrecen instancias preconfiguradas con drivers NVIDIA y PyTorch desde $0.20 USD la hora.
* **Corporativos**: Google Cloud Platform (GCP - VM N1 con GPU T4) o AWS (instancia `g4dn.xlarge`).

---

### 2. Preparar el Entorno en el Servidor (Ubuntu 22.04 LTS / Debian)

Una vez creada tu instancia GPU con Ubuntu, conéctate por SSH y ejecuta los siguientes comandos:

#### Paso 2.1: Actualizar el sistema e instalar dependencias del sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-dev git ffmpeg libsm6 libxext6 libgl1-mesa-glx
```

#### Paso 2.2: Instalar Drivers de CUDA (si usas una instancia limpia de AWS/GCP)
*(Si usas RunPod o Vast.ai, este paso ya viene listo de fábrica).*
```bash
# Verificar que el driver de NVIDIA esté operativo
nvidia-smi
```

#### Paso 2.3: Instalar dependencias de Python optimizadas para GPU
Para aprovechar la GPU T4 al máximo, debes instalar la versión correspondiente de **PyTorch con soporte CUDA** y **PaddlePaddle GPU**:

```bash
# 1. Instalar PyTorch compatible con CUDA 12.1 o superior
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 2. Instalar PaddlePaddle con soporte GPU (Esencial para la velocidad de PaddleOCR)
pip3 install paddlepaddle-gpu -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. Instalar las demás librerías de IA y Servidor
pip3 install ultralytics fastapi uvicorn websockets opencv-python pillow requests zeroconf
```

---

### 3. Configurar Credenciales y Base de Datos

1. Sube tu carpeta del proyecto al servidor.
2. Crea el archivo `config.env` en la raíz del proyecto en el servidor:
   ```env
   TELEGRAM_TOKEN=tu_token_de_telegram_aqui
   TELEGRAM_CHAT_ID=tu_chat_id_de_telegram_aqui
   GEMINI_API_KEY=tu_api_key_de_gemini_aqui
   ```
3. Inicializa tu base de datos SQLite de placas en el directorio correspondiente:
   * En Linux, el servidor buscará la base de datos en: `~/.local/share/AlertaVecinal/System/secure_placas.db`. Asegúrate de crear el directorio y copiar tu archivo de base de datos allí.

---

### 4. Conectar el Stream de tu Cámara Local (RTSP)

Para que la IA procese tu cámara local, necesitas enviarle el flujo de video RTSP:
* **Si tu cámara está en tu red local**: Puedes usar **Ngrok** para abrir un túnel TCP de tu puerto RTSP local (generalmente `554`) hacia el exterior, u ocupar una VPN ligera como **Tailscale** o **WireGuard** para conectar tu router/cámara local con la máquina virtual en la nube.
* En el servidor, inicia el script pasando la URL RTSP como parámetro:
  ```bash
  python3 servidor_ia_v14.py --video "rtsp://tu_usuario:tu_password@IP_TUNEL:PUERTO/stream1" --port 8765
  ```

---

### 5. Configurar el Firewall y Mantener el Proceso 24/7

#### Paso 5.1: Abrir puertos en el proveedor
Debes ingresar a la consola de red de tu proveedor de la nube (AWS/GCP/RunPod) y abrir el puerto de entrada:
* **Puerto TCP**: `8765` (WebSocket)

#### Paso 5.2: Correr el servidor en segundo plano permanentemente (con PM2)
Instala `PM2` para que el script se reinicie automáticamente si el servidor se apaga o hay un corte de conexión de la cámara:
```bash
# Instalar PM2 globalmente usando Node.js / NPM
sudo apt install -y nodejs npm
sudo npm install -g pm2

# Iniciar el servidor de la IA con PM2
pm2 start servidor_ia_v14.py --interpreter python3 -- --video "rtsp://..." --port 8765

# Guardar configuración para que se ejecute al reiniciar el sistema
pm2 save
pm2 startup
```

---

## PARTE 3: Conectar la App en Flutter / PWA con el Servidor en la Nube

1. Abre tu aplicación (PWA o Móvil) e ingresa a la sección de **Configuración**.
2. Cambia la URL del servidor IA por la IP pública de tu servidor en la nube:
   ```text
   ws://DIRECCION_IP_DEL_SERVIDOR:8765/ws
   ```
3. ¡Listo! La app comenzará a recibir el flujo de video procesado a 60 FPS directo de la GPU en la nube, y las alertas de Telegram llegarán de inmediato a tu canal de seguridad.
