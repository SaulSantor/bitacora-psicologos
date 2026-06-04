/**
 * Sistema de Notificaciones para PsychCalendar
 * Este archivo maneja las notificaciones en tiempo real para citas próximas
 * VERSIÓN REVISADA - solución a problemas de alcance
 */

// Definir el objeto de configuración global
window.NotificationConfig = {
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

// Crear el objeto de audio global
window.notificationAudio = new Audio(window.NotificationConfig.notificationSound);

/**
 * Formatea el tiempo restante en un texto legible
 */
window.formatTiempoRestante = function(minutos) {
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
};

/**
 * Muestra una notificación genérica en la aplicación
 */
window.showNotification = function(message, type = 'info') {
    console.log('Mostrando notificación:', message, type);
    
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
    notification.style.maxWidth = '350px';
    
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
    if (type === 'warning' && window.NotificationConfig.soundEnabled) {
        window.notificationAudio.play().catch(e => {
            console.warn('No se pudo reproducir el sonido de notificación:', e);
        });
    }
};

/**
 * Muestra una notificación para una cita específica
 */
window.showAppointmentNotification = function(cita) {
    // Obtener nombre del paciente y tiempo restante formateado
    const pacienteNombre = cita.paciente || 'Paciente';
    const tiempoRestante = window.formatTiempoRestante(cita.minutos_restantes);
    
    // Generar título y cuerpo de la notificación
    const titulo = `Cita próxima: ${pacienteNombre}`;
    const cuerpo = `Tienes una cita ${tiempoRestante} (${cita.hora}).
Tipo: ${cita.tipo || 'No especificado'}
Duración: ${cita.duracion || '60'} minutos`;

    // Mostrar notificación en la aplicación
    window.showNotification(titulo + ' - ' + cuerpo, 'warning');
    
    // Mostrar notificación de escritorio si tenemos permiso
    if (window.NotificationConfig.permissionGranted) {
        try {
            const notification = new Notification(titulo, {
                body: cuerpo,
                icon: window.NotificationConfig.notificationIcon
            });
            
            // Redirigir al calendario al hacer clic en la notificación
            notification.onclick = function() {
                window.focus();
                if (window.location.pathname !== '/psicologo') {
                    window.location.href = '/psicologo';
                }
            };
            
            // Reproducir sonido si está habilitado
            if (window.NotificationConfig.soundEnabled) {
                window.notificationAudio.play().catch(e => {
                    console.warn('No se pudo reproducir el sonido de notificación:', e);
                });
            }
        } catch (e) {
            console.error('Error al mostrar notificación de escritorio:', e);
        }
    }
};

/**
 * Guardar la configuración en localStorage
 */
window.saveNotificationConfigToLocalStorage = function() {
    const config = {
        notificationsEnabled: window.NotificationConfig.notificationsEnabled,
        soundEnabled: window.NotificationConfig.soundEnabled,
        tiempoAnticipacion: window.NotificationConfig.tiempoAnticipacion
    };
    
    localStorage.setItem('notificationConfig', JSON.stringify(config));
    console.log('Configuración guardada en localStorage:', config);
};

/**
 * Función auxiliar para cargar solo desde localStorage
 */
window.loadConfigFromLocalStorage = function() {
    try {
        const savedConfig = localStorage.getItem('notificationConfig');
        if (savedConfig) {
            const config = JSON.parse(savedConfig);
            console.log('Configuración cargada de localStorage:', config);
            
            window.NotificationConfig.notificationsEnabled = config.notificationsEnabled !== undefined 
                ? config.notificationsEnabled 
                : window.NotificationConfig.notificationsEnabled;
            
            window.NotificationConfig.soundEnabled = config.soundEnabled !== undefined 
                ? config.soundEnabled 
                : window.NotificationConfig.soundEnabled;
                
            window.NotificationConfig.tiempoAnticipacion = config.tiempoAnticipacion || window.NotificationConfig.tiempoAnticipacion;
        } else {
            console.log('No hay configuración guardada en localStorage');
        }
    } catch (e) {
        console.error('Error al cargar configuración de notificaciones desde localStorage:', e);
    }
};

/**
 * Actualizar la UI con la configuración actual
 */
window.updateNotificationUI = function() {
    // Verificar si estamos en la página de configuración
    const emailSwitch = document.getElementById('email-notifications');
    const soundSwitch = document.getElementById('sound-notifications');
    const notificationTimeSelect = document.getElementById('notification-time');
    
    if (emailSwitch) {
        emailSwitch.checked = window.NotificationConfig.notificationsEnabled;
        console.log('UI actualizada: email-notifications =', window.NotificationConfig.notificationsEnabled);
    }
    
    if (soundSwitch) {
        soundSwitch.checked = window.NotificationConfig.soundEnabled;
        console.log('UI actualizada: sound-notifications =', window.NotificationConfig.soundEnabled);
    }
    
    if (notificationTimeSelect) {
        // Intentar seleccionar el valor correcto
        const options = notificationTimeSelect.options;
        for (let i = 0; i < options.length; i++) {
            if (parseInt(options[i].value) === window.NotificationConfig.tiempoAnticipacion) {
                notificationTimeSelect.selectedIndex = i;
                console.log('UI actualizada: notification-time =', window.NotificationConfig.tiempoAnticipacion);
                break;
            }
        }
    }
};

/**
 * Verifica si hay notificaciones del sistema pendientes
 */
window.checkSystemNotifications = function() {
    fetch('/api/notificaciones/pendientes')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.notificaciones && data.notificaciones.length > 0) {
                // Procesar cada notificación
                data.notificaciones.forEach(notif => {
                    window.showNotification(
                        notif.contenido, 
                        notif.prioridad === 'alta' ? 'warning' : 'info'
                    );
                });
            }
        })
        .catch(error => {
            console.error('Error al verificar notificaciones del sistema:', error);
        });
};

