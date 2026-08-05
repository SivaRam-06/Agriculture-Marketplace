document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', () => {
      form.querySelectorAll('input, select, textarea').forEach((field) => {
        if (field.hasAttribute('required') && !field.value.trim()) {
          field.classList.add('is-invalid');
        }
      });
    });
  });
});
