document.addEventListener('DOMContentLoaded', function() {
    const thumbnailData = {
        trending: [
            {
                image: '/static/img/demo2.webp',
                title: '年始に読むと人生変わる本TOP5',
                lessonUrl: '/courses/111-63d62/lessons/102-b543e'
            },
            {
                image: '/static/img/demo2.webp',
                title: 'お金が増える8つの行動',
                lessonUrl: '/courses/111-63d62/lessons/103-xyz'
            },
            {
                image: '/static/img/demo2.webp',
                title: 'キャリアを決める7つのトリガー習慣',
                lessonUrl: '/courses/111-63d62/lessons/104-abc'
            }
        ],
        storymaster: [
            {
                image: '/static/img/demo3.webp',
                title: 'Acting Fundamentals'
            },
            {
                image: '/static/img/demo3.webp',
                title: 'Voice Training Basics'
            },
            {
                image: '/static/img/demo3.webp',
                title: 'Stage Performance Tips'
            }
        ],
        business: [
            {
                image: '/static/img/demo4.webp',
                title: 'Startup Essentials'
            },
            {
                image: '/static/img/demo4.webp',
                title: 'Leadership Skills'
            },
            {
                image: '/static/img/demo4.webp',
                title: 'Marketing Strategy'
            }
        ],
        english: [
            {
                image: '/static/img/community1.jpg',
                title: 'Public Speaking'
            },
            {
                image: '/static/img/community2.jpg',
                title: 'Community Building'
            },
            {
                image: '/static/img/community3.jpg',
                title: 'Social Impact'
            }
        ],
        japanese: [
            {
                image: '/static/img/food1.jpg',
                title: 'Culinary Basics'
            },
            {
                image: '/static/img/food2.jpg',
                title: 'Wine Tasting'
            },
            {
                image: '/static/img/food3.jpg',
                title: 'Pastry Making'
            }
        ],
        biography: [
            {
                image: '/static/img/art1.jpg',
                title: 'Digital Art'
            },
            {
                image: '/static/img/art2.jpg',
                title: 'Painting Techniques'
            },
            {
                image: '/static/img/art3.jpg',
                title: 'Sculpture Basics'
            }
        ],
    };

    const thumbnailContainer = document.getElementById('thumbnail-container');
    const categoryButtons = document.querySelectorAll('.category-button');
    const mobileCategorySelect = document.getElementById('mobile-category-select');
    const videoModal = document.getElementById('video-modal');
    const closeModal = document.getElementById('close-modal');
    const videoContainer = document.getElementById('video-container');

    // Function to create thumbnail HTML
    function createThumbnailHTML(item) {
        return `
            <a href="${item.lessonUrl}" class="thumbnail-item block">
                <img src="${item.image}" alt="${item.title}" class="w-full h-full object-cover">
            </a>
        `;
    }

    // Function to display thumbnails for a category
    function displayThumbnails(category) {
        const thumbnails = thumbnailData[category] || thumbnailData.trending;
        thumbnailContainer.innerHTML = thumbnails.map(createThumbnailHTML).join('');
    }

    // Add click handlers to category buttons
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            categoryButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const category = button.dataset.category || 'trending';
            displayThumbnails(category);
        });
    });

    // Display trending thumbnails by default
    displayThumbnails('trending');

    // Function to open modal with Cloudinary video
    function openVideoModal(videoUrl) {
        // Clear previous video
        videoContainer.innerHTML = '';
        
        // Create video element with required attributes
        const videoElement = document.createElement('video');
        videoElement.id = 'video-player-' + Math.random().toString(36).substr(2, 9);
        videoElement.className = 'cld-video-player absolute inset-0';
        videoElement.setAttribute('data-cloud-name', 'dkaouxk4m'); // Your cloud name
        videoElement.setAttribute('data-video-url', videoUrl);
        
        // Add to container
        videoContainer.appendChild(videoElement);

        // Initialize player
        const cld = cloudinary.videoPlayer(videoElement.id, {
            cloudName: 'dkaouxk4m' // Your cloud name
        });
        cld.source(videoUrl);

        // Show modal
        videoModal.classList.add('active');
        document.body.classList.add('modal-open');
    }

    // Function to close modal
    function closeVideoModal() {
        videoModal.classList.remove('active');
        document.body.classList.remove('modal-open');
        videoContainer.innerHTML = ''; // Remove video player
    }

    // Event listeners
    thumbnailContainer.addEventListener('click', (e) => {
        const thumbnail = e.target.closest('.thumbnail-item');
        if (thumbnail) {
            const videoUrl = thumbnail.dataset.videoUrl;
            if (videoUrl) {
                openVideoModal(videoUrl);
            }
        }
    });

    closeModal.addEventListener('click', closeVideoModal);

    // Close on background click
    videoModal.addEventListener('click', (e) => {
        if (e.target === videoModal) {
            closeVideoModal();
        }
    });

    // Close on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && videoModal.classList.contains('active')) {
            closeVideoModal();
        }
    });

    // Add change handler to mobile category select
    if (mobileCategorySelect) {
        mobileCategorySelect.addEventListener('change', () => {
            const category = mobileCategorySelect.value;
            
            // Also update the desktop buttons to show the active state
            categoryButtons.forEach(btn => {
                if (btn.dataset.category === category) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            
            displayThumbnails(category);
        });
    }
});