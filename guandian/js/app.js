(function () {
  'use strict';

  var SECTION_ORDER = ['overview', 'watchlist', 'research', 'predictions', 'log'];

  function guandianBase() {
    var path = location.pathname.replace(/\\/g, '/');
    var marker = '/guandian';
    var idx = path.indexOf(marker);
    if (idx !== -1) return path.slice(0, idx + marker.length) + '/';
    if (/\.html$/i.test(path)) return path.slice(0, path.lastIndexOf('/') + 1);
    return path.endsWith('/') ? path : path + '/';
  }

  function initMobileNav() {
    var toggle = document.querySelector('.site-header__toggle');
    var nav = document.querySelector('.site-header__nav');
    if (!toggle || !nav) return;

    var setOpen = function (open) {
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.classList.toggle('is-active', open);
      nav.classList.toggle('is-open', open);
      document.body.classList.toggle('nav-open', open);
    };

    toggle.addEventListener('click', function () {
      setOpen(!nav.classList.contains('is-open'));
    });

    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        setOpen(false);
      });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });
  }

  function initSectionNav(sectionIds) {
    var links = document.querySelectorAll('.site-header__nav a[href^="#"]');
    if (!links.length) return;

    var sections = sectionIds
      .map(function (id) {
        return document.getElementById(id);
      })
      .filter(Boolean);

    if (!sections.length) return;

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var id = entry.target.id;
          links.forEach(function (link) {
            link.classList.toggle('is-active', link.getAttribute('href') === '#' + id);
          });
        });
      },
      { rootMargin: '-40% 0px -50% 0px', threshold: 0 }
    );

    sections.forEach(function (section) {
      observer.observe(section);
    });
  }

  function viewClass(view) {
    if (!view) return '';
    if (/看好|买入|增持/i.test(view)) return ' company-card__view--bull';
    if (/谨慎|减持|回避/i.test(view)) return ' company-card__view--bear';
    return ' company-card__view--neutral';
  }

  function renderCompanies(data) {
    var watchlist = document.querySelector('[data-watchlist]');
    var research = document.querySelector('[data-research]');
    var predictions = document.querySelector('[data-predictions]');
    var intro = document.querySelector('[data-intro]');
    var updated = document.querySelector('[data-updated]');

    if (intro && data.intro) intro.textContent = data.intro;
    if (updated && data.updated) updated.textContent = '数据更新 · ' + data.updated;

    if (!data.companies || !data.companies.length) return;

    if (watchlist) {
      watchlist.innerHTML =
        '<table class="data-table">' +
        '<thead><tr>' +
        '<th>公司</th><th>代码</th><th>市场</th><th>行业</th>' +
        '<th>现价</th><th>涨跌幅</th><th>52周区间</th><th>状态</th>' +
        '</tr></thead><tbody>' +
        data.companies
          .map(function (c) {
            return (
              '<tr>' +
              '<td><strong>' + c.name + '</strong></td>' +
              '<td>' + c.ticker + '</td>' +
              '<td>' + c.market + '</td>' +
              '<td>' + c.sector + '</td>' +
              '<td>' + (c.price && c.price.current ? c.price.current : '—') + '</td>' +
              '<td>' + (c.price && c.price.change ? c.price.change : '—') + '</td>' +
              '<td>' + (c.price && c.price.range52w ? c.price.range52w : '—') + '</td>' +
              '<td>' + c.status + '</td>' +
              '</tr>'
            );
          })
          .join('') +
        '</tbody></table>';
    }

    if (research) {
      research.innerHTML = data.companies
        .map(function (c) {
          var p = c.prediction || {};
          return (
            '<article class="company-card" id="co-' + c.id + '">' +
            '<header class="company-card__head">' +
            '<div class="company-card__title-row">' +
            '<h3 class="company-card__name">' + c.name + '</h3>' +
            '<span class="company-card__ticker">' + c.ticker + ' · ' + c.market + '</span>' +
            '</div>' +
            '<div class="company-card__meta">' +
            '<span class="finance-tag">' + c.sector + '</span>' +
            '<span class="finance-tag">' + c.status + '</span>' +
            '<span class="company-card__price">现价 ' + (c.price && c.price.current ? c.price.current : '—') + '</span>' +
            '</div>' +
            '</header>' +
            '<div class="company-card__grid">' +
            '<div class="company-card__block">' +
            '<h4>关注逻辑</h4><p>' + c.thesis + '</p>' +
            '</div>' +
            '<div class="company-card__block">' +
            '<h4>发展方向</h4><p>' + c.direction + '</p>' +
            '</div>' +
            '<div class="company-card__block company-card__block--full">' +
            '<h4>股价与走势预测</h4>' +
            '<p class="company-card__prediction' + viewClass(p.view) + '">' +
            '<strong>' + (p.view || '待判断') + '</strong>' +
            (p.horizon && p.horizon !== '—' ? ' · 窗口 ' + p.horizon : '') +
            (p.target && p.target !== '—' ? ' · 目标 ' + p.target : '') +
            '</p>' +
            '<p>' + (p.summary || '—') + '</p>' +
            '</div>' +
            '<div class="company-card__block company-card__block--full">' +
            '<h4>风险与证伪</h4><p>' + (c.risks || '—') + '</p>' +
            '</div>' +
            '</div>' +
            '<footer class="company-card__foot">行情更新 ' + (c.price && c.price.updated ? c.price.updated : '—') + '</footer>' +
            '</article>'
          );
        })
        .join('');
    }

    if (predictions) {
      predictions.innerHTML =
        '<table class="data-table">' +
        '<thead><tr>' +
        '<th>公司</th><th>代码</th><th>现价</th><th>观点</th><th>目标 / 窗口</th><th>预测摘要</th>' +
        '</tr></thead><tbody>' +
        data.companies
          .map(function (c) {
            var p = c.prediction || {};
            return (
              '<tr>' +
              '<td><strong>' + c.name + '</strong></td>' +
              '<td>' + c.ticker + '</td>' +
              '<td>' + (c.price && c.price.current ? c.price.current : '—') + '</td>' +
              '<td><span class="pred-badge' + viewClass(p.view) + '">' + (p.view || '待判断') + '</span></td>' +
              '<td>' + (p.target && p.target !== '—' ? p.target : '—') + (p.horizon && p.horizon !== '—' ? ' / ' + p.horizon : '') + '</td>' +
              '<td>' + (p.summary || '—') + '</td>' +
              '</tr>'
            );
          })
          .join('') +
        '</tbody></table>';
    }
  }

  function loadCompanies() {
    fetch(guandianBase() + 'data/companies.json')
      .then(function (res) {
        return res.json();
      })
      .then(renderCompanies)
      .catch(function () {
        var err = '<p class="hub-error">公司研究数据加载失败。</p>';
        ['[data-watchlist]', '[data-research]', '[data-predictions]'].forEach(function (sel) {
          var el = document.querySelector(sel);
          if (el) el.innerHTML = err;
        });
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initMobileNav();
    initSectionNav(SECTION_ORDER);
    loadCompanies();
  });
})();
