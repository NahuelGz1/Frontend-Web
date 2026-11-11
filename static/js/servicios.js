// servicios.js - carrito del candy bar

document.addEventListener('DOMContentLoaded', () => {
    const contenedorServicios = document.getElementById('servicios-contenedor');
    if (!contenedorServicios) return;

    // panel de "Tu selección" (el aside de la derecha)
    const cartCountElem      = contenedorServicios.querySelector('[data-cart-count]');
    const cartItemsElem      = contenedorServicios.querySelector('[data-cart-items]');
    const cartEmptyElem      = contenedorServicios.querySelector('[data-cart-empty]');
    const serviceTotalElem   = contenedorServicios.querySelector('[data-service-total]');
    const checkoutBtn        = contenedorServicios.querySelector('[data-checkout]');
    const checkoutMsg        = contenedorServicios.querySelector('[data-checkout-message]');

    // resumen de compra de abajo (el de entradas + servicios)
    const purchaseLinesElem  = document.querySelector('[data-purchase-lines]');
    const purchaseEmptyElem  = document.querySelector('[data-purchase-empty]');
    const serviceTotalSum    = document.querySelector('[data-service-total-summary]');
    const purchaseTotalElem  = document.querySelector('[data-purchase-total]');
    const checkoutBtnSec     = document.querySelector('[data-checkout-secondary]');

    // el total de entradas ya viene renderizado desde el servidor, lo levantamos
    const ticketTotalElem    = document.querySelector('[data-ticket-total-display]');
    const ticketTotal        = ticketTotalElem
        ? parseInt(ticketTotalElem.textContent.replace(/\D/g, ''), 10) || 0
        : 0;

    // acá guardamos lo que el usuario va agregando: { id: { nombre, precio, cantidad } }
    const carrito = {};

    // formatea un número como precio en pesos argentinos
    function formatPesos(valor) {
        return `$${valor.toLocaleString('es-AR')}`;
    }

    // re-dibuja el carrito lateral y el resumen de abajo con lo que hay en `carrito`
    function actualizarUI() {
        let totalServicios = 0;
        let totalItems     = 0;

        Object.values(carrito).forEach(item => {
            totalServicios += item.precio * item.cantidad;
            totalItems     += item.cantidad;
        });

        // -- carrito lateral --

        if (cartCountElem) {
            cartCountElem.textContent =
                totalItems === 1 ? '1 artículo' : `${totalItems} artículos`;
        }

        if (serviceTotalElem) {
            serviceTotalElem.textContent = formatPesos(totalServicios);
        }

        // si no hay nada, mostramos el mensaje de "todavía no agregaste nada"
        if (cartEmptyElem) {
            cartEmptyElem.hidden = totalItems > 0;
        }

        // limpiamos las líneas anteriores y las volvemos a armar
        if (cartItemsElem) {
            cartItemsElem.querySelectorAll('[data-cart-line]').forEach(el => el.remove());

            Object.entries(carrito).forEach(([id, item]) => {
                if (item.cantidad <= 0) return;
                const linea = document.createElement('div');
                linea.setAttribute('data-cart-line', id);
                linea.className = 'service-cart-line';
                linea.innerHTML = `
                    <span>${item.nombre} × ${item.cantidad}</span>
                    <strong>${formatPesos(item.precio * item.cantidad)}</strong>
                    <button type="button" class="service-cart-remove" data-remove-id="${id}" aria-label="Quitar ${item.nombre}">✕</button>
                `;
                cartItemsElem.appendChild(linea);
            });
        }

        // el botón de continuar solo se habilita si hay algo en el carrito
        if (checkoutBtn)    checkoutBtn.disabled    = totalItems === 0;
        if (checkoutBtnSec) checkoutBtnSec.disabled = totalItems === 0;

        // -- resumen de compra (sección de abajo) --

        if (purchaseLinesElem) {
            purchaseLinesElem.querySelectorAll('[data-purchase-line]').forEach(el => el.remove());

            Object.entries(carrito).forEach(([id, item]) => {
                if (item.cantidad <= 0) return;
                const linea = document.createElement('div');
                linea.setAttribute('data-purchase-line', id);
                linea.style.display = 'flex';
                linea.style.justifyContent = 'space-between';
                linea.style.gap = '1rem';
                linea.innerHTML = `<span>${item.nombre} × ${item.cantidad}</span><strong>${formatPesos(item.precio * item.cantidad)}</strong>`;
                purchaseLinesElem.appendChild(linea);
            });

            if (purchaseEmptyElem) {
                purchaseEmptyElem.hidden = totalItems > 0;
            }
        }

        if (serviceTotalSum)   serviceTotalSum.textContent   = formatPesos(totalServicios);
        if (purchaseTotalElem) purchaseTotalElem.textContent = formatPesos(totalServicios + ticketTotal);
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
    async function manejarCheckout() {
        const serviciosSeleccionados = [];
        Object.entries(carrito).forEach(([id, item]) => {
            if (item.cantidad > 0) {
                const idNum = parseInt(id, 10);
                serviciosSeleccionados.push({
                    id_servicio: isNaN(idNum) ? id : idNum,
                    cantidad: item.cantidad
                });
            }
        });

        try {
            const respuesta = await fetch('/servicios/guardar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ servicios: serviciosSeleccionados })
            });

            if (respuesta.ok) {
                const datos = await respuesta.json();
                window.location.href = datos.redirect || '/pagar';
            } else {
                window.location.href = '/pagar';
            }
        } catch (e) {
            window.location.href = '/pagar';
        }
    }

    if (checkoutBtn)    checkoutBtn.addEventListener('click', manejarCheckout);
    if (checkoutBtnSec) checkoutBtnSec.addEventListener('click', manejarCheckout);

    // arrancamos con todo en cero
    actualizarUI();
});
