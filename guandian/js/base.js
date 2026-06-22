(function () {
  'use strict';
  var path = location.pathname.replace(/\\/g, '/');
  var marker = '/guandian';
  var idx = path.indexOf(marker);
  if (idx !== -1) {
    path = path.slice(0, idx + marker.length) + '/';
  } else if (/\.html$/i.test(path)) {
    path = path.slice(0, path.lastIndexOf('/') + 1);
  } else if (!path.endsWith('/')) {
    path += '/';
  }
  var base = document.createElement('base');
  base.href = path;
  document.head.prepend(base);
})();
