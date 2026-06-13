/* ============================================
   רקע מונפש — תזוזה עדינה של שכבות הרים
   ============================================ */

(function () {
    let raf = null;
    let t = 0;
    const back  = document.querySelector('.mtn-back');
    const mid   = document.querySelector('.mtn-mid');
    const front = document.querySelector('.mtn-front');
    const sun   = document.getElementById('sun');

    if (!back || !mid || !front || !sun) return;

    let pointerX = 0.5;
    let pointerY = 0.5;
    document.addEventListener('pointermove', e => {
        pointerX = e.clientX / window.innerWidth;
        pointerY = e.clientY / window.innerHeight;
    }, { passive: true });

    function loop() {
        t += 0.005;

        // Parallax based on cursor
        const px = (pointerX - 0.5) * 2;
        const py = (pointerY - 0.5) * 2;

        back.style.transform  = `translate3d(${px * -8}px, ${py * -4}px, 0)`;
        mid.style.transform   = `translate3d(${px * -14}px, ${py * -7}px, 0)`;
        front.style.transform = `translate3d(${px * -22}px, ${py * -10}px, 0)`;

        // Subtle sun pulse
        const pulse = 1 + Math.sin(t) * 0.02;
        sun.style.transform = `scale(${pulse})`;

        raf = requestAnimationFrame(loop);
    }

    function start() {
        if (!raf) loop();
    }
    function stop() {
        if (raf) cancelAnimationFrame(raf);
        raf = null;
    }

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) stop(); else start();
    });

    // Respect reduced motion
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReduced) start();
})();
