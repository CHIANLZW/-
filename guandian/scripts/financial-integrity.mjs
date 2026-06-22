/**
 * 财报真实性核查：管理层叙事 vs 剔除干扰项后的核心指标
 * 方法论：财务尽调盈利核查 + OCF 含金量 + 非经/公允价值剔除 + 研发资本化排查
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const integrityDir = path.join(__dirname, '..', 'data', 'financial-integrity');

export function buildFinancialIntegrity(c) {
  const customPath = path.join(integrityDir, `${c.id}.json`);
  if (fs.existsSync(customPath)) {
    return JSON.parse(fs.readFileSync(customPath, 'utf8'));
  }
  return buildGenericIntegrity(c);
}

function buildGenericIntegrity(c) {
  const a0 = c.annuals?.[0];
  const a1 = c.annuals?.[1];
  const unit = c.unit || '亿元';
  const adj = a0?.adjNetProfit ?? a0?.nonGaapNet;
  const net = a0?.netProfit;
  const gap = adj && net ? +(adj - net).toFixed(1) : null;

  const comparisons = [];
  if (a0?.yoyRev != null) {
    comparisons.push({
      metric: '营收同比',
      management: `${a0.yoyRev >= 0 ? '+' : ''}${a0.yoyRev}%`,
      stripped: '以法定披露为准；需核对分部结构是否拉动 headline',
      flag: 'ok',
      note: a0.label
    });
  }
  if (gap != null && Math.abs(gap) > 5) {
    comparisons.push({
      metric: '净利润口径差',
      management: adj ? `经调/Non-GAAP ${adj}${unit}` : '—',
      stripped: `归母 ${net}${unit}；差额 ${gap}${unit} 需查调节表`,
      flag: 'watch',
      note: '扣非/经调不等于「无一次性」'
    });
  }
  if (a0?.ocf != null && adj) {
    const ratio = +(a0.ocf / adj).toFixed(2);
    comparisons.push({
      metric: 'OCF / 经调净利',
      management: '现金流健康',
      stripped: `${a0.ocf}${unit} / ${adj}${unit} ≈ ${ratio}`,
      flag: ratio < 0.9 ? 'warn' : 'ok',
      note: a0.ocfYoy != null ? `OCF 同比 ${a0.ocfYoy}%` : ''
    });
  }
  if (a0?.fairValueGain) {
    comparisons.push({
      metric: '公允价值变动',
      management: '投资收益',
      stripped: `约 ${a0.fairValueGain}${unit}，建议剔除看核心经营`,
      flag: 'warn',
      note: '利润表非主营波动项'
    });
  }
  if (c.quarterly?.yoyRev != null && a0?.yoyRev != null) {
    const diverge = (c.quarterly.yoyRev > 0) !== (a0.yoyRev > 0) || Math.abs(c.quarterly.yoyRev - a0.yoyRev) > 15;
    comparisons.push({
      metric: '最新季报 vs 全年',
      management: c.quarterly.period,
      stripped: `季报营收同比 ${c.quarterly.yoyRev}% vs 全年 ${a0.yoyRev}%`,
      flag: diverge ? 'watch' : 'ok',
      note: '增速换挡信号'
    });
  }

  const rows = [];
  if (a0) {
    rows.push({ line: '营收', reported: a0.revenue, core: a0.revenue, unit, mgmt: true, coreOnly: true, note: `同比 ${a0.yoyRev ?? '—'}%` });
    if (net) rows.push({ line: '归母净利润', reported: net, core: null, unit, mgmt: false, coreOnly: false, note: '' });
    if (adj) rows.push({ line: '经调/Non-GAAP 净利', reported: adj, core: null, unit, mgmt: true, coreOnly: false, note: '' });
    if (a0.rd) rows.push({ line: '研发费用', reported: a0.rd, core: a0.rd, unit, mgmt: true, coreOnly: true, note: `占收 ${a0.rdPct ?? '—'}%` });
    if (a0.ocf) rows.push({ line: '经营现金流', reported: a0.ocf, core: a0.ocf, unit, mgmt: false, coreOnly: true, note: '' });
  }

  return {
    id: c.id,
    title: '财报真实性核查 · 管理层叙事 vs 剔除干扰后',
    methodology:
      '自动生成核查（待该公司手工深度模板）。框架：非经剔除、OCF 匹配、季报勾稽、研发资本化排查。完整版参照小米模板。',
    riskLevel: comparisons.some((x) => x.flag === 'warn') ? 'moderate' : 'low',
    riskLabel: comparisons.some((x) => x.flag === 'warn') ? '存在叙事-现金流张力' : '初步未见重大口径异常',
    managementSays: c.conclusion || c.definition || '',
    afterStripping: `基于 ${a0?.label || '最新财年'} 披露：营收 ${a0?.revenue ?? '—'}${unit}。${gap ? `经调与归母差额 ${gap}${unit}。` : ''}建议补充 OCF、公允价值、分部明细后完成深度核查（见小米模板）。`,
    comparisons,
    adjustmentItems: [],
    drillDown: { periods: rows.length ? [{ id: 'latest', label: a0?.label || '最新', source: c.latestReport || 'IR', rows }] : [] },
    forecastCalibration: { asOf: '2026-06-23', note: '待该公司手工校准预测输入' }
  };
}
