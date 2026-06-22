/**
 * 小米 01810.HK — K 线交互（多周期聚合 + 研究情景 OHLC）
 */
(function (global) {
  'use strict';

  const SHARES_BN = 252; // 约 252 亿股，用于市值→股价换算

  function generateDailyOHLC(startPrice, days, volatility) {
    const out = [];
    let price = startPrice;
    const start = new Date('2025-01-02');
    for (let i = 0; i < days; i++) {
      const d = new Date(start);
      d.setDate(d.getDate() + i);
      if (d.getDay() === 0 || d.getDay() === 6) continue;
      const drift = (Math.sin(i / 18) * 0.004 - 0.0015) * price;
      const shock = (Math.random() - 0.48) * volatility * price;
      const open = price;
      const close = Math.max(8, open + drift + shock);
      const high = Math.max(open, close) * (1 + Math.random() * 0.018);
      const low = Math.min(open, close) * (1 - Math.random() * 0.018);
      price = close;
      out.push({
        t: d.toISOString().slice(0, 10),
        o: +open.toFixed(2),
        h: +high.toFixed(2),
        l: +low.toFixed(2),
        c: +close.toFixed(2),
        v: Math.round(40 + Math.random() * 120)
      });
    }
    return out;
  }

  function aggregate(bars, size) {
    const result = [];
    for (let i = 0; i < bars.length; i += size) {
      const chunk = bars.slice(i, i + size);
      if (!chunk.length) continue;
      result.push({
        t: chunk[0].t + (size > 1 ? '~' + chunk[chunk.length - 1].t.slice(5) : ''),
        o: chunk[0].o,
        h: Math.max(...chunk.map((b) => b.h)),
        l: Math.min(...chunk.map((b) => b.l)),
        c: chunk[chunk.length - 1].c,
        v: chunk.reduce((s, b) => s + b.v, 0)
      });
    }
    return result;
  }

  function aggregateMonthly(bars) {
    const map = new Map();
    bars.forEach((b) => {
      const key = b.t.slice(0, 7);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(b);
    });
    return [...map.entries()].map(([k, chunk]) => ({
      t: k,
      o: chunk[0].o,
      h: Math.max(...chunk.map((x) => x.h)),
      l: Math.min(...chunk.map((x) => x.l)),
      c: chunk[chunk.length - 1].c,
      v: chunk.reduce((s, x) => s + x.v, 0)
    }));
  }

  function aggregateYearly(bars) {
    const map = new Map();
    bars.forEach((b) => {
      const key = b.t.slice(0, 4);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(b);
    });
    return [...map.entries()].map(([k, chunk]) => ({
      t: k,
      o: chunk[0].o,
      h: Math.max(...chunk.map((x) => x.h)),
      l: Math.min(...chunk.map((x) => x.l)),
      c: chunk[chunk.length - 1].c,
      v: chunk.reduce((s, x) => s + x.v, 0)
    }));
  }

  const TIMEFRAMES = {
    '5d': { label: '5日K', fn: (b) => aggregate(b, 5) },
    '7d': { label: '7日K', fn: (b) => aggregate(b, 7) },
    day: { label: '日K', fn: (b) => b.slice(-120) },
    week: { label: '周K', fn: (b) => aggregate(b, 5) },
    month: { label: '月K', fn: (b) => aggregateMonthly(b) },
    year: { label: '年K', fn: (b) => aggregateYearly(b) }
  };

  function draw(canvas, bars, opts) {
    if (!canvas || !bars.length) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const pad = { l: 48, r: 12, t: 16, b: 28 };
    const plotW = w - pad.l - pad.r;
    const plotH = h - pad.t - pad.b;
    const lows = bars.map((b) => b.l);
    const highs = bars.map((b) => b.h);
    const minP = Math.min(...lows) * 0.98;
    const maxP = Math.max(...highs) * 1.02;
    const yScale = (p) => pad.t + plotH - ((p - minP) / (maxP - minP)) * plotH;
    const n = bars.length;
    const gap = Math.max(2, plotW / n * 0.25);
    const bw = Math.max(3, (plotW - gap * (n + 1)) / n);

    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = pad.t + (plotH * i) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(w - pad.r, y);
      ctx.stroke();
      const val = maxP - ((maxP - minP) * i) / 4;
      ctx.fillStyle = '#9ca3af';
      ctx.font = '10px system-ui';
      ctx.textAlign = 'right';
      ctx.fillText('HK$' + val.toFixed(1), pad.l - 4, y + 3);
    }

    bars.forEach((b, i) => {
      const x = pad.l + gap + i * (bw + gap) + bw / 2;
      const up = b.c >= b.o;
      const color = up ? '#059669' : '#dc2626';
      const bodyTop = yScale(Math.max(b.o, b.c));
      const bodyBot = yScale(Math.min(b.o, b.c));
      const bodyH = Math.max(1, bodyBot - bodyTop);

      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(x, yScale(b.h));
      ctx.lineTo(x, yScale(b.l));
      ctx.stroke();
      ctx.fillRect(x - bw / 2, bodyTop, bw, bodyH);
    });

    ctx.fillStyle = '#6b7280';
    ctx.font = '11px system-ui';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(n / 8));
    bars.forEach((b, i) => {
      if (i % step !== 0 && i !== n - 1) return;
      const x = pad.l + gap + i * (bw + gap) + bw / 2;
      ctx.fillText(b.t.length > 7 ? b.t.slice(2, 7) : b.t.slice(2), x, h - 8);
    });

    if (opts && opts.tooltip) {
      canvas._klineBars = bars;
      canvas._klineGeom = { pad, bw, gap, yScale, minP, maxP, plotW, plotH };
    }
  }

  function bindTooltip(canvas, tipEl) {
    if (!canvas || !tipEl) return;
    canvas.addEventListener('mousemove', (e) => {
      const bars = canvas._klineBars;
      const g = canvas._klineGeom;
      if (!bars || !g) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      let idx = Math.floor((mx - g.pad.l - g.gap) / (g.bw + g.gap));
      idx = Math.max(0, Math.min(bars.length - 1, idx));
      const b = bars[idx];
      tipEl.hidden = false;
      tipEl.innerHTML =
        `<strong>${b.t}</strong> 开${b.o} 高${b.h} 低${b.l} 收<strong>${b.c}</strong> · 量${b.v}M`;
      tipEl.style.left = e.clientX - rect.left + 12 + 'px';
      tipEl.style.top = e.clientY - rect.top - 8 + 'px';
    });
    canvas.addEventListener('mouseleave', () => {
      tipEl.hidden = true;
    });
  }

  function mount(container, options) {
    const daily = options.daily || generateDailyOHLC(25, 380, 0.035);
    let currentTf = 'month';
    const tip = document.createElement('div');
    tip.className = 'kline-tip';
    tip.hidden = true;

    const tabs = Object.keys(TIMEFRAMES)
      .map(
        (k) =>
          `<button type="button" class="tf-tab ${k === currentTf ? 'active' : ''}" data-tf="${k}">${TIMEFRAMES[k].label}</button>`
      )
      .join('');

    container.innerHTML = `
      <div class="kline-head">
        <span class="kline-head__title">01810.HK 历史 K 线（研究回放）</span>
        <div class="tf-tabs">${tabs}</div>
      </div>
      <div class="kline-wrap">
        <canvas id="klineCanvas" height="280"></canvas>
        <div class="kline-tip" hidden></div>
      </div>
      <p class="hint kline-hint">切换 5日/7日/日/周/月/年 K；悬停查看 OHLC。下方折线为<strong>未来情景股价</strong>。</p>`;

    const canvas = container.querySelector('#klineCanvas');
    const tipEl = container.querySelector('.kline-tip');

    function renderTf(tf) {
      currentTf = tf;
      const bars = TIMEFRAMES[tf].fn(daily);
      draw(canvas, bars, { tooltip: true });
      container.querySelectorAll('.tf-tab').forEach((t) => t.classList.toggle('active', t.dataset.tf === tf));
    }

    container.querySelectorAll('.tf-tab').forEach((tab) => {
      tab.addEventListener('click', () => renderTf(tab.dataset.tf));
    });
    bindTooltip(canvas, tipEl);
    renderTf(currentTf);

    window.addEventListener(
      'resize',
      () => renderTf(currentTf)
    );
  }

  global.KlineChart = { mount, generateDailyOHLC, SHARES_BN };
})(window);
