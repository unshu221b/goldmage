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
            image: '/static/img/20220805.jpg',
            text: '"The quality of instruction and production is unmatched. Each class feels like a documentary film and master\'s degree rolled into one."',
            name: 'Michael',
            title: 'Software Engineer, Canada'
        },
        {
            image: '/static/img/20220806.jpg',
            text: '"The platform has transformed how I approach learning. The insights from industry leaders are invaluable."',
            name: 'Sarah',
            title: 'Creative Director, UK'
        }
    ];

    let currentIndex = 0;
    const dots = document.querySelectorAll('.dot');
    const prevButton = document.querySelector('.prev-button');
    const nextButton = document.querySelector('.next-button');
    const testimonialImage = document.querySelector('.testimonial-container img');
    const testimonialCard = document.querySelector('.testimonial-card');

    function updateTestimonial() {
        const testimonial = testimonials[currentIndex];
        
        // Update content with fade effect
        testimonialImage.style.opacity = '0';
        testimonialCard.style.opacity = '0';
        
        setTimeout(() => {
            testimonialImage.src = testimonial.image;
            testimonialCard.innerHTML = `
                <p class="mb-4">${testimonial.text}</p>
                <p class="font-bold">${testimonial.name}</p>
                <p>${testimonial.title}</p>
            `;
            testimonialImage.style.opacity = '1';
            testimonialCard.style.opacity = '1';
        }, 300);

        // Update dots
        dots.forEach((dot, index) => {
            dot.style.backgroundColor = index === currentIndex ? 'white' : 'rgba(255, 255, 255, 0.5)';
        });
    }

    // Add click handlers
    prevButton.addEventListener('click', () => {
        currentIndex = (currentIndex - 1 + testimonials.length) % testimonials.length;
        updateTestimonial();
    });

    nextButton.addEventListener('click', () => {
        currentIndex = (currentIndex + 1) % testimonials.length;
        updateTestimonial();
    });

    // Add dot click handlers
    dots.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            currentIndex = index;
            updateTestimonial();
        });
    });

    // Add transition styles
    testimonialImage.style.transition = 'opacity 0.3s ease';
    testimonialCard.style.transition = 'opacity 0.3s ease';
});