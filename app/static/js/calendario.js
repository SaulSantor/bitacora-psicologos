// Funcionalidad del Calendario
document.addEventListener('DOMContentLoaded', function() {
    // Variables globales
    let currentDate = new Date();
    let currentCitaId = null;
    
    // Referencias a elementos DOM
    const calendarDays = document.getElementById('calendar-days');
    const monthYearDisplay = document.getElementById('calendar-month-year');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const citaModal = document.getElementById('cita-modal');
    const closeModal = document.querySelector('.close-modal');
    const editCitaBtn = document.getElementById('edit-cita');
    const deleteCitaBtn = document.getElementById('delete-cita');
    const createCitaModal = document.getElementById('create-cita-modal');
    const createCitaForm = document.getElementById('create-cita-form');
    const closeCreateModal = createCitaModal.querySelector('.close-modal');
    const fechaInput = document.getElementById('fecha');
    const pacienteSelect = document.getElementById('paciente_id');
    const tipoCitaSelect = document.getElementById('tipo_cita_id');
    const motivoInput = document.getElementById('motivo');
    const horasOcupadasDiv = document.getElementById('horas-ocupadas');
    
    // Inicializar calendario
    initCalendar();
    
    // Event Listeners
    prevMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });
    
    nextMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });
    
    closeModal.addEventListener('click', () => {
        citaModal.style.display = 'none';
    });


    
    window.addEventListener('click', (e) => {
        if (e.target === citaModal) {
            citaModal.style.display = 'none';
        }
    });
    
    // Cerrar modal de crear cita
    closeCreateModal.addEventListener('click', () => {
        createCitaModal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === createCitaModal) {
            createCitaModal.style.display = 'none';
        }
    });

    editCitaBtn.addEventListener('click', () => {
        // Redirigir a la página de edición de cita
        if (currentCitaId) {
            window.location.href = `/cita/${currentCitaId}/editar`;
        }
    });
    
    deleteCitaBtn.addEventListener('click', () => {
        // Confirmar eliminación
        if (currentCitaId && confirm('¿Estás seguro de que deseas eliminar esta cita?')) {
            eliminarCita(currentCitaId);
        }
    });
    
    
    // Funciones principales
    function initCalendar() {
        renderCalendar();
        
        // Si hay un parámetro tab=calendario en la URL, activar la pestaña de calendario
        if (window.location.search.includes('tab=calendario')) {
            // Asumiendo que tienes un sistema de pestañas
            const tabLinks = document.querySelectorAll('.nav-tabs a');
            const calendarTab = Array.from(tabLinks).find(tab => tab.getAttribute('href') === '#calendario');
            if (calendarTab) {
                calendarTab.click();
            }
        }
    }
    
    function renderCalendar() {
        // Actualizar título del mes y año
        const monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        monthYearDisplay.textContent = `${monthNames[currentDate.getMonth()]} ${currentDate.getFullYear()}`;
        
        // Limpiar días existentes
        calendarDays.innerHTML = '';
        
        // Obtener primer día del mes y número de días
        const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
        const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
        
        // Calcular días del mes anterior para completar la primera semana
        const startingDayOfWeek = firstDay.getDay(); // 0 (domingo) a 6 (sábado)
        
        // Calcular días del mes siguiente para completar la última semana
        const endingDayOfWeek = lastDay.getDay();
        const totalDaysToShow = 42; // 6 semanas * 7 días
        
        // Crear array con todos los días a mostrar
        const daysToRender = [];
        
        // Días del mes anterior
        const prevMonthLastDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 0).getDate();
        for (let i = startingDayOfWeek - 1; i >= 0; i--) {
            const day = prevMonthLastDay - i;
            const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, day);
            daysToRender.push({
                date: date,
                dayNumber: day,
                isCurrentMonth: false
            });
        }
        
        // Días del mes actual
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
            daysToRender.push({
                date: date,
                dayNumber: day,
                isCurrentMonth: true
            });
        }
        
        // Días del mes siguiente
        const remainingDays = totalDaysToShow - daysToRender.length;
        for (let day = 1; day <= remainingDays; day++) {
            const date = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, day);
            daysToRender.push({
                date: date,
                dayNumber: day,
                isCurrentMonth: false
            });
        }
        
        // Definir todayStr en un ámbito superior
        const today = new Date();
        const todayStr = today.getFullYear() + '-' + 
                        String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                        String(today.getDate()).padStart(2, '0');

        // Crear elementos del calendario
        daysToRender.forEach(dayInfo => {
            const dayElement = document.createElement('div');
            dayElement.className = 'calendar-day';
            
            if (!dayInfo.isCurrentMonth) {
                dayElement.classList.add('other-month');
            }
            
            const dayStr = dayInfo.date.getFullYear() + '-' + 
                        String(dayInfo.date.getMonth() + 1).padStart(2, '0') + '-' + 
                        String(dayInfo.date.getDate()).padStart(2, '0');

            if (dayStr === todayStr) {
                dayElement.classList.add('today');
            }
            
            // Crear encabezado del día
            const dayHeader = document.createElement('div');
            dayHeader.className = 'calendar-day-header';
            dayHeader.textContent = dayInfo.dayNumber;
            dayElement.appendChild(dayHeader);
            
            // Contenedor para eventos
            const eventsContainer = document.createElement('div');
            eventsContainer.className = 'day-events';
            dayElement.appendChild(eventsContainer);
            
            // Guardar referencia a la fecha para usarla cuando se carguen las citas
            dayElement.dataset.date = dayInfo.date.toISOString().split('T')[0];
            
            calendarDays.appendChild(dayElement);
        });
        
        // Cargar citas para este mes
        loadAppointments();

        // Añadir eventos de clic a los días no pasados
        document.querySelectorAll('.calendar-day').forEach(day => {
            const dayDate = day.dataset.date;

            // Deshabilitar días pasados
            if (dayDate < todayStr) {
                day.classList.add('disabled');
                day.style.pointerEvents = 'none';
                day.style.opacity = '0.5';
            } else {
                day.addEventListener('click', (e) => {
                    if (!e.target.classList.contains('event')) {
                        openCreateCitaModal(day.dataset.date);
                    }
                });
            }
        });

        // Función para asegurar que el día actual sea visible
        function scrollToToday() {
            setTimeout(() => {
                const todayElement = document.querySelector('.calendar-day.today');
                if (todayElement) {
                    todayElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    todayElement.classList.add('today-highlight');
                    setTimeout(() => {
                        todayElement.classList.remove('today-highlight');
                    }, 2000);
                }
            }, 100);
        }

        scrollToToday();
    }


    function openCreateCitaModal(date) {
        const today = new Date();
        const todayStr = today.getFullYear() + '-' + 
                        String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                        String(today.getDate()).padStart(2, '0');

        // Validar que la fecha no sea pasada
        if (date < todayStr) {
            alert('No puedes crear citas para días pasados.');
            return;
        }

        // Establecer atributo min para el input de fecha
        fechaInput.setAttribute('min', todayStr);
        fechaInput.value = date;

        // Limpiar campos
        pacienteSelect.innerHTML = '<option value="">Selecciona un paciente</option>';
        tipoCitaSelect.innerHTML = '<option value="">Selecciona un tipo de cita</option>';
        motivoInput.value = '';
        horasOcupadasDiv.innerHTML = '';
        document.getElementById('no-pacientes-message').style.display = 'none';

        // Obtener la URL para crear nuevo paciente
        const nuevoPacienteUrl = createCitaModal.dataset.nuevoPacienteUrl;

        // Cargar lista de pacientes
        fetch('/api/pacientes')
            .then(response => {
                if (!response.ok) throw new Error('Error al cargar pacientes');
                return response.json();
            })
            .then(pacientes => {
                if (pacientes.length === 0) {
                    document.getElementById('no-pacientes-message').innerHTML = 
                        `No hay pacientes disponibles. <a href="${nuevoPacienteUrl}">Crear un nuevo paciente</a>.`;
                    document.getElementById('no-pacientes-message').style.display = 'block';
                } else {
                    pacientes.forEach(paciente => {
                        const option = document.createElement('option');
                        option.value = paciente.id;
                        option.textContent = `${paciente.nombre} ${paciente.apellido || ''}`; // Include apellido if available
                        pacienteSelect.appendChild(option);
                    });
                }

                // Cargar tipos de cita
                fetch('/api/tipos-cita')
                    .then(response => {
                        if (!response.ok) throw new Error('Error al cargar tipos de cita');
                        return response.json();
                    })
                    .then(tipos => {
                        tipos.forEach(tipo => {
                            const option = document.createElement('option');
                            option.value = tipo.id;
                            option.textContent = tipo.nombre;
                            tipoCitaSelect.appendChild(option);
                        });

                        // Cargar horas ocupadas para la fecha seleccionada
                        fetch(`/api/horas_ocupadas?fecha=${date}`)
                            .then(response => {
                                if (!response.ok) {
                                    return response.json().then(data => {
                                        throw new Error(data.message || 'Error al cargar horas ocupadas');
                                    });
                                }
                                return response.json();
                            })
                            .then(data => {
                                const horaSelect = document.getElementById('hora');
                                horaSelect.innerHTML = '<option value="">Selecciona una hora</option>';
                                const startHour = 8;
                                const endHour = 20;
                                const occupiedHours = Array.isArray(data) ? data : [];
                                
                                for (let h = startHour; h <= endHour; h++) {
                                    for (let m = 0; m < 60; m += 30) {
                                        const time = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
                                        if (!occupiedHours.includes(time)) {
                                            const option = document.createElement('option');
                                            option.value = time;
                                            option.textContent = time;
                                            horaSelect.appendChild(option);
                                        }
                                    }
                                }
                                
                                if (occupiedHours.length > 0) {
                                    horasOcupadasDiv.innerHTML = `Horas ocupadas: ${occupiedHours.join(', ')}`;
                                } else {
                                    horasOcupadasDiv.innerHTML = 'No hay horas ocupadas para este día.';
                                }
                            })
                            .catch(error => {
                                console.error('Error al cargar horas ocupadas:', error);
                                horasOcupadasDiv.innerHTML = `Error al cargar horas ocupadas: ${error.message}`;
                                const horaInput = document.createElement('input');
                                horaInput.type = 'time';
                                horaInput.id = 'hora';
                                horaInput.name = 'hora';
                                horaInput.required = true;
                                horaSelect.parentNode.replaceChild(horaInput, horaSelect);
                            })
                            .finally(() => {
                                createCitaModal.style.display = 'block';
                            });
                    })
                    .catch(error => {
                        console.error('Error al cargar tipos de cita:', error);
                        alert('Error al cargar los tipos de cita');
                        createCitaModal.style.display = 'block';
                    });
            })
            .catch(error => {
                console.error('Error al cargar pacientes:', error);
                document.getElementById('no-pacientes-message').innerHTML = 
                    `Error al cargar pacientes. <a href="${nuevoPacienteUrl}">Crear un nuevo paciente</a>.`;
                document.getElementById('no-pacientes-message').style.display = 'block';
                createCitaModal.style.display = 'block';
            });
    }

    // Manejar envío del formulario con AJAX
    createCitaForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = new FormData(createCitaForm);
        
        fetch('/nueva-cita', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.message || 'Error en la solicitud');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                createCitaModal.style.display = 'none';
                createCitaForm.reset();
                renderCalendar(); // Refrescar el calendario
                alert(data.message);
                window.location.href = data.redirect;
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error al crear cita:', error);
            alert(`Error al crear la cita: ${error.message}`);
        });
    });

    // Actualizar duración cuando se selecciona un tipo de cita
    tipoCitaSelect.addEventListener('change', () => {
        const selectedOption = tipoCitaSelect.options[tipoCitaSelect.selectedIndex];
        duracionInput.value = selectedOption ? selectedOption.dataset.duracion || '' : '';
    });
    
    
    function loadAppointments() {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth() + 1; // JavaScript meses son 0-11, API espera 1-12
        
        fetch(`/api/citas?year=${year}&month=${month}`)
            .then(response => response.json())
            .then(citas => {
                // Agrupar citas por fecha
                const citasPorFecha = {};
                
                citas.forEach(cita => {
                    // Extraer solo la fecha (sin hora)
                    const fecha = cita.fecha.split('T')[0];
                    
                    if (!citasPorFecha[fecha]) {
                        citasPorFecha[fecha] = [];
                    }
                    
                    citasPorFecha[fecha].push(cita);
                });
                
                // Añadir citas al calendario
                Object.keys(citasPorFecha).forEach(fecha => {
                    const dayElement = document.querySelector(`.calendar-day[data-date="${fecha}"]`);
                    
                    if (dayElement) {
                        const eventsContainer = dayElement.querySelector('.day-events');
                        
                        citasPorFecha[fecha].forEach(cita => {
                            const eventElement = document.createElement('div');
                            eventElement.className = 'event';
                            
                            // Verificar si la cita ya pasó
                            const citaFecha = new Date(cita.fecha);
                            const ahora = new Date();
                            
                            if (citaFecha < ahora) {
                                // Si la cita ya pasó, agregar clase para estilo verde
                                eventElement.classList.add('event-past');
                                
                                // Si además su status es "Completada", darle un estilo especial
                                if (cita.status === 'Completada') {
                                    eventElement.classList.add('event-completed');
                                }
                            } else {
                                // Si la cita es futura, aplicar clases según su status
                                if (cita.status === 'Cancelada') {
                                    eventElement.classList.add('event-cancelled');
                                } else if (cita.status === 'Reprogramada') {
                                    eventElement.classList.add('event-rescheduled');
                                } else {
                                    eventElement.classList.add('event-upcoming');
                                }
                            }
                            
                            // Formatear hora
                            const hora = citaFecha.toLocaleTimeString('es-ES', {
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                            
                            eventElement.textContent = `${hora} - ${cita.paciente_nombre}`;
                            eventElement.dataset.citaId = cita.id;
                            
                            // Añadir listener para mostrar detalles al hacer clic
                            eventElement.addEventListener('click', () => {
                                showAppointmentDetails(cita.id);
                            });
                            
                            eventsContainer.appendChild(eventElement);
                        });
                    }
                });
            })
            .catch(error => {
                console.error('Error al cargar las citas:', error);
            });
    }


    
    function showAppointmentDetails(citaId) {
        // Guardar ID de la cita actual
        currentCitaId = citaId;
        
        // Mostrar spinner o indicador de carga
        document.getElementById('cita-details').innerHTML = '<p>Cargando detalles...</p>';
        citaModal.style.display = 'block';
        
        // Cargar detalles de la cita
        fetch(`/api/cita/${citaId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const cita = data.cita;
                    
                    // Formatear fecha y hora
                    const fechaHora = new Date(cita.fecha);
                    const fechaFormateada = fechaHora.toLocaleDateString('es-ES', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric'
                    });
                    const horaFormateada = fechaHora.toLocaleTimeString('es-ES', {
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    
                    // Construir HTML para los detalles
                    let detailsHTML = `
                        <div><span class="cita-label">Paciente:</span> ${cita.paciente}</div>
                        <div><span class="cita-label">Fecha:</span> ${fechaFormateada}</div>
                        <div><span class="cita-label">Hora:</span> ${horaFormateada}</div>
                        <div><span class="cita-label">Duración:</span> ${cita.duracion} minutos</div>
                        <div><span class="cita-label">Motivo:</span> ${cita.tipo}</div>
                        <div><span class="cita-label">Status:</span> ${cita.status}</div>
                    `;
                    
                    if (cita.motivo) {
                        detailsHTML += `<div><span class="cita-label">Motivo:</span> ${cita.motivo}</div>`;
                    }
                    
                    if (cita.notas) {
                        detailsHTML += `<div><span class="cita-label">Notas:</span> ${cita.notas}</div>`;
                    }
                    
                    document.getElementById('cita-details').innerHTML = detailsHTML;
                } else {
                    document.getElementById('cita-details').innerHTML = '<p>No se pudieron cargar los detalles de la cita.</p>';
                }
            })
            .catch(error => {
                console.error('Error al cargar los detalles de la cita:', error);
                document.getElementById('cita-details').innerHTML = '<p>Error al cargar los detalles. Inténtalo de nuevo.</p>';
            });
    }
    
    function eliminarCita(citaId) {
        // Crear datos para enviar
        const formData = new FormData();
        
        // Realizar la petición para eliminar
        fetch(`/api/cita/${citaId}/eliminar`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Cerrar modal
                citaModal.style.display = 'none';
                
                // Actualizar calendario
                renderCalendar();
                
                // Mostrar mensaje de éxito
                alert('Cita eliminada correctamente');
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error al eliminar la cita:', error);
            alert('Error al eliminar la cita. Inténtalo de nuevo.');
        });
    }
});