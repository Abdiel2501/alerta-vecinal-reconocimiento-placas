# Guía de Despliegue en la Nube (Gratis y 24/7)

Para que tu PWA esté siempre en línea sin necesidad de correr un servidor local en tu PC, puedes usar servicios de la nube gratuitos. A continuación tienes las dos opciones más rápidas y recomendadas para este proyecto:

---

## Opción A: Activar GitHub Pages (¡Súper fácil!)
Dado que ya tienes tu repositorio subido a GitHub, puedes usar la función integrada de GitHub Pages.

1. Entra a tu repositorio en GitHub desde el navegador: `https://github.com/Abdiel2501/yolo-plate-recognition`
2. Ve a la pestaña **Settings** (Configuración) en la barra superior del repositorio.
3. En el menú de la izquierda, haz clic en **Pages**.
4. En la sección **Build and deployment**:
   * Bajo **Source**, asegúrate de que esté seleccionado `Deploy from a branch`.
   * Bajo **Branch**, selecciona tu rama principal `main` (o la que utilices) y la carpeta `/ (root)`.
   * Haz clic en **Save** (Guardar).
5. ¡Listo! Espera alrededor de 1 a 2 minutos. GitHub generará un enlace permanente arriba en esa misma página.
6. **Tu enlace permanente será:**
   ```text
   https://abdiel2501.github.io/yolo-plate-recognition/web_pwa/
   ```

*(Nota: Al acceder a esa URL, recuerda incluir `/web_pwa/` al final del enlace para que cargue directamente la PWA en lugar de la raíz del proyecto).*

---

## Opción B: Desplegar en Vercel (Recomendado para una URL limpia)
Vercel te permite desplegar gratis y hacer que el enlace apunte directamente a la aplicación sin subcarpetas.

1. Ve a [vercel.com](https://vercel.com/) y regístrate o inicia sesión con tu cuenta de **GitHub**.
2. Haz clic en **Add New** > **Project**.
3. Importa tu repositorio `yolo-plate-recognition`.
4. En la configuración del proyecto (**Project Settings**):
   * Busca la opción **Root Directory**.
   * Haz clic en **Edit** y selecciona o escribe la carpeta `web_pwa`. Esto hará que el enlace cargue directamente tu aplicación web.
5. Haz clic en **Deploy**.
6. En un par de segundos, Vercel te dará una URL única y segura como:
   ```text
   https://tu-proyecto-de-placas.vercel.app
   ```

### Ventaja de la nube:
Cada vez que hagas un `git push` con nuevos cambios, tanto GitHub Pages como Vercel actualizarán la aplicación automáticamente sin que tengas que hacer nada más.
