(function () {
  var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
  var total = slides.length;
  var idx = 0;

  var prevBtn = document.getElementById('prevBtn');
  var nextBtn = document.getElementById('nextBtn');
  var posLabel = document.getElementById('posLabel');

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function render() {
    slides.forEach(function (s, i) { s.classList.toggle('active', i === idx); });
    posLabel.textContent = (idx + 1) + ' / ' + total;
    prevBtn.disabled = idx === 0;
    nextBtn.disabled = idx === total - 1;
    slides.forEach(function (s, i) {
      var countEl = s.querySelector('.count');
      if (countEl) { countEl.textContent = pad(i + 1) + ' / ' + pad(total); }
    });
  }

  function go(delta) {
    idx = Math.max(0, Math.min(total - 1, idx + delta));
    render();
  }

  prevBtn.addEventListener('click', function () { go(-1); });
  nextBtn.addEventListener('click', function () { go(1); });

  window.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { go(1); e.preventDefault(); }
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') { go(-1); e.preventDefault(); }
  });

  render();
})();
