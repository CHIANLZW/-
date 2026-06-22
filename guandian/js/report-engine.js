(function () {
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  if (!id) { location.href = 'index.html'; return; }

  let company = null;
  let charts = [];

  function fmt(n, unit) {
    if (n == null || n === '') return '—';
    if (typeof n === 'number') return n.toLocaleString('zh-CN') + (unit || '');
    return n;
  }

  function yoyClass(v) {
    if (v == null) return '';
    return v >= 0 ? 'up' : 'down';
  }

  function yoyStr(v) {
    if (v == null) return '—';
    return (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
  }

  function avgAgentScore(agents) {
    if (!agents?.length) return '—';
    const s = agents.reduce((a, b) => a + b.score, 0) / agents.length;
    return Math.round(s);
  }

  function setTheme(color) {
    document.documentElement.style.setProperty('--primary', color);
    const dark = shadeColor(color, -15);
    document.documentElement.style.setProperty('--primary-dark', dark);
  }

  function shadeColor(hex, percent) {
    const num = parseInt(hex.replace('#', ''), 16);
    const r = Math.min(255, Math.max(0, (num >> 16) + percent));
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + percent));
    const b = Math.min(255, Math.max(0, (num & 0xff) + percent));
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  function renderHeader(c) {
    return `
      <header class="header">
        <span class="tag">${c.ticker} · ${c.exchange}${c.listed === false ? ' · 非上市' : ''}</span>
        <h1>${c.name}（${c.nameEn}）</h1>
        <p class="sub">${c.tagline || ''}</p>
        <div class="meta">
          <span>📅 报告日期：2026-06-22</span>
          <span>📊 最新财报：${c.latestReport || '—'}</span>
          ${c.ipoDate ? `<span>🏢 上市：${c.ipoDate}</span>` : ''}
          ${c.ceo ? `<span>👤 CEO：${c.ceo}</span>` : ''}
          <span>📆 财年截止：${c.fiscalYearEnd}</span>
        </div>
        ${c.aliasNote ? `<p class="sub" style="margin-top:10px;font-size:12px">⚠ ${c.aliasNote}</p>` : ''}
      </header>`;
  }

  function renderMarket(c) {
    const m = c.market || {};
    return `
      <section class="section" id="s1">
        <h2><span class="n">1</span>市值与市场表现</h2>
        <div class="kpi-grid">
          <div class="kpi"><div class="l">股价</div><div class="v">${m.price || '—'}</div><div class="c">${m.priceNote || ''}</div></div>
          <div class="kpi"><div class="l">市值</div><div class="v">${m.marketCap || '—'}</div></div>
          <div class="kpi"><div class="l">${m.peLabel || '市盈率'}</div><div class="v">${m.pe != null ? m.pe + '×' : '—'}</div></div>
          <div class="kpi"><div class="l">52周高</div><div class="v">${m.week52High || '—'}</div></div>
          <div class="kpi"><div class="l">52周低</div><div class="v">${m.week52Low || '—'}</div></div>
          ${m.ytdChange ? `<div class="kpi"><div class="l">年内涨跌</div><div class="v ${m.ytdChange.startsWith('-') ? 'down' : 'up'}">${m.ytdChange}</div></div>` : ''}
          ${m.dividendYield ? `<div class="kpi"><div class="l">股息率</div><div class="v">${m.dividendYield}</div></div>` : ''}
        </div>
        <p class="hint" style="margin-top:12px">来源：${m.source || '—'}${m.note ? ' · ' + m.note : ''}</p>
        <div class="chart-row">
          <div class="chart-box"><canvas id="revChart"></canvas></div>
          <div class="chart-box"><canvas id="profitChart"></canvas></div>
        </div>
      </section>`;
  }

  function renderFinancials(c) {
    const rows = (c.annuals || []).map(a => `
      <tr>
        <td><strong>${a.label || a.year}</strong></td>
        <td>${fmt(a.revenue)}</td>
        <td>${fmt(a.netProfit)}</td>
        <td>${fmt(a.adjNetProfit || a.nonGaapNet)}</td>
        <td>${a.grossMargin != null ? a.grossMargin + '%' : '—'}</td>
        <td>${a.netMargin != null ? a.netMargin + '%' : '—'}</td>
        <td>${fmt(a.rd)}</td>
        <td>${a.rdPct != null ? a.rdPct + '%' : '—'}</td>
        <td class="${yoyClass(a.yoyRev)}">${yoyStr(a.yoyRev)}</td>
        <td class="${yoyClass(a.yoyProfit)}">${yoyStr(a.yoyProfit)}</td>
      </tr>
    `).join('');

    const q = c.quarterly;
    const qRow = q ? `<tr style="background:#f0fdf4"><td><strong>${q.period}</strong> <span class="badge b-q">季报</span></td>
      <td>${fmt(q.revenue)}</td><td>—</td><td>${fmt(q.adjNetProfit)}</td><td>—</td><td>—</td>
      <td>${fmt(q.rd)}</td><td>—</td>
      <td class="${yoyClass(q.yoyRev)}">${yoyStr(q.yoyRev)}</td><td>—</td></tr>` : '';

    const reports = (c.reports || []).filter(r => r.title).map(r => `
      <tr><td>${r.date || '—'}</td><td><span class="badge b-${r.type || 'annual'}">${r.type === 'q' ? '季报' : '年报'}</span></td><td>${r.title}</td></tr>
    `).join('');

    return `
      <section class="section" id="s2">
        <h2><span class="n">2</span>近五年财务报告清单</h2>
        <p class="hint">金额单位：${c.unit}（${c.currency}）· 财年截止 ${c.fiscalYearEnd}</p>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>财年</th><th>营收</th><th>归母净利</th><th>经调/非GAAP净利</th>
              <th>毛利率</th><th>净利率</th><th>研发</th><th>研发占比</th><th>营收同比</th><th>利润同比</th>
            </tr></thead>
            <tbody>${rows}${qRow}</tbody>
          </table>
        </div>
        ${reports ? `<h3>近年披露清单</h3><div class="table-wrap"><table><thead><tr><th>日期</th><th>类型</th><th>公告</th></tr></thead><tbody>${reports}</tbody></table></div>` : ''}
      </section>`;
  }

  function renderSegments(c) {
    const segs = c.segments || [];
    if (!segs.length) return '';
    const hasNums = segs.some(s => s.y1 != null);
    if (!hasNums) {
      return `<section class="section" id="s3"><h2><span class="n">3</span>业务板块</h2>
        <div class="grid2">${segs.map(s => `<div class="block"><div class="t">${s.name}</div><p style="font-size:13px">${s.note || ''}</p></div>`).join('')}</div></section>`;
    }
    const y1 = segs[0].y1Label || 'Y1';
    const y2 = segs[0].y2Label || 'Y2';
    const rows = segs.map(s => `<tr>
      <td>${s.name}</td><td>${fmt(s.y1)}</td><td>${fmt(s.y2)}</td>
      <td>${s.y1 && s.y2 ? yoyStr(((s.y2 - s.y1) / s.y1) * 100) : '—'}</td>
      <td style="font-size:12px;color:var(--muted)">${s.note || ''}</td>
    </tr>`).join('');
    return `
      <section class="section" id="s3">
        <h2><span class="n">3</span>业务与产品线对比</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>板块</th><th>${y1}</th><th>${y2}</th><th>同比</th><th>备注</th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>
        <div class="chart-box" style="height:220px;margin-top:14px"><canvas id="segChart"></canvas></div>
      </section>`;
  }

  function renderRD(c) {
    const rd = c.rd;
    if (!rd?.years?.length) return '';
    const years = rd.years;
    let activeIdx = 0;

    function rdPanel(idx) {
      const y = years[idx];
      const bd = y.breakdown || [];
      const bdRows = bd.map((b, i) => `
        <div class="rd-metric"><span>${b.name}${b.est ? '<span class="tag-est">推算</span>' : '<span class="tag-official">披露</span>'}</span>
        <span>${fmt(b.amount)} ${b.note ? '('+b.note+')' : ''}</span></div>`).join('');
      return `
        <div class="rd-detail" id="rdPanel">
          <div class="rd-title">${y.year} 研发投入</div>
          <div class="rd-amt">${fmt(y.total)} ${c.unit}</div>
          <div class="rd-meta">占营收 ${y.pct != null ? y.pct + '%' : '—'} · ${rd.official ? '总额来自财报' : '估算'}</div>
          ${bdRows}
        </div>`;
    }

    const tabs = years.map((y, i) => `<button class="year-tab ${i === 0 ? 'active' : ''}" data-idx="${i}">${y.year}</button>`).join('');

    return `
      <section class="section" id="rdSection">
        <h2><span class="n">4</span>研发投入深度分析</h2>
        <p class="hint">${rd.note || ''}</p>
        <div class="year-tabs" id="rdTabs">${tabs}</div>
        <div class="rd-layout">
          <div>
            <div class="chart-box" style="height:280px"><canvas id="rdPie"></canvas></div>
            <div class="chart-box" style="height:200px;margin-top:14px"><canvas id="rdBar"></canvas></div>
          </div>
          ${rdPanel(0)}
        </div>
      </section>`;
  }

  function renderQualitative(c) {
    const q = c.qualitative || {};
    const agents = c.agents || [];
    const avg = avgAgentScore(agents);
    const cards = agents.map(a => `
      <div class="agent-card"><div class="role">${a.role}</div><div class="score">${a.score}</div><div class="view">${a.view}</div></div>
    `).join('');

    return `
      <section class="section" id="qualSection">
        <h2><span class="n">5</span>企业定性分析 · 十维辩论</h2>
        <div class="grid2">
          <div class="block"><div class="t">PE 估值逻辑</div><p style="font-size:13px">${q.peLowReason || '—'}</p></div>
          <div class="block"><div class="t">科技 vs 制造</div><p style="font-size:13px">${q.techVsMfg || '—'}</p></div>
        </div>
        ${q.userCorrection ? `<div class="compare-warn" style="margin-top:12px">${q.userCorrection}</div>` : ''}
        <p style="margin:14px 0 6px;font-weight:600">十维分析师辩论 · 综合分 <span style="color:var(--primary);font-size:20px">${avg}</span>/100</p>
        <div class="agent-grid">${cards}</div>
        <div class="chart-row">
          <div class="chart-box" style="height:300px"><canvas id="agentRadar"></canvas></div>
          <div class="chart-box" style="height:300px"><canvas id="agentBar"></canvas></div>
        </div>
        <p class="hint" style="margin-top:8px">定义：${c.definition || ''}</p>
      </section>`;
  }

  function renderDimensions(c) {
    const dims = c.dimensions || [];
    const bars = dims.map(d => `
      <div class="score-bar">
        <span class="lbl">${d.name}</span>
        <div class="bg"><div class="fill" style="width:${d.score || 0}%"></div></div>
        <span class="num">${d.score != null ? d.score : '—'}</span>
      </div>
      <p class="hint" style="margin:-2px 0 8px 108px">${d.detail || ''}</p>
    `).join('');
    return `
      <section class="section" id="s6">
        <h2><span class="n">6</span>六维综合财务分析</h2>
        ${bars}
        <div class="chart-box" style="height:260px;margin-top:14px"><canvas id="dimRadar"></canvas></div>
      </section>`;
  }

  function renderConclusion(c) {
    const sources = (c.sources || []).map(s => `<li><a href="${s.url}" target="_blank" rel="noopener">${s.title}</a></li>`).join('');
    return `
      <section class="section" id="s7">
        <h2><span class="n">7</span>外部研报与数据来源</h2>
        <ul class="source-list">${sources}</ul>
      </section>
      <section class="section" id="s8">
        <h2><span class="n">8</span>综合结论</h2>
        <div class="verdict"><div class="r">投资研究摘要</div><p>${c.conclusion || ''}</p></div>
      </section>`;
  }

  function initCharts(c) {
    charts.forEach(ch => ch.destroy());
    charts = [];
    const color = c.color;
    const annuals = [...(c.annuals || [])].reverse();
    const labels = annuals.map(a => a.label || a.year);
    const rev = annuals.map(a => a.revenue);
    const profit = annuals.map(a => a.netProfit);

    const revCtx = document.getElementById('revChart');
    if (revCtx) {
      charts.push(new Chart(revCtx, {
        type: 'bar',
        data: { labels, datasets: [{ label: `营收 (${c.unit})`, data: rev, backgroundColor: color + '99' }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: '近五年营收' } } }
      }));
    }
    const profitCtx = document.getElementById('profitChart');
    if (profitCtx) {
      charts.push(new Chart(profitCtx, {
        type: 'line',
        data: { labels, datasets: [{ label: `归母净利 (${c.unit})`, data: profit, borderColor: color, tension: 0.3, fill: false }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: '近五年净利润' } } }
      }));
    }

    const segs = (c.segments || []).filter(s => s.y2 != null);
    const segCtx = document.getElementById('segChart');
    if (segCtx && segs.length) {
      charts.push(new Chart(segCtx, {
        type: 'bar',
        data: {
          labels: segs.map(s => s.name),
          datasets: [
            { label: segs[0].y2Label || 'Y2', data: segs.map(s => s.y2), backgroundColor: color },
            { label: segs[0].y1Label || 'Y1', data: segs.map(s => s.y1), backgroundColor: color + '55' }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: '业务板块收入对比' } } }
      }));
    }

    const rd = c.rd;
    if (rd?.years?.length) {
      let rdIdx = 0;
      const pieColors = ['#ff6700','#3b82f6','#10b981','#f59e0b','#8b5cf6','#ec4899'];

      function updateRD(idx) {
        const y = rd.years[idx];
        const bd = y.breakdown || [];
        if (charts.find(ch => ch.canvas?.id === 'rdPie')) {
          const old = charts.find(ch => ch.canvas?.id === 'rdPie');
          old.destroy();
          charts = charts.filter(ch => ch !== old);
        }
        if (charts.find(ch => ch.canvas?.id === 'rdBar')) {
          const old = charts.find(ch => ch.canvas?.id === 'rdBar');
          old.destroy();
          charts = charts.filter(ch => ch !== old);
        }

        const pieCtx = document.getElementById('rdPie');
        if (pieCtx && bd.length) {
          charts.push(new Chart(pieCtx, {
            type: 'doughnut',
            data: { labels: bd.map(b => b.name), datasets: [{ data: bd.map(b => b.amount), backgroundColor: pieColors }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: `${y.year} 研发分板块` } } }
          }));
        }

        const barCtx = document.getElementById('rdBar');
        if (barCtx) {
          charts.push(new Chart(barCtx, {
            type: 'bar',
            data: {
              labels: rd.years.map(yr => yr.year),
              datasets: [{ label: '研发总额', data: rd.years.map(yr => yr.total), backgroundColor: color + 'aa' }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: '研发历年趋势' } } }
          }));
        }

        const panel = document.getElementById('rdPanel');
        if (panel) {
          const bdHtml = bd.map(b => `
            <div class="rd-metric"><span>${b.name}${b.est ? '<span class="tag-est">推算</span>' : '<span class="tag-official">披露</span>'}</span>
            <span>${fmt(b.amount)} ${c.unit}</span></div>`).join('');
          panel.innerHTML = `
            <div class="rd-title">${y.year} 研发投入</div>
            <div class="rd-amt">${fmt(y.total)} ${c.unit}</div>
            <div class="rd-meta">占营收 ${y.pct != null ? y.pct + '%' : '—'}</div>${bdHtml}`;
        }
      }

      document.querySelectorAll('#rdTabs .year-tab').forEach(tab => {
        tab.addEventListener('click', () => {
          document.querySelectorAll('#rdTabs .year-tab').forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          updateRD(+tab.dataset.idx);
        });
      });
      updateRD(0);
    }

    const agents = c.agents || [];
    if (agents.length) {
      const agentCtx = document.getElementById('agentRadar');
      if (agentCtx) {
        charts.push(new Chart(agentCtx, {
          type: 'radar',
          data: {
            labels: agents.map(a => a.role),
            datasets: [{ label: '评分', data: agents.map(a => a.score), backgroundColor: color + '33', borderColor: color }]
          },
          options: { responsive: true, maintainAspectRatio: false, scales: { r: { min: 0, max: 100 } } }
        }));
      }
      const agentBarCtx = document.getElementById('agentBar');
      if (agentBarCtx) {
        charts.push(new Chart(agentBarCtx, {
          type: 'bar',
          data: {
            labels: agents.map(a => a.role),
            datasets: [{ data: agents.map(a => a.score), backgroundColor: color + '99' }]
          },
          options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
        }));
      }
    }

    const dims = (c.dimensions || []).filter(d => d.score != null);
    const dimCtx = document.getElementById('dimRadar');
    if (dimCtx && dims.length) {
      charts.push(new Chart(dimCtx, {
        type: 'radar',
        data: {
          labels: dims.map(d => d.name),
          datasets: [{ label: '六维评分', data: dims.map(d => d.score), backgroundColor: color + '33', borderColor: color }]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { r: { min: 0, max: 100 } } }
      }));
    }
  }

  async function main() {
    const app = document.getElementById('app');
    try {
      const res = await fetch('data/companies.json');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      company = data.companies.find(c => c.id === id);
      if (!company) {
        app.innerHTML = '<div class="section"><p>未找到该公司，<a href="index.html">返回公司列表</a></p></div>';
        return;
      }
    } catch (e) {
      app.innerHTML =
        '<div class="section"><p class="hint" style="color:var(--neg)">报告数据加载失败</p>' +
        '<p class="hint">请通过网站服务器访问（不可直接双击本地 HTML）。<a href="index.html">返回公司列表</a></p></div>';
      return;
    }
    setTheme(company.color);
    document.title = `${company.name} · 综合财务分析报告`;
    document.getElementById('navTitle').textContent = company.name;

    document.getElementById('app').innerHTML =
      renderHeader(company) +
      renderMarket(company) +
      renderFinancials(company) +
      renderSegments(company) +
      renderRD(company) +
      renderQualitative(company) +
      renderDimensions(company) +
      renderConclusion(company);

    document.getElementById('disclaimer').textContent =
      `数据来源：各公司官方财报与 IR · 金额单位 ${company.unit} · 仅供研究参考，不构成投资建议`;

    initCharts(company);
  }

  main();
})();
