// config.js - JavaScript para la página de configuración

// Configuración para las notificaciones
const NotificationConfig = {
    checkInterval: 60000, // Verificar cada 1 minuto (60,000 ms)
    notificationIcon: '/static/img/notification-icon.png', // Ruta al ícono de notificación
    notificationSound: '/static/sound/notification.mp3', // Ruta al sonido de notificación
    notificationsEnabled: true, // Habilitado por defecto (se actualizará con la config del usuario)
    soundEnabled: false, // Deshabilitado por defecto (se actualizará con la config del usuario)
    checkTimeout: null, // Para controlar el intervalo
    tiempoAnticipacion: 60, // Minutos de anticipación (se actualizará con la config del usuario)
    citasNotificadas: new Set(), // Para evitar notificaciones duplicadas
    permissionGranted: false, // Si el usuario ha concedido permisos para notificaciones
};

// Objeto de audio para reproducir sonidos
const notificationAudio = new Audio(NotificationConfig.notificationSound);

document.addEventListener('DOMContentLoaded', function() {
    // Configurar navegación entre pestañas
    setupTabs();
    
    // Cargar datos iniciales
    loadProfileData();
    loadNotificationSettings();
    loadSecuritySettings();
    
    // Configurar botones de guardar
    setupSaveButtons();
    
    // Configurar el botón de eliminar cuenta
    setupDeleteAccountButton();
    
    // Inicializar sistema de notificaciones si el navegador lo soporta
    initNotificationSystem();
});

/**
 * Configura la navegación entre pestañas
 */
function setupTabs() {
    const tabs = document.querySelectorAll('.config-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remover clase active de todas las pestañas y contenidos
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Activar pestaña actual
            this.classList.add('active');
            
            // Mostrar contenido correspondiente
            const contentId = this.id.replace('-tab', '-content');
            document.getElementById(contentId).classList.add('active');
        });
    });
}

function loadProfileData() {
    fetch('/api/obtener-perfil-psicologo')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Llenar campos del formulario
                document.getElementById('title').value = data.titulo || '';
                document.getElementById('specialty').value = data.especialidad || '';
                document.getElementById('fullname').value = data.nombre_completo || '';
                document.getElementById('license').value = data.numero_licencia || '';
                document.getElementById('email').value = data.email || '';
                document.getElementById('phone').value = data.telefono || '';
                document.getElementById('address').value = data.direccion || '';

                // Manejar el campo 'Otro' en especialidad
                const otraEspecialidadField = document.getElementById('otra-especialidad-field');
                const otraEspecialidadInput = document.getElementById('otra_especialidad');

                if (data.especialidad === 'otro') {
                    otraEspecialidadField.style.display = 'block';
                    otraEspecialidadInput.disabled = false; 
                    otraEspecialidadInput.value = data.especialidad || ''; 
                } else {
                    otraEspecialidadField.style.display = 'none';
                    otraEspecialidadInput.disabled = true; 
                    otraEspecialidadInput.value = ''; 
                }
            } else {
                showNotification('Error al cargar datos del perfil', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error al cargar datos del perfil', 'error');
        });
}



/**
 * Carga la configuración de notificaciones
 */
function loadNotificationSettings() {
    fetch('/api/obtener-notification-config')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Llenar switches de notificaciones
                document.getElementById('email-notifications').checked = data.notificaciones_email;
                
                // Llenar selects
                document.getElementById('notification-time').value = data.tiempo_anticipacion;
                document.getElementById('reminder-frequency').value = data.frecuencia_recordatorios;
                
                // Llenar otros switches
                document.getElementById('cita-changes-alerts').checked = data.alertas_cambios_citas;
                document.getElementById('new-patients-alerts').checked = data.alertas_pacientes_nuevos;
                document.getElementById('update-notifications').checked = data.notificaciones_actualizacion;
                document.getElementById('sound-notifications').checked = data.sonidos_notificacion;
                
                // Actualizar la configuración de notificaciones
                NotificationConfig.notificationsEnabled = data.notificaciones_email;
                NotificationConfig.soundEnabled = data.sonidos_notificacion;
                NotificationConfig.tiempoAnticipacion = parseInt(data.tiempo_anticipacion);
                
                // Guardar en localStorage para persistencia
                saveNotificationConfigToLocalStorage();
            } else {
                console.warn('No se pudo cargar la configuración de notificaciones');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}


