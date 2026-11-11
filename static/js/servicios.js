// Mejora visual opcional: el formulario funciona sin este script.
document.addEventListener('DOMContentLoaded', () => {
    const formulario = document.getElementById('servicios-contenedor');
    if (!formulario) return;

    const cards = formulario.querySelectorAll('[data-service-card]');
    const entradas = document.querySelector('[data-ticket-total-display]');
    const totalEntradas = Number(entradas?.textContent.replace(/\D/g, '') || 0);
    const pesos = valor => `$${valor.toLocaleString('es-AR')}`;

    function actualizarResumen() {
        let total = 0;
        let cantidad = 0;
        const seleccion = [];
        cards.forEach(card => {
            const input = card.querySelector('[data-quantity]');
            if (input.disabled || !input.validity.valid) return;
            const unidades = input.valueAsNumber || 0;
            if (!unidades) return;
            const subtotal = unidades * Number(card.dataset.precio);
            cantidad += unidades;
            total += subtotal;
            seleccion.push(`${card.dataset.serviceName} × ${unidades}: ${pesos(subtotal)}`);
        });
        document.querySelector('[data-cart-count]').textContent = `${cantidad} artículos`;
        for (const selector of ['[data-cart-items]', '[data-purchase-lines]']) {
            const contenedor = document.querySelector(selector);
            contenedor.replaceChildren();
            for (const texto of seleccion.length ? seleccion : ['No agregaste servicios.']) {
                const linea = document.createElement('p');
                linea.textContent = texto;
                contenedor.appendChild(linea);
            }
        }
        document.querySelector('[data-service-total]').textContent = pesos(total);
        document.querySelector('[data-service-total-summary]').textContent = pesos(total);
        document.querySelector('[data-purchase-total]').textContent = pesos(totalEntradas + total);
    }

    // actualiza los botones y el contador de una card específica
    function actualizarCard(card) {
        const id              = card.dataset.serviceId;
        const cantidad        = carrito[id] ? carrito[id].cantidad : 0;
        const addBtn          = card.querySelector('[data-add]');
        const quantitySection = card.querySelector('[data-quantity-controls]');
        const quantityDisplay = card.querySelector('[data-quantity]');
        const maxQty          = parseInt(card.dataset.maxQuantity || '9999', 10);

        // si ya tiene al menos uno, escondemos el botón "Agregar" y mostramos los controles
        if (addBtn) {
            addBtn.hidden = cantidad > 0;
        }
        if (quantitySection) {
            quantitySection.hidden = cantidad === 0;
        }
        if (quantityDisplay) {
            quantityDisplay.textContent = cantidad;
        }

        // bloqueamos el "+" si llegamos al máximo permitido
        const increaseBtn = card.querySelector('[data-increase]');
        if (increaseBtn) {
            increaseBtn.disabled = cantidad >= maxQty;
        }
    }

    // escuchamos todos los clics dentro del contenedor (delegación)
    contenedorServicios.addEventListener('click', e => {

        // botón "Agregar +" que aparece la primera vez
        const addBtn = e.target.closest('[data-add]');
        if (addBtn) {
            const card   = addBtn.closest('[data-service-card]');
            if (!card) return;
            const id     = card.dataset.serviceId;
            const nombre = card.dataset.serviceName;
            const precio = parseFloat(card.dataset.precio || 0);
            const maxQty = parseInt(card.dataset.maxQuantity || '9999', 10);

            if (!carrito[id]) {
                carrito[id] = { nombre, precio, cantidad: 0 };
            }
            if (carrito[id].cantidad < maxQty) {
                carrito[id].cantidad++;
            }
            actualizarCard(card);
            actualizarUI();
            return;
        }

        // botón "+" del control de cantidad
        const incBtn = e.target.closest('[data-increase]');
        if (incBtn) {
            const card   = incBtn.closest('[data-service-card]');
            if (!card) return;
            const id     = card.dataset.serviceId;
            const maxQty = parseInt(card.dataset.maxQuantity || '9999', 10);

            if (carrito[id] && carrito[id].cantidad < maxQty) {
                carrito[id].cantidad++;
                actualizarCard(card);
                actualizarUI();
            }
            return;
        }

        // botón "−" del control de cantidad
        const decBtn = e.target.closest('[data-decrease]');
        if (decBtn) {
            const card = decBtn.closest('[data-service-card]');
            if (!card) return;
            const id = card.dataset.serviceId;

            if (carrito[id] && carrito[id].cantidad > 0) {
                carrito[id].cantidad--;
                actualizarCard(card);
                actualizarUI();
            }
            return;
        }

        // botón "✕" del carrito lateral - saca el producto entero
        const removeBtn = e.target.closest('[data-remove-id]');
        if (removeBtn) {
            const id = removeBtn.dataset.removeId;
            if (carrito[id]) {
                carrito[id].cantidad = 0;
            }
            // volvemos la card a su estado original
            const card = contenedorServicios.querySelector(`[data-service-id="${id}"]`);
            if (card) actualizarCard(card);
            actualizarUI();
            return;
        }
    });

    // si el usuario toca "Continuar"
    function manejarCheckout() {
        const formulario = document.createElement('form');
        formulario.method = 'POST';
        formulario.action = '/servicios/guardar';

        const csrf = document.createElement('input');
        csrf.type = 'hidden';
        csrf.name = 'csrf_token';
        csrf.value = document.getElementById('servicios-csrf-token')?.value || '';
        formulario.appendChild(csrf);

        Object.entries(carrito).forEach(([id, item]) => {
            if (item.cantidad > 0) {
                const idNum = parseInt(id, 10);
                if (Number.isInteger(idNum)) {
                    const cantidad = document.createElement('input');
                    cantidad.type = 'hidden';
                    cantidad.name = `cantidad_${idNum}`;
                    cantidad.value = String(item.cantidad);
                    formulario.appendChild(cantidad);
                }
            }
        });

        document.body.appendChild(formulario);
        formulario.submit();
    }

    if (checkoutBtn)    checkoutBtn.addEventListener('click', manejarCheckout);
    if (checkoutBtnSec) checkoutBtnSec.addEventListener('click', manejarCheckout);

    // arrancamos con todo en cero
    actualizarUI();
});
