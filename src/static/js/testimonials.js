document.addEventListener('DOMContentLoaded', function() {
    // Testimonial data
    const testimonials = [
        {
            image: '/static/img/20220804.jpg',
            text: '"I\'ve watched 36 MasterClasses by tuning in while I\'m in the bathroom, eating, and doing chores around the house. MasterClass teaches us how to live—with passion, grit, humility, and with a process that makes our life journeys something to savor instead."',
            name: 'Clarissa',
            title: 'Founder & Teacher, USA'
        },
        {
            image: '/static/img/ac-001.webp',
            text: '"The quality of instruction and production is unmatched. Each class feels like a documentary film and master\'s degree rolled into one."',
            name: 'Michael',
            title: 'Software Engineer, Canada'
        },
        {
            image: '/static/img/ac-002.webp',
            text: '"The platform has transformed how I approach learning. The insights from industry leaders are invaluable."',
            name: 'Sarah',
            title: 'Creative Director, UK'
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

    // Initialize first testimonial
    updateTestimonial();
});