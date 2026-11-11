// admin.js - interacciones visuales para las 5 pantallas del panel de administracion (peliculas, funciones, servicios, estadisticas, validar-qr)

document.addEventListener('DOMContentLoaded', () => {
    const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[character]));
    const deleteForms = document.querySelectorAll('form[data-confirm-delete]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (event) => {
            if (form.dataset.confirmed === 'true') return;
            event.preventDefault();
            const confirmation = document.createElement('div');
            confirmation.className = 'confirmation-card';
            confirmation.setAttribute('role', 'alert');
            const kind = form.dataset.itemKind || 'elemento';
            const itemName = escapeHtml(form.dataset.itemName || '');
            const capitalized = kind.charAt(0).toUpperCase() + kind.slice(1);
            confirmation.innerHTML = `<strong>Estado · Confirmar baja</strong>
                <span class="badge badge-danger">Confirmación pendiente</span>
                <h3>¿Dar de baja ${capitalized} ${itemName}?</h3>
                <p>${form.dataset.confirmDelete} La baja lo quitará del catálogo.</p>
                <div class="form-actions">
                    <button type="button" class="btn" data-cancel>Conservar ${kind}</button>
                    <button type="button" class="btn btn-delete" data-confirm>Sí, dar de baja</button>
                </div>`;
            const item = form.closest('.list-item, .function-row');
            const statePanel = item?.querySelector('.confirmation-slot');
            const fallbackPanel = form.parentElement;
            document.querySelectorAll('.confirmation-slot .confirmation-card').forEach((openConfirmation) => {
                openConfirmation.remove();
            });
            if (statePanel) statePanel.replaceChildren();
            (statePanel || fallbackPanel).appendChild(confirmation);
            confirmation.querySelector('[data-cancel]').addEventListener('click', () => {
                confirmation.remove();
            });

            confirmation.querySelector('[data-confirm]').addEventListener('click', () => {
                form.dataset.confirmed = 'true';
                confirmation.remove();
                form.requestSubmit();
            });
        });

    });

    const seatMap = document.querySelector('.seat-map');
    const rowsInput = document.getElementById('room-rows');
    const seatsInput = document.getElementById('room-seats');
    if (seatMap && rowsInput && seatsInput) {
        const renderSeats = () => {
            const rows = Math.max(0, Math.min(30, Number(rowsInput.value) || 0));
            const seats = Math.max(0, Math.min(40, Number(seatsInput.value) || 0));
            seatMap.replaceChildren();
            for (let row = 1; row <= rows; row += 1) {
                const line = document.createElement('div');
                line.className = 'seat-row';
                const label = document.createElement('span');
                label.textContent = row;
                line.appendChild(label);
                for (let seat = 1; seat <= seats; seat += 1) {
                    const item = document.createElement('i');
                    item.textContent = seat;
                    line.appendChild(item);
                }

                seatMap.appendChild(line);
            }
        };
        rowsInput.addEventListener('input', renderSeats);
        rowsInput.addEventListener('change', renderSeats);
        seatsInput.addEventListener('input', renderSeats);
        seatsInput.addEventListener('change', renderSeats);
        renderSeats();
    }

    const complexSelect = document.getElementById('function-complex');
    const roomSelect = document.getElementById('function-room');
    const complexHidden = document.querySelector('input[name="complejo_id"]');
    if (complexSelect && roomSelect) {
        const filterRooms = () => {
            const complex = complexSelect.value;
            if (complexHidden) complexHidden.value = complex;
            Array.from(roomSelect.options).forEach((option, index) => {
                if (index === 0) {
                    option.hidden = false;
                    return;
                }
                option.hidden = Boolean(complex) && option.dataset.complejo !== complex;
            });
            if (roomSelect.selectedOptions[0]?.hidden) roomSelect.value = '';
            roomSelect.disabled = false;
        };
        complexSelect.addEventListener('change', filterRooms);
        roomSelect.addEventListener('change', () => {
            const selectedRoom = roomSelect.selectedOptions[0];
            if (!selectedRoom || !selectedRoom.dataset.complejo) return;
            complexSelect.value = selectedRoom.dataset.complejo;
            if (complexHidden) complexHidden.value = selectedRoom.dataset.complejo;
            filterRooms();
            roomSelect.value = selectedRoom.value;
        });
        filterRooms();
    }

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