// Implementación básica de showNotification (reemplazar si usas una librería)
function showNotification(message, type) {
    const bgColor = type === 'error' ? '#dc3545' : type === 'warning' ? '#ffc107' : '#28a745';
    const notification = document.createElement('div');
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '15px';
    notification.style.backgroundColor = bgColor;
    notification.style.color = 'white';
    notification.style.borderRadius = '5px';
    notification.style.zIndex = '1000';
    notification.textContent = message;

    document.body.appendChild(notification);
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

document.addEventListener("DOMContentLoaded", function () {
    const fechaInput = document.getElementById("fecha");
    const horaInput = document.getElementById("hora");
    const timeSlots = document.querySelectorAll(".time-slot");

    // Restringir selección de fechas pasadas
    const today = new Date().toISOString().split("T")[0];
    fechaInput.setAttribute("min", today);

    // Función para actualizar la duración según el tipo de cita seleccionado
    function actualizarDuracion() {
        const tipoCitaSelect = document.getElementById('tipo_cita_id');
        const descripcionElement = document.querySelector('.tipo-descripcion');
        
        if (tipoCitaSelect && tipoCitaSelect.selectedIndex > 0) {
            const selectedOption = tipoCitaSelect.options[tipoCitaSelect.selectedIndex];
            
            if (descripcionElement) {
                descripcionElement.textContent = selectedOption.getAttribute('data-descripcion') || '';
            }
        }
    }

    // Inicializar la actualización de duración
    const tipoCitaSelect = document.getElementById('tipo_cita_id');
    if (tipoCitaSelect) {
        tipoCitaSelect.addEventListener("change", actualizarDuracion);
        actualizarDuracion();
    }

    // Función para cargar horas ocupadas
    function cargarHorasOcupadas(fecha) {
        const url = fecha ? `/api/horas_ocupadas?fecha=${fecha}` : '/api/horas_ocupadas';
        console.log('Cargando horas ocupadas desde:', url);
        fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Error al obtener horas ocupadas');
            }
            console.log('Horas ocupadas:', data.horas_ocupadas);
            const horasOcupadas = data.horas_ocupadas || [];

            timeSlots.forEach(slot => {
                const horaSlot = slot.getAttribute("data-hora");
                if (horasOcupadas.includes(horaSlot)) {
                    slot.classList.add("unavailable");
                    slot.setAttribute("disabled", "true");
                } else {
                    slot.classList.remove("unavailable");
                    slot.removeAttribute("disabled");
                }
            });
            console.log('Slots disponibles:', 
                Array.from(timeSlots).filter(s => !s.classList.contains("unavailable")).map(s => s.getAttribute("data-hora")));
        })
        .catch(error => {
            console.error("Error al obtener las horas ocupadas:", error);
            showNotification("No se pudieron cargar las horas ocupadas: " + error.message, "error");
        });
    }

    // Asignar eventos a los time-slot
    timeSlots.forEach(slot => {
        slot.addEventListener("click", (e) => {
            e.preventDefault();
            if (slot.classList.contains("unavailable")) {
                console.log('Slot no disponible:', slot.getAttribute("data-hora"));
                return;
            }
            timeSlots.forEach(s => s.classList.remove("selected"));
            slot.classList.add("selected");
            const hora = slot.getAttribute("data-hora");
            horaInput.value = hora;
            console.log('Hora seleccionada:', hora);
        });
    });

    // Cargar horas ocupadas inicialmente
    cargarHorasOcupadas(fechaInput.value);

    // Recargar horas ocupadas al cambiar la fecha
    fechaInput.addEventListener('change', () => {
        cargarHorasOcupadas(fechaInput.value);
        horaInput.value = '';
        timeSlots.forEach(slot => slot.classList.remove("selected"));
        console.log('Fecha cambiada a:', fechaInput.value);
    });

    // Validación y envío del formulario
    const form = document.getElementById("appointment-form-page");
    if (form) {
        form.addEventListener("submit", async function (e) {
            e.preventDefault();

            const paciente = document.getElementById("paciente_id").value;
            const fecha = document.getElementById("fecha").value;
            let hora = document.getElementById("hora").value;
            const tipoCita = document.getElementById("tipo_cita_id");
            const syncGoogle = document.getElementById("sync_google").checked;

            if (fecha < today) {
                showNotification("No puedes programar una cita en una fecha pasada.", "error");
                return;
            }

            if (!paciente || !fecha || !hora) {
                showNotification("Por favor, completa los campos de paciente, fecha y hora.", "warning");
                return;
            }

            if (tipoCita && !tipoCita.value) {
                showNotification("Por favor, selecciona un tipo de cita.", "warning");
                return;
            }

            if (!hora.includes(':')) {
                hora = `${hora}:00`;
                horaInput.value = hora;
            }

            try {
                const formData = new FormData(form);
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    redirect: 'manual' // Evitar que fetch siga redirecciones
                });

                // Manejar redirecciones manualmente
                if (response.type === 'opaqueredirect') {
                    // Extraer la URL de redirección desde los headers o asumir /api/google-auth
                    const redirectUrl = response.url || '/api/google-auth';
                    console.log('Redirigiendo a:', redirectUrl);
                    window.location.href = redirectUrl;
                    return;
                }

                const result = await response.json();

                if (!result.success) {
                    showNotification(result.message || "Error al guardar la cita", "error");
                    return;
                }

                if (result.redirect) {
                    console.log('Redirigiendo a:', result.redirect);
                    window.location.href = result.redirect;
                } else {
                    showNotification(result.message, "success");
                    window.location.href = result.redirect || "/historial";
                }
            } catch (error) {
                console.error("Error al guardar cita:", error);
                showNotification("Error al guardar la cita: " + error.message, "error");
            }
        });
    }

    // Evento para el botón de cancelar
    const cancelBtn = document.getElementById("cancel-btn");
    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            window.location.href = "/historial";
        });
    }
});


