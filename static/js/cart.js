document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-cart-add]').forEach((btn) => {
    btn.addEventListener('click', () => {
      btn.textContent = 'Added';
    });
  });
});
