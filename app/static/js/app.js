/* ============================================================
   MediCart — Main JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initMobileNav();
    initFlashMessages();
    initScrollAnimations();
    initLucideIcons();
});


/* ---- Theme Toggle (Dark Mode) ---- */
function initThemeToggle() {
    const toggle = document.getElementById('theme-toggle');
    const html = document.documentElement;
    const moonIcon = document.getElementById('theme-icon-moon');
    const sunIcon = document.getElementById('theme-icon-sun');

    // Load saved theme or respect system preference
    const savedTheme = localStorage.getItem('medicart-theme') || localStorage.getItem('campuskart-theme');
    if (savedTheme) {
        html.setAttribute('data-theme', savedTheme);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        html.setAttribute('data-theme', 'dark');
    }

    updateThemeIcons();

    if (toggle) {
        toggle.addEventListener('click', () => {
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('medicart-theme', next);
            updateThemeIcons();
        });
    }

    function updateThemeIcons() {
        const isDark = html.getAttribute('data-theme') === 'dark';
        if (moonIcon && sunIcon) {
            moonIcon.style.display = isDark ? 'none' : 'block';
            sunIcon.style.display = isDark ? 'block' : 'none';
        }
    }
}


/* ---- Mobile Navigation ---- */
function initMobileNav() {
    const toggle = document.getElementById('navbar-toggle');
    const nav = document.getElementById('navbar-nav');

    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            const isOpen = nav.classList.toggle('active');
            toggle.setAttribute('aria-expanded', isOpen);
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!toggle.contains(e.target) && !nav.contains(e.target)) {
                nav.classList.remove('active');
                toggle.setAttribute('aria-expanded', 'false');
            }
        });
    }
}


/* ---- Flash Messages Auto-Dismiss ---- */
function initFlashMessages() {
    const container = document.getElementById('flash-messages');
    if (!container) return;

    const messages = container.querySelectorAll('.flash-message');
    messages.forEach((msg, index) => {
        setTimeout(() => {
            msg.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => msg.remove(), 300);
        }, 3000 + (index * 500));
    });
}


/* ---- Scroll-Triggered Fade-In Animations ---- */
function initScrollAnimations() {
    const elements = document.querySelectorAll('.animate-fade-in');
    if (!elements.length) return;

    // Initially hide elements
    elements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(16px)';
    });

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const delay = el.classList.contains('animate-fade-in-delay-1') ? '0.1s' :
                              el.classList.contains('animate-fade-in-delay-2') ? '0.2s' :
                              el.classList.contains('animate-fade-in-delay-3') ? '0.3s' :
                              el.classList.contains('animate-fade-in-delay-4') ? '0.4s' : '0s';

                el.style.transition = `opacity 0.6s ease ${delay}, transform 0.6s ease ${delay}`;
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    elements.forEach(el => observer.observe(el));
}


/* ---- Initialize Lucide Icons ---- */
function initLucideIcons() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    } else {
        // Retry after script loads (deferred)
        window.addEventListener('load', () => {
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        });
    }
}


/* ---- Toast Notification Utility ---- */
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.classList.add('fade-out'); setTimeout(() => this.parentElement.remove(), 300)">&times;</button>
    `;

    container.appendChild(toast);

    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, 4000);
}


/* ---- Wishlist Toggle Utility ---- */
function toggleWishlist(productId, btnElement) {
    if (!productId || !btnElement) return;

    fetch(`/wishlist/toggle/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 401) {
            showToast('Please log in to save items to your wishlist', 'error');
            setTimeout(() => {
                window.location.href = '/auth/login';
            }, 1200);
            return null;
        }
        return response.json();
    })
    .then(data => {
        if (!data) return;
        
        if (data.status === 'added') {
            const icons = btnElement.querySelectorAll('i, svg');
            icons.forEach(icon => {
                icon.setAttribute('fill', 'currentColor');
            });
            btnElement.style.color = 'var(--accent, #e11d48)';
            btnElement.setAttribute('title', 'Remove from Wishlist');
            const textSpan = btnElement.querySelector('.wishlist-text');
            if (textSpan) textSpan.innerText = 'Saved to Wishlist';
            showToast(data.message || 'Added to wishlist', 'success');
        } else if (data.status === 'removed') {
            const icons = btnElement.querySelectorAll('i, svg');
            icons.forEach(icon => {
                icon.setAttribute('fill', 'none');
                icon.removeAttribute('fill');
            });
            btnElement.style.color = 'var(--text-muted, #94a3b8)';
            btnElement.setAttribute('title', 'Add to Wishlist');
            const textSpan = btnElement.querySelector('.wishlist-text');
            if (textSpan) textSpan.innerText = 'Save to Wishlist';
            
            // Check if on wishlist page and remove card smoothly
            const card = btnElement.closest('.card, .wishlist-item');
            if (window.location.pathname.startsWith('/wishlist') && card) {
                card.style.opacity = '0';
                card.style.transform = 'scale(0.9)';
                setTimeout(() => {
                    card.remove();
                    const remaining = document.querySelectorAll('.grid .card');
                    if (remaining.length === 0) {
                        location.reload();
                    }
                }, 300);
            }
            showToast(data.message || 'Removed from wishlist', 'info');
        } else {
            showToast(data.message || 'An error occurred', 'error');
        }
    })
    .catch(err => {
        console.error('Wishlist error:', err);
        showToast('Failed to connect to server', 'error');
    });
}

