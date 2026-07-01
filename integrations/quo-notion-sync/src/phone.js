// Phone matching is the join key between Quo and Notion, so normalization has to
// be forgiving: Notion stores things like "(612) 352-7343", Quo may send
// "+16123527343". We reduce both to the last 10 digits and compare those.

export function digitsOnly(value) {
  return (value || '').replace(/\D/g, '');
}

/**
 * Return the last 10 digits (US national number) as the canonical match key.
 * Handles a leading country code (e.g. 1 for US) and formatting noise.
 */
export function matchKey(value, defaultCountryCode = '1') {
  let d = digitsOnly(value);
  if (!d) return '';
  // Drop a leading country code if the number is longer than 10 digits.
  if (d.length > 10 && d.startsWith(defaultCountryCode)) {
    d = d.slice(defaultCountryCode.length);
  }
  return d.slice(-10);
}

export function samePhone(a, b, defaultCountryCode = '1') {
  const ka = matchKey(a, defaultCountryCode);
  const kb = matchKey(b, defaultCountryCode);
  return ka.length === 10 && ka === kb;
}
