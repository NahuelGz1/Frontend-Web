// main.js - funcionalidades globales para cine paradiso

document.addEventListener('DOMContentLoaded', () => {
    // cierre de mensajes flash de flask
    const alertButtons = document.querySelectorAll('.alert-close, [data-dismiss="alert"]');
    alertButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const alertBox = e.target.closest('.alert');
            if (alertBox) {
                alertBox.style.transition = 'opacity 0.3s ease';
                alertBox.style.opacity = '0';
                setTimeout(() => alertBox.remove(), 300);
            }
        });
    });

    // menu hamburguesa para vista responsive (si existe el boton)
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            navToggle.setAttribute('aria-expanded', navMenu.classList.contains('active'));
        });
    }
});