/**
 * Verifica si hay citas próximas y notifica si es necesario
 */
window.checkUpcomingAppointments = function() {
    if (!window.NotificationConfig.notificationsEnabled) {
        console.log('Notificaciones deshabilitadas, saltando verificación');
        return; // No hacer nada si las notificaciones están deshabilitadas
    }

    console.log('Verificando citas próximas con configuración:', {
        notificationsEnabled: window.NotificationConfig.notificationsEnabled,
        soundEnabled: window.NotificationConfig.soundEnabled,
        tiempoAnticipacion: window.NotificationConfig.tiempoAnticipacion
    });

    fetch('/api/proximas-citas')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Respuesta del servidor (citas próximas):', data);
            
            if (data.success && data.citas && data.citas.length > 0) {
                // Actualizar configuración si viene del servidor
                if (data.config) {
                    console.log('Actualizando configuración desde el servidor:', data.config);
                    
                    window.NotificationConfig.tiempoAnticipacion = data.config.tiempo_anticipacion || window.NotificationConfig.tiempoAnticipacion;
                    window.NotificationConfig.soundEnabled = data.config.sonidos_notificacion !== undefined 
                        ? data.config.sonidos_notificacion 
                        : window.NotificationConfig.soundEnabled;
                    
                    // Guardar en localStorage
                    window.saveNotificationConfigToLocalStorage();
                }

                // Procesar cada cita que necesita notificación
                data.citas.forEach(cita => {
                    if (!window.NotificationConfig.citasNotificadas.has(cita.id)) {
                        console.log('Mostrando notificación para cita:', cita);
                        
                        // Notificar al usuario
                        window.showAppointmentNotification(cita);
                        
                        // Marcar como notificada
                        window.NotificationConfig.citasNotificadas.add(cita.id);
                        
                        // También informar al servidor que se ha notificado
                        fetch(`/api/marcar-notificada/${cita.id}`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            }
                        }).catch(err => {
                            console.error('Error al marcar cita como notificada:', err);
                        });
                    }
                });
            } else {
                console.log('No hay citas próximas que requieran notificación');
            }
        })
        .catch(error => {
            console.error('Error al verificar citas próximas:', error);
        });
};

