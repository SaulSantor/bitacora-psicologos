document.addEventListener("DOMContentLoaded", function () {
    // Referencias a elementos del DOM
    const searchInput = document.getElementById("searchAppointment");
    const filterForm = document.getElementById("filterForm");
    const historyList = document.getElementById("history-list");
    const pageSizeSelect = document.getElementById("page-size");
    const prevPageBtn = document.getElementById("prev-page");
    const nextPageBtn = document.getElementById("next-page");
    const currentPageSpan = document.getElementById("current-page");
    const totalPagesSpan = document.getElementById("total-pages");
    const exportBtn = document.getElementById("exportBtn");
    const tipoSelect = document.getElementById("history-type"); // Cambiado a "history-type"

    // Variables de paginación
    let currentPage = 1;
    let pageSize = parseInt(pageSizeSelect ? pageSizeSelect.value : 10);
    let allAppointments = [];
    let filteredAppointments = [];
    let tiposCita = []; // Array para almacenar los tipos de cita

    // Función mejorada para cargar tipos de cita con mejor manejo de errores
    async function loadTiposCita() {
        try {
            
            // Establecer un valor predeterminado para tiposCita
            tiposCita = [];
            
            // Intentar cargar desde la API con timeout de 5 segundos
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            try {
                const response = await fetch("/api/tipos-cita", {
                    signal: controller.signal,
                    headers: {
                        'Cache-Control': 'no-cache',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`Error al cargar tipos de cita: ${response.status}`);
                }

                const data = await response.json();
                
                // Verificar que data es un array
                if (Array.isArray(data)) {
                    tiposCita = data;
                } else {
                    console.warn("Los datos recibidos no son un array:", data);
                    tiposCita = [];
                }
            } catch (fetchError) {
                clearTimeout(timeoutId);
                console.warn("Error en fetch de tipos de cita:", fetchError);
                
                // Usar tipos predefinidos como fallback
                tiposCita = getDefaultTiposCita();
            }
            
            // Poblar el select con ID "history-type"
            if (tipoSelect) {
                
                // Guardar valores actuales para debugging
                const currentValues = {};
                for (let i = 0; i < tipoSelect.options.length; i++) {
                    currentValues[tipoSelect.options[i].value] = tipoSelect.options[i].textContent;
                }
                
                // Guardar el valor seleccionado actualmente
                const selectedValue = tipoSelect.value;
                
                // Preservar la primera opción ("Todos los tipos")
                const defaultOption = tipoSelect.options[0];
                
                // Limpiar opciones actuales
                tipoSelect.innerHTML = '';
                
                // Restaurar la opción de "Todos los tipos"
                tipoSelect.appendChild(defaultOption);
                
                // Crear y agregar opciones para cada tipo de cita
                tiposCita.forEach(tipo => {
                    try {
                        const option = document.createElement('option');
                        
                        // IMPORTANTE: Verificar si estamos usando IDs o nombres como valores
                        // Vamos a intentar usar la misma estrategia que las opciones existentes
                        if (Object.values(currentValues).some(val => !isNaN(parseInt(val)))) {
                            // Parece que estamos usando IDs como valores
                            option.value = tipo.id; 
                        } else {
                            // Parece que estamos usando nombres como valores
                            option.value = tipo.nombre;
                        }
                        
                        option.textContent = tipo.nombre;
                        tipoSelect.appendChild(option);
                        
                    } catch (optionError) {
                        console.error(`Error al añadir opción para tipo ${JSON.stringify(tipo)}:`, optionError);
                    }
                });
                
                // Restaurar el valor seleccionado si existía
                if (selectedValue) {
                    tipoSelect.value = selectedValue;
                }
                
                // Verificar valores finales
                const finalValues = {};
                for (let i = 0; i < tipoSelect.options.length; i++) {
                    finalValues[tipoSelect.options[i].value] = tipoSelect.options[i].textContent;
                }
            } else {
                console.warn("No se encontró el elemento select con ID 'history-type'");
            }
        } catch (error) {
            console.error("Error general al cargar tipos de cita:", error);
            // No interrumpir el flujo de la aplicación
        }
    }

    // Función que proporciona tipos de cita predeterminados como respaldo
    function getDefaultTiposCita() {
        return [
            { id: 1, nombre: "Primera Consulta", color: "#4e73df", duracion: 60 },
            { id: 2, nombre: "Consulta Regular", color: "#1cc88a", duracion: 50 },
            { id: 3, nombre: "Seguimiento", color: "#36b9cc", duracion: 30 },
            { id: 4, nombre: "Urgencia", color: "#e74a3b", duracion: 60 },
            { id: 5, nombre: "Evaluación", color: "#f6c23e", duracion: 90 }
        ];
    }

    // Registrar eventos
    if (searchInput) {
        searchInput.addEventListener("keyup", function (e) {
            if (e.key === "Enter") {
                filterAppointments();
            }
        });
    }

    if (filterForm) {
        filterForm.addEventListener("submit", function (e) {
            e.preventDefault();
            filterAppointments();
        });
    }

    if (pageSizeSelect) {
        pageSizeSelect.addEventListener("change", function () {
            pageSize = parseInt(this.value);
            currentPage = 1;
            updatePagination();
            displayAppointments();
        });
    }

    if (prevPageBtn) {
        prevPageBtn.addEventListener("click", function () {
            if (currentPage > 1) {
                currentPage--;
                updatePagination();
                displayAppointments();
            }
        });
    }

    if (nextPageBtn) {
        nextPageBtn.addEventListener("click", function () {
            if (
                currentPage < Math.ceil(filteredAppointments.length / pageSize)
            ) {
                currentPage++;
                updatePagination();
                displayAppointments();
            }
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener("click", exportToCSV);
    }

    // Función unificada para filtrar citas
    function filterAppointments() {
        // Mostrar indicador de carga
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'loading-indicator';
        loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000;';
        loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Filtrando citas...</div>';
        document.body.appendChild(loadingIndicator);

        try {
            // Obtener términos de filtro
            const searchTerm = searchInput ? searchInput.value.toLowerCase() : "";
            const formData = new FormData(filterForm);

            // Obtener valores de los filtros
            const fromDate = formData.get("from_date")
                ? new Date(formData.get("from_date"))
                : null;
            const toDate = formData.get("to_date")
                ? new Date(formData.get("to_date"))
                : null;
            const pacienteId = formData.get("paciente_id");
            const tipoCitaId = formData.get("tipo");
            const statusFilter = formData.get("status");

            if (allAppointments.length === 0) {
                console.warn("No hay citas para filtrar - cargando datos primero");
                loadAppointmentsFromAPI().then(() => {
                    applyFilters();
                });
                return;
            }

            applyFilters();

            function applyFilters() {
                // Filtrar las citas según los criterios
                filteredAppointments = allAppointments.filter((appointment) => {
                    // Filtrar por término de búsqueda
                    const searchContent =
                        `${appointment.paciente || ''} ${appointment.tipo || ''} ${appointment.notas || ''}`.toLowerCase();
                    if (searchTerm && !searchContent.includes(searchTerm)) return false;

                    // Filtrar por fechas
                    if (fromDate && new Date(appointment.fecha) < fromDate)
                        return false;
                    if (toDate) {
                        const adjustedToDate = new Date(toDate);
                        adjustedToDate.setHours(23, 59, 59);
                        if (new Date(appointment.fecha) > adjustedToDate) return false;
                    }

                    // Filtrar por paciente
                    if (pacienteId && appointment.paciente_id != pacienteId)
                        return false;

                    // SOLUCIÓN MEJORADA: Filtrar por tipo de cita
                    if (tipoCitaId && tipoCitaId !== '') {
                        
                        // Verificar si el valor del filtro es el nombre del tipo o el ID
                        if (isNaN(parseInt(tipoCitaId))) {
                            // Es el nombre del tipo - comparar con el campo 'tipo'
                            if (appointment.tipo !== tipoCitaId) return false;
                        } else {
                            // Es el ID del tipo - comparar con el campo 'tipo_cita_id'
                            // Convertir ambos a número para comparación consistente
                            const tipoIdFilter = parseInt(tipoCitaId);
                            
                            // Si la cita tiene tipo_cita_id, convertirlo a número para comparar
                            let citaTipoId = null;
                            if (appointment.tipo_cita_id) {
                                citaTipoId = parseInt(appointment.tipo_cita_id);
                            }
                            
                            // Comparaciones más flexibles
                            if (citaTipoId !== tipoIdFilter) {
                                // Buscar el tipo de cita por ID para comparar por nombre
                                const tipoCita = tiposCita.find(t => parseInt(t.id) === tipoIdFilter);
                                if (tipoCita && tipoCita.nombre !== appointment.tipo) {
                                    return false;
                                }
                            }
                        }
                    }

                    // Filtrar por status
                    if (statusFilter && appointment.status !== statusFilter)
                        return false;

                    return true;
                });

                // Resetear a primera página y actualizar visualización
                currentPage = 1;
                updatePagination();
                displayAppointments();

                // Quitar indicador de carga
                document.body.removeChild(loadingIndicator);
            }
        } catch (error) {
            console.error("Error al filtrar citas:", error);
            showNotification("Error al aplicar filtros: " + error.message, "error");
            
            // Quitar indicador de carga en caso de error
            if (document.body.contains(loadingIndicator)) {
                document.body.removeChild(loadingIndicator);
            }
        }
    }

    // Función para actualizar datos de paginación
    function updatePagination() {
        if (totalPagesSpan) {
            totalPagesSpan.textContent =
                Math.ceil(filteredAppointments.length / pageSize) || 1;
        }
        if (currentPageSpan) {
            currentPageSpan.textContent = currentPage;
        }

        // Habilitar/deshabilitar botones de paginación
        if (prevPageBtn) {
            prevPageBtn.disabled = currentPage === 1;
        }
        if (nextPageBtn) {
            nextPageBtn.disabled =
                currentPage >=
                Math.ceil(filteredAppointments.length / pageSize);
        }
    }

    // Función para mostrar citas en la tabla
    function displayAppointments() {
        if (!historyList) {
            console.warn("No se encontró el elemento historyList");
            return;
        }
    
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const appointmentsToShow = filteredAppointments.slice(
            startIndex,
            endIndex
        );
    
        // Limpiar la tabla actual
        while (historyList.firstChild) {
            historyList.removeChild(historyList.firstChild);
        }
    
        // Si no hay citas para mostrar
        if (appointmentsToShow.length === 0) {
            const emptyRow = document.createElement('tr');
            const emptyCell = document.createElement('td');
            emptyCell.setAttribute('colspan', '8');
            emptyCell.className = 'text-center';
            emptyCell.textContent = 'No se encontraron citas que coincidan con los criterios de búsqueda';
            emptyRow.appendChild(emptyCell);
            historyList.appendChild(emptyRow);
            return;
        }
    
        // Mostrar las citas en la tabla
        appointmentsToShow.forEach(appointment => {
            // Crear fila
            const row = document.createElement('tr');
            
            // Formatear fecha
            const fecha = new Date(appointment.fecha);
            const fechaFormateada = `${fecha.getDate().toString().padStart(2, '0')}/${(fecha.getMonth() + 1).toString().padStart(2, '0')}/${fecha.getFullYear()}`;
            const horaFormateada = `${fecha.getHours().toString().padStart(2, '0')}:${fecha.getMinutes().toString().padStart(2, '0')}`;
            
            // Crear celdas para cada columna
            const createCell = (content, className = '') => {
                const cell = document.createElement('td');
                if (className) cell.className = className;
                cell.innerHTML = content;
                return cell;
            };
            
            // Celda de fecha
            row.appendChild(createCell(fechaFormateada));
            
            // Celda de hora
            row.appendChild(createCell(horaFormateada));
            
            // Celda de paciente - SOLUCIÓN MEJORADA
            let pacienteNombre = "No especificado";
            
            // Intentar obtener el nombre del paciente de diferentes propiedades posibles
            if (appointment.paciente && typeof appointment.paciente === 'string' && appointment.paciente.trim() !== '') {
                pacienteNombre = appointment.paciente;
            } else if (appointment.paciente_nombre && typeof appointment.paciente_nombre === 'string') {
                pacienteNombre = appointment.paciente_nombre;
            } else if (appointment.nombre_paciente && typeof appointment.nombre_paciente === 'string') {
                pacienteNombre = appointment.nombre_paciente;
            }
            
            row.appendChild(createCell(pacienteNombre));
            
            // === SOLUCIÓN PARA EL PROBLEMA DEL FILTRO DE TIPOS ===
            
            // Buscar y mostrar el nombre del tipo de cita correctamente
            let tipoNombre = "No especificado";
            let tipoStyle = '';
            
            // Primero intentar con tipo_cita_id
            if (appointment.tipo_cita_id) {
                // Convertir a número para comparación consistente
                const tipoId = parseInt(appointment.tipo_cita_id);
                const tipoCita = tiposCita.find(t => parseInt(t.id) === tipoId);
                
                if (tipoCita) {
                    tipoNombre = tipoCita.nombre;
                    if (tipoCita.color) {
                        tipoStyle = `style="color: ${tipoCita.color}; font-weight: bold;"`;
                    }
                }
            } 
            // Si no hay tipo_cita_id, usar el campo tipo si existe
            else if (appointment.tipo && typeof appointment.tipo === 'string' && appointment.tipo.trim() !== '') {
                tipoNombre = appointment.tipo;
                
                // Buscar si hay alguna coincidencia por nombre en los tipos cargados
                const tipoCita = tiposCita.find(t => t.nombre === appointment.tipo);
                if (tipoCita && tipoCita.color) {
                    tipoStyle = `style="color: ${tipoCita.color}; font-weight: bold;"`;
                }
            }
            
            // Celda de tipo de cita
            row.appendChild(createCell(`<span ${tipoStyle}>${tipoNombre}</span>`));
            
            // Celda de status con badge
            let statusHTML = appointment.status || 'No definido';
            if (appointment.status) {
                let badgeClass = '';
                switch (appointment.status.toLowerCase()) {
                    case 'completada':
                        badgeClass = 'status-vigente'; // Verde
                        break;
                    case 'programada':
                        badgeClass = 'status-waiting'; // Azul
                        break;
                    case 'cancelada':
                        badgeClass = 'status-urgencia'; // Rojo
                        break;
                    case 'reprogramada':
                        badgeClass = 'status-orientacion'; // Amarillo
                        break;
                }
                if (badgeClass) {
                    statusHTML = `<span class="status-badge ${badgeClass}">${appointment.status}</span>`;
                }
            }
            row.appendChild(createCell(statusHTML));
            
            // Celda de notas (truncadas)
            const notasText = appointment.notas && typeof appointment.notas === 'string' && appointment.notas.trim() !== '' 
                ? (appointment.notas.length > 50 
                    ? appointment.notas.substring(0, 47) + '...' 
                    : appointment.notas) 
                : 'Sin notas';
            row.appendChild(createCell(notasText));
            
            // Celda de acciones
            const actionsCell = document.createElement('td');
            actionsCell.className = 'actions-cell';
            
            // Botón ver
            const viewBtn = document.createElement('button');
            viewBtn.className = 'view-btn';
            viewBtn.title = 'Ver detalles';
            viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
            viewBtn.onclick = function() { viewAppointmentDetails(appointment.id); };
            actionsCell.appendChild(viewBtn);
            
            // Botón editar
            const editBtn = document.createElement('button');
            editBtn.className = 'edit-btn';
            editBtn.title = 'Editar';
            editBtn.innerHTML = '<i class="fas fa-edit"></i>';
            editBtn.onclick = function() { editAppointment(appointment.id); };
            actionsCell.appendChild(editBtn);
            
            // Botón notas
            const notesBtn = document.createElement('button');
            notesBtn.className = 'notes-btn';
            notesBtn.title = 'Notas';
            notesBtn.innerHTML = '<i class="fas fa-clipboard"></i>';
            notesBtn.onclick = function() { showAppointmentNotes(appointment.id); };
            actionsCell.appendChild(notesBtn);
            
            // Botón eliminar
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-btn';
            deleteBtn.title = 'Eliminar';
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.onclick = function() { confirmDeleteAppointment(appointment.id); };
            actionsCell.appendChild(deleteBtn);
            
            row.appendChild(actionsCell);
            
            // Añadir fila a la tabla
            historyList.appendChild(row);
        });
        
        // Actualizar paginación
        updatePagination();
    }

    // Cargar citas desde la API
    async function loadAppointmentsFromAPI() {
        try {
            const loadingIndicator = document.createElement('div');
            loadingIndicator.id = 'loading-indicator';
            loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000;';
            loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Cargando citas...</div>';
            document.body.appendChild(loadingIndicator);

            const response = await fetch("/api/citas");
            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            console.log("Datos de citas recibidos:", data);
            
            if (Array.isArray(data)) {
                allAppointments = data.map(appointment => {
                    return {
                        id: appointment.id,
                        fecha: appointment.fecha,
                        paciente: appointment.paciente_nombre || appointment.paciente || 'Sin nombre',
                        paciente_id: appointment.paciente_id,
                        tipo: appointment.tipo,
                        tipo_cita_id: appointment.tipo_cita_id,
                        status: appointment.status,
                        notas: appointment.notas || ''
                    };
                });
                
                filteredAppointments = [...allAppointments];
                
                console.log("Citas procesadas:", allAppointments);
                
                updatePagination();
                displayAppointments();
                
                if (allAppointments.length === 0) {
                    console.warn("No se encontraron citas");
                    showNotification("No se encontraron citas", "info");
                }
            } else {
                console.error("Respuesta de API incorrecta:", data);
                showNotification("Error al cargar citas", "error");
                extractAppointmentsFromDOM();
            }
        } catch (error) {
            console.error("Error al cargar citas desde API:", error);
            showNotification("Error al cargar citas. Usando datos locales.", "warning");
            extractAppointmentsFromDOM();
        } finally {
            const loadingIndicator = document.getElementById('loading-indicator');
            if (loadingIndicator) {
                document.body.removeChild(loadingIndicator);
            }
        }
    }

    // Extraer datos de citas del DOM como respaldo
    function extractAppointmentsFromDOM() {
        if (!historyList) {
            console.warn("No se pudo encontrar la tabla de historial para extraer datos");
            return;
        }

        // Intentar extraer citas de las filas de la tabla
        const rows = historyList.querySelectorAll('tr');
        allAppointments = [];

        rows.forEach(row => {
            // Obtener celdas
            const cells = row.querySelectorAll('td');
            if (cells.length < 6) return; // Ignorar filas sin suficientes celdas
            
            // Extraer ID del botón de ver detalles
            const viewButton = row.querySelector('.view-btn');
            if (!viewButton) return;
            
            const onclickAttr = viewButton.getAttribute('onclick') || '';
            const idMatch = onclickAttr.match(/viewAppointmentDetails\(['"](\d+)['"]\)/);
            const id = idMatch ? idMatch[1] : null;
            
            if (!id) return;
            
            // Extraer fecha y hora
            const fechaText = cells[0].textContent.trim();
            const horaText = cells[1].textContent.trim();
            
            // Convertir a objeto Date
            const [dia, mes, anio] = fechaText.split('/').map(n => parseInt(n));
            const [hora, minuto] = horaText.split(':').map(n => parseInt(n));
            const fecha = new Date(anio, mes - 1, dia, hora, minuto);
            
            // Crear objeto de cita
            const cita = {
                id: id,
                fecha: fecha.toISOString(),
                paciente: cells[2].textContent.trim(),
                paciente_id: null, // No podemos extraer esto del DOM
                tipo: cells[3].textContent.trim(),
                tipo_cita_id: null, // No podemos extraer esto del DOM
                status: cells[4].textContent.trim(),
                notas: cells[5].textContent.trim(),
                duracion: 0 // No podemos extraer esto del DOM
            };
            
            allAppointments.push(cita);
        });

        filteredAppointments = [...allAppointments];
        
        // Actualizar UI
        updatePagination();
        displayAppointments();
    }

    // Función para exportar a CSV
    function exportToCSV() {
        if (filteredAppointments.length === 0) {
            showNotification("No hay datos para exportar", "warning");
            return;
        }

        // Construir cabeceras
        const headers = [
            "Fecha",
            "Hora",
            "Paciente",
            "Tipo",
            "Status",
            "Notas",
        ];

        // Construir filas de datos
        const rows = filteredAppointments.map((appointment) => {
            const date = new Date(appointment.fecha);
            
            // Obtener el nombre del tipo de cita
            let tipoNombre = appointment.tipo || "No especificado";
            if (appointment.tipo_cita_id) {
                const tipoCita = tiposCita.find(t => t.id == appointment.tipo_cita_id);
                if (tipoCita) {
                    tipoNombre = tipoCita.nombre;
                }
            }
            
            return [
                date.toLocaleDateString(),
                date.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                }),
                appointment.paciente || "No especificado",
                tipoNombre,
                appointment.status || "No especificado",
                (appointment.notas || "").replace(/"/g, '""'), // Escapar comillas dobles
            ];
        });

        // Combinar todo en formato CSV
        let csvContent = [
            headers.join(","),
            ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
        ].join("\n");

        // Crear un Blob y un enlace de descarga
        const blob = new Blob([csvContent], {
            type: "text/csv;charset=utf-8;",
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        // Configurar y simular clic en el enlace
        link.setAttribute("href", url);
        link.setAttribute(
            "download",
            `historial_citas_${new Date().toLocaleDateString()}.csv`
        );
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showNotification("Exportación completada exitosamente", "success");
    }

    // Inicializar datos de citas
    function initializeAppointmentsData() {
        // Cargar tipos de cita primero con manejo de errores
        loadTiposCita()
            .then(() => {
                // Verificar si se pudieron cargar tipos de cita
                if (tiposCita.length === 0) {
                    console.warn("No se pudieron cargar tipos de cita desde API, usando valores predefinidos");
                    // Usar tipos predeterminados
                    tiposCita = getDefaultTiposCita();
                    
                    // Actualizar el select si existe
                    if (tipoSelect) {
                        updateTiposCitaSelect();
                    }
                }
            })
            .catch(() => {
                console.warn("Error al cargar tipos de cita, usando valores predefinidos");
                // Usar tipos predeterminados
                tiposCita = getDefaultTiposCita();
                
                // Actualizar el select si existe
                if (tipoSelect) {
                    updateTiposCitaSelect();
                }
            })
            .finally(() => {
                // Luego cargar las citas
                loadAppointmentsFromAPI();
            });
    }

    // Función auxiliar para actualizar el select de tipos de cita
    function updateTiposCitaSelect() {
        if (!tipoSelect) return;
        
        // Guardar el valor seleccionado actualmente
        const selectedValue = tipoSelect.value;
        
        // Limpiar opciones actuales
        tipoSelect.innerHTML = '';
        
        // Agregar opción "Todos"
        const allOption = document.createElement('option');
        allOption.value = '';
        allOption.textContent = 'Todos los tipos';
        tipoSelect.appendChild(allOption);
        
        // Agregar las opciones de tipos de cita
        tiposCita.forEach(tipo => {
            const option = document.createElement('option');
            option.value = tipo.id;
            option.textContent = tipo.nombre;
            tipoSelect.appendChild(option);
        });
        
        // Restaurar el valor seleccionado si existía
        if (selectedValue) {
            tipoSelect.value = selectedValue;
        }
    }

    // Inicializar la página
    initializeAppointmentsData();
});

// Actualización de la función viewAppointmentDetails para agregar botón de editar
function viewAppointmentDetails(appointmentId) {
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'details-loading';
    loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000;';
    loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Cargando detalles...</div>';
    document.body.appendChild(loadingIndicator);

    console.log(`Intentando cargar detalles de cita con ID: ${appointmentId}`);

    fetch(`/api/cita/${appointmentId}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
        .then((response) => {
            console.log(`Respuesta del servidor: ${response.status}`);
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || `Error en la respuesta del servidor: ${response.status}`);
                }).catch(() => {
                    throw new Error(`Error en la respuesta del servidor: ${response.status}`);
                });
            }
            return response.json();
        })
        .then((data) => {
            document.body.removeChild(loadingIndicator);
            console.log('Datos de la cita:', data);

            if (!data.success) {
                throw new Error(data.message || 'Error al cargar detalles de la cita');
            }

            if (!data.cita) {
                throw new Error('No se encontraron datos de la cita en la respuesta');
            }

            const requiredFields = ['id', 'paciente', 'fecha', 'duracion', 'tipo', 'status'];
            const missingFields = requiredFields.filter(field => !(field in data.cita));
            if (missingFields.length > 0) {
                throw new Error(`Faltan campos en la respuesta: ${missingFields.join(', ')}`);
            }

            const appointmentDetailsContent = document.getElementById("appointment-details-content");
            if (!appointmentDetailsContent) {
                throw new Error("No se encontró el contenedor de detalles (appointment-details-content)");
            }

            let fechaFormateada = 'No especificada';
            let horaFormateada = 'No especificada';
            try {
                const fecha = new Date(data.cita.fecha);
                if (isNaN(fecha.getTime())) {
                    throw new Error('Fecha inválida en la respuesta');
                }
                fechaFormateada = fecha.toLocaleDateString();
                horaFormateada = fecha.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                });
            } catch (e) {
                console.warn('Error al formatear la fecha:', e.message);
            }

            const paciente = data.cita.paciente || 'No especificado';
            const duracion = data.cita.duracion || 0;
            const tipo = data.cita.tipo || 'No especificado';
            const status = data.cita.status || 'No especificado';
            const notas = data.cita.notas || 'No hay notas disponibles';

            appointmentDetailsContent.innerHTML = `
                <div class="appointment-detail">
                    <p><strong>Paciente:</strong> ${paciente}</p>
                    <p><strong>Fecha:</strong> ${fechaFormateada}</p>
                    <p><strong>Hora:</strong> ${horaFormateada}</p>
                    <p><strong>Duración:</strong> ${duracion} minutos</p>
                    <p><strong>Motivo:</strong> ${tipo}</p>
                    <p><strong>Status:</strong> ${status}</p>
                    <div>
                        <p><strong>Notas:</strong></p>
                        <div style="padding: 10px; background-color: #f8f9fa; border-radius: 4px; margin-top: 5px;">
                            ${notas}
                        </div>
                    </div>
                </div>
            `;

            openAppointmentModal();
        })
        .catch((error) => {
            document.body.removeChild(loadingIndicator);
            console.error("Error al cargar detalles de la cita:", error);
            showNotification(`Error al cargar detalles de la cita: ${error.message}`, "error");
        });
}

// Función para editar cita
function editAppointment(appointmentId) {
    console.log(`Intentando editar cita con ID: ${appointmentId}`);
    
    // Añadir más logging
    console.log('Ruta de edición:', `/cita/${appointmentId}/editar`);
    
    // Intentar manejar posibles errores
    fetch(`/cita/${appointmentId}/editar`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        console.log('Respuesta del servidor:', response.status);
        
        if (!response.ok) {
            throw new Error(`Error en la respuesta: ${response.status}`);
        }
        
        // Si la respuesta es exitosa, redirigir
        window.location.href = `/cita/${appointmentId}/editar`;
    })
    .catch(error => {
        console.error('Error al intentar editar:', error);
        showNotification(`Error al editar cita: ${error.message}`, 'error');
    });
}

function openAppointmentModal() {
    const modal = document.getElementById("appointment-details-modal");
    if (modal) {
        modal.style.display = "flex";
        document.body.style.overflow = "hidden";
    } else {
        console.error("Modal element not found");
    }
}

function closeAppointmentModal() {
    const modal = document.getElementById("appointment-details-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    }
}

function confirmDeleteAppointment(appointmentId) {
    const modal = document.getElementById("delete-modal");
    if (!modal) {
        console.error("Modal de eliminación no encontrado");
        showNotification("Error: Modal de eliminación no encontrado", "error");
        return;
    }
    
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";

    const confirmButton = document.getElementById("confirm-delete");
    if (confirmButton) {
        confirmButton.onclick = function () {
            deleteAppointment(appointmentId);
        };
    }
}

function closeDeleteModal() {
    const modal = document.getElementById("delete-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    }
}

function deleteAppointment(appointmentId) {
    console.log(`Intentando eliminar cita con ID: ${appointmentId}`);

    const confirmButton = document.getElementById("confirm-delete");
    if (confirmButton) {
        confirmButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eliminando...';
        confirmButton.disabled = true;
    }

    fetch(`/api/cita/${appointmentId}/eliminar`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
    })
        .then((response) => {
            console.log(`Respuesta del servidor para eliminar: ${response.status}`);
            
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || `Error del servidor: ${response.status}`);
                }).catch(() => {
                    throw new Error(`Error del servidor: ${response.status}`);
                });
            }
            return response.json();
        })
        .then((data) => {
            if (data.success) {
                closeDeleteModal();
                showNotification("Cita eliminada correctamente", "success");
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                throw new Error(data.message || "Error al eliminar la cita");
            }
        })
        .catch((error) => {
            console.error("Error al eliminar la cita:", error);
            closeDeleteModal();
            showNotification("Error al eliminar la cita: " + error.message, "error");
            
            if (confirmButton) {
                confirmButton.innerHTML = 'Eliminar';
                confirmButton.disabled = false;
            }
        });
}




async function showAppointmentNotes(appointmentId) {
    try {
        console.log(`Cargando notas para cita ID: ${appointmentId}`);

        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'notes-loading';
        loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000;';
        loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Cargando notas...</div>';
        document.body.appendChild(loadingIndicator);

        const response = await fetch(`/api/cita/${appointmentId}/notas`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`Error en la respuesta del servidor: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Datos recibidos:', data);

        document.body.removeChild(loadingIndicator);

        if (!data.success) {
            throw new Error(data.message || 'Error al obtener la nota de la cita');
        }

        // Obtener la nota más reciente (si existe)
        const nota = data.notas && data.notas.length > 0 ? data.notas[0].contenido : '';

        const notesContent = document.getElementById('notes-content');
        if (!notesContent) {
            throw new Error('No se encontró el contenedor de notas');
        }

        notesContent.innerHTML = `
            <div class="form-group">
                <label for="newNote">Nota de la Cita</label>
                <textarea id="newNote" class="form-control" rows="4">${nota}</textarea>
                <div class="invalid-feedback" id="newNote-error"></div>
            </div>
            <div class="modal-footer" style="padding: 1rem; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn btn-secondary" onclick="closeNotesModal()">Cerrar</button>
                <button type="button" class="btn btn-primary" id="saveNote">Guardar Nota</button>
            </div>
        `;

        const modal = document.getElementById('notes-modal');
        if (!modal) {
            throw new Error('No se encontró el modal de notas');
        }
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        document.getElementById('saveNote').addEventListener('click', async () => {
            const newNoteContent = document.getElementById('newNote').value.trim();
            const errorDiv = document.getElementById('newNote-error');

            if (newNoteContent.length > 1000) {
                errorDiv.textContent = 'La nota no puede exceder los 1000 caracteres.';
                document.getElementById('newNote').classList.add('is-invalid');
                return;
            }

            try {
                console.log(`Guardando nota para cita ID: ${appointmentId}`);
                const saveButton = document.getElementById('saveNote');
                saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
                saveButton.disabled = true;

                const saveResponse = await fetch(`/api/cita/${appointmentId}/notas`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ contenido: newNoteContent }),
                    credentials: 'same-origin'
                });

                const saveData = await saveResponse.json();
                console.log('Respuesta de guardado:', saveData);

                saveButton.innerHTML = 'Guardar Nota';
                saveButton.disabled = false;

                if (saveData.success) {
                    console.log('Nota guardada exitosamente');
                    showNotification('Nota guardada correctamente', 'success');
                    closeNotesModal();
                    if (typeof loadAppointmentsFromAPI === 'function') {
                        await loadAppointmentsFromAPI();
                    } else {
                        console.warn('loadAppointmentsFromAPI no está definida. La tabla de citas no se actualizará.');
                        window.location.reload();
                    }
                } else {
                    throw new Error(saveData.message || 'Error al guardar la nota');
                }
            } catch (error) {
                console.error('Error al guardar la nota:', error);
                showNotification('Error al guardar la nota: ' + error.message, 'error');
                saveButton.innerHTML = 'Guardar Nota';
                saveButton.disabled = false;
            }
        });
    } catch (error) {
        console.error('Error al cargar la nota:', error);
        showNotification('Error al cargar la nota: ' + error.message, 'error');
        document.body.removeChild(loadingIndicator);
    }
}


function closeNotesModal() {
    const modal = document.getElementById("notes-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    }
}

function updateCitaNotes(cita_id) {
    const notesTextarea = document.getElementById("update-notes");
    if (!notesTextarea) {
        showNotification("Error: No se encontró el área de texto", "error");
        return;
    }

    const contenido = notesTextarea.value.trim();
    if (!contenido) {
        showNotification("El contenido de la nota no puede estar vacío", "error");
        return;
    }

    // Deshabilitar textarea y mostrar indicador de carga
    notesTextarea.disabled = true;
    const saveButton = notesTextarea.nextElementSibling;
    if (saveButton) {
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        saveButton.disabled = true;
    }

    fetch(`/api/cita/${cita_id}/notas`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ contenido }),  // Cambiado de 'notes' a 'contenido'
        credentials: "same-origin",
    })
        .then((response) => {
            console.log(`Respuesta del servidor para POST notas: ${response.status}`);
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || `Error en la respuesta del servidor: ${response.status}`);
                });
            }
            return response.json();
        })
        .then((data) => {
            if (data.success) {
                closeNotesModal();
                showNotification("Nota agregada correctamente", "success");
                notesTextarea.disabled = false;
                if (saveButton) {
                    saveButton.innerHTML = 'Guardar nota';
                    saveButton.disabled = false;
                }
            } else {
                showNotification(data.message || "Error al agregar la nota", "error");
                notesTextarea.disabled = false;
                if (saveButton) {
                    saveButton.innerHTML = 'Guardar nota';
                    saveButton.disabled = false;
                }
            }
        })
        .catch((error) => {
            console.error("Error:", error);
            showNotification("Error al agregar la nota: " + error.message, "error");
            notesTextarea.disabled = false;
            if (saveButton) {
                saveButton.innerHTML = 'Guardar nota';
                saveButton.disabled = false;
            }
        });
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
            : type === "info"
            ? "#2196F3"
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
    }, 3000);
}