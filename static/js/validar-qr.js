(() => {
    const form = document.getElementById('form-validar-qr');
    const controls = document.getElementById('qr-camera-controls');
    if (!form || !controls) return;

    const input = document.getElementById('qr-identifier');
    const openButton = document.getElementById('qr-camera-open');
    const closeButton = document.getElementById('qr-camera-close');
    const activeControls = document.getElementById('qr-camera-active-controls');
    const reader = document.getElementById('qr-camera-reader-wrapper');
    const placeholder = document.getElementById('qr-camera-placeholder');
    const guide = document.getElementById('qr-camera-guide');
    const cameraSelector = document.getElementById('qr-camera-selector');
    const cameraSelect = document.getElementById('qr-camera-select');
    const photo = document.getElementById('qr-photo');
    const message = document.getElementById('qr-camera-message');
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d', { willReadFrequently: true });
    let scanner = null;
    let starting = null;
    let stopping = Promise.resolve();
    let operation = 0;
    let submitted = false;
    let availableCameras = [];
    controls.hidden = false;

    const showMessage = (text) => {
        message.classList.remove('is-success');
        message.textContent = text;
    };

    const stopCamera = () => {
        operation += 1;
        reader.hidden = true;
        placeholder.hidden = false;
        guide.hidden = true;
        activeControls.hidden = true;
        cameraSelector.hidden = true;
        openButton.setAttribute('aria-expanded', 'false');
        const pending = starting;
        const currentScanner = scanner;
        scanner = null;
        starting = null;
        if (currentScanner) {
            stopping = stopping.then(async () => {
                if (pending) {
                    try {
                        await pending;
                    } catch (error) {
                        return;
                    }
                }
                await currentScanner.stop();
            }).catch((error) => {
                console.error('No se pudo cerrar la cámara:', error);
                showMessage('No se pudo cerrar la cámara. Cerrá o recargá esta página para liberarla.');
            });
        }
        return stopping;
    };

    const readCode = (value) => {
        const text = value.trim();
        if (!text) return '';
        if (!/^https?:\/\//i.test(text)) return text;
        try {
            const url = new URL(text);
            const queryCode = url.searchParams.get('codigo') || url.searchParams.get('codigo_qr');
            if (queryCode) return queryCode.trim();
            const parts = url.pathname.split('/').filter(Boolean);
            const last = parts[parts.length - 1];
            return last && last !== 'validar-qr' ? decodeURIComponent(last).trim() : '';
        } catch (error) {
            return '';
        }
    };

    const submitCode = async (text) => {
        if (submitted) return;
        const code = readCode(text);
        if (!code) {
            stopCamera();
            showMessage('El QR no contiene un código válido. Probá otra foto o ingresalo manualmente.');
            return;
        }
        submitted = true;
        await stopCamera();
        input.value = code;
        form.requestSubmit();
    };

    const decodeImage = (source, width, height) => {
        const scale = Math.min(1, 2000 / Math.max(width, height));
        canvas.width = Math.max(1, Math.round(width * scale));
        canvas.height = Math.max(1, Math.round(height * scale));
        context.drawImage(source, 0, 0, canvas.width, canvas.height);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
        return window.jsQR(pixels.data, pixels.width, pixels.height);
    };

    const getCameras = async () => {
        try {
            return await window.Html5Qrcode.getCameras();
        } catch (error) {
            if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) throw error;
            const devices = await navigator.mediaDevices.enumerateDevices();
            const cameras = devices.filter((device) => device.kind === 'videoinput' && device.deviceId)
                .map((device) => ({ id: device.deviceId, label: device.label }));
            if (!cameras.length) throw error;
            return cameras;
        }
    };

    const startCameras = async (cameras, currentOperation) => {
        let lastError;
        for (const camera of cameras) {
            if (currentOperation !== operation) return;
            const currentScanner = new window.Html5Qrcode('qr-camera-reader');
            scanner = currentScanner;
            reader.hidden = false;
            try {
                starting = currentScanner.start(
                    camera.id, { fps: 10, qrbox: { width: 250, height: 250 } },
                    (text) => { if (currentOperation === operation) submitCode(text); },
                    () => {}
                );
                await starting;
                if (currentOperation !== operation) return;
                starting = null;
                placeholder.hidden = true;
                guide.hidden = false;
                cameraSelect.value = camera.id;
                cameraSelector.hidden = availableCameras.length <= 1;
                showMessage('');
                return;
            } catch (error) {
                if (currentOperation !== operation) return;
                scanner = null;
                starting = null;
                reader.hidden = true;
                lastError = error;
                console.error('No se pudo iniciar una cámara:', error);
            }
        }
        throw lastError;
    };

    const showCameraError = (error) => {
        console.error('No se pudo iniciar la cámara:', error);
        stopCamera();
        const errorText = `${error.name || ''} ${String(error)}`;
        if (/NotAllowedError|SecurityError|PermissionDeniedError/i.test(errorText)) {
            showMessage('Se denegó el acceso a la cámara. Revisá los permisos del navegador y del sistema, o usá una foto o el ingreso manual.');
        } else if (/NotFoundError|OverconstrainedError/i.test(errorText)) {
            showMessage('No se encontró una cámara disponible. Conectá una cámara o usá una foto o el ingreso manual.');
        } else if (/NotReadableError|AbortError|TrackStartError/i.test(errorText)) {
            showMessage('No se pudo iniciar la cámara. Cerrá otras aplicaciones que la estén usando, o usá una foto o el ingreso manual.');
        } else {
            showMessage('No se pudo iniciar la cámara. Revisá los permisos y el dispositivo, o usá una foto o el ingreso manual.');
        }
    };

    openButton.addEventListener('click', async () => {
        if (typeof window.Html5Qrcode !== 'function') {
            showMessage('No se pudo cargar el lector QR. Revisá tu conexión o ingresá el código manualmente.');
            return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showMessage('La cámara no está disponible. Usá HTTPS, escaneá desde una foto o ingresá el código manualmente.');
            return;
        }
        const previousStop = stopCamera();
        const currentOperation = operation;
        activeControls.hidden = false;
        openButton.setAttribute('aria-expanded', 'true');
        showMessage('Solicitando acceso a la cámara...');
        try {
            await previousStop;
            if (currentOperation !== operation) return;
            const cameras = await getCameras();
            if (currentOperation !== operation) return;
            if (!cameras.length) throw new DOMException('No hay cámaras disponibles', 'NotFoundError');
            availableCameras = cameras;
            cameraSelect.replaceChildren(...cameras.map((camera, index) => {
                const option = document.createElement('option');
                option.value = camera.id;
                option.textContent = camera.label || `Cámara ${index + 1}`;
                return option;
            }));
            const preferred = cameras.find((camera) => /trasera|back|rear|environment/i.test(camera.label || ''));
            const ordered = preferred
                ? [preferred, ...cameras.filter((camera) => camera !== preferred)]
                : cameras;
            await startCameras(ordered, currentOperation);
        } catch (error) {
            if (currentOperation !== operation) return;
            showCameraError(error);
        }
    });

    cameraSelect.addEventListener('change', async () => {
        const selected = availableCameras.find((camera) => camera.id === cameraSelect.value);
        if (!selected) return;
        const previousStop = stopCamera();
        const currentOperation = operation;
        activeControls.hidden = false;
        openButton.setAttribute('aria-expanded', 'true');
        showMessage('Cambiando de cámara...');
        try {
            await previousStop;
            if (currentOperation !== operation) return;
            await startCameras([selected], currentOperation);
        } catch (error) {
            if (currentOperation !== operation) return;
            showCameraError(error);
        }
    });

    closeButton.addEventListener('click', () => {
        stopCamera();
        showMessage('');
        openButton.focus();
    });

    photo.addEventListener('change', () => {
        const file = photo.files[0];
        photo.value = '';
        if (!file) return;
        stopCamera();
        const currentOperation = operation;
        if (typeof window.jsQR !== 'function' || !context) {
            showMessage('No se pudo cargar el lector QR. Revisá tu conexión o ingresá el código manualmente.');
            return;
        }
        showMessage('Buscando un QR en la imagen...');
        const image = new Image();
        const url = URL.createObjectURL(file);
        image.onload = () => {
            URL.revokeObjectURL(url);
            if (currentOperation !== operation || submitted) return;
            try {
                const result = decodeImage(image, image.naturalWidth, image.naturalHeight);
                if (result) submitCode(result.data);
                else showMessage('No se encontró un QR en la foto. Probá otra imagen o ingresá el código manualmente.');
            } catch (error) {
                console.error('No se pudo leer la imagen:', error);
                showMessage('No se pudo leer la imagen. Probá otra foto o ingresá el código manualmente.');
            }
        };
        image.onerror = () => {
            URL.revokeObjectURL(url);
            if (currentOperation === operation) showMessage('No se pudo abrir la imagen. Probá otra foto o ingresá el código manualmente.');
        };
        image.src = url;
    });

    form.addEventListener('submit', stopCamera);
    window.addEventListener('pagehide', stopCamera);
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) stopCamera();
    });
})();
