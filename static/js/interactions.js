/* ============================================================
   PhotoLens — Apple-Style Interactions & Motion Design
   Scroll reveals · Spring physics · Glass effects · Micro-interactions
   ============================================================ */

// ===== 1. Scroll Progress Bar =====
(function initScrollProgress() {
    const bar = document.createElement('div');
    bar.className = 'scroll-progress';
    bar.innerHTML = '<div class="scroll-progress-fill"></div>';
    document.body.prepend(bar);

    const fill = bar.querySelector('.scroll-progress-fill');

    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(() => {
                const h = document.documentElement;
                const pct = h.scrollHeight - h.clientHeight;
                fill.style.transform = `scaleX(${pct > 0 ? h.scrollTop / pct : 0})`;
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });
})();


// ===== 2. Intersection Observer — Scroll-Triggered Reveals =====
(function initScrollReveals() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                // Staggered children within the target
                const children = entry.target.querySelectorAll('.reveal-child');
                children.forEach((child, i) => {
                    setTimeout(() => child.classList.add('revealed'), i * 60);
                });
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    // Observe cards after they're rendered
    const observeCards = () => {
        document.querySelectorAll('.card:not(.upload-card), .dimension-item, .mbti-card, .audience-card, .mood-banner').forEach(el => {
            if (!el.classList.contains('reveal-ready')) {
                el.classList.add('reveal-ready');
                observer.observe(el);
            }
        });
    };

    // Re-observe after results render
    const originalRenderScores = window._renderScoresHook;
    const mutationObserver = new MutationObserver(() => {
        setTimeout(observeCards, 200);
    });
    mutationObserver.observe(document.getElementById('results-section') || document.body, {
        childList: true, subtree: true, attributes: true, attributeFilter: ['class']
    });

    // Initial observation
    observeCards();
})();


// ===== 3. Spring Physics Count-Up =====
function springCountUp(el, from, to, duration = 1200) {
    if (!el) return;
    if (isNaN(to) || isNaN(from)) return;
    const start = performance.now();
    const stiffness = 180;
    const damping = 12;
    const mass = 1;

    let value = from;
    let velocity = 0;

    function animate(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);

        // Spring physics toward target
        const force = (to - value) * stiffness / mass;
        const accel = force - velocity * damping / mass;
        velocity += accel * 0.016;
        value += velocity * 0.016;

        // Blend with linear progress to ensure we hit target
        const display = progress < 0.9
            ? value
            : value + (to - value) * (progress - 0.9) * 10;

        el.textContent = Math.round(Math.max(0, Math.min(to, display)));

        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            el.textContent = to;
        }
    }

    requestAnimationFrame(animate);
}


// ===== 4. Morph Loading to Content =====
(function initLoadingMorph() {
    // Watch for analysis completion — when loading-section gets hidden
    const loadingObserver = new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.target.id === 'loading-section' && m.target.classList.contains('hidden')) {
                // Loading finished, trigger score count-up
                setTimeout(() => {
                    const scoreEl = document.getElementById('overall-score');
                    if (scoreEl && scoreEl.textContent !== '--') {
                        const target = parseInt(scoreEl.textContent);
                        if (!isNaN(target)) {
                            springCountUp(scoreEl, 0, target, 1500);
                        }
                    }

                    // Stagger dimension items
                    const dims = document.querySelectorAll('.dimension-item');
                    dims.forEach((dim, i) => {
                        dim.style.animationDelay = `${i * 0.07}s`;
                        dim.classList.add('reveal-ready', 'revealed');
                    });
                }, 300);
                break;
            }
        }
    });
    const ls = document.getElementById('loading-section');
    if (ls) loadingObserver.observe(ls, { attributes: true, attributeFilter: ['class'] });
})();


// ===== 5. Button Press Micro-Interaction =====
(function initButtonPress() {
    document.addEventListener('mousedown', (e) => {
        const btn = e.target.closest('.btn');
        if (btn) {
            btn.style.transform = 'scale(0.96)';
            btn.style.transition = 'transform 0.1s cubic-bezier(0.25, 0.1, 0.25, 1)';
        }
    }, true);

    document.addEventListener('mouseup', (e) => {
        const btn = e.target.closest('.btn');
        if (btn) {
            btn.style.transform = '';
        }
    }, true);

    document.addEventListener('mouseleave', (e) => {
        const btn = e.target.closest('.btn');
        if (btn) {
            btn.style.transform = '';
        }
    }, true);
})();


// ===== 6. Card Hover Lift =====
(function initCardHover() {
    document.addEventListener('mouseenter', (e) => {
        const card = e.target.closest('.card-lift');
        if (card) {
            card.style.transform = 'translateY(-4px)';
            card.style.boxShadow = 'var(--shadow-lg)';
        }
    }, true);

    document.addEventListener('mouseleave', (e) => {
        const card = e.target.closest('.card-lift');
        if (card) {
            card.style.transform = '';
            card.style.boxShadow = '';
        }
    }, true);
})();


// ===== 7. Respect Reduced Motion =====
(function initReducedMotion() {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) {
        document.documentElement.classList.add('reduced-motion');
    }
    mq.addEventListener('change', (e) => {
        document.documentElement.classList.toggle('reduced-motion', e.matches);
    });
})();


// ===== 8. Tilt Effect on Photo Panels =====
(function initTiltEffect() {
    document.addEventListener('mousemove', (e) => {
        const tilt = e.target.closest('.tilt-effect');
        if (!tilt) return;

        const rect = tilt.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;

        tilt.style.transform = `perspective(1000px) rotateY(${x * 3}deg) rotateX(${-y * 3}deg) translateZ(4px)`;
        tilt.style.transition = 'transform 0.1s ease-out';
    }, true);

    document.addEventListener('mouseleave', (e) => {
        const tilt = e.target.closest('.tilt-effect');
        if (tilt) {
            tilt.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) translateZ(0)';
            tilt.style.transition = 'transform 0.5s cubic-bezier(0.25, 0.1, 0.25, 1)';
        }
    }, true);
})();


// ===== 9. Parallax Score Ring Glow =====
(function initScoreRingParallax() {
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(() => {
                const ring = document.querySelector('.score-ring-wrapper');
                if (ring) {
                    const rect = ring.getBoundingClientRect();
                    const center = rect.top + rect.height / 2;
                    const viewportCenter = window.innerHeight / 2;
                    const offset = (center - viewportCenter) / viewportCenter;
                    ring.style.setProperty('--ring-offset', `${offset * 20}px`);
                }
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });
})();


// ===== 10. Smooth Page Transition on Upload =====
(function initPageTransition() {
    const analyzeBtn = document.getElementById('analyze-btn');
    if (!analyzeBtn) return;

    analyzeBtn.addEventListener('click', () => {
        const uploadSection = document.getElementById('upload-section');
        if (uploadSection && !uploadSection.classList.contains('hidden')) {
            uploadSection.style.transform = 'translateY(-8px)';
            uploadSection.style.opacity = '0.5';
            uploadSection.style.transition = 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)';

            setTimeout(() => {
                uploadSection.style.transform = '';
                uploadSection.style.opacity = '';
            }, 400);
        }
    });
})();