/**
 * Guarda la configuración de notificaciones en localStorage
 */
function saveNotificationConfigToLocalStorage() {
    const config = {
        notificationsEnabled: NotificationConfig.notificationsEnabled,
        soundEnabled: NotificationConfig.soundEnabled,
        tiempoAnticipacion: NotificationConfig.tiempoAnticipacion
    };
    
    localStorage.setItem('notificationConfig', JSON.stringify(config));
}

/**
 * Inicializa el sistema de notificaciones
 */
function initNotificationSystem() {

    // Verificar si el navegador soporta notificaciones
    if (!('Notification' in window)) {
        console.warn('Este navegador no soporta notificaciones de escritorio');
        return;
    }

    // Solicitar permiso para notificaciones
    if (Notification.permission === 'granted') {
        NotificationConfig.permissionGranted = true;
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                NotificationConfig.permissionGranted = true;
            }
        });
    }
}

/**
 * Muestra una notificación para una cita específica
 */
function showAppointmentNotification(cita) {
    // Obtener nombre del paciente y tiempo restante formateado
    const pacienteNombre = cita.paciente || 'Paciente';
    const tiempoRestante = formatTiempoRestante(cita.minutos_restantes);
    
    // Generar título y cuerpo de la notificación
    const titulo = `Cita próxima: ${pacienteNombre}`;
    const cuerpo = `Tienes una cita ${tiempoRestante} (${cita.hora}).
Tipo: ${cita.tipo || 'No especificado'}
Duración: ${cita.duracion || '60'} minutos`;

    // Mostrar notificación en la aplicación
    showNotification(titulo + ' - ' + cuerpo, 'warning');
    
    // Mostrar notificación de escritorio si tenemos permiso
    if (NotificationConfig.permissionGranted) {
        try {
            const notification = new Notification(titulo, {
                body: cuerpo,
                icon: NotificationConfig.notificationIcon
            });
            
            // Redirigir al calendario al hacer clic en la notificación
            notification.onclick = function() {
                window.focus();
                if (window.location.pathname !== '/psicologo') {
                    window.location.href = '/psicologo';
                }
            };
            
            // Reproducir sonido si está habilitado
            if (NotificationConfig.soundEnabled) {
                notificationAudio.play().catch(e => {
                    console.warn('No se pudo reproducir el sonido de notificación:', e);
                });
            }
        } catch (e) {
            console.error('Error al mostrar notificación de escritorio:', e);
        }
    }
}

/**
 * Formatea el tiempo restante en un texto legible
 */
function formatTiempoRestante(minutos) {
    if (minutos <= 0) {
        return 'ahora mismo';
    } else if (minutos < 60) {
        return `en ${minutos} minutos`;
    } else {
        const horas = Math.floor(minutos / 60);
        const minutosRestantes = minutos % 60;
        
        if (minutosRestantes === 0) {
            return `en ${horas} ${horas === 1 ? 'hora' : 'horas'}`;
        } else {
            return `en ${horas} ${horas === 1 ? 'hora' : 'horas'} y ${minutosRestantes} minutos`;
        }
    }
}

/**
 * Carga la configuración de seguridad
 */
