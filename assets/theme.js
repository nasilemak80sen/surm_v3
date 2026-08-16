/*
╔════════════════════════════════════════════════════════════════════════╗
║                    SURM Toolkit v2.0 — Client Script                  ║
║                     Modern • Performant • Professional                 ║
╚════════════════════════════════════════════════════════════════════════╝
*/

'use strict';

/**
 * SURM Toolkit Theme Engine
 * Handles interactive enhancements, animations, and UX improvements
 */

const SURMTheme = (() => {
    
    // ═════════════════════════════════════════════════════════════════
    // Configuration
    // ═════════════════════════════════════════════════════════════════
    
    const config = {
        debounceDelay: 150,
        rippleOpacity: 0.25,
        animationDuration: 300,
    };

    // ═════════════════════════════════════════════════════════════════
    // Utility Functions
    // ═════════════════════════════════════════════════════════════════
    
    /**
     * Debounce function for performance optimization
     */
    const debounce = (fn, delay) => {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    };

    /**
     * Check if element is in viewport
     */
    const isElementInViewport = (el) => {
        const rect = el.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    };

    // ═════════════════════════════════════════════════════════════════
    // Button Enhancements
    // ═════════════════════════════════════════════════════════════════
    
    const enhanceButtons = () => {
        const buttons = document.querySelectorAll('button:not([data-theme-enhanced])');
        
        buttons.forEach(btn => {
            btn.dataset.themeEnhanced = 'true';
            
            // Add click ripple effect
            btn.addEventListener('click', function (e) {
                const ripple = createRipple(e, this);
                if (ripple) this.appendChild(ripple);
            });
            
            // Add press animation
            btn.addEventListener('mousedown', function () {
                this.style.transform = 'scale(0.98)';
            });
            
            btn.addEventListener('mouseup', function () {
                this.style.transform = '';
            });
            
            btn.addEventListener('mouseleave', function () {
                this.style.transform = '';
            });
        });
    };

    /**
     * Create ripple effect for buttons
     */
    const createRipple = (event, button) => {
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            border-radius: 50%;
            background: rgba(255, 255, 255, ${config.rippleOpacity});
            left: ${x}px;
            top: ${y}px;
            pointer-events: none;
            animation: ripple-animation ${config.animationDuration}ms ease-out;
        `;
        
        ripple.addEventListener('animationend', () => ripple.remove());
        return ripple;
    };

    // ═════════════════════════════════════════════════════════════════
    // Card Animations
    // ═════════════════════════════════════════════════════════════════
    
    const observeCards = () => {
        const cards = document.querySelectorAll('.card, [class*="card"]');
        
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.animation = 'fadeIn 0.3s ease-out';
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1 });
            
            cards.forEach(card => observer.observe(card));
        }
    };

    // ═════════════════════════════════════════════════════════════════
    // Tab Navigation Enhancement
    // ═════════════════════════════════════════════════════════════════
    
    const enhanceTabs = () => {
        const tabButtons = document.querySelectorAll('[role="tab"]');
        
        tabButtons.forEach(tab => {
            tab.addEventListener('click', () => {
                // Smooth scroll into view if needed
                setTimeout(() => {
                    if (!isElementInViewport(tab)) {
                        tab.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                }, 100);
            });
        });
    };

    // ═════════════════════════════════════════════════════════════════
    // Form Input Enhancement
    // ═════════════════════════════════════════════════════════════════
    
    const enhanceInputs = () => {
        const inputs = document.querySelectorAll('input:not([data-theme-enhanced]), select:not([data-theme-enhanced]), textarea:not([data-theme-enhanced])');
        
        inputs.forEach(input => {
            input.dataset.themeEnhanced = 'true';
            
            // Add focus indicator
            input.addEventListener('focus', function () {
                this.parentElement?.style.setProperty('box-shadow', '0 0 0 3px rgba(31, 107, 58, 0.1)');
            });
            
            input.addEventListener('blur', function () {
                this.parentElement?.style.removeProperty('box-shadow');
            });
        });
    };

    // ═════════════════════════════════════════════════════════════════
    // Progress Bar Animation
    // ═════════════════════════════════════════════════════════════════
    
    const animateProgressBars = () => {
        const progressBars = document.querySelectorAll('.progress-fill');
        
        progressBars.forEach(bar => {
            const width = bar.style.width;
            bar.style.width = '0';
            
            // Trigger reflow to restart animation
            void bar.offsetWidth;
            bar.style.width = width;
        });
    };

    // ═════════════════════════════════════════════════════════════════
    // Smooth Scrolling
    // ═════════════════════════════════════════════════════════════════
    
    const enableSmoothScroll = () => {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                const target = document.querySelector(href);
                
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    };

    // ═════════════════════════════════════════════════════════════════
    // Performance Monitoring
    // ═════════════════════════════════════════════════════════════════
    
    const logPerformanceMetrics = () => {
        if ('PerformanceObserver' in window) {
            try {
                const perfData = window.performance.timing;
                const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
                
                if (pageLoadTime > 0) {
                    console.log(`📊 SURM Toolkit loaded in ${pageLoadTime}ms`);
                }
            } catch (e) {
                // Silently fail if performance API unavailable
            }
        }
    };

    // ═════════════════════════════════════════════════════════════════
    // MutationObserver for Dynamic Content
    // ═════════════════════════════════════════════════════════════════
    
    const observeDynamicContent = () => {
        const observer = new MutationObserver(debounce(() => {
            enhanceButtons();
            enhanceInputs();
            animateProgressBars();
            observeCards();
        }, config.debounceDelay));
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'style'],
        });
    };

    // ═════════════════════════════════════════════════════════════════
    // Keyboard Navigation
    // ═════════════════════════════════════════════════════════════════
    
    const enhanceKeyboardNav = () => {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + S for save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                const saveBtn = document.querySelector('[data-testid="baseButton"][kind="primary"]') ||
                               document.querySelector('button:contains("Save")');
                if (saveBtn) saveBtn.click();
            }
        });
    };

    // ═════════════════════════════════════════════════════════════════
    // Initialization
    // ═════════════════════════════════════════════════════════════════
    
    const init = () => {
        // Wait for DOM to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeTheme);
        } else {
            initializeTheme();
        }
    };

    const initializeTheme = () => {
        console.log('🎨 SURM Toolkit Theme Engine v2.0 Initializing...');
        
        // Initial enhancements
        enhanceButtons();
        enhanceInputs();
        enhanceTabs();
        observeCards();
        animateProgressBars();
        enableSmoothScroll();
        enhanceKeyboardNav();
        logPerformanceMetrics();
        
        // Observe for dynamic content
        observeDynamicContent();
        
        console.log('✅ SURM Toolkit Theme Engine Ready');
    };

    // ═════════════════════════════════════════════════════════════════
    // Public API
    // ═════════════════════════════════════════════════════════════════
    
    return {
        init,
        version: '2.0',
        config,
    };
})();

// ═════════════════════════════════════════════════════════════════════════
// CSS Animations (Injected)
// ═════════════════════════════════════════════════════════════════════════

const styleSheet = document.createElement('style');
styleSheet.textContent = `
    @keyframes ripple-animation {
        to {
            opacity: 0;
            transform: scale(4);
        }
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    button {
        position: relative;
        overflow: hidden;
    }
`;
document.head.appendChild(styleSheet);

// ═════════════════════════════════════════════════════════════════════════
// Start the engine!
// ═════════════════════════════════════════════════════════════════════════

SURMTheme.init();