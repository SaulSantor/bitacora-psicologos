document.addEventListener("DOMContentLoaded", function () {
    // DOM Elements
    const searchInput = document.getElementById("searchPatient");
    const applyFiltersBtn = document.getElementById("apply-filters");
    const pageSizeSelect = document.getElementById("page-size");
    const prevPageBtn = document.getElementById("prev-page");
    const nextPageBtn = document.getElementById("next-page");
    const currentPageSpan = document.getElementById("current-page");
    const totalPagesSpan = document.getElementById("total-pages");
    const filterStatusSelect = document.getElementById('filter-status');
    const filterDiagnosisSelect = document.getElementById('filter-diagnosis');
    const filterLastVisitSelect = document.getElementById('filter-last-visit');
    const applyFiltersButton = document.getElementById('apply-filters');
    const patientsList = document.getElementById('patients-list');
    const calendarTab = document.getElementById("calendar-tab");
    const calendarTabBtn = document.getElementById("calendar-tab-btn");

    // Pagination variables
    let currentPage = 1;
    let pageSize = parseInt(pageSizeSelect?.value || 10);
    let filteredPatients = [];
    let allPatients = [];

    // Helper function for case-insensitive string comparison
    function normalizeString(str) {
        return str ? str.toLowerCase().trim() : '';
    }

    // Load patients from API
    function loadPatients() {
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'initial-loading';
        loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000;';
        loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Cargando pacientes...</div>';
        document.body.appendChild(loadingIndicator);
        
        fetch("/api/pacientes")
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Error en la respuesta del servidor: ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                if (Array.isArray(data)) {
                    allPatients = data;
                    filteredPatients = [...allPatients];
                    displayPatients();
                } else {
                    console.error("API did not return an array:", data);
                    showNotification("Error: Formato de datos incorrecto", "error");
                }
            })
            .catch((error) => {
                console.error("Error fetching patients:", error);
                showNotification("Usando datos de prueba mientras se repara la API", "warning");
                allPatients = [
                    {
                        id: 1, 
                        nombre: "Juan", 
                        apellido: "Pérez", 
                        status: "vigente", 
                        diagnostico: "Trastorno de Ansiedad Generalizada",
                        email: "juan@example.com",
                        telefono: "555-1234",
                        ultima_cita: new Date(Date.now() - 7*24*60*60*1000).toISOString(),
                        proxima_cita: new Date(Date.now() + 7*24*60*60*1000).toISOString()
                    },
                    {
                        id: 2,
                        nombre: "María",
                        apellido: "López",
                        status: "urgencia",
                        diagnostico: "Trastorno Depresivo Mayor",
                        email: "maria@example.com",
                        telefono: "555-5678",
                        ultima_cita: new Date(Date.now() - 14*24*60*60*1000).toISOString(),
                        proxima_cita: null
                    },
                    {
                        id: 3,
                        nombre: "Carlos",
                        apellido: "Rodríguez",
                        status: "orientacion",
                        diagnostico: "Duelo",
                        email: "carlos@example.com",
                        telefono: "555-9012",
                        ultima_cita: null,
                        proxima_cita: new Date(Date.now() + 3*24*60*60*1000).toISOString()
                    }
                ];
                filteredPatients = [...allPatients];
                displayPatients();
            })
            .finally(() => {
                if (document.getElementById('initial-loading')) {
                    document.body.removeChild(loadingIndicator);
                }
            });
    }

    // Calendar tab redirect
    if (calendarTab) {
        calendarTab.addEventListener("click", function(event) {
            event.preventDefault();
            window.location.href = "/psicologo";
        });
    }
    
    if (calendarTabBtn) {
        calendarTabBtn.addEventListener("click", function(event) {
            event.preventDefault();
            window.location.href = "/psicologo";
        });
    }

    // Display patients based on filters and pagination
    function displayPatients() {
        if (!patientsList) {
            console.warn("No patients-list element found in the DOM");
            return;
        }

        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const patientsToShow = filteredPatients.slice(startIndex, endIndex);
        
        while (patientsList.firstChild) {
            patientsList.removeChild(patientsList.firstChild);
        }
        
        if (patientsToShow.length === 0) {
            const emptyRow = document.createElement('tr');
            const emptyCell = document.createElement('td');
            emptyCell.setAttribute('colspan', '8');
            emptyCell.className = 'text-center';
            emptyCell.textContent = 'No hay pacientes que coincidan con los filtros';
            emptyRow.appendChild(emptyCell);
            patientsList.appendChild(emptyRow);
            
            updatePagination();
            return;
        }

        patientsToShow.forEach(paciente => {
            let ultimaCitaText = 'no ha tenido citas';
            let proximaCitaText = 'no hay citas programadas';
            
            if (paciente.ultima_cita) {
                const fechaUltima = new Date(paciente.ultima_cita);
                ultimaCitaText = formatDateWithTime(fechaUltima);
            }
            
            if (paciente.proxima_cita) {
                const fechaProxima = new Date(paciente.proxima_cita);
                proximaCitaText = formatDateWithTime(fechaProxima);
            }
            
            const row = document.createElement('tr');
            
            const tdNombre = document.createElement('td');
            const strongNombre = document.createElement('strong');
            strongNombre.textContent = `${paciente.nombre} ${paciente.apellido}`;
            tdNombre.appendChild(strongNombre);
            
            const tdStatus = document.createElement('td');
            const statusValue = paciente.status || 'vigente';
            const spanStatus = document.createElement('span');
            
            if (statusValue === 'vigente') {
                spanStatus.className = 'status-badge status-vigente';
                spanStatus.textContent = 'Vigente';
            } else if (statusValue === 'orientacion') {
                spanStatus.className = 'status-badge status-orientacion';
                spanStatus.textContent = 'Orientación';
            } else if (statusValue === 'urgencia') {
                spanStatus.className = 'status-badge status-urgencia';
                spanStatus.textContent = 'Urgencia';
            } else if (statusValue === 'waiting') {
                spanStatus.className = 'status-badge status-waiting';
                spanStatus.textContent = 'En Espera';
            } else {
                spanStatus.className = 'status-badge';
                spanStatus.textContent = statusValue;
            }
            
            tdStatus.appendChild(spanStatus);
            
            const tdDiagnostico = document.createElement('td');
            tdDiagnostico.textContent = paciente.diagnostico || 'No especificado';
            
            const tdUltimaCita = document.createElement('td');
            tdUltimaCita.textContent = ultimaCitaText;
            
            const tdProximaCita = document.createElement('td');
            tdProximaCita.textContent = proximaCitaText;
            
            const tdTelefono = document.createElement('td');
            tdTelefono.textContent = paciente.telefono || '';
            
            const tdEmail = document.createElement('td');
            tdEmail.textContent = paciente.email || '';
            
            const tdAcciones = document.createElement('td');
            const divAcciones = document.createElement('div');
            divAcciones.className = 'actions-cell';
            
            const patientId = parseInt(paciente.id);
            
            const btnVer = document.createElement('button');
            btnVer.className = 'action-btn view-btn';
            btnVer.title = 'Ver detalles';
            btnVer.addEventListener('click', function() {
                viewPatientDetails(patientId);
            });
            const iVer = document.createElement('i');
            iVer.className = 'fas fa-eye';
            btnVer.appendChild(iVer);
            
            const btnEditar = document.createElement('button');
            btnEditar.className = 'action-btn edit-btn';
            btnEditar.title = 'Editar';
            btnEditar.addEventListener('click', function() {
                openEditModal(patientId);
            });
            const iEditar = document.createElement('i');
            iEditar.className = 'fas fa-edit';
            btnEditar.appendChild(iEditar);
            
            const btnNotas = document.createElement('button');
            btnNotas.className = 'action-btn notes-btn';
            btnNotas.title = 'Notas';
            btnNotas.addEventListener('click', function() {
                showPatientNotes(patientId);
            });
            const iNotas = document.createElement('i');
            iNotas.className = 'fas fa-clipboard';
            btnNotas.appendChild(iNotas);
            
            const btnEliminar = document.createElement('button');
            btnEliminar.className = 'action-btn delete-btn';
            btnEliminar.title = 'Eliminar';
            btnEliminar.addEventListener('click', function() {
                confirmDeletePatient(patientId);
            });
            const iEliminar = document.createElement('i');
            iEliminar.className = 'fas fa-trash';
            btnEliminar.appendChild(iEliminar);
            
            divAcciones.appendChild(btnVer);
            divAcciones.appendChild(btnEditar);
            divAcciones.appendChild(btnNotas);
            divAcciones.appendChild(btnEliminar);
            tdAcciones.appendChild(divAcciones);
            
            row.appendChild(tdNombre);
            row.appendChild(tdStatus);
            row.appendChild(tdDiagnostico);
            row.appendChild(tdUltimaCita);
            row.appendChild(tdProximaCita);
            row.appendChild(tdTelefono);
            row.appendChild(tdEmail);
            row.appendChild(tdAcciones);
            
            patientsList.appendChild(row);
        });
        
        updatePagination();
    }

    // Format date with time
    function formatDateWithTime(date) {
        return `${date.getDate().toString().padStart(2, "0")}/${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getFullYear()} ${date.getHours().toString().padStart(2, "0")}:${date.getMinutes().toString().padStart(2, "0")}`;
    }

    // Update pagination information
    function updatePagination() {
        if (!totalPagesSpan || !currentPageSpan) return;
        
        totalPagesSpan.textContent = Math.ceil(filteredPatients.length / pageSize) || 1;
        currentPageSpan.textContent = currentPage;

        if (prevPageBtn) {
            prevPageBtn.disabled = currentPage === 1;
        }
        
        if (nextPageBtn) {
            nextPageBtn.disabled = currentPage >= Math.ceil(filteredPatients.length / pageSize);
        }
    }

    // Apply filters function
    function applyFilters() {
        try {
            const statusFilter = filterStatusSelect ? filterStatusSelect.value : '';
            const diagnosisFilter = filterDiagnosisSelect ? filterDiagnosisSelect.value : '';
            const lastVisitFilter = filterLastVisitSelect ? filterLastVisitSelect.value : '';
            const searchTerm = searchInput && searchInput.value ? searchInput.value.trim() : '';
                        
            const loadingIndicator = document.createElement('div');
            loadingIndicator.id = 'loading-indicator';
            loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000;';
            loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Cargando...</div>';
            document.body.appendChild(loadingIndicator);

            if (allPatients && allPatients.length > 0) {
                const statusFilterNorm = normalizeString(statusFilter);
                const diagnosisFilterNorm = normalizeString(diagnosisFilter);
                const searchTermNorm = normalizeString(searchTerm);
                
                filteredPatients = allPatients.filter(paciente => {
                    if (statusFilter && normalizeString(paciente.status) !== statusFilterNorm) {
                        return false;
                    }
                    
                    if (diagnosisFilter && normalizeString(paciente.diagnostico) !== diagnosisFilterNorm) {
                        return false;
                    }
                    
                    if (searchTerm) {
                        const nombreCompleto = normalizeString(`${paciente.nombre || ''} ${paciente.apellido || ''}`);
                        const diagnostico = normalizeString(paciente.diagnostico || '');
                        const email = normalizeString(paciente.email || '');
                        
                        if (!nombreCompleto.includes(searchTermNorm) && 
                            !diagnostico.includes(searchTermNorm) && 
                            !email.includes(searchTermNorm)) {
                            return false;
                        }
                    }
                    
                    if (lastVisitFilter && paciente.ultima_cita) {
                        try {
                            const fechaUltimaCita = new Date(paciente.ultima_cita);
                            if (isNaN(fechaUltimaCita.getTime())) {
                                console.warn("Invalid date:", paciente.ultima_cita);
                                return true;
                            }
                            
                            const hoy = new Date();
                            
                            if (lastVisitFilter === 'week') {
                                const unaSemanaDespues = new Date(hoy);
                                unaSemanaDespues.setDate(hoy.getDate() - 7);
                                if (fechaUltimaCita < unaSemanaDespues) {
                                    return false;
                                }
                            } else if (lastVisitFilter === 'month') {
                                const unMesDespues = new Date(hoy);
                                unMesDespues.setMonth(hoy.getMonth() - 1);
                                if (fechaUltimaCita < unMesDespues) {
                                    return false;
                                }
                            } else if (lastVisitFilter === 'quarter') {
                                const unTrimestreDespues = new Date(hoy);
                                unTrimestreDespues.setMonth(hoy.getMonth() - 3);
                                if (fechaUltimaCita < unTrimestreDespues) {
                                    return false;
                                }
                            } else if (lastVisitFilter === 'year') {
                                const unAñoDespues = new Date(hoy);
                                unAñoDespues.setFullYear(hoy.getFullYear() - 1);
                                if (fechaUltimaCita < unAñoDespues) {
                                    return false;
                                }
                            }
                        } catch (e) {
                            console.warn("Date error:", e);
                            return true;
                        }
                    }
                    
                    return true;
                });
                
                currentPage = 1;
                displayPatients();
                
                if (document.getElementById('loading-indicator')) {
                    document.body.removeChild(loadingIndicator);
                }
                return;
            }

            const params = new URLSearchParams();
            if (statusFilter) params.append('status', statusFilter);
            if (diagnosisFilter) params.append('diagnosis', diagnosisFilter);
            if (lastVisitFilter) params.append('last_visit', lastVisitFilter);
            if (searchTerm) params.append('search', searchTerm);
            
            const url = `/api/pacientes?${params.toString()}`;
            
            fetch(url)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Error en la respuesta del servidor: ${response.status}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    if (!Array.isArray(data)) {
                        throw new Error("La respuesta no tiene el formato esperado");
                    }
                    
                    filteredPatients = data;
                    currentPage = 1;
                    displayPatients();
                })
                .catch((error) => {
                    console.error("Error al cargar pacientes:", error);
                    showNotification("Error al aplicar filtros: " + error.message, "error");
                    displayPatients();
                })
                .finally(() => {
                    if (document.getElementById('loading-indicator')) {
                        document.body.removeChild(loadingIndicator);
                    }
                });
        } catch (error) {
            console.error("Error en la función applyFilters:", error);
            showNotification("Error inesperado al aplicar filtros", "error");
            displayPatients();
        }
    }

    if (searchInput) {
        searchInput.addEventListener("keyup", function (e) {
            if (e.key === "Enter") {
                applyFilters();
            }
        });
    }

    if (pageSizeSelect) {
        pageSizeSelect.addEventListener("change", function () {
            pageSize = parseInt(this.value);
            currentPage = 1;
            displayPatients();
        });
    }

    if (prevPageBtn) {
        prevPageBtn.addEventListener("click", function () {
            if (currentPage > 1) {
                currentPage--;
                displayPatients();
            }
        });
    }

    if (nextPageBtn) {
        nextPageBtn.addEventListener("click", function () {
            if (currentPage < Math.ceil(filteredPatients.length / pageSize)) {
                currentPage++;
                displayPatients();
            }
        });
    }

    if (applyFiltersButton) {
        applyFiltersButton.addEventListener('click', applyFilters);
    }

    loadPatients();
});



