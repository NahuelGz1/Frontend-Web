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

    formulario.addEventListener('input', actualizarResumen);
    actualizarResumen();
});
