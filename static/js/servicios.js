// servicios.js - logica del carrito de candy bar / servicios

document.addEventListener('DOMContentLoaded', () => {
    const contenedorServicios = document.getElementById('servicios-contenedor');
    if (!contenedorServicios) return;

    const totalGeneralElem = document.getElementById('total-servicios');
    const inputTotalOculto = document.getElementById('total_servicios_input');

    function actualizarTotales() {
        let totalGeneral = 0;
        const filasProductos = contenedorServicios.querySelectorAll('.servicio-card, .item-servicio');

        filasProductos.forEach(fila => {
            const btnRestar = fila.querySelector('.btn-restar');
            const inputCant = fila.querySelector('input[type="number"], .input-cantidad');
            const subtotalElem = fila.querySelector('.subtotal-item');
            const precioUnitario = parseFloat(fila.dataset.precio || 0);

            if (!inputCant) return;

            let cantidad = parseInt(inputCant.value || 0, 10);
            if (cantidad < 0) cantidad = 0;

            // deshabilita restar cuando la cantidad es cero
            if (btnRestar) btnRestar.disabled = cantidad === 0;

            const subtotal = cantidad * precioUnitario;
            totalGeneral += subtotal;

            if (subtotalElem) {
                subtotalElem.textContent = `$${subtotal.toLocaleString('es-AR')}`;
            }
        });

        if (totalGeneralElem) {
            totalGeneralElem.textContent = `$${totalGeneral.toLocaleString('es-AR')}`;
        }
        if (inputTotalOculto) {
            inputTotalOculto.value = totalGeneral;
        }
    }

    // delegacion de eventos para incrementar o decrementar
    contenedorServicios.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-sumar, .btn-restar');
        if (!btn) return;

        const contenedorControles = btn.closest('.controles-cantidad, .servicio-card, .item-servicio');
        const inputCant = contenedorControles.querySelector('input[type="number"], .input-cantidad');

        if (!inputCant) return;

        let val = parseInt(inputCant.value || 0, 10);
        if (btn.classList.contains('btn-sumar')) {
            val++;
        } else if (btn.classList.contains('btn-restar') && val > 0) {
            val--;
        }

        inputCant.value = val;
        actualizarTotales();
    });

    // escuchar entradas manuales si el campo es editable
    contenedorServicios.addEventListener('input', (e) => {
        if (e.target.matches('input[type="number"], .input-cantidad')) {
            actualizarTotales();
        }
    });

    actualizarTotales();
});