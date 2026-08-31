from pathlib import Path

p = Path('category-hubs/outing/content.html')
s = p.read_text(encoding='utf-8')

replacements = {
    '<strong>ちょっと遠くへ</strong>': '<strong>旅に出る</strong>',
    '山口・鳥取・大分・淡路島。車で行くから面白い旅。': '山口・鳥取・大分・淡路島。実際に出かけた旅をまとめました。',
    '<h2>ちょっと遠くへ</h2>': '<h2>旅に出る</h2>',
    'せっかくの休みなら、朝から走る。広島を飛び出して遊んだ旅を集めました。': 'せっかくの休みなら、いつもより少し遠くへ。山口・鳥取・大分・淡路島など、実際に出かけた旅を集めました。',
}

for old, new in replacements.items():
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'EXPECTED_ONE_MATCH count={count} text={old}')
    s = s.replace(old, new, 1)

if 'ちょっと遠くへ' in s:
    raise SystemExit('OLD_WORDING_REMAINS')
if s.count('旅に出る') < 2:
    raise SystemExit('NEW_WORDING_MISSING')

p.write_text(s, encoding='utf-8')
print('OUTING_TRAVEL_WORDING_PATCHED')
