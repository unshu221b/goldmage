document.addEventListener('DOMContentLoaded', function() {
    class Carousel {
        constructor(container) {
            // Core elements
            this.container = container;
            this.track = container.querySelector('.slides-track');
            this.slides = container.querySelectorAll('.video-card');
            this.prevBtn = container.querySelector('.prev');
            this.nextBtn = container.querySelector('.next');
            
            // Configuration
            this.currentIndex = 0;
            this.slidesToShow = Math.min(6, this.slides.length);
            this.slideWidth = this.container.offsetWidth / this.slidesToShow;
            
            // Initialize
            this.init();
        }
        
        init() {
            if (!this.track || !this.slides.length) return;
            
            // Set initial slide widths
            this.setSlideWidths();
            
            // Add event listeners
            this.addNavigationListeners();
            this.addResizeListener();
            
            // Initial navigation state
            this.updateNavigation();
        }
        
        setSlideWidths() {
            this.slides.forEach(slide => {
                slide.style.width = `${this.slideWidth}px`;
            });
        }
        
        addNavigationListeners() {
            if (this.prevBtn) {
                this.prevBtn.addEventListener('click', () => this.navigate('prev'));
            }
            
            if (this.nextBtn) {
                this.nextBtn.addEventListener('click', () => this.navigate('next'));
            }
        }
        
        navigate(direction) {
            if (direction === 'prev') {
                this.currentIndex = Math.max(0, this.currentIndex - this.slidesToShow);
            } else {
                this.currentIndex = Math.min(
                    this.slides.length - this.slidesToShow,
                    this.currentIndex + this.slidesToShow
                );
            }
            
            this.updateSlidePosition();
            this.updateNavigation();
        }
        
        updateSlidePosition() {
            this.track.style.transform = `translateX(-${this.currentIndex * this.slideWidth}px)`;
        }
        
        updateNavigation() {
            if (this.prevBtn) {
                this.prevBtn.style.display = this.currentIndex <= 0 ? 'none' : 'block';
            }
            
            if (this.nextBtn) {
                this.nextBtn.style.display = 
                    this.currentIndex >= this.slides.length - this.slidesToShow ? 'none' : 'block';
            }
        }
        
        addResizeListener() {
            window.addEventListener('resize', debounce(() => {
                // Recalculate dimensions
                this.slideWidth = this.container.offsetWidth / this.slidesToShow;
                
                // Update slide widths
                this.setSlideWidths();
                
                // Update position
                this.updateSlidePosition();
            }, 250));
        }
    }
    
    // Utility function for debouncing
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Initialize all carousels on the page
    const carouselContainers = document.querySelectorAll('.carousel-container');
    carouselContainers.forEach(container => new Carousel(container));
});
