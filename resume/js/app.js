(function () {
  'use strict';

  var SECTION_ORDER = ['profile', 'skills', 'internship', 'projects', 'education', 'strengths'];

  function resumeBase() {
    var path = location.pathname.replace(/\\/g, '/');
    var marker = '/resume';
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

  function initSectionNav() {
    var links = document.querySelectorAll('.site-header__nav a[href^="#"]');
    if (!links.length) return;

    var sections = SECTION_ORDER.map(function (id) {
      return document.getElementById(id);
    }).filter(Boolean);

    if (!sections.length) return;

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var id = entry.target.id;
          links.forEach(function (link) {
            var active = link.getAttribute('href') === '#' + id;
            link.classList.toggle('is-active', active);
          });
        });
      },
      { rootMargin: '-40% 0px -50% 0px', threshold: 0 }
    );

    sections.forEach(function (section) {
      observer.observe(section);
    });
  }

  function renderRoleHub() {
    var hub = document.querySelector('[data-role-hub]');
    if (!hub) return;

    fetch(resumeBase() + 'data/roles.json')
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        var person = data.person;
        var contact = document.querySelector('[data-hub-contact]');
        if (contact) {
          contact.innerHTML =
            '<p class="hub__contact-title">联系方式</p>' +
            '<p class="hub__contact-lines">电话 <a href="tel:' +
            person.phone +
            '">' +
            person.phone +
            '</a><br>邮箱 <a href="mailto:' +
            person.email +
            '">' +
            person.email +
            '</a></p>';
        }

        hub.innerHTML = data.roles
          .map(function (role) {
            var featured = role.featured ? ' role-card role-card--featured' : ' role-card';
            return (
              '<a href="' +
              role.slug +
              '" class="' +
              featured.trim() +
              '">' +
              '<span class="role-card__label">' +
              role.label +
              '</span>' +
              '<span class="role-card__title">' +
              role.title +
              '</span>' +
              '<span class="role-card__meta">' +
              person.location +
              ' · 期望薪资 ' +
              role.salary +
              '</span>' +
              '<span class="role-card__tags">' +
              role.tags.join(' · ') +
              '</span>' +
              '<span class="role-card__arrow">查看简历 →</span>' +
              '</a>'
            );
          })
          .join('');
      })
      .catch(function () {
        hub.innerHTML = '<p class="hub-error">岗位列表加载失败，请直接访问各岗位页面。</p>';
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initMobileNav();
    initSectionNav();
    renderRoleHub();
  });
})();