function loadSecuritySettings() {
    fetch('/api/obtener-security-config')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Llenar switches de seguridad
                document.getElementById('auth-dos-factores').checked = data.auth_dos_factores;
                document.getElementById('cierre-sesion-auto').checked = data.cierre_sesion_auto;
                
                // Llenar selects
                document.getElementById('tiempo-inactividad').value = data.tiempo_inactividad;
                document.getElementById('retencion-datos').value = data.retencion_datos;
            } else {
                console.warn('No se pudo cargar la configuración de seguridad');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

/**
 * Configura los botones de guardar para cada pestaña
 */
function setupSaveButtons() {
    // Botón de pestaña de perfil
    const profileSaveButton = document.querySelector('#profile-content .btn-primary');
    if (profileSaveButton) {
        profileSaveButton.addEventListener('click', saveProfileSettings);
    }
    
    // Botón de pestaña de notificaciones
    const notificationsSaveButton = document.querySelector('#notifications-content .btn-primary');
    if (notificationsSaveButton) {
        notificationsSaveButton.addEventListener('click', saveNotificationSettings);
    }
    
    // Botón de pestaña de seguridad
    const securitySaveButton = document.querySelector('#security-content .btn-primary');
    if (securitySaveButton) {
        securitySaveButton.addEventListener('click', saveSecuritySettings);
    }
    
    // Configurar botones de restaurar valores predeterminados
    const resetButtons = document.querySelectorAll('.btn-secondary');
    resetButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (confirm('¿Estás seguro de que deseas restaurar los valores predeterminados?')) {
                const tabContent = this.closest('.tab-content');
                if (tabContent.id === 'profile-content') {
                    loadProfileData();
                } else if (tabContent.id === 'notifications-content') {
                    loadNotificationSettings();
                } else if (tabContent.id === 'security-content') {
                    loadSecuritySettings();
                }
            }
        });
    });
}

/**
 * Guarda la configuración del perfil
 */
function saveProfileSettings() {
    // Obtener datos del formulario
    const profileData = {
        tab: 'profile',
        title: document.getElementById('title').value,
        specialty: document.getElementById('specialty').value,
        fullname: document.getElementById('fullname').value,
        license: document.getElementById('license').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        address: document.getElementById('address').value
    };
    
    // Validar datos
    if (!validateProfileData(profileData)) {
        return;
    }
    
    // Mostrar indicador de carga
    const saveButton = document.querySelector('#profile-content .btn-primary');
    const originalButtonText = saveButton.textContent;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    saveButton.disabled = true;
    
    // Guardar datos
    fetch('/api/guardar-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || 'Perfil actualizado correctamente', 'success');
        } else {
            showNotification(data.message || 'Error al guardar el perfil', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error al guardar el perfil', 'error');
    })
    .finally(() => {
        // Restaurar botón
        saveButton.textContent = originalButtonText;
        saveButton.disabled = false;
    });
}

/**
 * Valida los datos del perfil antes de guardar
 */
function validateProfileData(data) {
    // Validar nombre completo
    if (!data.fullname || data.fullname.trim() === '') {
        showNotification('El nombre completo es obligatorio', 'error');
        return false;
    }
    
    // Validar email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!data.email || !emailRegex.test(data.email)) {
        showNotification('El correo electrónico no es válido', 'error');
        return false;
    }
    
    return true;
}

/**
 * Guarda la configuración de notificaciones
 */
function saveNotificationSettings() {
    // Obtener datos del formulario
    const notificationData = {
        tab: 'notifications',
        notificaciones_email: document.getElementById('email-notifications').checked,
        tiempo_anticipacion: document.getElementById('notification-time').value,
        frecuencia_recordatorios: document.getElementById('reminder-frequency').value,
        alertas_cambios_citas: document.getElementById('cita-changes-alerts').checked,
        alertas_pacientes_nuevos: document.getElementById('new-patients-alerts').checked,
        notificaciones_actualizacion: document.getElementById('update-notifications').checked,
        sonidos_notificacion: document.getElementById('sound-notifications').checked
    };
    
    // Mostrar indicador de carga
    const saveButton = document.querySelector('#notifications-content .btn-primary');
    const originalButtonText = saveButton.textContent;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    saveButton.disabled = true;
    
    // Guardar datos
    fetch('/api/guardar-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(notificationData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || 'Configuración de notificaciones actualizada', 'success');
            
            // Actualizar la configuración de notificaciones en memoria
            NotificationConfig.notificationsEnabled = notificationData.notificaciones_email;
            NotificationConfig.soundEnabled = notificationData.sonidos_notificacion;
            NotificationConfig.tiempoAnticipacion = parseInt(notificationData.tiempo_anticipacion);
            
            // Guardar en localStorage para persistencia
            saveNotificationConfigToLocalStorage();
        } else {
            showNotification(data.message || 'Error al guardar la configuración', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error al guardar la configuración', 'error');
    })
    .finally(() => {
        // Restaurar botón
        saveButton.textContent = originalButtonText;
        saveButton.disabled = false;
    });
}

