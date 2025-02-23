
document.addEventListener('DOMContentLoaded', function() {
    const stickyFooter = document.getElementById('sticky-footer');
    const realFooter = document.querySelector('footer'); // Get the real footer
    
    if (!stickyFooter || !realFooter) {
        console.error('Required elements not found.');
        return;
    }

    let lastScrollTop = 0;
    const offset = 100; // Offset before the footer when we want the sticky footer to disappear

    window.addEventListener('scroll', function() {
        let scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        let footerPosition = realFooter.getBoundingClientRect().top;
        let windowHeight = window.innerHeight;

        if (scrollTop > lastScrollTop) {
            // Scrolling down
            if (footerPosition > windowHeight + offset) {
                // Show sticky footer only if we're not near the real footer
                stickyFooter.classList.add('visible');
            } else {
                // Hide sticky footer when near the real footer
                stickyFooter.classList.remove('visible');
            }
        } else if (scrollTop === 0) {
            // Back to top
            stickyFooter.classList.remove('visible');
        }

        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop; // For Mobile or negative scrolling
    });
});