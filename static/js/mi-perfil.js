document.addEventListener('DOMContentLoaded', () => {
    const modal = document.querySelector('[data-profile-modal]');
    if (!modal) return;
    const abrir = () => {
        modal.hidden = false;
        document.body.classList.add('modal-open');
        modal.querySelector('input')?.focus();
    };
    const cerrar = () => {
        modal.hidden = true;
        document.body.classList.remove('modal-open');
    };
    document.querySelector('[data-open-profile-modal]')?.addEventListener('click', abrir);
    modal.querySelectorAll('[data-close-profile-modal]').forEach((elemento) => {
        elemento.addEventListener('click', cerrar);
    });
    if (window.location.hash === '#editar-perfil') abrir();
});