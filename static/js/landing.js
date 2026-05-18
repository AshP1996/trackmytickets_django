/**
 * TrackMyTickets landing page — animations & interactions
 */
(function () {
    'use strict';

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ── Mobile navigation ───────────────────────────────────────────────
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.getElementById('nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            const open = navLinks.classList.toggle('open');
            navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            document.body.classList.toggle('nav-open', open);
        });
        navLinks.querySelectorAll('a[href^="#"]').forEach((link) => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('open');
                navToggle.setAttribute('aria-expanded', 'false');
                document.body.classList.remove('nav-open');
            });
        });
    }

    // ── Navbar scroll ───────────────────────────────────────────────────
    const navbar = document.getElementById('navbar');
    if (navbar) {
        const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 40);
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // ── Smooth scroll ───────────────────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (!href || href === '#') return;
            const target = document.querySelector(href);
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
        });
    });

    // ── Scroll reveal ───────────────────────────────────────────────────
    const revealSelectors = [
        '.reveal',
        '.feature-card',
        '.benefit-item',
        '.testimonial-card',
        '.step-card',
        '.section-title',
        '.section-subtitle',
        '.stat-item',
        '.clean-ui-content',
        '.clean-ui-visual',
    ];

    const revealEls = document.querySelectorAll(revealSelectors.join(','));
    revealEls.forEach((el, i) => {
        el.classList.add('reveal');
        el.style.setProperty('--reveal-delay', `${Math.min(i % 8, 7) * 0.08}s`);
    });

    if (!prefersReducedMotion && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
        );
        revealEls.forEach((el) => observer.observe(el));
    } else {
        revealEls.forEach((el) => el.classList.add('is-visible'));
    }

    // ── Animated stat counters ──────────────────────────────────────────
    function animateCounter(el) {
        const target = parseFloat(el.dataset.count);
        const suffix = el.dataset.suffix || '';
        const prefix = el.dataset.prefix || '';
        const decimals = parseInt(el.dataset.decimals || '0', 10);
        const duration = prefersReducedMotion ? 0 : 1800;
        if (!target || duration === 0) {
            el.textContent = prefix + target + suffix;
            return;
        }
        const start = performance.now();
        const step = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = (target * eased).toFixed(decimals);
            el.textContent = prefix + value + suffix;
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    const statObserver = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    statObserver.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.5 }
    );
    document.querySelectorAll('[data-count]').forEach((el) => statObserver.observe(el));

    // ── Typewriter ──────────────────────────────────────────────────────
    const textElement = document.querySelector('.typewriter-text');
    if (textElement && !prefersReducedMotion) {
        const phrases = [
            'High-Growth Enterprises',
            'Internal IT Teams',
            'Customer Support Leads',
            'SaaS Startups',
        ];
        let phraseIndex = 0;
        let charIndex = 0;
        let isDeleting = false;

        function type() {
            const currentPhrase = phrases[phraseIndex];
            let typeSpeed = 90;

            if (isDeleting) {
                textElement.textContent = currentPhrase.substring(0, charIndex - 1);
                charIndex--;
                typeSpeed = 45;
            } else {
                textElement.textContent = currentPhrase.substring(0, charIndex + 1);
                charIndex++;
            }

            if (!isDeleting && charIndex === currentPhrase.length) {
                isDeleting = true;
                typeSpeed = 2200;
            } else if (isDeleting && charIndex === 0) {
                isDeleting = false;
                phraseIndex = (phraseIndex + 1) % phrases.length;
                typeSpeed = 400;
            }
            setTimeout(type, typeSpeed);
        }
        type();
    } else if (textElement) {
        textElement.textContent = 'Modern Support Teams';
    }

    // ── Screenshot carousel ─────────────────────────────────────────────
    const track = document.querySelector('.carousel-track');
    if (track) {
        const slides = track.querySelectorAll('.carousel-slide');
        const nextBtn = document.querySelector('.carousel-btn.next');
        const prevBtn = document.querySelector('.carousel-btn.prev');
        const indicators = document.querySelectorAll('.carousel-indicators .indicator');
        let currentIndex = 0;
        let autoTimer;

        function updateSlide(index) {
            currentIndex = index;
            track.style.transform = `translateX(-${index * 100}%)`;
            indicators.forEach((ind, i) => ind.classList.toggle('active', i === index));
        }

        function next() {
            updateSlide((currentIndex + 1) % slides.length);
        }

        function prev() {
            updateSlide((currentIndex - 1 + slides.length) % slides.length);
        }

        if (nextBtn) nextBtn.addEventListener('click', next);
        if (prevBtn) prevBtn.addEventListener('click', prev);
        indicators.forEach((ind, i) => ind.addEventListener('click', () => updateSlide(i)));

        function startAuto() {
            if (prefersReducedMotion) return;
            autoTimer = setInterval(next, 5500);
        }
        function stopAuto() {
            clearInterval(autoTimer);
        }

        const carousel = document.querySelector('.screenshot-carousel');
        if (carousel) {
            carousel.addEventListener('mouseenter', stopAuto);
            carousel.addEventListener('mouseleave', startAuto);
        }
        startAuto();
    }

    // ── FAQ accordion ───────────────────────────────────────────────────
    document.querySelectorAll('.faq-item').forEach((item) => {
        const question = item.querySelector('.faq-question');
        if (!question) return;
        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            document.querySelectorAll('.faq-item').forEach((i) => i.classList.remove('active'));
            if (!isActive) item.classList.add('active');
        });
    });

    // ── 3D tilt on feature cards (desktop only) ──────────────────────────
    if (!prefersReducedMotion && window.matchMedia('(pointer: fine)').matches) {
        document.querySelectorAll('[data-tilt]').forEach((card) => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;
                card.style.transform = `perspective(800px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg) translateY(-6px)`;
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // ── Parallax hero blobs ─────────────────────────────────────────────
    if (!prefersReducedMotion) {
        const hero = document.querySelector('.hero');
        if (hero) {
            window.addEventListener(
                'mousemove',
                (e) => {
                    const x = (e.clientX / window.innerWidth - 0.5) * 20;
                    const y = (e.clientY / window.innerHeight - 0.5) * 20;
                    hero.style.setProperty('--mouse-x', `${x}px`);
                    hero.style.setProperty('--mouse-y', `${y}px`);
                },
                { passive: true }
            );
        }
    }
})();
