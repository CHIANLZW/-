/** 个人简历 — 导航与样式兜底 */
(function ensureResumeAssets() {
  function resumePrefix() {
    var path = location.pathname.replace(/\\/g, '/');
    var marker = '/resume';
    var idx = path.indexOf(marker);
    if (idx !== -1) return path.slice(0, idx + marker.length);
    if (/\.html$/i.test(path)) return path.slice(0, path.lastIndexOf('/'));
    return path.endsWith('/') ? path.slice(0, -1) : path;
  }

  function cssLoaded() {
    return Array.from(document.styleSheets).some(function (sheet) {
      try {
        return sheet.href && sheet.href.indexOf('resume.css') !== -1 && sheet.cssRules.length > 0;
      } catch (e) {
        return sheet.href && sheet.href.indexOf('resume.css') !== -1;
      }
    });
  }

  function injectCss() {
    if (cssLoaded()) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = resumePrefix() + '/css/resume.css';
    document.head.appendChild(link);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectCss);
  } else {
    injectCss();
  }
})();

document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.topbar__toggle');
  var nav = document.querySelector('.topbar__nav');

  if (toggle && nav) {
    var setOpen = function (open) {
      toggle.classList.toggle('active', open);
      nav.classList.toggle('open', open);
      document.body.classList.toggle('nav-open', open);
    };

    toggle.addEventListener('click', function () {
      setOpen(!nav.classList.contains('open'));
    });

    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        setOpen(false);
      });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });
  }
});