/**
 * Guarda la configuración de seguridad
 */
function saveSecuritySettings() {
    // Verificar si hay cambio de contraseña
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    // Si hay datos de contraseña, validar y procesar por separado
    if (currentPassword || newPassword || confirmPassword) {
        if (!validatePasswordData(currentPassword, newPassword, confirmPassword)) {
            return;
        }
        
        // Procesar cambio de contraseña
        changePassword(currentPassword, newPassword);
    }
    
    // Obtener datos de seguridad
    const securityData = {
        tab: 'security',
        auth_dos_factores: document.getElementById('auth-dos-factores').checked,
        cierre_sesion_auto: document.getElementById('cierre-sesion-auto').checked,
        tiempo_inactividad: document.getElementById('tiempo-inactividad').value,
        retencion_datos: document.getElementById('retencion-datos').value
    };
    
    // Mostrar indicador de carga
    const saveButton = document.querySelector('#security-content .btn-primary');
    const originalButtonText = saveButton.textContent;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    saveButton.disabled = true;
    
    // Guardar datos
    fetch('/api/guardar-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(securityData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || 'Configuración de seguridad actualizada', 'success');
            
            // Limpiar campos de contraseña
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
        } else {
            showNotification(data.message || 'Error al guardar la configuración', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error al guardar la configuración', 'error');
    })
    .finally(() => {
        // Restaurar botón
        saveButton.textContent = originalButtonText;
        saveButton.disabled = false;
    });
}

/**
 * Valida los datos de cambio de contraseña
 */
function validatePasswordData(currentPassword, newPassword, confirmPassword) {
    // Validar que la contraseña actual esté ingresada
    if (!currentPassword) {
        showNotification('Debe ingresar su contraseña actual', 'error');
        return false;
    }
    
    // Validar que la nueva contraseña cumpla los requisitos
    if (newPassword.length < 8) {
        showNotification('La contraseña debe tener al menos 8 caracteres', 'error');
        return false;
    }
    
    if (!/[A-Z]/.test(newPassword)) {
        showNotification('La contraseña debe contener al menos una letra mayúscula', 'error');
        return false;
    }
    
    if (!/\d/.test(newPassword)) {
        showNotification('La contraseña debe contener al menos un número', 'error');
        return false;
    }
    
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(newPassword)) {
        showNotification('La contraseña debe contener al menos un carácter especial', 'error');
        return false;
    }
    
    // Validar que las contraseñas coincidan
    if (newPassword !== confirmPassword) {
        showNotification('Las contraseñas no coinciden', 'error');
        return false;
    }
    
    return true;
}

/**
 * Procesa el cambio de contraseña
 */
function changePassword(currentPassword, newPassword) {
    fetch('/api/cambiar-contrasena', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || 'Contraseña actualizada correctamente', 'success');
            
            // Limpiar campos
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
        } else {
            showNotification(data.message || 'Error al cambiar la contraseña', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error al cambiar la contraseña', 'error');
    });
}

/**
 * Configura el botón de eliminar cuenta
 */
