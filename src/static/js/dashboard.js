document.addEventListener('DOMContentLoaded', function() {
    const carousels = document.querySelectorAll('.carousel-container');
    
    carousels.forEach(carousel => {
        const track = carousel.querySelector('.slides-track.lg\\:flex');
        const slides = Array.from(carousel.querySelectorAll('.slide-group'));
        const prevButton = carousel.querySelector('.prev');
        const nextButton = carousel.querySelector('.next');
        
        let currentIndex = 0;
        
        function isMobile() {
            return window.innerWidth < 1024;
        }
        
        function updateSlidePosition() {
            if (isMobile()) {
                const mobileTrack = carousel.querySelector('.slides-track.flex');
                const slideWidth = carousel.offsetWidth;
                mobileTrack.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
            } else {
                const slideWidth = carousel.offsetWidth;
                track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
            }
        }
        
        prevButton.addEventListener('click', () => {
            if (!isMobile() && currentIndex > 0) {
                currentIndex--;
                updateSlidePosition();
            }
        });
        
        nextButton.addEventListener('click', () => {
            if (!isMobile() && currentIndex < slides.length - 1) {
                currentIndex++;
                updateSlidePosition();
            }
        });
        
        updateSlidePosition();
        
        window.addEventListener('resize', () => {
            currentIndex = 0;
            updateSlidePosition();
        });
    });
});

class Carousel {
    constructor(element) {
        this.container = element;
        this.track = element.querySelector('.slides-track');
        this.slides = Array.from(element.querySelectorAll('.video-card'));
        this.prevButton = element.querySelector('.prev');
        this.nextButton = element.querySelector('.next');
        
        this.isDragging = false;
        this.startPos = 0;
        this.currentTranslate = 0;
        this.prevTranslate = 0;
        this.animationID = 0;
        this.currentIndex = 0;
        this.slidesCount = this.slides.length;
        this.slidesPerView = 5;
        
        this.handleResize();
        this.setupEventListeners();
        this.updatePosition();
    }
    
    handleResize() {
        this.track.querySelectorAll('[data-clone="true"]').forEach(clone => clone.remove());
        
        const width = window.innerWidth;
        if (width >= 1024) {
            this.slidesPerView = 5;
        } else if (width >= 640) {
            this.slidesPerView = 3;
        } else {
            this.slidesPerView = 1;
        }
        
        this.currentIndex = 0;
        
        this.setupInfiniteLoop();
        this.updatePosition();
    }
    
    setupEventListeners() {
        this.prevButton.addEventListener('click', () => this.prev());
        this.nextButton.addEventListener('click', () => this.next());
        
        this.track.addEventListener('touchstart', this.touchStart.bind(this));
        this.track.addEventListener('touchmove', this.touchMove.bind(this));
        this.track.addEventListener('touchend', this.touchEnd.bind(this));
        
        this.track.addEventListener('contextmenu', e => {
            e.preventDefault();
            e.stopPropagation();
        });
    }
    
    touchStart(event) {
        this.isDragging = true;
        this.startPos = event.touches[0].clientX;
        this.animationID = requestAnimationFrame(this.animation.bind(this));
        this.track.style.cursor = 'grabbing';
    }
    
    touchMove(event) {
        if (!this.isDragging) return;
        
        const currentPosition = event.touches[0].clientX;
        const diff = currentPosition - this.startPos;
        
        this.currentTranslate = this.prevTranslate + diff;
    }
    
    touchEnd() {
        this.isDragging = false;
        cancelAnimationFrame(this.animationID);
        
        const movedBy = this.currentTranslate - this.prevTranslate;
        
        if (movedBy < -100 && this.currentIndex < this.slidesCount - 1) {
            this.next();
        }
        else if (movedBy > 100 && this.currentIndex > 0) {
            this.prev();
        }
        else {
            this.updatePosition();
        }
        
        this.track.style.cursor = 'grab';
    }
    
    animation() {
        if (this.isDragging) {
            this.setSliderPosition();
            requestAnimationFrame(this.animation.bind(this));
        }
    }
    
    setSliderPosition() {
        this.track.style.transform = `translateX(${this.currentTranslate}px)`;
    }
    
    setupInfiniteLoop() {
        const slidesToClone = this.slides.slice(0, this.slidesPerView);
        slidesToClone.forEach(slide => {
            const clone = slide.cloneNode(true);
            clone.setAttribute('data-clone', 'true');
            this.track.appendChild(clone);
        });
    }
    
    next() {
        this.currentIndex++;
        const maxIndex = this.slidesCount - this.slidesPerView;
        
        if (this.currentIndex > maxIndex) {
            this.currentIndex = 0;
            this.track.style.transition = 'none';
            this.updatePosition();
            this.track.offsetHeight;
            this.track.style.transition = 'transform 0.3s ease';
        }
        this.updatePosition();
    }
    
    prev() {
        this.currentIndex--;
        if (this.currentIndex < 0) {
            this.currentIndex = this.slidesCount - this.slidesPerView;
            this.track.style.transition = 'none';
            this.updatePosition();
            this.track.offsetHeight;
            this.track.style.transition = 'transform 0.3s ease';
        }
        this.updatePosition();
    }
    
    updatePosition() {
        const slideWidth = this.container.offsetWidth / this.slidesPerView;
        const transform = -this.currentIndex * slideWidth;
        this.currentTranslate = transform;
        this.prevTranslate = transform;
        this.track.style.transform = `translateX(${transform}px)`;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const carousels = document.querySelectorAll('.carousel-container');
    carousels.forEach(carousel => {
        const instance = new Carousel(carousel);
        window.addEventListener('resize', () => instance.handleResize());
    });
});
