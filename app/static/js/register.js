/**
 * register.js - Funcionalidades para el formulario de registro
 */

// Cuando el documento esté cargado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar funcionalidad de tipo de usuario
    initUserTypeSelector();
    
    // Inicializar validación del formulario
    initFormValidation();
    
    // Inicializar manejo de toast alerts
    initToastAlerts();

    // Inicializar selector de especialidad para psicólogos
    initEspecialidadSelector();
});

/**
 * Alterna la visibilidad de la contraseña
 */
function togglePasswordVisibility(inputId) {
    const passwordInput = document.getElementById(inputId);
    const toggleIcon = passwordInput.nextElementSibling;

    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        toggleIcon.classList.remove("fa-eye");
        toggleIcon.classList.add("fa-eye-slash");
    } else {
        passwordInput.type = "password";
        toggleIcon.classList.remove("fa-eye-slash");
        toggleIcon.classList.add("fa-eye");
    }
}

/**
 * Inicializa el selector de tipo de usuario
 */
function initUserTypeSelector() {
    const tipoUsuarioSelect = document.getElementById('tipo_usuario');
    const psicologoFields = document.getElementById('psicologo_fields');
    const psicologoSelector = document.getElementById('psicologo_selector');
    const psicologoId = document.getElementById('psicologo_id');
    const tituloProfesionalField = document.getElementById('titulo_profesional_field');
    
    // Función para actualizar campos según el tipo seleccionado
    function updateFields() {
        if (tipoUsuarioSelect.value === 'paciente') {
            // Si es paciente, mostrar selector de psicólogo y ocultar campos de psicólogo
            psicologoSelector.style.display = 'block';
            psicologoFields.style.display = 'none';
            if (tituloProfesionalField) {
                tituloProfesionalField.style.display = 'none';
            }
            if (psicologoId) {
                psicologoId.setAttribute('required', 'required');
            }
        } else {
            // Si es psicólogo, ocultar selector de psicólogo y mostrar campos de psicólogo
            psicologoSelector.style.display = 'none';
            psicologoFields.style.display = 'block';
            if (tituloProfesionalField) {
                tituloProfesionalField.style.display = 'block';
            }
            if (psicologoId) {
                psicologoId.removeAttribute('required');
            }
        }
    }
    
    // Ejecutar al cargar y cuando cambie la selección
    updateFields();
    tipoUsuarioSelect.addEventListener('change', updateFields);
}

/**
 * Inicializa el selector de especialidad para psicólogos
 */
function initEspecialidadSelector() {
    const selectEspecialidad = document.getElementById("especialidad");
    const otroField = document.getElementById("especialidad_otro");
    const otraEspecialidadInput = document.getElementById("otra_especialidad");

    function toggleOtroField() {
        if (selectEspecialidad.value === "otro") {
            otroField.style.display = "block";
            otraEspecialidadInput.required = true; // Hace el campo obligatorio si se selecciona "Otro"
        } else {
            otroField.style.display = "none";
            otraEspecialidadInput.required = false;
        }
    }

    // Ejecutar al cargar la página en caso de que "Otro" ya esté seleccionado
    toggleOtroField();

    // Agregar el evento al select
    selectEspecialidad.addEventListener("change", toggleOtroField);
}

/**
 * Inicializa la validación del formulario
 */
function initFormValidation() {
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    const form = document.getElementById('register-form');
    
    // Validar en tiempo real la coincidencia de contraseñas
    confirmPassword.addEventListener('input', validatePasswordMatch);
    password.addEventListener('input', function() {
        if (confirmPassword.value) {
            validatePasswordMatch();
        }
    });
    
    function validatePasswordMatch() {
        const invalidFeedback = confirmPassword.parentElement.nextElementSibling;
        
        if (password.value !== confirmPassword.value) {
            confirmPassword.classList.add('is-invalid');
            invalidFeedback.style.display = 'block';
            return false;
        } else {
            confirmPassword.classList.remove('is-invalid');
            invalidFeedback.style.display = 'none';
            return true;
        }
    }
    
    // Validación al enviar el formulario
    form.addEventListener('submit', function (event) {
        let isValid = true;

        // Validar coincidencia de contraseñas
        if (!validatePasswordMatch()) {
            isValid = false;
        }

        // Validar campos requeridos
        const requiredFields = document.querySelectorAll('[required]');
        requiredFields.forEach((field) => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                const invalidFeedback = field.parentElement.nextElementSibling;
                if (invalidFeedback && invalidFeedback.classList.contains('invalid-feedback')) {
                    invalidFeedback.style.display = 'block';
                }
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
                const invalidFeedback = field.parentElement.nextElementSibling;
                if (invalidFeedback && invalidFeedback.classList.contains('invalid-feedback')) {
                    invalidFeedback.style.display = 'none';
                }
            }
        });

        if (!isValid) {
            event.preventDefault();
        }
    });
}

/**
 * Inicializa el manejo de alertas toast
 */
function initToastAlerts() {
    // Función para cerrar las alertas toast
    window.closeToast = function(button) {
        const toast = button.closest('.toast-alert');
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    };

    // Ocultar automáticamente las alertas después de 5 segundos
    const toasts = document.querySelectorAll('.toast-alert');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    });
}
