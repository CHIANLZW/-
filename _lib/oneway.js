(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var brand = document.querySelector('.site-header__brand');
    if (brand && brand.tagName === 'A') {
      var span = document.createElement('div');
      span.className = brand.className;
      span.innerHTML = brand.innerHTML;
      brand.replaceWith(span);
    }
  });
})();
