document.addEventListener('DOMContentLoaded', () => {
  const input = document.querySelector('[name="q"]');
  if (input) {
    input.addEventListener('input', () => {
      const value = input.value.trim();
      if (!value) return;
      fetch(`/search?q=${encodeURIComponent(value)}`)
        .then((res) => res.json())
        .then(() => {});
    });
  }
});
