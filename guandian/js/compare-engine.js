(function () {
  const params = new URLSearchParams(location.search);
  const ids = (params.get('ids') || '').split(',').filter(Boolean);
  if (ids.length < 2) { location.href = 'index.html'; return; }

  function fmt(n) { return n == null ? '—' : n.toLocaleString('zh-CN'); }

  async function main() {
    const app = document.getElementById('compareApp');
    try {
      const res = await fetch('data/companies.json');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      const list = ids.map(id => data.companies.find(c => c.id === id)).filter(Boolean);
      if (list.length < 2) { location.href = 'index.html'; return; }

    const latest = c => (c.annuals || [])[0] || {};
    const prev = c => (c.annuals || [])[1] || {};

    const rows = [
      { label: '股票代码', fn: c => c.ticker },
      { label: '财年截止', fn: c => c.fiscalYearEnd },
      { label: '最新财年', fn: c => latest(c).label || latest(c).year },
      { label: '营收', fn: c => fmt(latest(c).revenue) + ' ' + c.unit },
      { label: '营收同比', fn: c => latest(c).yoyRev != null ? (latest(c).yoyRev >= 0 ? '+' : '') + latest(c).yoyRev.toFixed(1) + '%' : '—' },
      { label: '归母净利', fn: c => fmt(latest(c).netProfit) + ' ' + c.unit },
      { label: '利润同比', fn: c => latest(c).yoyProfit != null ? (latest(c).yoyProfit >= 0 ? '+' : '') + latest(c).yoyProfit.toFixed(1) + '%' : '—' },
      { label: '研发', fn: c => fmt(latest(c).rd) + ' ' + c.unit },
      { label: '研发占比', fn: c => latest(c).rdPct != null ? latest(c).rdPct + '%' : '—' },
      { label: '市值', fn: c => (c.market || {}).marketCap || '—' },
      { label: '市盈率', fn: c => (c.market || {}).pe != null ? c.market.pe + '×' : '—' },
      { label: '十维均分', fn: c => {
        const a = c.agents || [];
        return a.length ? Math.round(a.reduce((s, x) => s + x.score, 0) / a.length) : '—';
      }}
    ];

    let html = '<section class="section"><h2>核心指标对比</h2><div class="table-wrap"><table class="compare-table"><thead><tr><th>指标</th>';
    list.forEach(c => { html += `<th style="border-top:3px solid ${c.color}">${c.name}</th>`; });
    html += '</tr></thead><tbody>';
    rows.forEach(r => {
      html += `<tr><td><strong>${r.label}</strong></td>`;
      list.forEach(c => { html += `<td>${r.fn(c)}</td>`; });
      html += '</tr>';
    });
    html += '</tbody></table></div></section>';

    html += '<section class="section"><h2>营收趋势对比（最新五年）</h2><div class="chart-box" style="height:360px"><canvas id="cmpChart"></canvas></div></section>';

    html += '<section class="section"><h2>各公司定义摘要</h2><div class="grid2">';
    list.forEach(c => {
      html += `<div class="block" style="border-left:3px solid ${c.color}"><div class="t">${c.name}</div><p style="font-size:13px">${c.definition || ''}</p>
        <a href="report.html?id=${c.id}" style="font-size:12px;color:var(--primary)">查看完整报告 →</a></div>`;
    });
    html += '</div></section>';

    document.getElementById('compareApp').innerHTML = html;

    const ctx = document.getElementById('cmpChart');
    const datasets = list.map(c => {
      const annuals = [...(c.annuals || [])].reverse();
      return {
        label: c.name,
        data: annuals.map(a => a.revenue),
        borderColor: c.color,
        backgroundColor: c.color + '33',
        tension: 0.3
      };
    });
    const labels = [...new Set(list.flatMap(c => [...(c.annuals || [])].reverse().map(a => a.label || a.year)))];
    new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: '营收（各自单位：亿元/亿美元）— 勿跨币种直接比绝对值' } } }
    });
    } catch (e) {
      app.innerHTML =
        '<div class="section"><p class="hint" style="color:var(--neg)">对比数据加载失败</p>' +
        '<p class="hint"><a href="index.html">返回公司列表</a></p></div>';
    }
  }
