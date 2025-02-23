document.addEventListener('DOMContentLoaded', function() {
    // Assuming you have a video player element with id 'video-player'
    const videoPlayer = document.getElementById('video-player');
    
    if (videoPlayer) {
        videoPlayer.addEventListener('timeupdate', function() {
            const currentTime = this.currentTime;
            const duration = this.duration;
            
            // Update progress every 5 seconds or when video ends
            if (Math.floor(currentTime) % 5 === 0 || currentTime === duration) {
                fetch('/api/update-progress/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        lesson_id: LESSON_ID, // This should be set in your lesson.html template
                        current_time: currentTime,
                        total_duration: duration
                    })
                });
            }
        });
    }
});