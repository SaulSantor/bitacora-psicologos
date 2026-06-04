// theme.js - Controla el modo oscuro

// Función para verificar si el navegador/SO prefiere el modo oscuro
function getPreferredTheme() {
    // Primero chequea si hay una preferencia guardada
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        return savedTheme;
    }
    
    // Si no hay preferencia guardada, detecta la preferencia del sistema
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

// Función para aplicar el tema
function applyTheme(theme) {
    if (theme === 'dark') {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    
    // Guarda la preferencia
    localStorage.setItem('theme', theme);
    
    // Actualiza el estado del botón
    updateToggleButton(theme);
}

// Función para actualizar el estado visual del botón
function updateToggleButton(theme) {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (!toggleBtn) return;
    
    if (theme === 'dark') {
        toggleBtn.setAttribute('aria-label', 'Cambiar a modo claro');
    } else {
        toggleBtn.setAttribute('aria-label', 'Cambiar a modo oscuro');
    }
}

// Función para cambiar el tema
function toggleTheme() {
    const currentTheme = localStorage.getItem('theme') || getPreferredTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(newTheme);
}

// Inicializar tema al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    // Aplicar el tema inicial
    const initialTheme = getPreferredTheme();
    applyTheme(initialTheme);
    
    // Agregar event listener al botón
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleTheme);
    }
    
    // Escuchar cambios en la preferencia del sistema
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
});