window.currentPatientId = null; // Mantener para compatibilidad
window.currentCitas = []; // Almacenar citas temporalmente

window.viewPatientDetails = function(patientId) {
    console.log("View details clicked for patient ID:", patientId);
    
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'details-loading';
    loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000;';
    loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Cargando detalles...</div>';
    document.body.appendChild(loadingIndicator);

    if (typeof patientId !== 'number') {
        patientId = parseInt(patientId, 10);
    }
    
    if (isNaN(patientId)) {
        console.error("Invalid patient ID:", patientId);
        showNotification("Error: ID de paciente inválido", "error");
        document.body.removeChild(loadingIndicator);
        return;
    }

    window.currentPatientId = patientId;

    fetch(`/api/paciente/${patientId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Error en la respuesta del servidor: " + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log("Datos recibidos de la API:", data);
            document.body.removeChild(loadingIndicator);

            if (data.success) {
                const patientDetailsContent = document.getElementById("patient-details-content");
                if (!patientDetailsContent) {
                    showNotification("Error: No se encontró el contenedor de detalles", "error");
                    return;
                }

                const paciente = data.paciente;
                const citas = data.paciente.citas || [];

                if (!paciente.id || isNaN(paciente.id)) {
                    console.error("Invalid patient ID in paciente:", paciente);
                    showNotification("Error: ID de paciente inválido en los datos", "error");
                    return;
                }

                // Almacenar citas globalmente
                window.currentCitas = citas;

                const formattedCitas = citas.map(cita => {
                    const fecha = new Date(cita.fecha);
                    const fechaFormateada = fecha.toLocaleDateString();
                    const horaFormateada = fecha.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                    return {
                        ...cita,
                        fechaFormateada,
                        horaFormateada,
                    };
                });

                patientDetailsContent.innerHTML = `
                    <div class="patient-detail">
                        <h4>Información del Paciente</h4>
                        <p><strong>Paciente:</strong> ${paciente.nombre} ${paciente.apellido}</p>
                        <p><strong>Email:</strong> ${paciente.email || "No especificado"}</p>
                        <p><strong>Teléfono:</strong> ${paciente.telefono || "No especificado"}</p>
                        <p><strong>Diagnóstico:</strong> ${paciente.diagnostico || "No especificado"}</p>
                        <div>
                            <p><strong>Notas del Paciente:</strong></p>
                            <div style="padding: 10px; background-color: #f8f9fa; border-radius: 4px; margin-top: 5px;">
                                ${paciente.notas.length > 0 ? paciente.notas.map(nota => `
                                    <div style="margin-bottom: 10px;">
                                        <p><strong>Fecha:</strong> ${new Date(nota.creado_en).toLocaleString()}</p>
                                        <p><strong>Última actualización:</strong> ${new Date(nota.actualizado_en).toLocaleString()}</p>
                                        <p>${nota.contenido || "<em>Sin contenido</em>"}</p>
                                    </div>
                                `).join("") : "<em>No hay notas disponibles</em>"}
                            </div>
                        </div>
                        
                        <h5 style="margin-top: 20px; border-bottom: 1px solid #dee2e6; padding-bottom: 10px;">Historial de Citas</h5>
                        
                        ${formattedCitas.length > 0 ? formattedCitas.map(cita => `
                            <div class="appointment-detail" style="margin-bottom: 15px; padding: 10px; border-left: 3px solid #4e73df; background-color: #f8f9fc;" data-patient-id="${paciente.id}">
                                <p><strong>Fecha:</strong> ${cita.fechaFormateada}</p>
                                <p><strong>Hora:</strong> ${cita.horaFormateada}</p>
                                <p><strong>Duración:</strong> ${cita.duracion ? cita.duracion + " minutos" : "Calculando..."} </p>
                                <p><strong>Motivo de cita:</strong> ${cita.tipo || "No especificado"}</p>
                                <p><strong>Status:</strong> ${cita.status || "No especificado"}</p>
                                <div>
                                    <p><strong>Notas de la Cita:</strong></p>
                                    <div style="padding: 10px; background-color: #f8f9fa; border-radius: 4px; margin-top: 5px;">
                                        ${cita.notas && cita.notas.length > 0 ? cita.notas.map(nota => `
                                            <div style="margin-bottom: 10px;">
                                                <p><strong>Fecha:</strong> ${new Date(nota.creado_en).toLocaleString()}</p>
                                                <p><strong>Última actualización:</strong> ${new Date(nota.actualizado_en).toLocaleString()}</p>
                                                <p>${nota.contenido || "<em>Sin contenido</em>"}</p>
                                            </div>
                                        `).join("") : "<em>No hay notas disponibles</em>"}
                                    </div>
                                    <div style="margin-top: 10px;">
                                        <textarea class="form-control" rows="3" placeholder="Añadir nota a la cita" id="new-cita-note-${cita.id}"></textarea>
                                        <button type="button" class="btn btn-primary" style="margin-top: 0.5rem" onclick="addCitaNote(${cita.id})">
                                            Agregar Nota a Cita
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `).join("") : '<p style="font-style: italic;">No hay citas registradas para este paciente</p>'}
                    </div>
                `;

                openPatientModal();
            } else {
                showNotification(data.message || "Error al cargar detalles del paciente", "error");
            }
        })
        .catch(error => {
            console.error("API Error:", error);
            showNotification("Error al cargar detalles del paciente: " + error.message, "error");
            document.body.removeChild(loadingIndicator);
        });
}


function addCitaNote(citaId) {
    const notesTextarea = document.getElementById(`new-cita-note-${citaId}`);
    if (!notesTextarea) {
        showNotification("Error: No se encontró el área de texto", "error");
        return;
    }

    const contenido = notesTextarea.value.trim();
    if (!contenido) {
        showNotification("Error: La nota no puede estar vacía", "warning");
        return;
    }

    // Buscar la cita en window.currentCitas
    const cita = window.currentCitas.find(c => c.id === citaId);
    const patientIdFromCita = cita && cita.notas && cita.notas.length > 0 ? cita.notas[0].paciente_id : null;

    console.log("Cita encontrada:", cita); // Depuración
    console.log("Patient ID from cita:", patientIdFromCita); // Depuración

    const patientId = patientIdFromCita || window.currentPatientId;
    console.log("Patient ID final:", patientId); // Depuración

    if (!patientId || isNaN(patientId)) {
        showNotification("Error: No se pudo obtener el ID del paciente", "error");
        return;
    }

    notesTextarea.disabled = true;
    const saveButton = notesTextarea.nextElementSibling;
    if (saveButton) {
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        saveButton.disabled = true;
    }

    fetch(`/api/cita/${citaId}/notas`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ contenido }),
        credentials: "same-origin",
    })
        .then(response => {
            if (!response.ok) {
                throw new Error("Error en la respuesta del servidor: " + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showNotification("Nota de cita agregada correctamente", "success");
                viewPatientDetails(data.patient_id || patientId);
                notesTextarea.disabled = false;
                saveButton.innerHTML = 'Agregar Nota a Cita';
                saveButton.disabled = false;
            } else {
                showNotification(data.message || "Error al agregar la nota de cita", "error");
                notesTextarea.disabled = false;
                if (saveButton) {
                    saveButton.innerHTML = 'Agregar Nota a Cita';
                    saveButton.disabled = false;
                }
            }
        })
        .catch(error => {
            console.error("Error:", error);
            showNotification("Error al agregar la nota de cita: " + error.message, "error");
            notesTextarea.disabled = false;
            if (saveButton) {
                saveButton.innerHTML = 'Agregar Nota a Cita';
                saveButton.disabled = false;
            }
        });
}

function openPatientModal() {
    const modal = document.getElementById("patient-details-modal");
    if (modal) {
        modal.style.display = "flex";
        document.body.style.overflow = "hidden";
    } else {
        console.error("Modal element not found!");
    }
}

function closePatientModal() {
    const modal = document.getElementById("patient-details-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    }
}

function confirmDeletePatient(patientId) {
    console.log("Delete clicked for patient ID:", patientId);
    
    if (typeof patientId !== 'number') {
        patientId = parseInt(patientId, 10);
    }
    
    if (isNaN(patientId)) {
        console.error("Invalid patient ID:", patientId);
        showNotification("Error: ID de paciente inválido", "error");
        return;
    }
    
    const modal = document.getElementById("delete-modal");
    if (modal) {
        modal.style.display = "flex";
        document.body.style.overflow = "hidden";

        const confirmButton = document.getElementById("confirm-delete");
        if (confirmButton) {
            confirmButton.onclick = function () {
                deletePatient(patientId);
            };
        }
    }
}

function closeDeleteModal() {
    const modal = document.getElementById("delete-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    }
}

function deletePatient(patientId) {
    const deleteButton = document.getElementById('confirm-delete');
    if (deleteButton) {
        deleteButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eliminando...';
        deleteButton.disabled = true;
    }

    fetch(`/api/paciente/${patientId}/eliminar`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ id: patientId, confirm: true }),
        credentials: "same-origin",
    })
        .then((response) => {
            return response.json().then(data => ({ status: response.status, body: data }));
        })
        .then(({ status, body }) => {
            if (status !== 200) {
                throw new Error(body.message || `Error en la respuesta del servidor: ${status}`);
            }
            closeDeleteModal();
            showNotification("Paciente eliminado correctamente", "success");
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        })
        .catch((error) => {
            console.error("Error:", error);
            closeDeleteModal();
            showNotification(`Error al eliminar el paciente: ${error.message}`, "error");
        })
        .finally(() => {
            if (deleteButton) {
                deleteButton.innerHTML = 'Confirmar';
                deleteButton.disabled = false;
            }
        });
}



function showPatientNotes(patientId) {
    console.log("Notes clicked for patient ID:", patientId);
    
    if (typeof patientId !== 'number') {
        patientId = parseInt(patientId, 10);
    }
    
    if (isNaN(patientId)) {
        console.error("Invalid patient ID:", patientId);
        showNotification("Error: ID de paciente inválido", "error");
        return;
    }
    
    const modal = document.getElementById("notes-modal");
    const notesContent = document.getElementById("notes-content");

    if (!modal || !notesContent) {
        console.error("Modal or content element not found!");
        showNotification("Error: Elemento de modal no encontrado", "error");
        return;
    }

    notesContent.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Cargando notas...</div>';
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";

    fetch(`/api/paciente/${patientId}/notas`, {
        method: "GET",
        headers: {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json"
        },
        credentials: "same-origin"
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error en la respuesta del servidor: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                notesContent.innerHTML = `
                    <div class="patient-notes">
                        <h4>Notas de ${data.patient_name}</h4>
                        ${data.notas.length > 0 ? data.notas.map(nota => `
                            <div style="padding: 10px; background-color: #f8f9fa; border-radius: 4px; margin: 10px 0;">
                                <p><strong>Fecha:</strong> ${new Date(nota.creado_en).toLocaleString()}</p>
                                <p><strong>Última actualización:</strong> ${new Date(nota.actualizado_en).toLocaleString()}</p>
                                <p>${nota.contenido || "<em>Sin contenido</em>"}</p>
                            </div>
                        `).join("") : "<p><em>No hay notas para este paciente</em></p>"}
                        <div style="margin-top: 1rem;">
                            <textarea id="new-note-${patientId}" class="form-control" rows="4" placeholder="Añadir nueva nota"></textarea>
                            <button type="button" class="btn btn-primary" style="margin-top: 0.5rem" onclick="addPatientNote(${patientId})">Agregar Nota</button>
                        </div>
                    </div>
                `;
            } else {
                notesContent.innerHTML = `
                    <div class="alert alert-danger">
                        <p>Error al cargar las notas del paciente: ${data.message || "Error desconocido"}</p>
                    </div>
                `;
                showNotification(data.message || "Error al cargar notas", "error");
            }
        })
        .catch(error => {
            console.error("Error fetching notes:", error);
            notesContent.innerHTML = `
                <div class="alert alert-danger">
                    <p>No se pudieron cargar las notas: ${error.message}. Por favor, intenta de nuevo.</p>
                </div>
            `;
            showNotification("Error al cargar notas: " + error.message, "error");
        });
}



function addPatientNote(patientId) {
    const notesTextarea = document.getElementById(`new-note-${patientId}`);
    if (!notesTextarea) {
        console.error(`No se encontró el textarea con id 'new-note-${patientId}'`);
        showNotification("Error: No se encontró el área de texto", "error");
        return;
    }
    
    const contenido = notesTextarea.value.trim();
    if (!contenido) {
        showNotification("Error: La nota no puede estar vacía", "warning");
        return;
    }

    notesTextarea.disabled = true;
    const saveButton = notesTextarea.nextElementSibling;
    if (saveButton) {
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        saveButton.disabled = true;
    }

    fetch(`/api/paciente/${patientId}/notas`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ contenido }),
        credentials: "same-origin"
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error en la respuesta del servidor: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showNotification("Nota agregada correctamente", "success");
                closeNotesModal(); // This will now work
                showPatientNotes(patientId);
            } else {
                showNotification(data.message || "Error al agregar la nota", "error");
            }
        })
        .catch(error => {
            console.error("Error adding note:", error);
            showNotification("Error al agregar la nota: " + error.message, "error");
        })
        .finally(() => {
            notesTextarea.disabled = false;
            if (saveButton) {
                saveButton.innerHTML = 'Agregar Nota';
                saveButton.disabled = false;
            }
        });
}





function closeNotesModal() {
    const modal = document.getElementById("notes-modal");
    if (modal) {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    }
}




function openEditModal(paciente_id) {
    console.log("Edit clicked for patient ID:", paciente_id);
    
    if (typeof paciente_id !== 'number') {
        paciente_id = parseInt(paciente_id, 10);
    }
    
    if (isNaN(paciente_id)) {
        console.error("Invalid patient ID:", paciente_id);
        showNotification("Error: ID de paciente inválido", "error");
        return;
    }
    
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'edit-loading';
    loadingIndicator.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255, 255,255,0.7); display: flex; justify-content: center; align-items: center; z-index: 1001;">';
    loadingIndicator.innerHTML = '<div style="padding: 20px; background: white; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i> Cargando datos...</div>';
    document.body.appendChild(loadingIndicator);

    fetch(`/api/paciente/${paciente_id}`)
        .then(response => {
            console.log("API response status:", response.status);
            
            if (!response.ok) {
                throw new Error("Error en la respuesta del servidor: " + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log("API response data:", data);
            
            document.body.removeChild(loadingIndicator);

            if (data.success) {
                let paciente = data.paciente;
                const idInput = document.getElementById("paciente_id");
                const nombreInput = document.getElementById("nombre");
                const apellidoInput = document.getElementById("apellido");
                const statusSelect = document.getElementById("status");
                const diagnosticoInput = document.getElementById("diagnostico");
                const telefonoInput = document.getElementById("telefono");
                const emailInput = document.getElementById("email");
                
                if (idInput) idInput.value = paciente.id || "";
                if (nombreInput) nombreInput.value = paciente.nombre || "";
                if (apellidoInput) apellidoInput.value = paciente.apellido || "";
                if (statusSelect) statusSelect.value = paciente.status || "";
                if (diagnosticoInput) diagnosticoInput.value = paciente.diagnostico || "";
                if (telefonoInput) telefonoInput.value = paciente.telefono || "";
                if (emailInput) emailInput.value = paciente.email || "";

                const modal = document.getElementById("editPacienteModal");
                if (modal) {
                    // Forzar renderizado y visibilidad
                    modal.style.display = 'flex';
                    modal.style.opacity = '1';
                    modal.style.pointerEvents = 'auto';
                    // Forzar repintado
                    modal.offsetHeight; // Trigger reflow
                    modal.style.opacity = '1';
                } else {
                    showNotification("Error: No se encontró el modal de edición", "error");
                }
            } else {
                showNotification(data.message || "Error: No se encontró el paciente", "error");
            }
        })
        .catch(error => {
            if (document.getElementById('edit-loading')) {
                document.body.removeChild(loadingIndicator);
            }
            
            console.error("Error loading patient:", error);
            showNotification("Error al cargar datos del paciente: " + error.message, "error");
        });
};

function closeEditModal() {
    const modal = document.getElementById("editPacienteModal");
    if (modal) {
        modal.style.display = 'none';
        modal.style.opacity = '0';
    }
}

function updatePaciente() {
    const pacienteIdInput = document.getElementById("paciente_id");
    if (!pacienteIdInput) {
        showNotification("Error: No se pudo encontrar el ID del paciente", "error");
        return;
    }
    
    const paciente_id = pacienteIdInput.value;
    if (!paciente_id) {
        showNotification("Error: ID de paciente no válido", "error");
        return;
    }
    
    const nombreInput = document.getElementById("nombre");
    const apellidoInput = document.getElementById("apellido");
    const statusInput = document.getElementById("status");
    const diagnosticoInput = document.getElementById("diagnostico");
    const telefonoInput = document.getElementById("telefono");
    const emailInput = document.getElementById("email");
    
    if (!nombreInput || !apellidoInput || !statusInput || !diagnosticoInput || !telefonoInput || !emailInput) {
        showNotification("Error: Faltan campos en el formulario", "error");
        return;
    }

    const nombre = nombreInput.value.trim();
    const apellido = apellidoInput.value.trim();
    const status = statusInput.value.trim();
    const diagnostico = diagnosticoInput.value.trim();
    const telefono = telefonoInput.value.trim();
    const email = emailInput.value.trim();

    if (!nombre || !apellido) {
        showNotification("El nombre y apellido son obligatorios", 'warning');
        return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (email && !emailRegex.test(email)) {
        showNotification("El formato del correo electrónico no es válido", 'warning');
        return;
    }

    const data = { nombre, apellido, status, diagnostico, telefono, email };
    console.log("Sending data to /api/paciente/editar:", data);

    const saveButton = document.querySelector("#editPacienteModal .btn-primary");
    if (saveButton) {
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        saveButton.disabled = true;
    }

    fetch(`/api/paciente/${paciente_id}/editar`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(data),
        credentials: "same-origin",
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Error en la respuesta del servidor: " + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            closeEditModal();
            showNotification("Paciente actualizado correctamente", "success");
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showNotification("Error: " + (data.message || "No se pudo actualizar el paciente"), "error");
            if (saveButton) {
                saveButton.innerHTML = 'Guardar cambios';
                saveButton.disabled = false;
            }
        }
    })
    .catch(error => {
        console.error("Error al actualizar paciente:", error);
        showNotification("Error al actualizar paciente: " + error.message, "error");
        if (saveButton) {
            saveButton.innerHTML = 'Guardar cambios';
            saveButton.disabled = false;
        }
    });
}



function addPatientNoteFromEdit(pacienteId) {
    const notesTextarea = document.getElementById("new-note");
    if (!notesTextarea) {
        showNotification("Error: No se encontró el área de texto", "error");
        return;
    }

    const contenido = notesTextarea.value.trim();
    if (!contenido) {
        showNotification("Error: La nota no puede estar vacía", "warning");
        return;
    }

    notesTextarea.disabled = true;
    const saveButton = notesTextarea.nextElementSibling;
    if (saveButton) {
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        saveButton.disabled = true;
    }

    fetch(`/api/paciente/${pacienteId}/notas`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ contenido }),
        credentials: "same-origin",
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Error en la respuesta del servidor: " + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification("Nota agregada correctamente", "success");
            notesTextarea.value = "";
        } else {
            showNotification(data.message || "Error al agregar la nota", "error");
        }
    })
    .catch(error => {
        showNotification("Error al agregar la nota: " + error.message, "error");
    })
    .finally(() => {
        notesTextarea.disabled = false;
        if (saveButton) {
            saveButton.innerHTML = 'Agregar Nota';
            saveButton.disabled = false;
        }
    });
}



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

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = "1";
        notification.style.transform = "translateY(0)";
    }, 10);

    setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transform = "translateY(-10px)";
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}