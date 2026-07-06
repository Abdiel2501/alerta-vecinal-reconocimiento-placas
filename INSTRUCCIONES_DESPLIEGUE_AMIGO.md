# Guía Rápida para el Despliegue de la IA V13 en Google Cloud (GCP)

Hola. Esta guía contiene los pasos exactos y comandos necesarios para levantar el servidor de Inteligencia Artificial Multiusuario (`servidor_ia_v13.py`) en una máquina virtual de Google Cloud con una GPU T4.

---

## PASO 1: Crear la Instancia de VM en GCP
Entra a la consola de Google Cloud, ve a **Compute Engine** > **Instancias de VM** > **Crear Instancia**, y configura exactamente estos campos:

1. **Configuración de la Máquina**:
   * **Serie**: `N1` (las GPUs T4 solo están disponibles en la serie N1).
   * **Tipo de máquina**: Selecciona **`n1-standard-4`** (4 vCPUs, 15 GB RAM) o **`n1-standard-2`** (7.5 GB RAM) para evitar que la máquina se quede sin memoria.
2. **GPU (Tarjeta de Video)**:
   * Haz clic en la pestaña **GPU** (al lado de *De uso general*).
   * Haz clic en **Añadir GPU**.
   * **Tipo de GPU**: Selecciona **NVIDIA Tesla T4** (Cantidad: 1).
   * *(Nota: Si te da un error de cuota `GPUS-ALL-REGIONS`, cambia la **Región** del servidor a `us-east1` (Carolina del Sur) o `us-west1` (Oregón) y reintenta).*
3. **SO y Almacenamiento (Disco de arranque)**:
   * Haz clic en **Cambiar** (debajo de *Disco de arranque*).
   * **Sistema operativo**: **Ubuntu**.
   * **Versión**: **Ubuntu 22.04 LTS**.
   * **Tamaño del disco**: Escribe **`50` GB**.
   * Haz clic en **Seleccionar**.
4. **Firewall**:
   * Marca las casillas **Permitir tráfico HTTP** y **Permitir tráfico HTTPS**.
5. Haz clic en **Crear**.

---

## PASO 2: Abrir el puerto del WebSocket (8765)
Para que la app de Flutter se conecte a la IA:
1. Ve a **Red de VPC** > **Cortafuegos** (Firewall) en la consola de GCP.
2. Haz clic en **Crear regla de cortafuegos**.
3. Configúrala así:
   * **Nombre**: `permitir-websocket-ia`
   * **Intervalos de IP de origen**: `0.0.0.0/0`
   * **Protocolos y puertos**: Selecciona **Protocolos y puertos especificados**, marca **TCP** y escribe **`8765`**.
4. Haz clic en **Crear**.

---

## PASO 3: Ejecutar en el Servidor (Consola SSH)
Cuando la máquina esté lista, haz clic en el botón **SSH** en tu lista de instancias para abrir la terminal, y ejecuta línea por línea:

### 1. Actualizar el sistema e instalar drivers de NVIDIA
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers install
sudo reboot
```
*Espera 1 minuto, vuelve a conectarte por SSH y verifica la tarjeta con:*
```bash
nvidia-smi
```

### 2. Instalar dependencias y descargar el repositorio (Shallow Clone)
```bash
# Dependencias del sistema
sudo apt install -y python3-pip python3-dev git ffmpeg libsm6 libxext6 libgl1-mesa-glx

# Clonar solo el último commit (evita descargar 40 GB de historial antiguo)
git clone --depth 1 https://github.com/Abdiel2501/alerta-vecinal-reconocimiento-placas.git
cd alerta-vecinal-reconocimiento-placas
```

### 3. Instalar librerías de Python (GPU)
```bash
# PyTorch con soporte CUDA
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# PaddlePaddle con soporte GPU (esencial para PaddleOCR a 60 FPS)
pip3 install paddlepaddle-gpu -i https://pypi.tuna.tsinghua.edu.cn/simple

# Dependencias de FastAPI y YOLO
pip3 install ultralytics fastapi uvicorn websockets opencv-python pillow requests
```

### 4. Configurar llaves en `config.env`
Crea el archivo en la raíz del proyecto:
```bash
nano config.env
```
Pega tus datos privados y guarda (`Ctrl + O`, `Enter`, `Ctrl + X`):
```env
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
GEMINI_API_KEY=tu_api_key_de_gemini
```

---

## PASO 4: Iniciar el Servidor de IA V13
Ejecuta el servidor en el puerto expuesto:
```bash
python3 servidor_ia_v13.py --port 8765
```

En la app de Flutter, conéctense a la IP pública de la máquina de GCP usando:
```text
ws://IP_PUBLICA_GCP:8765/ws/{token}
```
*(Nota: Para iniciar sesión en la app, primero llamen a los endpoints `/api/register` y `/api/login` del servidor).*
