/**
 * 工作室官网隐私脱敏规则（文字）
 */
const COMPANY_SUFFIXES = ['有限责任公司', '股份有限公司', '有限公司', '培训学校'];

const PHONE_PATTERNS = [
  /1[3-9]\d{9}/g,
  /1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}/g
];

const COMPANY_IN_TEXT =
  /[\u4e00-\u9fff（(][\u4e00-\u9fff]{1,28}(?:有限责任公司|股份有限公司|有限公司|培训学校)/g;

const PERSON_SUFFIX = /([\u4e00-\u9fff]{1,3})(老师|先生|女士|经理)/g;

function hashSeed(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

export function maskCompanyName(name) {
  if (!name || typeof name !== 'string') return name;
  let body = name.trim();
  let suffix = '';
  for (const s of COMPANY_SUFFIXES) {
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
  const h = hashSeed(name);
  let i1 = 1 + (h % (chars.length - 1));
  let i2 = 1 + ((h >>> 8) % (chars.length - 1));
  if (i1 === i2) i2 = i1 < chars.length - 1 ? i1 + 1 : i1 - 1;
  chars[i1] = '*';
  chars[i2] = '*';
  return chars.join('') + suffix;
}

export function maskPersonToken(_match, prefix, suffix) {
  if (prefix.length === 1) return '*' + suffix;
  const chars = [...prefix];
  const idx = 1 + (hashSeed(prefix) % Math.max(1, chars.length - 1));
  chars[idx] = '*';
  return chars.join('') + suffix;
}

export function stripPhones(text) {
  if (!text || typeof text !== 'string') return text;
  let t = text;
  for (const re of PHONE_PATTERNS) t = t.replace(re, '');
  t = t.replace(/tel:\d+/gi, '');
  t = t.replace(/[、,，；;]\s*[、,，；;]+/g, '、');
  t = t.replace(/\s{2,}/g, ' ');
  return t.trim();
}

export function maskPersonsInText(text) {
  if (!text) return text;
  return text.replace(PERSON_SUFFIX, (full, prefix, suffix) => maskPersonToken(full, prefix, suffix));
}

export function maskCompaniesInText(text) {
  if (!text) return text;
  return text.replace(COMPANY_IN_TEXT, (m) => (m.includes('*') ? m : maskCompanyName(m)));
}

export function looksLikeCompany(s) {
  if (!s) return false;
  return COMPANY_SUFFIXES.some((x) => s.includes(x));
}

export function desensitizeString(value, key = '') {
  if (typeof value !== 'string') return value;
  let t = stripPhones(value);
  const keyLower = String(key).toLowerCase();

  if (keyLower === 'name' || keyLower === 'company') {
    if (!t.includes('*') && looksLikeCompany(t)) t = maskCompanyName(t);
    return t;
  }

  if (keyLower === 'title' || keyLower === 'source') {
    t = maskCompaniesInText(t);
    t = maskPersonsInText(t);
    return t;
  }

  if (
    keyLower === 'summary' ||
    keyLower === 'identified_copy' ||
    keyLower === 'proposed_name' ||
    keyLower === 'original'
  ) {
    t = maskCompaniesInText(t);
    t = maskPersonsInText(t);
    return stripPhones(t);
  }

  t = maskPersonsInText(t);
  t = maskCompaniesInText(t);
  t = t.replace(/[A-Za-z]:\\Users\\[^\\]+\\[^\n"']+/g, '[本地路径已移除]');
  return t;
}
