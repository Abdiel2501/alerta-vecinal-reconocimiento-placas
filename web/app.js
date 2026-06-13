document.addEventListener('DOMContentLoaded', () => {
    const connectBtn = document.getElementById('connectBtn');
    const toast = document.getElementById('toast');

    // El enlace directo al bot de Telegram que creamos
    const BOT_USERNAME = 'alerta_vecinaltelegram_bot';
    const TELEGRAM_URL = `https://t.me/${BOT_USERNAME}?start=auth`;

    connectBtn.addEventListener('click', () => {
        // Pequeña animación del botón
        connectBtn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            connectBtn.style.transform = '';
        }, 150);

        // Mostrar notificación tipo Toast
        toast.classList.remove('hidden');
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        // Ocultar Toast después de 5 segundos
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 400); // esperar que termine la transición CSS
        }, 5000);

        // Abrir la aplicación de Telegram (móvil o PC)
        window.open(TELEGRAM_URL, '_blank');
    });
});
