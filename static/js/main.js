document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.querySelector('[data-search]');
  const searchResults = document.querySelector('[data-search-results]');
  if (searchInput && searchResults) {
    let timeout;
    searchInput.addEventListener('input', () => {
      clearTimeout(timeout);
      const q = searchInput.value.trim();
      if (!q) { searchResults.innerHTML=''; return; }
      timeout = setTimeout(() => {
        fetch(`/search?q=${encodeURIComponent(q)}`)
          .then(r => r.json())
          .then(data => {
            searchResults.innerHTML = data.map(item => `<a href="/product/${item.slug}" class="dropdown-item">${item.name}</a>`).join('');
          });
      }, 250);
    });
  }
});