/**
 * Inicia la verificación periódica de citas próximas
 */
window.startCheckingForAppointments = function() {
    console.log('Iniciando verificación periódica de citas...');
    
    // Verificar inmediatamente al cargar
    window.checkUpcomingAppointments();

    // Configurar verificación periódica
    if (window.NotificationConfig.checkTimeout) {
        clearInterval(window.NotificationConfig.checkTimeout);
    }

    window.NotificationConfig.checkTimeout = setInterval(() => {
        window.checkUpcomingAppointments();
    }, window.NotificationConfig.checkInterval);

    console.log(`Sistema de notificaciones iniciado. Verificando cada ${window.NotificationConfig.checkInterval / 1000} segundos.`);
};

/**
 * Inicia la verificación periódica de notificaciones del sistema
 */
window.startCheckingForSystemNotifications = function() {
    // Verificar cada 2 minutos
    setInterval(() => {
        window.checkSystemNotifications();
    }, 120000); // 2 minutos
    
    // También verificar inmediatamente
    window.checkSystemNotifications();
};

/**
 * Carga la configuración de notificaciones del usuario
 */
window.loadUserNotificationSettings = function() {
    console.log('Cargando configuración de notificaciones...');
    
    // Primero cargar configuración desde localStorage
    window.loadConfigFromLocalStorage();
    
    // Luego intentar cargar desde el servidor
    fetch('/api/obtener-notification-config')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('Configuración cargada del servidor:', data);
                
                // Actualizar configuración
                window.NotificationConfig.notificationsEnabled = data.notificaciones_email;
                window.NotificationConfig.soundEnabled = data.sonidos_notificacion;
                window.NotificationConfig.tiempoAnticipacion = parseInt(data.tiempo_anticipacion);
                
                // Guardar en localStorage para uso futuro
                window.saveNotificationConfigToLocalStorage();
                
                // También actualizar UI si estamos en la página de configuración
                window.updateNotificationUI();
            }
        })
        .catch(error => {
            console.error('Error al cargar configuración del servidor:', error);
            // Si falla, usar lo que hay en localStorage (ya cargado)
        });
};

/**
 * Inicializa el sistema de notificaciones
 */
window.initNotificationSystem = function() {
    console.log('Inicializando sistema de notificaciones...');

    // Verificar si el navegador soporta notificaciones
    if (!('Notification' in window)) {
        console.warn('Este navegador no soporta notificaciones de escritorio');
        return;
    }

    // Solicitar permiso para notificaciones
    if (Notification.permission === 'granted') {
        window.NotificationConfig.permissionGranted = true;
        window.startCheckingForAppointments();
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                window.NotificationConfig.permissionGranted = true;
                window.startCheckingForAppointments();
            }
        });
    }

    // Cargar configuración del usuario
    window.loadUserNotificationSettings();

    // Iniciar verificación periódica de citas
    window.startCheckingForAppointments();
    
    // Iniciar verificación periódica de notificaciones del sistema
    window.startCheckingForSystemNotifications();
};

