document.addEventListener("DOMContentLoaded", () => {
    const botones = document.querySelectorAll("[data-acordeon-btn]");

    botones.forEach((boton) => {
        boton.addEventListener("click", () => {
            const card = boton.closest(".card");
            const contenido = card.querySelector("[data-acordeon-contenido]");
            const flecha = boton.querySelector("[data-acordeon-flecha]");

            const abrir = contenido.hidden;
            contenido.hidden = !abrir;
            boton.setAttribute("aria-expanded", String(abrir));

            if (flecha) {
                flecha.style.transform = abrir ? "rotate(90deg)" : "rotate(0deg)";
            }
            card.style.borderColor = abrir ? "var(--cinema-red)" : "";
        });
    });
});