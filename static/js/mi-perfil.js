document.addEventListener('DOMContentLoaded', () => {
    const botonesCancelar = document.querySelectorAll('.profile-cancel-button');
    botonesCancelar.forEach(boton => {
        boton.addEventListener('click', (e) => {
            const confirmado = confirm('¿Estás seguro de que querés cancelar esta compra?');
            if (!confirmado) {
                e.preventDefault();
            }
        });
    });
});