// Función de diagnóstico para verificar el sistema de notificaciones
window.diagnosticarNotificaciones = function() {
    console.group('🔍 Diagnóstico del Sistema de Notificaciones');
    
    // Verificar si NotificationConfig está definido
    if (typeof window.NotificationConfig === 'undefined') {
        console.error('❌ NotificationConfig no está definido. Verifica que el archivo notifications.js esté cargado correctamente.');
        console.groupEnd();
        return;
    }
    
    console.log('✅ NotificationConfig está definido');
    console.log('Configuración actual:', {
        notificationsEnabled: window.NotificationConfig.notificationsEnabled,
        soundEnabled: window.NotificationConfig.soundEnabled,
        tiempoAnticipacion: window.NotificationConfig.tiempoAnticipacion,
        permissionGranted: window.NotificationConfig.permissionGranted
    });
    
    // Verificar permisos del navegador
    console.log('Permisos de notificación del navegador:', Notification.permission);
    
    // Verificar localStorage
    try {
        const savedConfig = localStorage.getItem('notificationConfig');
        if (savedConfig) {
            console.log('✅ Configuración en localStorage:', JSON.parse(savedConfig));
        } else {
            console.warn('⚠️ No hay configuración guardada en localStorage');
        }
    } catch (e) {
        console.error('❌ Error al leer localStorage:', e);
    }
    
    // Verificar funciones principales
    const funciones = [
        'initNotificationSystem',
        'loadUserNotificationSettings',
        'startCheckingForAppointments',
        'checkUpcomingAppointments',
        'showNotification',
        'showAppointmentNotification'
    ];
    
    funciones.forEach(func => {
        if (typeof window[func] === 'function') {
            console.log(`✅ Función ${func} está definida`);
        } else {
            console.error(`❌ Función ${func} no está definida`);
        }
    });
    
    // Verificar si estamos en la página de configuración
    const isConfigPage = window.location.pathname.includes('/config');
    console.log('¿Estamos en la página de configuración?', isConfigPage);
    
    if (isConfigPage) {
        // Verificar elementos de la UI
        const elementos = [
            'email-notifications',
            'sound-notifications',
            'notification-time',
            'reminder-frequency',
            'cita-changes-alerts',
            'new-patients-alerts',
            'update-notifications',
        ];
        
        elementos.forEach(id => {
            const elemento = document.getElementById(id);
            if (elemento) {
                console.log(`✅ Elemento ${id} encontrado:`, elemento.checked !== undefined ? elemento.checked : elemento.value);
            } else {
                console.warn(`⚠️ Elemento ${id} no encontrado`);
            }
        });
    }
    
    // Probar una llamada a la API
    console.log('Probando conexión con la API...');
    fetch('/api/obtener-notification-config')
        .then(response => {
            console.log('Respuesta API status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('✅ Respuesta API:', data);
        })
        .catch(error => {
            console.error('❌ Error en la API:', error);
        });
    
    // Mostrar notificación de prueba
    console.log('Creando notificación de prueba...');
    window.showNotification('Notificación de prueba de diagnóstico', 'info');
    
    console.groupEnd();
    
    return "Diagnóstico completado. Revisa la consola para ver los resultados.";
};

// Iniciar el sistema de notificaciones cuando el DOM esté cargado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar sistema de notificaciones
    console.log('DOM cargado, inicializando sistema de notificaciones...');
    window.initNotificationSystem();
});

// Forzar una comprobación rápida para asegurarnos de que todas las funciones están disponibles
// Este código se ejecutará tan pronto como se cargue el script
(function verificarFuncionesDisponibles() {
    console.log('Verificando disponibilidad de funciones de notificación...');
    
    const funcionesCriticas = [
        'initNotificationSystem', 
        'loadUserNotificationSettings', 
        'startCheckingForAppointments', 
        'checkUpcomingAppointments'
    ];
    
    let todasDisponibles = true;
    funcionesCriticas.forEach(func => {
        if (typeof window[func] !== 'function') {
            console.error(`❌ CRÍTICO: Función ${func} no está disponible globalmente`);
            todasDisponibles = false;
        }
    });
    
    if (todasDisponibles) {
        console.log('✅ Todas las funciones críticas están disponibles globalmente');
    } else {
        console.error('❌ Algunas funciones críticas no están disponibles. El sistema de notificaciones podría no funcionar correctamente.');
    }
})();