async function syncAppointment(citaId, fecha, hora, tipoCitaSelect) {
    console.log('Iniciando sincronización:', { citaId, fecha, hora }); // Depuración

    // Validar fecha y hora
    if (!fecha || !hora) {
        console.error('Fecha u hora no válidas', { fecha, hora });
        showNotification('Por favor, seleccione fecha y hora', 'warning');
        return;
    }

    // Validar formato de fecha (YYYY-MM-DD)
    const fechaRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!fechaRegex.test(fecha)) {
        console.error('Formato de fecha inválido:', fecha);
        showNotification('Formato de fecha inválido. Use YYYY-MM-DD', 'error');
        return;
    }

    // Normalizar hora al formato HH:mm
    let horaFormatted = hora;
    if (!hora.includes(':')) {
        horaFormatted = `${hora}:00`;
    }
    const horaRegex = /^\d{2}:\d{2}$/;
    if (!horaRegex.test(horaFormatted)) {
        console.error('Formato de hora inválido:', hora);
        showNotification('Formato de hora inválido. Use HH:mm', 'error');
        return;
    }

    // Crear fecha segura
    let fechaHora;
    try {
        fechaHora = new Date(`${fecha}T${horaFormatted}`);
        console.log('Fecha construida:', fechaHora); // Depuración

        if (isNaN(fechaHora.getTime())) {
            throw new Error(`Fecha no válida: ${fecha}T${horaFormatted}`);
        }

        // Validar que la fecha no sea pasada
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (fechaHora < today) {
            throw new Error('No se pueden sincronizar citas en fechas pasadas');
        }
    } catch (error) {
        console.error('Error al crear fecha:', error.message);
        showNotification(error.message, 'error');
        return;
    }

    // Obtener duración y descripción
    const duracion = tipoCitaSelect.options[tipoCitaSelect.selectedIndex].getAttribute('data-duracion') || 60;
    const summary = tipoCitaSelect.options[tipoCitaSelect.selectedIndex].text;
    const description = tipoCitaSelect.options[tipoCitaSelect.selectedIndex].getAttribute('data-descripcion') || '';

    // Preparar datos para enviar
    const datosSync = {
        cita_id: parseInt(citaId),
        fecha: fechaHora.toISOString(),
        notifications: {
            email: 30,
            popup: 10
        },
        summary: summary,
        description: description,
        duration: parseInt(duracion)
    };

    console.log('Datos enviados:', datosSync); // Depuración

    try {
        const response = await fetch('/api/sync-google-calendar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(datosSync)
        });

        const data = await response.json();
        if (data.success) {
            showNotification('Cita sincronizada con Google Calendar', 'success');
            window.location.href = "/historial"; // Redirigir tras sincronizar
        } else if (data.redirect) {
            console.log('Redirigiendo para autenticación:', data.redirect);
            window.location.href = data.redirect;
        } else {
            showNotification(data.message || 'Error al sincronizar', 'error');
        }
    } catch (error) {
        console.error('Error en sincronización:', error);
        showNotification('Error al sincronizar con Google Calendar: ' + error.message, 'error');
    }
}