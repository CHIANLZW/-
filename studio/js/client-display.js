/** 经典版在 /classic/ 或 /studio/classic/ 子目录，静态资源需回退 */
window.assetUrl = function assetUrl(path) {
  const clean = String(path).replace(/^\//, '');
  const pathname = location.pathname.replace(/\\/g, '/');
  if (/\/classic(?:\/|$)/i.test(pathname)) {
    return pathname.includes('/studio/') ? '../../' + clean : '../' + clean;
  }
  return clean;
};

/** 客户名称：别名归一 + 敏感信息打码 */
window.ClientDisplay = (() => {
  let config = { aliases: {}, sensitive: [], sensitiveMask: '***' };

  async function load() {
    try {
      const res = await fetch(assetUrl('assets/data/client-display.json'));
      config = await res.json();
    } catch {
      /* 使用默认空配置 */
    }
  }

  function normalize(raw) {
    if (!raw) return '';
    return String(raw)
      .replace(/^[\d._\-]+/, '')
      .replace(/\s*运营合格证$/, '')
      .replace(/\s*资料$/, '')
      .trim();
  }

  function resolveAlias(name) {
    const n = normalize(name);
    if (config.aliases[n]) return config.aliases[n];
    return n;
  }

  function isSensitive(name) {
    const resolved = resolveAlias(name);
    return (config.sensitive || []).some(
      (s) => resolved === s || resolved.includes('苍凌信息技术')
    );
  }

  function maskCompanyName(name) {
    const suffixes = ['有限责任公司', '股份有限公司', '有限公司', '培训学校'];
    let body = name.trim();
    let suffix = '';
    for (const s of suffixes) {
      if (body.endsWith(s)) {
        suffix = s;
        body = body.slice(0, -s.length);
        break;
      }
    }
    const chars = [...body];
    if (chars.length <= 1) return name;
    if (chars.length === 2) {
      chars[1] = '*';
      return chars.join('') + suffix;
    }
    let h = 0;
    for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
    let i1 = 1 + (h % (chars.length - 1));
    let i2 = 1 + ((h >>> 8) % (chars.length - 1));
    if (i1 === i2) i2 = i1 < chars.length - 1 ? i1 + 1 : i1 - 1;
    chars[i1] = '*';
    chars[i2] = '*';
    return chars.join('') + suffix;
  }

  function format(name) {
    const resolved = resolveAlias(name);
    if (!resolved) return '其他案例';
    if (isSensitive(resolved)) return config.sensitiveMask || '***';
    if (/有限公司|有限责任公司|培训学校/.test(resolved)) return maskCompanyName(resolved);
    return resolved;
  }

  return { load, normalize, resolveAlias, isSensitive, format };
})();
