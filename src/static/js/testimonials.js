document.addEventListener('DOMContentLoaded', function() {
    // Testimonial data
    const testimonials = [
        {
            image: '/static/img/20220804.jpg',
            text: '"我透過在浴室、吃飯和做家務時觀看36個大師班，學會了如何生活——充滿熱情、堅韌、謙遜，並且有一個過程，讓我們的生活旅程變得值得品味。"',
            name: 'Clarissa',
            title: '創辦人 & 教師, 東京'
        },
        {
            image: '/static/img/ac-001.webp',
            text: '"教學品質和製作水準無與倫比。每堂課都像是紀錄片與碩士學位的完美結合。"',
            name: '小陳',
            title: '軟體工程師，加拿大'
        },
        {
            image: '/static/img/ac-002.webp',
            text: '"這個平台徹底改變了我的學習方式。來自業界領袖的見解非常寶貴。"',
            name: '小芳',
            title: '創意總監，英國'
        }
    ];

    // Preload images
    const preloadImages = () => {
        testimonials.forEach(testimonial => {
            const img = new Image();
            img.src = testimonial.image;
        });
    };
    preloadImages();

    let currentIndex = 0;
    const dots = document.querySelectorAll('.dot');
    const prevButton = document.querySelector('.prev-button');
    const nextButton = document.querySelector('.next-button');
    const testimonialImage = document.querySelector('.testimonial-container img');
    const testimonialCard = document.querySelector('.testimonial-card');
    const testimonialContainer = document.querySelector('.testimonial-container');
    let startX, startY;
    let currentX;
    let isDragging = false;
    let isHorizontalDrag = false;
    let startTime;
    const swipeThreshold = 50;
    const timeThreshold = 300;
    const directionThreshold = 30; // Threshold to determine horizontal vs vertical swipe

    function updateTestimonial() {
        const testimonial = testimonials[currentIndex];
        const nextImage = new Image();
        
        // Start loading the next image
        nextImage.src = testimonial.image;
        nextImage.onload = () => {
            // Fade out current content
            testimonialImage.style.opacity = '0';
            testimonialCard.style.opacity = '0';
            
            // Update content after fade out
            setTimeout(() => {
                testimonialImage.src = testimonial.image;
                testimonialCard.innerHTML = `
                    <p class="mb-4">${testimonial.text}</p>
                    <p class="font-bold">${testimonial.name}</p>
                    <p>${testimonial.title}</p>
                `;
                
                // Fade in new content
                testimonialImage.style.opacity = '1';
                testimonialCard.style.opacity = '1';
            }, 150); // Reduced timing for smoother transition
        };

        // Update dots immediately
        dots.forEach((dot, index) => {
            dot.style.backgroundColor = index === currentIndex ? 'white' : 'rgba(255, 255, 255, 0.5)';
        });
    }

    // Add click handlers with debounce
    let isTransitioning = false;
    
    prevButton.addEventListener('click', () => {
        if (!isTransitioning) {
            isTransitioning = true;
            currentIndex = (currentIndex - 1 + testimonials.length) % testimonials.length;
            updateTestimonial();
            setTimeout(() => { isTransitioning = false; }, 300);
        }
    });

    nextButton.addEventListener('click', () => {
        if (!isTransitioning) {
            isTransitioning = true;
            currentIndex = (currentIndex + 1) % testimonials.length;
            updateTestimonial();
            setTimeout(() => { isTransitioning = false; }, 300);
        }
    });

    // Add dot click handlers
    dots.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            if (!isTransitioning) {
                isTransitioning = true;
                currentIndex = index;
                updateTestimonial();
                setTimeout(() => { isTransitioning = false; }, 300);
            }
        });
    });

    // Add transition styles
    testimonialImage.style.transition = 'opacity 0.15s ease';
    testimonialCard.style.transition = 'opacity 0.15s ease';

    // Touch events
    testimonialContainer.addEventListener('touchstart', handleDragStart, { passive: true });
    testimonialContainer.addEventListener('touchmove', handleDragMove, { passive: false });
    testimonialContainer.addEventListener('touchend', handleDragEnd);

    // Mouse events
    testimonialContainer.addEventListener('mousedown', handleDragStart);
    testimonialContainer.addEventListener('mousemove', handleDragMove);
    testimonialContainer.addEventListener('mouseup', handleDragEnd);
    testimonialContainer.addEventListener('mouseleave', handleDragEnd);

    function handleDragStart(e) {
        if (isTransitioning) return;
        
        const touch = e.type === 'mousedown' ? e : e.touches[0];
        startX = touch.pageX;
        startY = touch.pageY;
        currentX = startX;
        
        isDragging = true;
        isHorizontalDrag = false; // Reset direction check
        startTime = new Date().getTime();
        
        testimonialContainer.style.cursor = 'grabbing';
    }

    function handleDragMove(e) {
        if (!isDragging) return;
        
        const touch = e.type === 'mousemove' ? e : e.touches[0];
        const deltaX = touch.pageX - startX;
        const deltaY = touch.pageY - startY;

        // Determine drag direction on first significant movement
        if (!isHorizontalDrag && (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10)) {
            isHorizontalDrag = Math.abs(deltaX) > Math.abs(deltaY);
        }

        // Only prevent default and move slider if it's a horizontal drag
        if (isHorizontalDrag) {
            e.preventDefault();
            currentX = touch.pageX;
            testimonialContainer.style.transform = `translateX(${deltaX * 0.5}px)`;
        }
    }

    function handleDragEnd(e) {
        if (!isDragging) return;
        
        const endTime = new Date().getTime();
        const timeElapsed = endTime - startTime;
        const diff = currentX - startX;

        testimonialContainer.style.cursor = '';
        testimonialContainer.style.transform = '';
        
        isDragging = false;

        // Only process as swipe if it was a horizontal drag
        if (isHorizontalDrag && timeElapsed <= timeThreshold && Math.abs(diff) >= swipeThreshold) {
            if (diff > 0) {
                // Swipe right
                if (!isTransitioning) {
                    isTransitioning = true;
                    currentIndex = (currentIndex - 1 + testimonials.length) % testimonials.length;
                    updateTestimonial();
                    setTimeout(() => { isTransitioning = false; }, 300);
                }
            } else {
                // Swipe left
                if (!isTransitioning) {
                    isTransitioning = true;
                    currentIndex = (currentIndex + 1) % testimonials.length;
                    updateTestimonial();
                    setTimeout(() => { isTransitioning = false; }, 300);
                }
            }
        }
    }

    // Initialize first testimonial
    updateTestimonial();
});