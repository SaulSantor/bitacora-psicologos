document.addEventListener("DOMContentLoaded", function () {
    // Activar/desactivar el menú de usuario al hacer clic
    const userMenuContainer = document.querySelector(".user-menu-container");
    if (userMenuContainer) {
        userMenuContainer.addEventListener("click", function (event) {
            // Prevenir que el clic en el avatar o el nombre active el menú
            event.stopPropagation();
            // Alternar la clase 'active' para mostrar el menú
            userMenuContainer.classList.toggle("active");
        });

        // Cerrar el menú si se hace clic fuera de él
        document.addEventListener("click", function (event) {
            if (!userMenuContainer.contains(event.target)) {
                userMenuContainer.classList.remove("active");
            }
        });
    }
});
