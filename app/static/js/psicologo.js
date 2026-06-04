// Script para integrar Google Calendar en tu aplicación
document.addEventListener("DOMContentLoaded", function () {
    // Referencias a elementos DOM
    const calendarGrid = document.querySelector(".calendar-grid");
    const currentMonthElement = document.getElementById("current-month");
    const prevMonthButton = document.getElementById("prev-month");
    const nextMonthButton = document.getElementById("next-month");
    const todayButton = document.getElementById("today-btn");
    
    // Referencias a elementos de tabs y botones de navegación
    const calendarTab = document.getElementById("calendar-tab");
    const patientsTab = document.getElementById("patients-tab");
    const calendarTabBtn = document.getElementById("calendar-tab-btn");
    const patientsTabBtn = document.getElementById("patients-tab-btn");
    
    // ID de cliente OAuth2 de Google (deberás obtener esto de Google Cloud Console)
    const CLIENT_ID = '808058535566-646gp8htci7bjamup1gn9jlf5hst607b.apps.googleusercontent.com';
    const API_KEY = 'AIzaSyBYWkxF4zddtZsWKwRJWpPhs5NqJzOQjj8';
    
    // Ámbitos de autorización para Google Calendar
    const SCOPES = 'https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events';
    
    // Variable para el cliente de API de Google
    let gapiInited = false;
    let gisInited = false;
    let tokenClient;
    
    // Mapa para convertir status de citas a colores de Google Calendar
    const statusColorMap = {
        'programada': '1', // Azul
        'completada': '10', // Verde
        'cancelada': '11', // Rojo
        'ausente': '6',    // Naranja
        'en espera': '7'    // Turquesa
    };
    
    // Cargar las bibliotecas de cliente de la API de Google
    function loadGoogleLibraries() {
        const scriptGapi = document.createElement('script');
        scriptGapi.src = 'https://apis.google.com/js/api.js';
        scriptGapi.onload = () => {
            gapi.load('client', initializeGapiClient);
        };
        document.head.appendChild(scriptGapi);
        
        const scriptGis = document.createElement('script');
        scriptGis.src = 'https://accounts.google.com/gsi/client';
        scriptGis.onload = () => initializeGisClient();
        document.head.appendChild(scriptGis);
    }
    
    // Inicializar cliente GAPI
    async function initializeGapiClient() {
        await gapi.client.init({
            apiKey: API_KEY,
            discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest'],
        });
        gapiInited = true;
        maybeEnableButtons();
    }
    
    // Inicializar cliente GIS
    function initializeGisClient() {
        tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: CLIENT_ID,
            scope: SCOPES,
            callback: '', // Será definido en el momento de la llamada
        });
        gisInited = true;
        maybeEnableButtons();
    }
    
    // Habilitar botones cuando las bibliotecas estén cargadas
    function maybeEnableButtons() {
        if (gapiInited && gisInited) {
            // Añadir un botón para autenticarse con Google si el usuario aún no está autenticado
            const authButton = document.createElement('button');
            authButton.className = 'btn btn-primary';
            authButton.textContent = 'Conectar con Google Calendar';
            authButton.id = 'authorize_button';
            authButton.addEventListener('click', handleAuthClick);
            
            const calendarControls = document.querySelector('.calendar-controls');
            if (calendarControls) {
                calendarControls.appendChild(authButton);
            }
        }
    }
    
    // Manejar clic en el botón de autorización
    function handleAuthClick() {
        tokenClient.callback = async (resp) => {
            if (resp.error !== undefined) {
                console.error('Error de autorización:', resp);
                return;
            }
            document.getElementById('authorize_button').style.display = 'none';
            
            // Cargar eventos
            loadGoogleCalendarEvents();
        };
        
        // Solicitar token
        if (gapi.client.getToken() === null) {
            tokenClient.requestAccessToken({ prompt: 'consent' });
        } else {
            tokenClient.requestAccessToken({ prompt: '' });
        }
    }
    
    // Cargar eventos del calendario de Google
    async function loadGoogleCalendarEvents() {
        try {
            // Obtener fecha de inicio y fin del mes actual
            const currentDate = new Date();
            const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
            const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
            
            // Formatear fechas como lo espera la API de Google
            const timeMin = firstDay.toISOString();
            const timeMax = lastDay.toISOString();
            
            // Solicitar eventos
            const response = await gapi.client.calendar.events.list({
                'calendarId': 'primary',
                'timeMin': timeMin,
                'timeMax': timeMax,
                'showDeleted': false,
                'singleEvents': true,
                'orderBy': 'startTime'
            });
            
            const events = response.result.items;
            displayGoogleCalendarEvents(events);
            
            // Actualizar el texto del mes
            const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
            currentMonthElement.textContent = `${monthNames[currentDate.getMonth()]} ${currentDate.getFullYear()}`;
            
        } catch (error) {
            console.error('Error al cargar eventos:', error);
        }
    }
    
    // Mostrar eventos del calendario de Google
    function displayGoogleCalendarEvents(events) {
        // Primero, renderizar el esqueleto del calendario
        renderCalendarGrid();
        
        // Luego, añadir los eventos
        events.forEach(event => {
            const startDateTime = new Date(event.start.dateTime || event.start.date);
            const day = startDateTime.getDate();
            
            // Encontrar la celda del día correspondiente
            const dayCell = document.querySelector(`.calendar-day:not(.other-month) .day-number[data-day="${day}"]`)?.parentNode;
            
            if (dayCell) {
                // Crear elemento para el evento
                const eventDiv = document.createElement('div');
                eventDiv.classList.add('appointment');
                
                // Determinar status/color del evento
                let eventColor = event.colorId || '1'; // Por defecto, azul (programada)
                
                // Aplicar clase según el color
                if (eventColor === '1') { // Azul
                    eventDiv.classList.add('appointment-scheduled');
                } else if (eventColor === '10') { // Verde
                    eventDiv.classList.add('appointment-completed');
                } else if (eventColor === '11') { // Rojo
                    eventDiv.classList.add('appointment-cancelled');
                } else if (eventColor === '6') { // Naranja
                    eventDiv.classList.add('appointment-missed');
                } else if (eventColor === '7') { // Turquesa/Celeste
                    eventDiv.classList.add('appointment-waiting');
                }
                
                // Formatear hora
                let eventTime = '';
                if (event.start.dateTime) {
                    const hours = startDateTime.getHours().toString().padStart(2, '0');
                    const minutes = startDateTime.getMinutes().toString().padStart(2, '0');
                    eventTime = `${hours}:${minutes} - `;
                }
                
                // Añadir contenido
                eventDiv.textContent = `${eventTime}${event.summary}`;
                
                // Añadir evento de clic para ver detalles
                eventDiv.addEventListener('click', () => viewGoogleEventDetails(event));
                
                // Añadir a la celda del día
                dayCell.appendChild(eventDiv);
            }
        });
    }
    
    // Crear el esqueleto del calendario
    function renderCalendarGrid() {
        // Limpiar el calendario (dejamos los encabezados de día)
        const dayHeaders = Array.from(document.querySelectorAll(".calendar-day-header"));
        while (calendarGrid.childElementCount > dayHeaders.length) {
            calendarGrid.removeChild(calendarGrid.lastChild);
        }
        
        // Fecha actual
        const currentDate = new Date();
        
        // Primer día del mes
        const firstDayOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
        
        // Último día del mes
        const lastDayOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
        
        // Día de la semana del primer día (0 = Domingo, 1 = Lunes, etc.)
        let firstDayOfWeek = firstDayOfMonth.getDay();
        
        // Calcular días del mes anterior para completar la primera semana
        const daysFromPrevMonth = firstDayOfWeek;
        
        // Obtener el último día del mes anterior
        const lastDayOfPrevMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 0);
        
        // Crear celdas para los días del mes anterior (si los hay)
        for (let i = daysFromPrevMonth - 1; i >= 0; i--) {
            const dayDiv = document.createElement("div");
            dayDiv.classList.add("calendar-day", "other-month");
            
            const dayNumber = lastDayOfPrevMonth.getDate() - i;
            const dayNumberSpan = document.createElement("span");
            dayNumberSpan.className = "day-number";
            dayNumberSpan.textContent = dayNumber;
            dayDiv.appendChild(dayNumberSpan);
            
            calendarGrid.appendChild(dayDiv);
        }
        
        // Fecha actual para comparar
        const today = new Date();
        const isCurrentMonth = today.getMonth() === currentDate.getMonth() && today.getFullYear() === currentDate.getFullYear();
        
        // Crear celdas para los días del mes actual
        for (let day = 1; day <= lastDayOfMonth.getDate(); day++) {
            const dayDiv = document.createElement("div");
            dayDiv.classList.add("calendar-day");
            
            // Añadir clase "today" si es el día actual
            if (isCurrentMonth && day === today.getDate()) {
                dayDiv.classList.add("today");
            }
            
            // Añadir número del día con atributo data-day para facilitar búsqueda
            const dayNumberSpan = document.createElement("span");
            dayNumberSpan.className = "day-number";
            dayNumberSpan.textContent = day;
            dayNumberSpan.setAttribute("data-day", day);
            dayDiv.appendChild(dayNumberSpan);
            
            // Añadir la celda del día al calendario
            calendarGrid.appendChild(dayDiv);
        }
        
        // Calcular cuántos días del mes siguiente necesitamos
        const totalDaysAdded = daysFromPrevMonth + lastDayOfMonth.getDate();
        const remainingDays = 42 - totalDaysAdded; // 42 = 6 semanas * 7 días
        
        // Añadir días del mes siguiente
        for (let i = 1; i <= remainingDays; i++) {
            const dayDiv = document.createElement("div");
            dayDiv.classList.add("calendar-day", "other-month");
            
            const dayNumberSpan = document.createElement("span");
            dayNumberSpan.className = "day-number";
            dayNumberSpan.textContent = i;
            dayDiv.appendChild(dayNumberSpan);
            
            calendarGrid.appendChild(dayDiv);
        }
    }
    
    // Ver detalles de un evento de Google
    function viewGoogleEventDetails(event) {
        // Crear o actualizar el modal
        let modalElement = document.getElementById("event-details-modal");
        
        // Si el modal no existe, crearlo
        if (!modalElement) {
            modalElement = document.createElement("div");
            modalElement.id = "event-details-modal";
            modalElement.className = "modal";
            document.body.appendChild(modalElement);
        }
        
        // Formatear fechas
        const startDateTime = new Date(event.start.dateTime || event.start.date);
        const endDateTime = new Date(event.end.dateTime || event.end.date);
        
        let dateTimeFormatted = '';
        
        // Si es un evento de todo el día
        if (!event.start.dateTime) {
            dateTimeFormatted = `${startDateTime.getDate().toString().padStart(2, "0")}/${(startDateTime.getMonth() + 1).toString().padStart(2, "0")}/${startDateTime.getFullYear()} (Todo el día)`;
        } else {
            // Si es un evento con hora específica
            const startFormatted = `${startDateTime.getDate().toString().padStart(2, "0")}/${(startDateTime.getMonth() + 1).toString().padStart(2, "0")}/${startDateTime.getFullYear()} ${startDateTime.getHours().toString().padStart(2, "0")}:${startDateTime.getMinutes().toString().padStart(2, "0")}`;
            const endFormatted = `${endDateTime.getHours().toString().padStart(2, "0")}:${endDateTime.getMinutes().toString().padStart(2, "0")}`;
            dateTimeFormatted = `${startFormatted} - ${endFormatted}`;
        }
        
        // Determinar el status según el colorId
        let statusClass = 'status-scheduled';
        let statusText = 'Programada';
        
        if (event.colorId === '10') {
            statusClass = 'status-completed';
            statusText = 'Completada';
        } else if (event.colorId === '11') {
            statusClass = 'status-cancelled';
            statusText = 'Cancelada';
        } else if (event.colorId === '6') {
            statusClass = 'status-missed';
            statusText = 'Ausente';
        } else if (event.colorId === '7') {
            statusClass = 'status-waiting';
            statusText = 'En Espera';
        }
        
        // Actualizar el contenido del modal
        modalElement.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Detalles del Evento</h3>
                    <button class="close-modal" onclick="closeEventModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <p><strong>Título:</strong> ${event.summary}</p>
                    <p><strong>Fecha:</strong> ${dateTimeFormatted}</p>
                    <p><strong>Status:</strong> <span class="status-badge ${statusClass}">${statusText}</span></p>
                    ${event.description ? `<p><strong>Descripción:</strong> ${event.description}</p>` : ''}
                    ${event.location ? `<p><strong>Ubicación:</strong> ${event.location}</p>` : ''}
                </div>
                <div class="modal-footer">
                    <a href="${event.htmlLink}" target="_blank" class="btn btn-primary">Ver en Google Calendar</a>
                    <button class="btn btn-secondary" onclick="closeEventModal()">Cerrar</button>
                </div>
            </div>
        `;
        
        // Definir la función para cerrar el modal en el ámbito global
        window.closeEventModal = function() {
            modalElement.classList.remove("active");
        };
        
        // Mostrar el modal
        modalElement.classList.add("active");
    }
    
    // Función para sincronizar una cita con Google Calendar
    async function createGoogleCalendarEvent(cita, paciente) {
        // Verificar que estamos autenticados
        if (!gapi.client.getToken()) {
            alert('Por favor, conéctate a Google Calendar primero');
            return;
        }
        
        // Fecha y hora de la cita
        const fechaInicio = new Date(cita.fecha);
        
        // Calcular fecha fin (sumando la duración en minutos)
        const fechaFin = new Date(fechaInicio.getTime() + (cita.duracion * 60 * 1000));
        
        // Determinar color según status
        const colorId = statusColorMap[cita.status.toLowerCase()] || '1';
        
        // Construir el evento
        const event = {
            'summary': `Cita: ${paciente.nombre} ${paciente.apellido}`,
            'description': cita.motivo + (cita.notas ? `\n\nNotas: ${cita.notas}` : ''),
            'start': {
                'dateTime': fechaInicio.toISOString(),
                'timeZone': 'America/Mexico_City' // Ajustar según tu zona horaria
            },
            'end': {
                'dateTime': fechaFin.toISOString(),
                'timeZone': 'America/Mexico_City' // Ajustar según tu zona horaria
            },
            'colorId': colorId
        };
        
        try {
            // Crear el evento en Google Calendar
            const response = await gapi.client.calendar.events.insert({
                'calendarId': 'primary',
                'resource': event
            });
            
            // Devolver el ID del evento creado para posible almacenamiento
            return response.result.id;
        } catch (error) {
            console.error('Error al crear evento en Google Calendar:', error);
            throw error;
        }
    }
    
    // Función para actualizar un evento en Google Calendar
    async function updateGoogleCalendarEvent(eventId, cita, paciente) {
        // Verificar que estamos autenticados
        if (!gapi.client.getToken()) {
            alert('Por favor, conéctate a Google Calendar primero');
            return;
        }
        
        // Fecha y hora de la cita
        const fechaInicio = new Date(cita.fecha);
        
        // Calcular fecha fin (sumando la duración en minutos)
        const fechaFin = new Date(fechaInicio.getTime() + (cita.duracion * 60 * 1000));
        
        // Determinar color según status
        const colorId = statusColorMap[cita.status.toLowerCase()] || '1';
        
        // Construir el evento
        const event = {
            'summary': `Cita: ${paciente.nombre} ${paciente.apellido}`,
            'description': cita.motivo + (cita.notas ? `\n\nNotas: ${cita.notas}` : ''),
            'start': {
                'dateTime': fechaInicio.toISOString(),
                'timeZone': 'America/Mexico_City' // Ajustar según tu zona horaria
            },
            'end': {
                'dateTime': fechaFin.toISOString(),
                'timeZone': 'America/Mexico_City' // Ajustar según tu zona horaria
            },
            'colorId': colorId
        };
        
        try {
            // Actualizar el evento en Google Calendar
            await gapi.client.calendar.events.update({
                'calendarId': 'primary',
                'eventId': eventId,
                'resource': event
            });
            
            return true;
        } catch (error) {
            console.error('Error al actualizar evento en Google Calendar:', error);
            throw error;
        }
    }
    
    // Event Listeners para cambiar de mes
    if (prevMonthButton) {
        prevMonthButton.addEventListener("click", function() {
            const currentDate = new Date();
            currentDate.setMonth(currentDate.getMonth() - 1);
            loadGoogleCalendarEvents();
        });
    }
    
    if (nextMonthButton) {
        nextMonthButton.addEventListener("click", function() {
            const currentDate = new Date();
            currentDate.setMonth(currentDate.getMonth() + 1);
            loadGoogleCalendarEvents();
        });
    }
    
    if (todayButton) {
        todayButton.addEventListener("click", function() {
            loadGoogleCalendarEvents();
        });
    }
    
    // Configurar el evento para redirigir a la página de pacientes
    if (patientsTab) {
        patientsTab.addEventListener("click", function(event) {
            event.preventDefault();
            window.location.href = "/pacientes";
        });
    }
    
    // Si tenemos el botón del menú lateral de pacientes, lo configuramos también
    if (patientsTabBtn) {
        patientsTabBtn.addEventListener("click", function(event) {
            // Evitar comportamiento predeterminado en caso de que ya tenga un href
            event.preventDefault();
            window.location.href = "/pacientes";
        });
    }
    
    // Inicializar la carga de las bibliotecas de Google
    loadGoogleLibraries();
    
    // Exportar funciones para uso global
    window.createGoogleCalendarEvent = createGoogleCalendarEvent;
    window.updateGoogleCalendarEvent = updateGoogleCalendarEvent;
});