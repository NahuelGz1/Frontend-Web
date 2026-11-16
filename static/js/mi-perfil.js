document.addEventListener('DOMContentLoaded', () => {
    const modal = document.querySelector('[data-profile-modal]');
    if (!modal) return;

    const form = modal.querySelector('form');
    const inputNombre = modal.querySelector('#perfil-nombre');
    const inputApellido = modal.querySelector('#perfil-apellido');
    const inputEmail = modal.querySelector('#perfil-email');
    const errorBox = modal.querySelector('[data-profile-modal-error]');

    const mostrarError = (mensaje) => {
        if (!errorBox) return;
        errorBox.textContent = mensaje;
        errorBox.style.display = 'flex';
    };

    const limpiarError = () => {
        if (!errorBox) return;
        errorBox.textContent = '';
        errorBox.style.display = 'none';
    };

    const abrir = (e) => {
        if (e) e.preventDefault();
        limpiarError();
        form?.reset();
        modal.hidden = false;
        document.body.classList.add('modal-open');
        inputNombre?.focus();
    };

    const cerrar = (e) => {
        if (e) e.preventDefault();
        modal.hidden = true;
        document.body.classList.remove('modal-open');
        limpiarError();
        if (window.location.hash === '#editar-perfil') {
            history.replaceState(null, '', window.location.pathname + window.location.search);
        }
    };

    document.querySelector('[data-open-profile-modal]')?.addEventListener('click', abrir);
    modal.querySelectorAll('[data-close-profile-modal]').forEach((elemento) => {
        elemento.addEventListener('click', cerrar);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.hidden) cerrar();
    });

    form?.addEventListener('submit', (e) => {
        limpiarError();
        const nombre = inputNombre.value.trim();
        const apellido = inputApellido.value.trim();
        const email = inputEmail.value.trim();

        if (!nombre && !apellido && !email) {
            e.preventDefault();
            mostrarError('Completá al menos el correo electrónico o tu nombre y apellido.');
            return;
        }

        if ((nombre && !apellido) || (!nombre && apellido)) {
            e.preventDefault();
            mostrarError('Para actualizar tu nombre, tenés que completar tanto el nombre como el apellido.');
            (nombre ? inputApellido : inputNombre).focus();
            return;
        }

        if (email && !inputEmail.checkValidity()) {
            e.preventDefault();
            mostrarError('Ingresá un correo electrónico válido.');
            inputEmail.focus();
        }
    });

    if (window.location.hash === '#editar-perfil') abrir();
});