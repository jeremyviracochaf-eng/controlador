/* ============================================================
   SCRIPT GLOBAL - CONTROL DE ACCESO RFID
   ============================================================ */

document.addEventListener('DOMContentLoaded', function() {
    initializeSidebar();
    initializeTheme();
    initializeAnimations();
});

/* ============================================================
   SIDEBAR MOBILE
   ============================================================ */

function initializeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarClose = document.getElementById('sidebar-close');
    const overlay = document.getElementById('sidebar-overlay');
    
    // Toggle sidebar
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
            overlay?.classList.toggle('active');
        });
    }
    
    // Close sidebar
    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
            overlay?.classList.remove('active');
        });
    }
    
    // Close on overlay click
    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
        });
    }
    
    // Close on nav item click (mobile)
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth < 768) {
                sidebar.classList.remove('mobile-open');
                overlay?.classList.remove('active');
            }
        });
    });
    
    // Set active nav item
    const currentPath = window.location.pathname;
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href === currentPath || currentPath.includes(href.split('/')[1])) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

/* ============================================================
   TEMA
   ============================================================ */

function initializeTheme() {
    const theme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
}

/* ============================================================
   ANIMACIONES
   ============================================================ */

function initializeAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.card, .stat-card').forEach(el => {
        observer.observe(el);
    });
}

/* ============================================================
   FORMULARIOS
   ============================================================ */

function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    let isValid = true;
    const inputs = form.querySelectorAll('[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            showError(input, 'Este campo es requerido');
            isValid = false;
        }
    });
    
    return isValid;
}

function showError(element, message) {
    element.classList.add('error');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-error';
    errorDiv.textContent = message;
    element.parentNode.appendChild(errorDiv);
}

function clearError(element) {
    element.classList.remove('error');
    const errorDiv = element.parentNode.querySelector('.form-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

/* ============================================================
   ALERTAS
   ============================================================ */

function showAlert(message, type = 'primary', duration = 5000) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} animate-fade-in`;
    alert.innerHTML = `
        <div class="alert-icon">
            <i class="fas fa-${getIconByType(type)}"></i>
        </div>
        <div class="alert-content">
            <div class="alert-message">${message}</div>
        </div>
    `;
    
    const container = document.querySelector('.content-area') || document.body;
    container.insertBefore(alert, container.firstChild);
    
    if (duration > 0) {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, duration);
    }
    
    return alert;
}

function getIconByType(type) {
    const icons = {
        'primary': 'info-circle',
        'success': 'check-circle',
        'danger': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'circle-info'
    };
    return icons[type] || icons['primary'];
}

/* ============================================================
   MODALES
   ============================================================ */

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

/* ============================================================
   UTILIDADES
   ============================================================ */

function formatDate(date) {
    return new Date(date).toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatTime(date) {
    return new Date(date).toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateTime(date) {
    return new Date(date).toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/* ============================================================
   BÚSQUEDA Y FILTROS
   ============================================================ */

function filterTable(tableId, inputId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    
    if (!input || !table) return;
    
    input.addEventListener('keyup', function() {
        const searchTerm = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    });
}

/* ============================================================
   COPIAR AL PORTAPAPELES
   ============================================================ */

function copyToClipboard(text, buttonElement) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = buttonElement.textContent;
        buttonElement.textContent = '✓ Copiado';
        buttonElement.classList.add('copied');
        
        setTimeout(() => {
            buttonElement.textContent = originalText;
            buttonElement.classList.remove('copied');
        }, 2000);
    }).catch(() => {
        showAlert('No se pudo copiar', 'danger');
    });
}

/* ============================================================
   CONFIRMACIÓN
   ============================================================ */

function confirm(message, onConfirm, onCancel) {
    if (window.confirm(message)) {
        onConfirm();
    } else if (onCancel) {
        onCancel();
    }
}
