document.addEventListener("DOMContentLoaded", function () {

    // Obtener la fecha de hoy con la hora establecida a medianoche
    const hoy = new Date();
    const año = hoy.getFullYear();
    const mes = String(hoy.getMonth() + 1).padStart(2, '0');
    const dia = String(hoy.getDate()).padStart(2, '0');
    const fechaMaxima = `${año}-${mes}-${dia}`;

    // Establecer el atributo max
    const fechaInput = document.getElementById('fecha_nacimiento');
    fechaInput.setAttribute('max', fechaMaxima);

    // Validación en el evento change
    fechaInput.addEventListener('change', function() {
        const fechaSeleccionada = this.value;
        
        if (fechaSeleccionada > fechaMaxima) {
            alert('La fecha de nacimiento no puede estar en el futuro.');
            this.value = ''; // Limpiar el valor
        }
    });

    // Validación adicional en el envío del formulario
    document.getElementById('patient-form').addEventListener('submit', function(event) {
        const fechaSeleccionada = fechaInput.value;
        
        if (fechaSeleccionada && fechaSeleccionada > fechaMaxima) {
            event.preventDefault();
            alert('La fecha de nacimiento no puede estar en el futuro.');
            fechaInput.value = '';
        }
    });

    // Referencia al formulario
    const patientForm = document.getElementById("patient-form");

    // Validación personalizada del formulario
    if (patientForm) {
        patientForm.addEventListener("submit", function (event) {
            // Verificar campos requeridos
            const requiredFields = patientForm.querySelectorAll("[required]");
            let isValid = true;

            requiredFields.forEach((field) => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add("is-invalid");

                    // Crear mensaje de error si no existe
                    if (
                        !field.nextElementSibling ||
                        !field.nextElementSibling.classList.contains(
                            "invalid-feedback"
                        )
                    ) {
                        const errorMessage = document.createElement("div");
                        errorMessage.className = "invalid-feedback";
                        errorMessage.textContent = "Este campo es obligatorio";
                        field.parentNode.appendChild(errorMessage);
                    }
                } else {
                    field.classList.remove("is-invalid");
                    field.classList.add("is-valid");
                }
            });

            // Validar formato de email si no está vacío
            const emailField = document.getElementById("email");
            if (emailField && emailField.value.trim()) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(emailField.value.trim())) {
                    isValid = false;
                    emailField.classList.add("is-invalid");

                    // Crear mensaje de error si no existe
                    if (
                        !emailField.nextElementSibling ||
                        !emailField.nextElementSibling.classList.contains(
                            "invalid-feedback"
                        )
                    ) {
                        const errorMessage = document.createElement("div");
                        errorMessage.className = "invalid-feedback";
                        errorMessage.textContent = "Ingrese un email válido";
                        emailField.parentNode.appendChild(errorMessage);
                    }
                }
            }

            // Validar formato de teléfono si no está vacío
            const phoneField = document.getElementById("telefono");
            if (phoneField && phoneField.value.trim()) {
                const phoneRegex = /^[0-9\s\-\+\(\)]{6,20}$/;
                if (!phoneRegex.test(phoneField.value.trim())) {
                    isValid = false;
                    phoneField.classList.add("is-invalid");

                    // Crear mensaje de error si no existe
                    if (
                        !phoneField.nextElementSibling ||
                        !phoneField.nextElementSibling.classList.contains(
                            "invalid-feedback"
                        )
                    ) {
                        const errorMessage = document.createElement("div");
                        errorMessage.className = "invalid-feedback";
                        errorMessage.textContent =
                            "Ingrese un número de teléfono válido";
                        phoneField.parentNode.appendChild(errorMessage);
                    }
                }
            }

            // Detener el envío si no es válido
            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();

                // Mostrar alerta
                showNotification(
                    "Por favor, complete todos los campos requeridos correctamente.",
                    "warning"
                );

                // Hacer scroll al primer campo con error
                const firstInvalid = patientForm.querySelector(".is-invalid");
                if (firstInvalid) {
                    firstInvalid.scrollIntoView({
                        behavior: "smooth",
                        block: "center",
                    });
                    firstInvalid.focus();
                }
            }
        });

        // Eliminar validación visual cuando el usuario comienza a escribir
        patientForm
            .querySelectorAll("input, select, textarea")
            .forEach((field) => {
                field.addEventListener("input", function () {
                    this.classList.remove("is-invalid");

                    // Eliminar mensaje de error si existe
                    const errorFeedback =
                        this.parentNode.querySelector(".invalid-feedback");
                    if (errorFeedback) {
                        errorFeedback.remove();
                    }
                });
            });
    }

    // Calcular edad automáticamente cuando se selecciona fecha de nacimiento
    const dobField = document.getElementById("fecha_nacimiento");
    if (dobField) {
        dobField.addEventListener("change", function () {
            calculateAge(this.value);
        });
    }

    // Función para calcular edad basada en la fecha de nacimiento
    function calculateAge(birthDateString) {
        if (!birthDateString) return;

        const today = new Date();
        const birthDate = new Date(birthDateString);
        let age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();

        if (
            monthDiff < 0 ||
            (monthDiff === 0 && today.getDate() < birthDate.getDate())
        ) {
            age--;
        }

        // Puedes mostrar la edad en algún lugar o guardarla
        console.log("Edad calculada:", age);

        // Si quieres mostrar la edad en algún elemento HTML:
        // const ageDisplay = document.getElementById('age-display');
        // if (ageDisplay) {
        //     ageDisplay.textContent = age;
        // }
    }

    // Función para mostrar notificaciones
    function showNotification(message, type) {
        const notification = document.createElement("div");
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.position = "fixed";
        notification.style.top = "20px";
        notification.style.right = "20px";
        notification.style.padding = "12px 20px";
        notification.style.borderRadius = "4px";
        notification.style.backgroundColor =
            type === "success"
                ? "#4CAF50"
                : type === "error"
                ? "#F44336"
                : type === "warning"
                ? "#FF9800"
                : "#2196F3";
        notification.style.color = "white";
        notification.style.boxShadow = "0 4px 6px rgba(0,0,0,0.1)";
        notification.style.zIndex = "9999";
        notification.style.opacity = "0";
        notification.style.transform = "translateY(-10px)";
        notification.style.transition = "opacity 0.3s, transform 0.3s";

        // Añadir al DOM
        document.body.appendChild(notification);

        // Animar entrada
        setTimeout(() => {
            notification.style.opacity = "1";
            notification.style.transform = "translateY(0)";
        }, 10);

        // Eliminar después de un tiempo
        setTimeout(() => {
            notification.style.opacity = "0";
            notification.style.transform = "translateY(-10px)";

            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 4000);
    }
});
