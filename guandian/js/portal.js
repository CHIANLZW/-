(function () {
  let companies = [];

  const ICONS = {
    xiaomi: '米',
    alibaba: '阿',
    tencent: '腾',
    apple: '',
    nvidia: 'N',
    amd: 'D',
    luxshare: '立'
  };

  const DEEP = { xiaomi: true };

  function reportUrl(id) {
    return 'report.html?id=' + encodeURIComponent(id);
  }

  function isFileProtocol() {
    return location.protocol === 'file:';
  }

  function loadCompanies() {
    if (window.GUANDIAN_COMPANIES) {
      return Promise.resolve(window.GUANDIAN_COMPANIES);
    }
    if (isFileProtocol()) {
      return Promise.reject(new Error('file-protocol'));
    }
    return fetch('data/companies.json').then((r) => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function renderGrid() {
    const grid = document.getElementById('companyGrid');
    grid.innerHTML = companies
      .map(
        (c) => `
      <a class="company-card" href="${reportUrl(c.id)}" style="--primary:${c.color}">
        <div class="logo" style="background:${c.color}">${ICONS[c.id] || c.name[0]}</div>
        <h3>${c.name}</h3>
        <div class="ticker">${c.ticker} · ${c.exchange}</div>
        <div class="brief">${c.tagline || ''}</div>
        <div class="company-card__meta">
          <span>${c.latestReport || '—'}</span>
          ${DEEP[c.id] ? '<span class="company-card__badge">深度模板</span>' : '<span class="company-card__badge">标准版</span>'}
        </div>
        <div class="company-card__cta">进入研究报告 →</div>
      </a>`
      )
      .join('');
  }

  function init() {
    loadCompanies()
      .then((data) => {
        companies = data.companies || [];
        if (!companies.length) throw new Error('empty');
        renderGrid();
      })
      .catch((err) => {
        console.error(err);
        const hint =
          err.message === 'file-protocol'
            ? '当前为本地文件打开（file://），浏览器会拦截 JSON 请求。请双击 <code>打开门户.bat</code>，或在项目根目录运行 <code>npm start</code> 后访问 <code>http://localhost:8080/guandian/</code>。也可使用在线版：<a href="https://chianlzw.github.io/-/guandian/" target="_blank" rel="noopener">chianlzw.github.io/-/guandian/</a>'
            : '公司列表加载失败。请通过 <a href="https://chianlzw.github.io/-/guandian/" target="_blank" rel="noopener">GitHub Pages</a> 或本地服务器（<code>npm start</code>）访问。';
        document.getElementById('companyGrid').innerHTML =
          '<div class="section" style="grid-column:1/-1"><p class="hint" style="color:var(--neg)">' + hint + '</p></div>';
      });
  }

  init();
})();
