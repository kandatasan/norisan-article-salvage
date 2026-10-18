/* Standalone pure search helpers: no cross-table prefecture/fish inference. */
(function (host) {
  "use strict";
  const normalize = value => String(value == null ? "" : value).normalize("NFKC").toLocaleLowerCase("ja-JP").replace(/\s+/g, "").trim();
  const validString = s => String(s || "").trim();
  function paginate(items, pageSize, offset) {
    const limit = Math.max(1, Math.min(100, Number(pageSize) || 25));
    const start = Math.max(0, Number(offset) || 0);
    return {total: items.length, rows: items.slice(start, start + limit), offset: start, limit};
  }
  function searchCodes(dataset, query, limit, offset) {
    const q=normalize(query);
    if (!q) return paginate([], limit, offset);
    const found = dataset.riverCodes.filter(([code, name, basin, watercode]) =>
      [code,name,basin,watercode].some(v => normalize(v).includes(q)));
    // Every match is an official CODE LABEL, never a prefecture/location match.
    return paginate(found,limit,offset);
  }
  function searchLocal(dataset, query, prefecture, kind, limit, offset) {
    const q=normalize(query), p=validString(prefecture), k=validString(kind);
    if (!q && !p && !k) return paginate([],limit,offset);
    const found=dataset.localEvidence.filter(([pref,name,type,basin,area])=>
      (!p || p===pref) &&
      (!k || k===type) &&
      (!q || [name,basin,area].some(v=>normalize(v).includes(q))));
    return paginate(found,limit,offset);
  }
  function searchFish(dataset, query, watershed, region, limit, offset) {
    const q=normalize(query), w=normalize(watershed), r=validString(region);
    if (!q && !w && !r) return paginate([],limit,offset);
    const found=dataset.fishCensus.filter(([regionCode,basin,year,fish])=>
      (!r || r===regionCode) &&
      (!w || normalize(basin).includes(w)) &&
      (!q || normalize(fish).includes(q)));
    return paginate(found,limit,offset);
  }
  function isOfficialSource(url) {
    try {
      const link=new URL(url);
      return link.protocol==="https:" && /(^|\.)[a-z0-9.-]+\.jp$/i.test(link.hostname);
    } catch (_) {return false;}
  }
  host.RiverBetaCore={normalize,searchCodes,searchLocal,searchFish,isOfficialSource};
})(typeof window==="undefined" ? globalThis : window);