function setupDeleteAccountButton() {
    const deleteButton = document.getElementById('delete-account-btn');
    if (deleteButton) {
        deleteButton.addEventListener('click', function() {
            // Crear modal para confirmación
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.position = 'fixed';
            modal.style.top = '0';
            modal.style.left = '0';
            modal.style.width = '100vw';
            modal.style.height = '100vh';
            modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            modal.style.display = 'flex';
            modal.style.alignItems = 'center';
            modal.style.justifyContent = 'center';
            modal.style.zIndex = '1000'; // Asegurar que esté sobre todo
            modal.innerHTML = `
                <div class="modal-content" style="background-color: white; padding: 20px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <h3 style="color: #e74a3b; margin-top: 0;">Eliminar cuenta</h3>
                    <p>Esta acción es irreversible. Se eliminarán todos sus datos.</p>
                    <p>Por favor, ingrese su contraseña para confirmar:</p>
                    <input type="password" id="delete-password" class="form-control" style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: flex-end; gap: 10px;">
                        <button id="cancel-delete" class="btn btn-secondary">Cancelar</button>
                        <button id="confirm-delete" class="btn btn-danger">Eliminar cuenta</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Configurar botones
            document.getElementById('cancel-delete').addEventListener('click', function() {
                document.body.removeChild(modal);
            });
            
            document.getElementById('confirm-delete').addEventListener('click', function() {
                const password = document.getElementById('delete-password').value;
                
                if (!password) {
                    alert('Por favor, ingrese su contraseña');
                    return;
                }
                
                // Mostrar indicador de carga
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eliminando...';
                this.disabled = true;
                
                // Enviar solicitud de eliminación
                fetch('/api/eliminar-cuenta', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ password: password })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification(data.message || 'Cuenta eliminada correctamente', 'success');
                        
                        // Redireccionar al login después de unos segundos
                        setTimeout(function() {
                            window.location.href = '/login';
                        }, 2000);
                    } else {
                        alert(data.message || 'Error al eliminar la cuenta');
                        this.textContent = 'Eliminar cuenta';
                        this.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error al eliminar la cuenta');
                    this.textContent = 'Eliminar cuenta';
                    this.disabled = false;
                });
            });
        });
    }
}

/**
 * Muestra una notificación al usuario
 */
function showNotification(message, type = 'success') {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.className = 'notification ' + type;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.padding = '15px 20px';
    notification.style.borderRadius = '4px';
    notification.style.backgroundColor = type === 'success' ? '#1cc88a' : 
                                         type === 'error' ? '#e74a3b' : 
                                         type === 'warning' ? '#f6c23e' : '#4e73df';
    notification.style.color = 'white';
    notification.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
    notification.style.opacity = '0';
    notification.style.transform = 'translateX(50px)';
    notification.style.transition = 'opacity 0.3s, transform 0.3s';
    
    // Agregar icono según el tipo
    const icon = document.createElement('i');
    icon.className = type === 'success' ? 'fas fa-check-circle' : 
                      type === 'error' ? 'fas fa-exclamation-circle' :
                      type === 'warning' ? 'fas fa-exclamation-triangle' : 'fas fa-info-circle';
    icon.style.marginRight = '10px';
    notification.appendChild(icon);
    
    // Agregar mensaje
    const text = document.createTextNode(message);
    notification.appendChild(text);
    
    // Añadir al DOM
    document.body.appendChild(notification);
    
    // Mostrar con animación
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // Desaparecer después de 5 segundos
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(50px)';
        
        // Eliminar del DOM después de la animación
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 5000);
    
    // Reproducir sonido si está habilitado y es una notificación de tipo warning
    if (type === 'warning' && NotificationConfig.soundEnabled) {
        notificationAudio.play().catch(e => {
            console.warn('No se pudo reproducir el sonido de notificación:', e);
        });
    }
}




// Configurar botón de programación de notificaciones
const programNotificationsBtn = document.getElementById('program-notifications-btn');
if (programNotificationsBtn) {
    programNotificationsBtn.addEventListener('click', function() {
        // Mostrar estado
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Programando...';
        this.disabled = true;
        
        // Enviar solicitud
        fetch('/api/programar-notificaciones', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error al programar notificaciones', 'error');
        })
        .finally(() => {
            // Restaurar botón
            this.innerHTML = '<i class="fas fa-tasks"></i> Programar notificaciones';
            this.disabled = false;
        });
    });
}