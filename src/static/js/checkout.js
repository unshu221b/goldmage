initialize();

// Create a Checkout Session
async function initialize() {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const fetchClientSecret = async () => {
    try {
      const csrfToken = getCookie('csrftoken');
      const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
      const token = csrfToken || (csrfInput ? csrfInput.value : null);
      
      if (!token) {
        throw new Error('CSRF token not found');
      }

      const response = await fetch("/payment/checkout/", {
        method: "POST",
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'same-origin',
        mode: 'same-origin',
        cache: 'no-cache'
      });
      
      if (!response.ok) {
        throw new Error(`Payment setup failed`);  // Generic error message
      }
      
      const data = await response.json();
      return data.clientSecret;
    } catch (error) {
      console.error("Payment setup error");  // Generic error message
      throw error;
    }
  };

  try {
    const checkout = await stripe.initEmbeddedCheckout({
      fetchClientSecret,
    });
    
    checkout.mount('#checkout');
  } catch (error) {
    document.getElementById('checkout').innerHTML = 
      '<div class="text-red-500 p-4">Unable to load payment form. Please try again.</div>';
  }
}