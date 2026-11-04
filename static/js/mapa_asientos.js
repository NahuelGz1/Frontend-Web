// mapa_asientos.js - logica interactiva del plano de butacas

document.addEventListener('DOMContentLoaded', () => {
    const mapaContainer = document.getElementById('mapa-butacas');
    if (!mapaContainer) return;

    const checkboxes = mapaContainer.querySelectorAll('input[type="checkbox"][name="butacas"]');
    const contadorSeleccionadas = document.getElementById('cant-butacas');
    const totalPrecioElem = document.getElementById('total-precio-butacas');
    const btnContinuar = document.getElementById('btn-continuar-pago');

    function actualizarResumen() {
        const seleccionadas = Array.from(checkboxes).filter(cb => cb.checked);
        const cantidad = seleccionadas.length;

        if (contadorSeleccionadas) {
            contadorSeleccionadas.textContent = cantidad;
        }

        // calcula el total parcial dinamico
        if (totalPrecioElem) {
            const total = seleccionadas.reduce((acc, cb) => {
                const precio = parseFloat(cb.dataset.precio || 0);
                return acc + precio;
            }, 0);
            totalPrecioElem.textContent = `$${total.toLocaleString('es-AR')}`;
        }

        // bloquea el avance si no hay butacas elegidas
        if (btnContinuar) {
            btnContinuar.disabled = cantidad === 0;
        }
    }

    checkboxes.forEach(cb => {
        cb.addEventListener('change', actualizarResumen);
    });

    actualizarResumen();
});