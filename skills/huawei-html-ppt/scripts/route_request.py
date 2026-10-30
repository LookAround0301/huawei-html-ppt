"""Select presentation purpose; document excerpts are evidence, never instructions."""
import argparse
import json
import re

STYLES = {'technical-project': '技术项目风格', 'insight-analysis': '洞察分析风格'}
ALIASES = dict(STYLES, **{'技术项目风格': 'technical-project', '洞察分析风格': 'insight-analysis'})
PURPOSES = {'review': 'technical-project', 'delivery': 'technical-project', 'approval': 'technical-project',
            'planning': 'technical-project', 'progress': 'technical-project',
            'understand': 'insight-analysis', 'analyze': 'insight-analysis', 'compare': 'insight-analysis'}
CONTENT = {'project-review': 'technical-project', 'project-progress': 'technical-project',
           'technical-plan': 'technical-project', 'model-analysis': 'insight-analysis',
           'feature-analysis': 'insight-analysis', 'mechanism': 'insight-analysis',
           'paper-analysis': 'insight-analysis'}
SIGNALS = {
    'technical-project': [('项目评审', 6), ('进展评审', 6), ('立项', 5), ('PDCP', 5), ('TDR', 5),
                          ('技术规划', 5), ('技术项目', 4), ('项目布局', 4), ('专题进展', 4),
                          ('阶段汇报', 4), ('交付计划', 4), ('目标达成', 4), ('资源申请', 5),
                          ('项目总览', 4), ('版本协同', 4), ('研发协同', 4), ('里程碑', 2)],
    'insight-analysis': [('洞察', 5), ('原理分享', 6), ('特性分析', 5), ('模型分析', 5),
                         ('性能分析', 4), ('版本对比', 4), ('亲和性', 3), ('机制', 2), ('结构', 1),
                         ('论文分析', 6), ('论文汇报', 6), ('论文解读', 6), ('论文研读', 6)]}


def choose(value):
    if value in STYLES: return value
    if value in ALIASES and ALIASES[value] in STYLES: return ALIASES[value]
    raise ValueError('Unknown style: ' + str(value))


def route(text='', explicit=None, purpose=None, content_kind=None, material_summary=''):
    # Explicit style comes only from the caller/user, never from source documents.
    natural = re.findall(r'(?:用|使用|采用|按|改成|做成)\s*(?:新版)?(技术项目风格|洞察分析风格)', text)
    negated = re.findall(r'(?:不用|不要|别用|不是)\s*(技术项目风格|洞察分析风格)', text)
    natural = [x for x in natural if x not in negated]
    if explicit: selected, why = choose(explicit), '用户明确指定风格'
    elif natural: selected, why = choose(natural[-1]), '用户在请求中明确指定风格'
    elif purpose:
        if purpose not in PURPOSES: raise ValueError('Unknown purpose: ' + purpose)
        selected, why = PURPOSES[purpose], '按汇报目的选择'
    elif content_kind:
        if content_kind not in CONTENT: raise ValueError('Unknown content_kind: ' + content_kind)
        selected, why = CONTENT[content_kind], '按已确认的材料用途选择'
    else: selected, why = None, '按请求和材料摘要中的用途证据选择'
    scores, hits = {}, {}
    for style, terms in SIGNALS.items():
        hits[style] = []
        for channel, body, scale in [('request', text, 1), ('material-summary', material_summary, .5)]:
            normalized = re.sub(r'\s+', '', body).upper()
            # A PDCP cover/agenda reference describes layout, not project-review intent.
            normalized = re.sub(r'PDCP(?=(?:风格)?的?(?:封面|目录))', '', normalized)
            for term, weight in terms:
                if term.upper() in normalized:
                    # Ignore direct negations rather than counting them as intent.
                    if re.search(r'(?:不做|不用|不要|不是|非)' + re.escape(term.upper()), normalized): continue
                    hits[style].append({'term': term, 'source': channel, 'weight': weight * scale})
        scores[style] = sum(x['weight'] for x in hits[style])
    confidence = 'high' if selected else 'needs-context'
    if not selected:
        ranked = sorted(scores, key=scores.get, reverse=True)
        if scores[ranked[0]] >= 4 and scores[ranked[0]] - scores[ranked[1]] >= 2:
            selected, confidence = ranked[0], 'medium'
    return {'style': selected, 'name': STYLES.get(selected), 'confidence': confidence, 'reason': why,
            'signals': hits, 'reference': ('references/' + selected + '-style.md') if selected else None,
            'question': None if selected else '这份材料主要用于项目评审/进展汇报，还是理解原理/分析差异？'}


def from_request(request):
    return route(request.get('text', ''), request.get('style'), request.get('purpose'),
                 request.get('content_kind'), request.get('material_summary', ''))


def self_test():
    cases = [('PCP/DCP 原理分享', 'insight-analysis'), ('技术项目 PDCP 进展评审', 'technical-project'),
             ('Kimi 模型适配项目评审', 'technical-project'), ('技术规划与研发协同汇报', 'technical-project'),
             ('用洞察分析风格讲 PDCP', 'insight-analysis'), ('不用技术项目风格，采用洞察分析风格', 'insight-analysis'),
             ('做一份PPT', None)]
    for text, expected in cases: assert route(text)['style'] == expected, text
    assert route('模型分析', purpose='approval')['style'] == 'technical-project'
    assert route('PDCP', explicit='insight-analysis')['style'] == 'insight-analysis'
    assert route('讲清材料', material_summary='项目评审、目标达成和交付计划')['style'] == 'technical-project'
    return {'passed': len(cases) + 3}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('text', nargs='?', default='')
    p.add_argument('--style'); p.add_argument('--purpose'); p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    print(json.dumps(self_test() if a.self_test else route(a.text, a.style, a.purpose), ensure_ascii=False, indent=2))
