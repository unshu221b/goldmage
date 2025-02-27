// This is your test secret API key.
const stripe = Stripe("pk_live_51NtNwpKJgMl2RgJ1dTVn2Lk60PGhYrkRo6MqyyzxKPUSHQsn2KxwpQoacbb3aC5SI3Oxj3xJCaTOIeoFUnjNQ7Tn00rNdcl7Po");

initialize();

// Create a Checkout Session
async function initialize() {
  // Get CSRF token from cookie
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
      const response = await fetch("/payment/checkout/", {
        method: "POST",
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Response data:", data);  // Debug log
      
      if (!data.clientSecret) {
        throw new Error('No client secret in response');
      }
      
      return data.clientSecret;
    } catch (error) {
      console.error("Error fetching client secret:", error);
      throw error;
    }
  };

  try {
    const checkout = await stripe.initEmbeddedCheckout({
      fetchClientSecret,
    });
    
    // Mount Checkout
    checkout.mount('#checkout');
  } catch (error) {
    console.error("Error initializing checkout:", error);
  }
}