document.addEventListener('DOMContentLoaded', () => {
    // Confirmación de cancelación de compra
    const botonesCancelar = document.querySelectorAll('.profile-cancel-button');
    botonesCancelar.forEach(boton => {
        boton.addEventListener('click', (e) => {
            const confirmado = confirm('¿Estás seguro de que querés cancelar esta compra?');
            if (!confirmado) {
                e.preventDefault();
            }
        });
    });

    // Modal de edición de perfil
    const modal = document.getElementById('modal-editar-perfil');
    const btnAbrir = document.getElementById('btn-abrir-modal-editar');
    const btnCerrar = document.getElementById('btn-cerrar-modal-editar');
    const inputNombre = document.getElementById('edit_nombre');
    const inputApellido = document.getElementById('edit_apellido');
    const formEditar = modal ? modal.querySelector('form') : null;

    if (btnAbrir && modal) {
        btnAbrir.addEventListener('click', () => {
            if (formEditar) formEditar.reset();
            if (inputNombre) inputNombre.required = false;
            if (inputApellido) inputApellido.required = false;
            modal.style.display = 'flex';
        });
    }

    if (btnCerrar && modal) {
        btnCerrar.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Validación dependiente entre Nombre y Apellido
    const actualizarRequeridos = () => {
        const hayNombre = inputNombre && inputNombre.value.trim().length > 0;
        const hayApellido = inputApellido && inputApellido.value.trim().length > 0;

        if (hayNombre || hayApellido) {
            inputNombre.required = true;
            inputApellido.required = true;
        } else {
            inputNombre.required = false;
            inputApellido.required = false;
        }
    };

    if (inputNombre && inputApellido) {
        inputNombre.addEventListener('input', actualizarRequeridos);
        inputApellido.addEventListener('input', actualizarRequeridos);
    }
});