document.addEventListener('DOMContentLoaded', function() {
    const thumbnailData = {
        trending: [
            {
                image: '/static/img/ur11.png',
                title: '年始に読むと人生変わる本TOP5',
                lessonUrl: '/courses/111-63d62/lessons/102-b543e'
            },
            {
                image: '/static/img/ur12.png',
                title: 'お金が増える8つの行動',
                lessonUrl: '/courses/111-63d62/lessons/103-xyz'
            },
            {
                image: '/static/img/20220806.jpg',
                title: 'キャリアを決める7つのトリガー習慣',
                lessonUrl: '/courses/111-63d62/lessons/104-abc'
            }
        ],
        acting: [
            {
                image: '/static/img/acting1.jpg',
                title: 'Acting Fundamentals'
            },
            {
                image: '/static/img/acting2.jpg',
                title: 'Voice Training Basics'
            },
            {
                image: '/static/img/acting3.jpg',
                title: 'Stage Performance Tips'
            }
        ],
        business: [
            {
                image: '/static/img/business1.jpg',
                title: 'Startup Essentials'
            },
            {
                image: '/static/img/business2.jpg',
                title: 'Leadership Skills'
            },
            {
                image: '/static/img/business3.jpg',
                title: 'Marketing Strategy'
            }
        ],
        community: [
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
        food: [
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
        art: [
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
        games: [
            {
                image: '/static/img/games1.jpg',
                title: 'Game Design'
            },
            {
                image: '/static/img/games2.jpg',
                title: '3D Modeling'
            },
            {
                image: '/static/img/games3.jpg',
                title: 'Animation'
            }
        ],
        film: [
            {
                image: '/static/img/film1.jpg',
                title: 'Cinematography'
            },
            {
                image: '/static/img/film2.jpg',
                title: 'Video Editing'
            },
            {
                image: '/static/img/film3.jpg',
                title: 'Screenwriting'
            }
        ],
        health: [
            {
                image: '/static/img/health1.jpg',
                title: 'Meditation'
            },
            {
                image: '/static/img/health2.jpg',
                title: 'Yoga Practice'
            },
            {
                image: '/static/img/health3.jpg',
                title: 'Nutrition Basics'
            }
        ],
        music: [
            {
                image: '/static/img/music1.jpg',
                title: 'Guitar Basics'
            },
            {
                image: '/static/img/music2.jpg',
                title: 'Music Production'
            },
            {
                image: '/static/img/music3.jpg',
                title: 'Piano Lessons'
            }
        ],
        outdoor: [
            {
                image: '/static/img/outdoor1.jpg',
                title: 'Rock Climbing'
            },
            {
                image: '/static/img/outdoor2.jpg',
                title: 'Hiking Skills'
            },
            {
                image: '/static/img/outdoor3.jpg',
                title: 'Photography'
            }
        ],
        science: [
            {
                image: '/static/img/science1.jpg',
                title: 'Coding Basics'
            },
            {
                image: '/static/img/science2.jpg',
                title: 'Data Science'
            },
            {
                image: '/static/img/science3.jpg',
                title: 'AI Fundamentals'
            }
        ],
        sports: [
            {
                image: '/static/img/sports1.jpg',
                title: 'Fitness Training'
            },
            {
                image: '/static/img/sports2.jpg',
                title: 'Tennis Basics'
            },
            {
                image: '/static/img/sports3.jpg',
                title: 'Swimming'
            }
        ],
        writing: [
            {
                image: '/static/img/writing1.jpg',
                title: 'Creative Writing'
            },
            {
                image: '/static/img/writing2.jpg',
                title: 'Storytelling'
            },
            {
                image: '/static/img/writing3.jpg',
                title: 'Content Creation'
            }
        ]
    };

    const thumbnailContainer = document.getElementById('thumbnail-container');
    const categoryButtons = document.querySelectorAll('.category-button');
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
});