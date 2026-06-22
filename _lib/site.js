(function (global) {
  'use strict';

  function normalizePath(path) {
    return path.replace(/\\/g, '/');
  }

  function sectionRoot(section) {
    var path = normalizePath(global.location.pathname);
    var marker = '/' + section.replace(/^\/+|\/+$/g, '');
    var idx = path.indexOf(marker);
    if (idx !== -1) {
      return path.slice(0, idx + marker.length) + '/';
    }
    if (/\.html$/i.test(path)) {
      return path.slice(0, path.lastIndexOf('/') + 1);
    }
    return path.endsWith('/') ? path : path + '/';
  }

  function asset(rel, section) {
    var base = global.location.origin + sectionRoot(section || '');
    return new URL(rel, base).href;
  }

  function page(rel, section) {
    return asset(rel, section);
  }

  function isFileProtocol() {
    return global.location.protocol === 'file:';
  }

  function showFileProtocolBanner() {
    if (!isFileProtocol() || document.getElementById('site-file-banner')) return;
    var banner = document.createElement('div');
    banner.id = 'site-file-banner';
    banner.setAttribute('role', 'alert');
    banner.style.cssText =
      'position:fixed;inset:0 auto auto 0;right:0;z-index:99999;padding:14px 18px;' +
      'background:#7f1d1d;color:#fff;font:14px/1.6 system-ui,sans-serif;text-align:center;' +
      'box-shadow:0 4px 20px rgba(0,0,0,.25)';
    banner.innerHTML =
      '当前为本地文件模式，网站无法加载数据。请在项目根目录运行 <strong>npm start</strong> 或 <strong>./start.ps1</strong>，' +
      '然后访问 <strong>http://localhost:8080</strong>';
    document.body.prepend(banner);
    document.body.style.paddingTop = '56px';
  }

  global.Site = {
    sectionRoot: sectionRoot,
    asset: asset,
    page: page,
    isFileProtocol: isFileProtocol,
    showFileProtocolBanner: showFileProtocolBanner
  };

  if (document.body) {
    showFileProtocolBanner();
  } else {
    document.addEventListener('DOMContentLoaded', showFileProtocolBanner);
  }
})(window);
