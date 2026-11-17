// cartelera.js - logica para detalle de pelicula y seleccion de funciones

document.addEventListener('DOMContentLoaded', () => {
    const selectComplejo = document.getElementById('complejo');
    const selectFecha = document.getElementById('fecha');
    const chipsComplejo = document.querySelectorAll('.chip[data-complejo]');
    const funcionesCards = document.querySelectorAll('#funciones-contenedor .funcion-card');
    const sinFuncionesMsg = document.getElementById('sin-funciones-msg');

    if (!selectComplejo && !chipsComplejo.length) return;

    // actualiza la visibilidad de las funciones en base a los filtros
    function filtrarFunciones() {
        const complejoSel = selectComplejo ? selectComplejo.value : '';
        const fechaSel = selectFecha ? selectFecha.value : '';

        // sincronizar estado visual de los chips
        chipsComplejo.forEach(chip => {
            if (chip.dataset.complejo === complejoSel) {
                chip.classList.add('active');
            } else {
                chip.classList.remove('active');
            }
        });

        let visibles = 0;
        funcionesCards.forEach(card => {
            const matchComplejo = !complejoSel || card.dataset.complejo === complejoSel;
            const matchFecha = !fechaSel || card.dataset.fecha === fechaSel;

            if (matchComplejo && matchFecha) {
                card.style.display = '';
                visibles++;
            } else {
                card.style.display = 'none';
            }
        });

        if (sinFuncionesMsg) {
            sinFuncionesMsg.style.display = visibles === 0 ? 'block' : 'none';
        }
    }

    // listeners para selectores
    if (selectComplejo) selectComplejo.addEventListener('change', filtrarFunciones);
    if (selectFecha) selectFecha.addEventListener('change', filtrarFunciones);

    // listeners para botones rapidos (chips)
    chipsComplejo.forEach(chip => {
        chip.addEventListener('click', () => {
            if (selectComplejo) {
                selectComplejo.value = chip.dataset.complejo;
                filtrarFunciones();
            }
        });
    });

    // marcado de la tarjeta de funcion seleccionada
    funcionesCards.forEach(card => {
        const btnAccion = card.querySelector('[data-btn-accion]');
        if (btnAccion) {
            btnAccion.addEventListener('click', () => {
                funcionesCards.forEach(c => {
                    c.classList.remove('seleccionada');
                    const badge = c.querySelector('[data-badge]');
                    if (badge) badge.style.display = 'none';
                });

                card.classList.add('seleccionada');
                const badge = card.querySelector('[data-badge]');
                if (badge) badge.style.display = 'inline-block';
            });
        }
    });

    filtrarFunciones();
});