(function () {
  const params = new URLSearchParams(location.search);
  const companyId = params.get('id');
  if (!companyId) {
    location.href = 'index.html';
    return;
  }

  let data = null;
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

  function shadeColor(hex, percent) {
    const num = parseInt(hex.replace('#', ''), 16);
    const r = Math.min(255, Math.max(0, (num >> 16) + percent));
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + percent));
    const b = Math.min(255, Math.max(0, (num & 0xff) + percent));
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  function setTheme(color) {
    document.documentElement.style.setProperty('--primary', color);
    document.documentElement.style.setProperty('--primary-dark', shadeColor(color, -15));
  }

  function monthIndex(ym) {
    const [y, m] = ym.split('-').map(Number);
    return y * 12 + (m - 1);
  }

  function indexToMonth(idx) {
    const y = Math.floor(idx / 12);
    const m = (idx % 12) + 1;
    return y + '-' + String(m).padStart(2, '0');
  }

  function interpolateAnchors(anchors, field) {
    if (!anchors?.length) return [];
    const f = field || 'value';
    const sorted = [...anchors].sort((a, b) => monthIndex(a.month) - monthIndex(b.month));
    const start = monthIndex(sorted[0].month);
    const end = monthIndex(sorted[sorted.length - 1].month);
    const out = [];
    let ai = 0;
    for (let i = start; i <= end; i++) {
      while (ai < sorted.length - 2 && i > monthIndex(sorted[ai + 1].month)) ai++;
      const a = sorted[ai];
      const b = sorted[Math.min(ai + 1, sorted.length - 1)];
      const ia = monthIndex(a.month);
      const ib = monthIndex(b.month);
      let val = a[f];
      if (ib > ia) {
        const t = (i - ia) / (ib - ia);
        val = a[f] + (b[f] - a[f]) * t;
      }
      const point = { month: indexToMonth(i) };
      point[f] = field === 'price' ? +val.toFixed(2) : Math.round(val);
      out.push(point);
    }
    return out;
  }

  function buildSeries(forecast, field) {
    const keys = ['bull', 'base', 'bear', 'consensus'];
    const series = {};
    keys.forEach((k) => {
      series[k] = interpolateAnchors(forecast.anchors[k], field);
    });
    return { months: series.base.map((p) => p.month), series };
  }

  function stanceClass(stance) {
    if (!stance) return '';
    if (stance.includes('空')) return 'stance-bear';
    if (stance.includes('多')) return 'stance-bull';
    return 'stance-neutral';
  }

  function pricePrefix(c) {
    if (c.currency === 'USD') return '$';
    if (c.ticker?.includes('.HK')) return 'HK$';
    return '¥';
  }

  function capUnit(c) {
    if (c.currency === 'USD') return '亿美元';
    if (c.ticker?.includes('.HK')) return '亿港元';
    return '亿元';
  }

  function fmtPrice(c, val) {
    if (val == null || val === '—') return '—';
    return pricePrefix(c) + val;
  }

  function segUnit(c) {
    return c.unit || '亿元';
  }

  function roundText(r) {
    if (Array.isArray(r)) return r.map((p) => `<p>${p}</p>`).join('');
    return `<p>${r}</p>`;
  }

  function secTitle(num, text, badge) {
    return `<h2 class="section__title"><span class="sec-num">${num}</span><span class="sec-text">${text}</span>${badge || ''}</h2>`;
  }

  function scoreRing(score, color) {
    const s = Math.min(100, Math.max(0, score || 0));
    const r = 34;
    const circ = 2 * Math.PI * r;
    const offset = circ * (1 - s / 100);
    return `<div class="score-ring-wrap" title="综合评分 ${s}/100">
      <svg class="score-ring" viewBox="0 0 80 80" width="64" height="64" aria-hidden="true">
        <circle cx="40" cy="40" r="${r}" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="7"/>
        <circle cx="40" cy="40" r="${r}" fill="none" stroke="${color || '#fff'}" stroke-width="7"
          stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}"
          stroke-linecap="round" transform="rotate(-90 40 40)"/>
        <text x="40" y="44" text-anchor="middle" fill="#fff" font-size="16" font-weight="700">${s}</text>
      </svg>
      <span class="score-ring__lbl">综合分</span>
    </div>`;
  }

  function renderProgressBar() {
    return '<div class="read-progress" aria-hidden="true"><div class="read-progress__bar"></div></div>';
  }

  function renderReportMeta(c, meta) {
    return `<div class="report-meta">
      <span>数据截至 ${meta.reportDate || '2026-06-23'}</span>
      <span>·</span>
      <span>${c.exchange || ''}</span>
      <span>·</span>
      <span>财年 ${c.fiscalYearEnd || '—'}</span>
      <span>·</span>
      <span class="report-meta__tag">分析师研究版 v4</span>
    </div>`;
  }

  async function loadData(id) {
    if (window.GUANDIAN_REPORTS && window.GUANDIAN_REPORTS[id]) {
      const ext = window.GUANDIAN_REPORTS[id];
      const companies = window.GUANDIAN_COMPANIES || { meta: {}, companies: [] };
      const company = (companies.companies || []).find((c) => c.id === id);
      if (!company) throw new Error('company not found');
      return { meta: companies.meta || {}, company, ...ext };
    }
    const compRes = await fetch('data/companies.json');
    if (!compRes.ok) throw new Error('companies.json');
    const companiesData = await compRes.json();
    const company = (companiesData.companies || []).find((c) => c.id === id);
    if (!company) throw new Error('company not found: ' + id);
    const repRes = await fetch('data/reports/' + id + '.json');
    if (!repRes.ok) throw new Error('report ' + id);
    const ext = await repRes.json();
    return { meta: companiesData.meta, company, ...ext };
  }

  function renderToc() {
    const items = [
      ['s-integrity', '财报核查'],
      ['s-plan', '优化计划'],
      ['s-narr', '研究正文'],
      ['s-seg', '分部对标'],
      ['s-forecast', '股价预测'],
      ['s-agents', '博弈'],
      ['s-appendix', '附录']
    ];
    return `
      <nav class="report-toc" aria-label="报告目录">
        <span class="report-toc__label">目录</span>
        ${items.map(([id, label]) => `<a href="#${id}">${label}</a>`).join('')}
      </nav>`;
  }

  function renderOptimizationPlan(plan) {
    if (!plan?.sections?.length) return '';
    const chars = plan.meta?.actualChars || plan.paragraphs?.join('').length || 0;
    const body = plan.sections
      .map(
        (sec) => `
        <details class="plan-section" ${sec.id === 'ui' ? 'open' : ''}>
          <summary class="plan-section__head">${sec.title}</summary>
          <div class="plan-section__body">
            ${sec.paragraphs.map((p) => `<p>${p}</p>`).join('')}
          </div>
        </details>`
      )
      .join('');
    return `
      <section class="section section--plan" id="s-plan">
        ${secTitle('02', '优化计划方案', `<span class="badge b-annual">${chars} 字</span>`)}
        <p class="hint">${plan.subtitle || ''} · ${plan.reportDate || ''}</p>
        ${body}
      </section>`;
  }

  function flagBadge(flag) {
    const map = { ok: 'b-q', watch: 'b-interim', warn: 'b-annual' };
    const label = { ok: '一致', watch: '关注', warn: '偏离' }[flag] || flag;
    return `<span class="badge ${map[flag] || ''}">${label}</span>`;
  }

  function renderIntegrityViz(fi) {
    if (!fi) return '';
    const ratio = fi.ocfRatio != null ? Math.round(fi.ocfRatio * 100) : null;
    const flags = fi.comparisons || [];
    const ok = flags.filter((f) => f.flag === 'ok').length;
    const watch = flags.filter((f) => f.flag === 'watch').length;
    const warn = flags.filter((f) => f.flag === 'warn').length;
    return `
      <div class="fin-viz">
        ${ratio != null ? `<div class="fin-viz__card">
          <div class="fin-viz__title">利润含金量 · OCF/经调净利</div>
          <div class="fin-viz__bar"><div class="fin-viz__fill" style="width:${ratio}%"></div></div>
          <div class="fin-viz__meta"><span>${ratio}%</span><span class="muted">${ratio < 90 ? '低于 90% 需关注' : '相对健康'}</span></div>
        </div>` : ''}
        <div class="fin-viz__card fin-viz__flags">
          <div class="fin-viz__title">核查信号分布</div>
          <div class="flag-chips">
            <span class="flag-chip flag-chip--ok">一致 ${ok}</span>
            <span class="flag-chip flag-chip--watch">关注 ${watch}</span>
            <span class="flag-chip flag-chip--warn">偏离 ${warn}</span>
          </div>
        </div>
      </div>`;
  }

  function renderFinancialIntegrity(fi) {
    if (!fi) return '';
    const riskClass = fi.riskLevel === 'moderate' ? 'stance-neutral' : fi.riskLevel === 'high' ? 'stance-bear' : 'stance-bull';
    const cmpRows = (fi.comparisons || [])
      .map(
        (r) => `<tr>
        <td>${r.metric}</td>
        <td>${r.management}</td>
        <td>${r.stripped}</td>
        <td>${flagBadge(r.flag)}</td>
      </tr>`
      )
      .join('');

    const periods = (fi.drillDown?.periods || [])
      .map((p) => {
        const rows = (p.rows || [])
          .map(
            (row) => `<tr class="fin-row" data-period="${p.id}">
            <td>${row.line}</td>
            <td>${row.reported != null ? row.reported + (row.unit || '') : '—'}</td>
            <td class="${row.coreOnly ? 'up' : ''}">${row.core != null ? row.core + (row.unit || '') : '—'}</td>
            <td>${row.mgmt ? '管理层' : '法定/核心'}</td>
            <td class="muted">${row.note || ''}</td>
          </tr>`
          )
          .join('');
        return `
        <details class="fin-period" id="fin-${p.id}">
          <summary class="fin-period__head">${p.label} <span class="muted">${p.source || ''}</span></summary>
          <div class="table-wrap table-wrap--compact">
            <table>
              <thead><tr><th>科目</th><th>披露值</th><th>核心/剔除后</th><th>口径</th><th>说明</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </details>`;
      })
      .join('');

    const adjList = (fi.adjustmentItems || [])
      .map(
        (a) => `<li><strong>${a.name}</strong> ${a.amount}${a.unit}（${a.year}）— ${a.effect}。${a.action} <span class="muted">来源：${a.source}</span></li>`
      )
      .join('');

    return `
      <section class="section section--integrity" id="s-integrity">
        ${secTitle('01', '财报真实性核查', `<span class="badge ${riskClass}">${fi.riskLabel || fi.riskLevel}</span>`)}
        <p class="hint hint--method">${fi.methodology}</p>
        ${renderIntegrityViz(fi)}
        <div class="fin-compare-grid">
          <div class="block block--mgmt">
            <div class="block__label">管理层叙事</div>
            <div class="t">想让你看到的</div>
            <p>${fi.managementSays}</p>
          </div>
          <div class="block block--core">
            <div class="block__label">核查结论</div>
            <div class="t">剔除干扰项后</div>
            <p>${fi.afterStripping}</p>
          </div>
        </div>
        <details class="fold" open>
          <summary>叙事 vs 事实对照表</summary>
          <div class="table-wrap table-wrap--compact">
            <table><thead><tr><th>指标</th><th>管理层叙事</th><th>核查后</th><th>信号</th></tr></thead><tbody>${cmpRows}</tbody></table>
          </div>
        </details>
        ${adjList ? `<details class="fold"><summary>建议剔除/单独列示项</summary><ul class="fin-adj-list">${adjList}</ul></details>` : ''}
        <details class="fold fin-drill" open id="s-fin-drill">
          <summary>点击展开 · 财务数据钻取（法定 vs 核心）</summary>
          ${periods}
        </details>
      </section>`;
  }

  function renderNarrative(narr) {
    if (!narr?.paragraphs?.length) return '';
    const chunks = narr.paragraphs;
    const preview = chunks.slice(0, 3).map((p) => `<p>${p}</p>`).join('');
    const rest = chunks
      .slice(3)
      .map((p) => `<p>${p}</p>`)
      .join('');
    return `
      <section class="section section--compact" id="s-narr">
        ${secTitle('03', '深度研究正文', `<span class="badge b-q">约 ${narr.paragraphs.join('').length} 字</span>`)}
        ${preview}
        <details class="fold"><summary>展开全文</summary><div class="narr-body">${rest}</div></details>
      </section>`;
  }

  function renderChiefBar(c, syn, sp, fc) {
    const spBase = sp?.scenarios?.base;
    const fcBase = fc?.scenarios?.base || (fc?.baseline ? { endValue: fc.baseline.value, changePct: '—' } : null);
    const horizon = sp?.horizonEnd || '2028-06';
    return `
      <section class="chief-bar" id="top">
        <div class="chief-bar__layout">
          <div class="chief-bar__main">
            <span class="tag">${c.ticker}</span>
            <h1>${c.name}</h1>
            <p class="chief-bar__sub">${c.tagline || ''}</p>
            <p class="chief-bar__stance ${stanceClass(syn.stance)}">${syn.stance} · ${syn.confidence || '中'}置信</p>
          </div>
          ${scoreRing(syn.finalScore, c.color)}
        </div>
        <div class="chief-kpi">
          <div class="chief-kpi__item"><span>现价</span><strong>${c.market?.price || '—'}</strong></div>
          <div class="chief-kpi__item"><span>市值</span><strong>${c.market?.marketCap || '—'}</strong></div>
          ${spBase ? `<div class="chief-kpi__item"><span>基准股价(${horizon.slice(5)})</span><strong class="up">${fmtPrice(c, spBase.endPrice)}</strong></div>` : ''}
          ${fcBase ? `<div class="chief-kpi__item"><span>基准市值</span><strong class="up">${fmt(fcBase.endValue)}${capUnit(c)}</strong></div>` : ''}
        </div>
        <p class="chief-bar__verdict">${syn.verdict || c.conclusion || ''}</p>
      </section>`;
  }

  function renderSegments(benchmarks, company) {
    const u = segUnit(company);
    const cards = benchmarks
      .map((seg, idx) => {
        const x = seg.company || seg.xiaomi || {};
        const peerRows = seg.peers
          .map(
            (p) => `
          <tr class="peer-row" data-tip="${encodeURIComponent(p.hover || p.gap)}">
            <td><strong>${p.name}</strong><br><span class="muted">${p.ticker}</span></td>
            <td>${p.revenue}</td>
            <td>${p.rd}</td>
            <td>${p.margin || '—'}</td>
            <td class="gap-cell">${p.gap}</td>
          </tr>`
          )
          .join('');
        return `
        <details class="seg-panel" ${idx === 0 ? 'open' : ''}>
          <summary class="seg-panel__head">
            <span class="seg-panel__icon">${seg.icon}</span>
            <span class="seg-panel__title">${seg.name}</span>
            <span class="seg-panel__rev">${fmt(x.revenue2025)}${u} · ${x.yoy || ''}</span>
          </summary>
          <div class="seg-panel__body">
            <div class="seg-company">
              <span class="tip-chip" title="最新营收">营收 ${fmt(x.revenue2025)}${u}</span>
              ${x.yoy ? `<span class="tip-chip">同比 ${x.yoy}</span>` : ''}
              ${x.grossMargin ? `<span class="tip-chip">毛利 ${x.grossMargin}</span>` : ''}
              ${x.rd2025 ? `<span class="tip-chip" title="研发">研发 ${x.rd2025}亿</span>` : ''}
              ${x.volume ? `<span class="tip-chip">${x.volume}</span>` : ''}
              ${x.deliveries ? `<span class="tip-chip">${x.deliveries}</span>` : ''}
              ${x.asp ? `<span class="tip-chip">ASP ${x.asp}</span>` : ''}
            </div>
            <p class="seg-analyst">${seg.analystTake}</p>
            <div class="table-wrap table-wrap--compact">
              <table class="peer-table">
                <thead><tr><th>对标公司</th><th>营收规模</th><th>研发投入</th><th>毛利/利润率</th><th>与${company.name}差距</th></tr></thead>
                <tbody>${peerRows}</tbody>
              </table>
            </div>
          </div>
        </details>`;
      })
      .join('');

    return `
      <section class="section section--compact" id="s-seg">
        ${secTitle('04', '业务板块深度对标', '<span class="badge b-q">分析师视角</span>')}
        <p class="hint">鼠标悬停对标行显示细节；各板块营收/研发为最新公开财年口径。</p>
        <div id="peerTip" class="peer-tip" hidden>悬停表格行查看详情</div>
        ${cards}
      </section>`;
  }

  function renderForecast(fc, sp, c) {
    if (!sp?.scenarios) return '<section class="section section--compact"><p class="hint">暂无股价情景数据</p></section>';

    const calNote = sp?.calibrationNote || fc?.calibrationNote || '';
    const cards = ['bull', 'base', 'bear', 'consensus']
      .filter((k) => sp.scenarios[k])
      .map((k) => {
        const s = fc?.scenarios?.[k];
        const p = sp.scenarios[k];
        const color = p.color || { bull: '#059669', base: '#ff6700', bear: '#dc2626', consensus: '#2563eb' }[k];
        return `<div class="scenario-card" style="--sc-color:${color}">
          <div class="scenario-card__label">${p.label || k}</div>
          <div class="scenario-card__price">${p.endPrice != null ? fmtPrice(c, p.endPrice) : '—'}</div>
          <div class="scenario-card__cap">${s ? fmt(s.endValue) + capUnit(c) : '—'}</div>
          <div class="scenario-card__chg ${(p.changePct || '').startsWith('+') ? 'up' : (p.changePct || '').startsWith('-') ? 'down' : ''}">${p.changePct || ''}</div>
        </div>`;
      })
      .join('');

    return `
      <section class="section section--compact" id="s-forecast">
        ${secTitle('05', '股价与市值预测', '<span class="badge b-interim">2026-06 → 2028-06</span>')}
        ${calNote ? `<p class="hint">${calNote}</p>` : '<p class="hint">基准价约 2026-06 行情；情景折线为研究推演。</p>'}
        <div class="scenario-grid">${cards}</div>
        <div id="klineMount" class="kline-mount"></div>
        <div class="chart-tabs">
          <button type="button" class="chart-tab active" data-chart="price">股价情景折线</button>
          ${fc?.anchors ? '<button type="button" class="chart-tab" data-chart="cap">市值情景折线</button>' : ''}
        </div>
        <div class="chart-box chart-box--fc"><canvas id="forecastMainChart"></canvas></div>
        <details class="fold">
          <summary>展开季度预测节点表</summary>
          <div class="table-wrap table-wrap--compact">
            <table id="forecastTable"><thead><tr><th>月份</th><th>股价综合</th><th>市值综合</th><th>股价区间</th></tr></thead><tbody></tbody></table>
          </div>
        </details>
      </section>`;
  }

  function renderAgents(fw) {
    if (!fw) return '';
    const syn = fw.synthesis || {};
    const agents = fw.agents || [];
    const agentCount = agents.length;
    const agentList = agents
      .map(
        (a, i) => `
      <details class="agent-fold">
        <summary class="agent-fold__head">
          <span class="agent-fold__role">${a.role}</span>
          <span class="skills">${(a.skills || []).slice(0, 3).join(' · ')}</span>
          <span class="stance ${stanceClass(a.stance)}">${a.stance || ''}</span>
          <span class="agent-fold__score">${a.score}</span>
          ${a.targetPrice ? `<span class="agent-fold__target">${fmtPrice(data.company, a.targetPrice.low)}–${fmtPrice(data.company, a.targetPrice.high)}</span>` : ''}
        </summary>
        <div class="agent-fold__body">
          <p class="hint">覆盖板块：${(a.segmentFocus || []).join('、') || '—'}</p>
          ${a.rounds ? `<div class="round-block"><h4>R1 事实陈述</h4>${roundText(a.rounds['1'])}</div>
          <div class="round-block"><h4>R2 交叉质询</h4>${roundText(a.rounds['2'])}</div>
          <div class="round-block"><h4>R3 情景定价</h4>${roundText(a.rounds['3'])}</div>` : `<p>${a.view || ''}</p>`}
        </div>
      </details>`
      )
      .join('');

    return `
      <section class="section section--compact" id="s-agents">
        ${secTitle('06', `${agentCount} 席分析师架构博弈`, '<span class="badge b-annual">默认折叠</span>')}
        <p class="hint">${fw.methodology}</p>
        <details class="fold fold--chief" open>
          <summary>首席综合研判 · ${syn.stance} · ${syn.finalScore}/100</summary>
          <div class="chief-detail">
            <p>${syn.summary}</p>
            <p class="seg-verdict"><strong>分部结论：</strong>${syn.segmentVerdict || ''}</p>
            <div class="grid3">
              <div class="block block--bull"><div class="t">乐观</div><p>${syn.bullCase}</p></div>
              <div class="block"><div class="t">基准</div><p>${syn.baseCase}</p></div>
              <div class="block block--bear"><div class="t">悲观</div><p>${syn.bearCase}</p></div>
            </div>
          </div>
        </details>
        <div class="agent-folds">${agentList}</div>
        <details class="fold">
          <summary>展开评分雷达图</summary>
          <div class="chart-row chart-row--compact">
            <div class="chart-box chart-box--sm"><canvas id="agentRadar"></canvas></div>
            <div class="chart-box chart-box--sm"><canvas id="agentBar"></canvas></div>
          </div>
        </details>
      </section>`;
  }

  function renderAppendix(c, fi) {
    const rows = (c.annuals || [])
      .map(
        (a) => `<tr class="appendix-row" style="cursor:pointer" title="点击查看财报真实性钻取">
        <td>${a.label}</td><td>${fmt(a.revenue)}</td><td>${fmt(a.adjNetProfit ?? a.netProfit)}</td>
        <td>${a.grossMargin != null ? a.grossMargin + '%' : '—'}</td><td class="${yoyClass(a.yoyRev)}">${yoyStr(a.yoyRev)}</td>
      </tr>`
      )
      .join('');

    return `
      <section class="section section--compact" id="s-appendix">
        ${secTitle('07', '附录 · 财务数据', '')}
        ${fi ? '<p class="hint">点击下表任一行可跳转至 <a href="#s-fin-drill">财报真实性钻取</a>；「核心/剔除后」列见各期明细。</p>' : ''}
        <details class="fold" open>
          <summary>近五年财报简表（可点击钻取）</summary>
          <div class="table-wrap table-wrap--compact">
            <table><thead><tr><th>财年</th><th>营收</th><th>经调净利</th><th>毛利率</th><th>营收同比</th></tr></thead><tbody>${rows}</tbody></table>
          </div>
        </details>
        <details class="fold">
          <summary>营收 / 利润趋势图</summary>
          <div class="chart-row chart-row--compact">
            <div class="chart-box chart-box--sm"><canvas id="revChart"></canvas></div>
            <div class="chart-box chart-box--sm"><canvas id="profitChart"></canvas></div>
          </div>
        </details>
        <details class="fold">
          <summary>六维评分</summary>
          ${(c.dimensions || [])
            .map(
              (d) => `<div class="score-bar score-bar--sm">
            <span class="lbl">${d.name}</span><div class="bg"><div class="fill" style="width:${d.score}%"></div></div><span class="num">${d.score}</span>
          </div><p class="hint hint--inline">${d.detail}</p>`
            )
            .join('')}
        </details>
      </section>`;
  }

  function bindAppendixDrill() {
    document.querySelectorAll('.appendix-row').forEach((row) => {
      row.addEventListener('click', () => {
        const target = document.getElementById('s-fin-drill') || document.getElementById('s-integrity');
        if (target) {
          target.open = true;
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  function bindPeerTips() {
    const tip = document.getElementById('peerTip');
    document.querySelectorAll('.peer-row').forEach((row) => {
      row.addEventListener('mouseenter', () => {
        if (!tip) return;
        tip.hidden = false;
        tip.textContent = decodeURIComponent(row.dataset.tip || '');
      });
      row.addEventListener('mouseleave', () => {
        if (tip) tip.hidden = true;
      });
    });
  }

  function fillForecastTable(months, capSeries, priceSeries, sp, fc, c) {
    const tbody = document.querySelector('#forecastTable tbody');
    if (!tbody) return;
    const cu = capUnit(c);
    const show = months.filter((_, i) => i % 3 === 0 || i === months.length - 1);
    tbody.innerHTML = show
      .map((m) => {
        const cp = priceSeries.consensus.find((p) => p.month === m)?.price ?? '—';
        const cm = capSeries.consensus.find((p) => p.month === m)?.value ?? '—';
        const bull = priceSeries.bull.find((p) => p.month === m)?.price ?? '—';
        const bear = priceSeries.bear.find((p) => p.month === m)?.price ?? '—';
        return `<tr><td>${m}</td><td><strong>${fmtPrice(c, cp)}</strong></td><td>${fmt(cm)}${cu}</td><td class="muted">${fmtPrice(c, bear)} – ${fmtPrice(c, bull)}</td></tr>`;
      })
      .join('');
  }

  function initForecastCharts(fc, sp, c) {
    if (!sp?.anchors) return;
    const capData = fc?.anchors ? buildSeries({ anchors: fc.anchors }, 'value') : null;
    const priceData = buildSeries(sp, 'price');
    fillForecastTable(priceData.months, capData?.series || priceData.series, priceData.series, sp, fc, c);

    let mode = sp ? 'price' : 'cap';
    const canvas = document.getElementById('forecastMainChart');
    if (!canvas) return;

    function renderChart() {
      const old = charts.find((c) => c.canvas === canvas);
      if (old) {
        old.destroy();
        charts = charts.filter((c) => c !== old);
      }
      const isPrice = mode === 'price';
      const forecast = isPrice ? sp : fc;
      const field = isPrice ? 'price' : 'value';
      const built = isPrice ? priceData : capData;
      const sc = forecast.scenarios;
      const unit = isPrice ? (sp.unit || pricePrefix(c).replace('$', '美元').replace('HK$', '港元')) : capUnit(c);

      charts.push(
        new Chart(canvas, {
          type: 'line',
          data: {
            labels: built.months,
            datasets: ['bull', 'base', 'bear', 'consensus'].map((k) => ({
              label: sc[k].label,
              data: built.series[k].map((p) => p[field]),
              borderColor: sc[k].color,
              borderWidth: k === 'consensus' ? 2.5 : 1.5,
              borderDash: k === 'consensus' ? [] : [4, 3],
              tension: 0.35,
              pointRadius: 0,
              pointHoverRadius: 4
            }))
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
            scales: {
              y: { ticks: { font: { size: 10 } } },
              x: { ticks: { maxTicksLimit: 10, font: { size: 9 } } }
            }
          }
        })
      );
    }

    document.querySelectorAll('.chart-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.chart-tab').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        mode = tab.dataset.chart;
        renderChart();
      });
    });
    renderChart();
  }

  function initAppendixCharts(c) {
    const color = c.color;
    const annuals = [...(c.annuals || [])].reverse();
    const labels = annuals.map((a) => a.label);
    const revCtx = document.getElementById('revChart');
    if (revCtx) {
      charts.push(
        new Chart(revCtx, {
          type: 'bar',
          data: { labels, datasets: [{ label: '营收', data: annuals.map((a) => a.revenue), backgroundColor: color + '99' }] },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        })
      );
    }
    const profitCtx = document.getElementById('profitChart');
    if (profitCtx) {
      charts.push(
        new Chart(profitCtx, {
          type: 'line',
          data: { labels, datasets: [{ label: '净利', data: annuals.map((a) => a.netProfit), borderColor: color, tension: 0.3 }] },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        })
      );
    }

    const agents = data.agentFramework.agents || [];
    const agentCtx = document.getElementById('agentRadar');
    if (agentCtx && agents.length) {
      charts.push(
        new Chart(agentCtx, {
          type: 'radar',
          data: {
            labels: agents.map((a) => a.role.replace(/分析师|研究员|师/g, '')),
            datasets: [{ data: agents.map((a) => a.score), backgroundColor: color + '33', borderColor: color }]
          },
          options: { responsive: true, maintainAspectRatio: false, scales: { r: { min: 0, max: 100 } } }
        })
      );
    }
    const agentBarCtx = document.getElementById('agentBar');
    if (agentBarCtx && agents.length) {
      charts.push(
        new Chart(agentBarCtx, {
          type: 'bar',
          data: { labels: agents.map((a) => a.role.slice(0, 4)), datasets: [{ data: agents.map((a) => a.score), backgroundColor: color + '99' }] },
          options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
        })
      );
    }
  }

  async function main() {
    const app = document.getElementById('app');
    try {
      data = await loadData(companyId);
    } catch (e) {
      console.error(e);
      app.innerHTML =
        '<div class="section"><p class="hint" style="color:var(--neg)">报告加载失败（' +
        companyId +
        '）</p><p class="hint"><a href="index.html">返回公司列表</a></p></div>';
      return;
    }

    const c = data.company;
    const fw = data.agentFramework;
    const fc = data.marketCapForecast;
    const sp = data.stockPriceForecast;
    const benchmarks = data.segmentBenchmarks || [];
    const syn = fw?.synthesis || { stance: '中性', finalScore: 60, verdict: c.conclusion };
    const meta = data.meta || {};

    setTheme(c.color || '#ff6700');
    document.title = `${c.name} · 分析师研究报`;
    const navTitle = document.getElementById('navTitle');
    if (navTitle) navTitle.textContent = c.name;

    const price0 = parseFloat(String(c.market?.price || '25').replace(/[^\d.]/g, '')) || 25;

    app.innerHTML =
      renderProgressBar() +
      renderReportMeta(c, meta) +
      renderChiefBar(c, syn, sp, fc) +
      renderToc() +
      renderFinancialIntegrity(data.financialIntegrity) +
      renderOptimizationPlan(data.optimizationPlan) +
      renderNarrative(data.narrative) +
      renderSegments(benchmarks, c) +
      renderForecast(fc, sp, c) +
      renderAgents(fw) +
      renderAppendix(c, data.financialIntegrity);

    const disclaimer = document.getElementById('disclaimer');
    if (disclaimer) {
      disclaimer.textContent = `数据来源：公司 IR / 交易所公开披露 · 情景推演不构成投资建议 · ${meta.reportDate || '2026-06-23'}`;
    }

    bindPeerTips();
    bindAppendixDrill();
    if (window.KlineChart) {
      const mount = document.getElementById('klineMount');
      if (mount) KlineChart.mount(mount, { daily: KlineChart.generateDailyOHLC(price0, 380, 0.032) });
    }
    if (fc && sp) initForecastCharts(fc, sp, c);
    initAppendixCharts(c);
    if (window.GuandianReportUI) GuandianReportUI.init();
  }

  main();
})();
