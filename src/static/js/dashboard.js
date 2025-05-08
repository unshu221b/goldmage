document.addEventListener('DOMContentLoaded', function() {
    const closeButton = document.getElementById('close-verification-modal');
    const modal = document.querySelector('[role="dialog"]');
    
    if (closeButton && modal) {
        closeButton.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }

    const resendButton = document.getElementById('resend-verification');
    
    if (resendButton) {
        resendButton.addEventListener('click', function() {
            // Disable button to prevent multiple clicks
            resendButton.disabled = true;
            resendButton.textContent = 'Sending...';
            
            fetch('/resend-verification/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'Content-Type': 'application/json'
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert(data.message);
                } else {
                    // Show error message
                    alert(data.message);
                }
            })
            .catch(error => {
                alert('An error occurred. Please try again.');
                console.error('Error:', error);
            })
            .finally(() => {
                // Re-enable button after request completes
                resendButton.disabled = false;
                resendButton.textContent = 'Resend Email';
            });
        });
    }

    // Mobile tab switching
    const tabs = document.querySelectorAll('[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active states from all tabs
            tabs.forEach(t => {
                t.classList.remove('border-blue-500', 'text-white');
                t.classList.add('text-gray-500');
            });

            // Add active state to clicked tab
            tab.classList.remove('text-gray-500');
            tab.classList.add('border-blue-500', 'text-white');

            // Hide all tab contents
            tabContents.forEach(content => {
                content.classList.add('hidden');
            });

            // Show selected tab content
            const targetId = `${tab.dataset.tab}-section`;
            document.getElementById(targetId).classList.remove('hidden');
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const sidebarButton = document.querySelector('[data-drawer-toggle="logo-sidebar"]');
    const sidebar = document.getElementById('logo-sidebar');
    let isOpen = false;

    // Initially close the sidebar
    if (sidebar) {
        sidebar.style.transform = 'translateX(-100%)';
    }

    if (sidebarButton && sidebar) {
        sidebarButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            isOpen = !isOpen;
            
            if (isOpen) {
                sidebar.style.transform = 'translateX(0)';
            } else {
                sidebar.style.transform = 'translateX(-100%)';
            }
        });
    }

    // Remove backdrop when clicking anywhere on the document
    document.addEventListener('click', function() {
        const backdrop = document.querySelector('.bg-gray-900\\/50');
        if (backdrop) {
            backdrop.remove();
        }
    });
});