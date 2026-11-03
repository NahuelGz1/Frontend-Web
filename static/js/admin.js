// admin.js - interacciones visuales para las 5 pantallas del panel de administracion (peliculas, funciones, servicios, estadisticas, validar-qr)

document.addEventListener('DOMContentLoaded', () => {

    // confirmacion previa al enviar un formulario de eliminacion
    const deleteForms = document.querySelectorAll('form[data-confirm-delete]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const mensaje = form.dataset.confirmDelete || '¿Estás seguro de que deseas eliminar este registro?';
            if (!confirm(mensaje)) {
                e.preventDefault();
            }
        });
    });

    // previsualizacion inmediata de imagenes subidas (ej. afiches o banners)
    const imageInputs = document.querySelectorAll('input[type="file"][data-preview-target]');
    imageInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            const targetId = input.dataset.previewTarget;
            const previewElem = document.getElementById(targetId);

            if (file && previewElem) {
                const reader = new FileReader();
                reader.onload = (evt) => {
                    previewElem.src = evt.target.result;
                    previewElem.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // foco automatico en el campo de la pantalla validar qr para escanear
    const formValidarQR = document.getElementById('form-validar-qr');
    if (formValidarQR) {
        const inputQR = formValidarQR.querySelector('input[name="codigo_qr"]');
        if (inputQR) {
            inputQR.focus();
        }
    }
});