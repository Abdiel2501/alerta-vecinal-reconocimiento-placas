# Guía para Reducir y Limpiar el Tamaño del Repositorio (Evitar los 40 GB de historial)

El repositorio en la nube contiene un historial con archivos grandes antiguos (videos, pesos de modelos, zips) que pesan varios Gigabytes. Si intentas hacer un clone o pull clásico, Git intentará descargar todo ese historial antiguo, lo cual tardará horas y puede dar errores de desconexión.

Sigue estos pasos en tu máquina local para descargar únicamente el código más nuevo de hoy (sin el historial de 40 GB de basura):

---

## Opción 1: Si vas a clonar el proyecto desde cero (Recomendado y más rápido)
Usa un **Clonado Superficial (Shallow Clone)**. Esto le indica a Git que solo descargue la última versión de los archivos de hoy, ignorando por completo todo el historial pesado de commits antiguos:

```bash
# Clonar solo el último commit (peso de descarga de pocos Megabytes en lugar de Gigabytes)
git clone --depth 1 https://github.com/Abdiel2501/alerta-vecinal-reconocimiento-placas.git
```

---

## Opción 2: Si ya tienes el repositorio clonado y quieres reducir su tamaño

### Paso 1: Limpiar los archivos bloqueadores (Locks)
Si alguna descarga anterior se interrumpió y te da error, elimina los archivos temporales de bloqueo:
* **En Windows (PowerShell)**:
  ```powershell
  Remove-Item -Force -ErrorAction SilentlyContinue .git/shallow.lock, .git/index.lock, .git/config.lock
  ```
* **En Linux / Mac**:
  ```bash
  rm -f .git/shallow.lock .git/index.lock .git/config.lock
  ```

### Paso 2: Convertir tu repositorio local en superficial (Shallow)
Para recortar el historial localmente y descargar solo lo más nuevo de hoy:
```bash
# Descargar solo el último commit de la rama principal
git fetch --depth 1 origin main

# Forzar a tu rama local a sincronizarse exactamente con el servidor
git reset --hard origin/main
```

### Paso 3: Ejecutar el Recolector de Basura de Git
Para purgar de tu disco duro todos los archivos pesados que se quedaron sueltos de descargas anteriores:
```bash
# Purgar y optimizar la base de datos local de Git
git gc --prune=now --aggressive
```
Esto encogerá tu carpeta `.git` local a su tamaño mínimo absoluto.
