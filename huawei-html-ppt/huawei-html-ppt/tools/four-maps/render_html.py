# -*- coding: utf-8 -*-
"""
四张地图 HTML 渲染器 v2: spec.yaml -> <组名>四张地图.html
视觉保真: 直接内嵌原 PPT 的封面横带/内容页背景/花瓣Logo (assets/ 下三张图),
字号按模板实测换算(24pt页标题/10.5pt正文/10pt表格), 1280x720 画布 = 128px/in。
"""
import sys, io, os, re, argparse, base64, html as H
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import yaml

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

COMPETENCY = {'高': '92D050', '胜任度高': '92D050',
              '胜任': 'FFFF00',
              '基本': 'FFC000', '基本胜任': 'FFC000',
              '不胜任': 'FF0000', '暂不胜任': 'FF0000'}
MAPS = ('业务地图', '组织地图', '人才地图', '氛围地图')


def b64(name):
    with open(os.path.join(ASSETS, name), 'rb') as f:
        return 'data:image/%s;base64,%s' % (
            'jpeg' if name.endswith(('jpg', 'jpeg')) else 'png',
            base64.b64encode(f.read()).decode())


def esc(t):
    return H.escape(str(t if t is not None else '')).replace('\n', '<br>')


CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#7f7f7f; font-family:'Microsoft YaHei','PingFang SC',sans-serif; }
.slide { width:1280px; height:720px; background:#fff; margin:20px auto; position:relative;
         overflow:hidden; box-shadow:0 2px 14px rgba(0,0,0,.35); page-break-after:always; }
@media print {
  body { background:#fff; }
  .slide { margin:0; box-shadow:none; }
  @page { size:1280px 720px; margin:0; }
}
.bg { position:absolute; inset:0; width:100%; height:100%; z-index:0; }
.footer-strip { position:absolute; left:0; bottom:0; width:100%; height:67px; z-index:1; }
/* 页眉 */
.page-title { position:absolute; left:24px; top:12px; font-size:42px; font-weight:700;
              color:#C00000; letter-spacing:1px; z-index:3; }
.nav { position:absolute; right:18px; top:14px; display:flex; z-index:3; }
.nav span { font-size:19px; color:#1a1a1a; padding:2px 14px; }
.nav span.cur { background:#C00000; color:#fff; font-weight:700; }
/* ---- 封面/结束页 ---- */
.cv-t1 { position:absolute; left:0; width:73%; top:198px; text-align:center; color:#fff;
         font-size:55px; font-weight:700; letter-spacing:3px; z-index:2; }
.cv-t2 { position:absolute; left:0; width:73%; top:300px; text-align:center; color:#fff;
         font-size:55px; font-weight:700; letter-spacing:3px; z-index:2; }
.cv-pl { position:absolute; left:0; width:73%; top:437px; text-align:center; color:#fff;
         font-size:27px; z-index:2; }
.cv-logo { position:absolute; right:82px; bottom:48px; width:110px; z-index:2; }
.thanks { position:absolute; left:96px; top:170px; font-size:72px; color:#3f3f3f; z-index:2; }
/* ---- 业务地图 ---- */
.biz { position:absolute; left:26px; right:80px; top:78px; bottom:78px; background:#F2F2F2;
       padding:10px 30px; z-index:2; display:flex; flex-direction:column;
       justify-content:space-evenly; }
.biz h3 { color:#C00000; font-size:20px; font-weight:700; margin:0; line-height:1.35; }
.biz p { font-size:16px; color:#1a1a1a; line-height:1.45; margin:5px 0 0; }
/* ---- 组织地图 ---- */
.legend { position:absolute; right:10px; top:42px; z-index:4; }
.legend div { width:106px; height:23px; font-size:14px; text-align:center; line-height:21px;
              border:1px solid #7f7f7f; color:#111; }
.org-wrap { position:absolute; left:18px; top:0; bottom:78px; z-index:2;
            display:flex; flex-direction:column; }
.org-body { display:flex; gap:21px; flex:1 1 auto; }
.org-col { display:flex; flex-direction:column; gap:12px; min-width:0; }
.org-col.l { width:517px; padding-top:68px; }
.org-col.r { width:681px; padding-top:68px; }
/* col:2 底部居中放置(整页横贯带, 文档流内 margin-top:auto 贴底) */
.org-bottom { display:flex; gap:21px; }
.org-bottom .ftable { flex:0 0 auto; }
.ftable { border:2px solid #000; background:#fff; display:flex; flex-direction:column; }
.org-col .ftable { flex:1 1 auto; }
.ftable .t { background:#C00000; color:#fff; font-weight:700; font-size:17px;
             text-align:center; padding:2px 8px; flex:0 0 auto; }
.ftable table { width:100%; border-collapse:collapse; table-layout:fixed; flex:1 1 auto; }
.ftable th { background:#D9D9D9; font-weight:700; font-size:15px; padding:2px 5px;
             border:1px solid #000; }
.ftable td { border:1px solid #000; font-size:15px; padding:2px 5px; height:22px;
             word-wrap:break-word; vertical-align:middle; line-height:1.3; }
.ftable td.subcell { background:#f7f7f7; }
.ftable td.name { text-align:center; background:#e8e8e8; }
.ftable tr.st td { background:#fbe9e7; font-weight:700; height:20px; }
.ftable tr.partner td { font-size:13px; height:20px; color:#1a1a1a; }
/* 密度自适应: 组织地图整页估高超容量时收紧行距与字号(版式/配色不变) */
.org-wrap.dense .ftable .t { font-size:14px; padding:1px 6px; }
.org-wrap.dense .ftable th { font-size:12px; padding:1px 3px; }
.org-wrap.dense .ftable td { font-size:12.5px; height:15px; padding:0 3px;
                             line-height:1.12; }
.org-wrap.dense .ftable tr.partner td { font-size:11px; height:14px; }
/* ---- 人才地图 ---- */
.tal { position:absolute; left:36px; right:36px; top:74px; z-index:2; }
.tal-label { font-size:19px; font-weight:700; margin:6px 0 3px; }
.tal table { width:100%; border-collapse:collapse; table-layout:fixed; margin-bottom:4px;
             border:2px solid #000; }
.tal th { font-size:16px; font-weight:700; padding:3px 8px; border:1px solid #000; }
.tal th.red { background:#C00000; color:#fff; }
.tal th.gray { background:#D9D9D9; color:#1a1a1a; }
.tal td { border:1px solid #000; font-size:15px; padding:3px 8px; word-wrap:break-word;
          vertical-align:middle; line-height:1.35; }
.tal td.role { color:#C00000; font-weight:700; text-align:center; }
.tal .out { font-size:19px; font-weight:700; margin-top:4px; }
.tal .pend { font-size:16px; margin-top:1px; }
/* ---- 氛围地图 ---- */
.atm-box { position:absolute; left:40px; right:40px; top:96px; height:478px;
           border:1px solid #404040; padding:16px 34px; z-index:2; }
.atm .kt { color:#C00000; font-size:23px; font-weight:700; margin-bottom:8px; }
.atm .kt::before { content:'● '; font-size:19px; }
.atm .sec { font-size:20px; font-weight:700; margin:12px 0 2px 1.2em; }
.atm .sec::before { content:'❒ '; }
.atm .stmt { font-size:20px; font-weight:700; margin-left:1.2em; }
.atm .blk { font-size:20px; font-weight:700; margin:10px 0 0 1.2em; }
.atm .blk::before { content:'❒ '; }
.atm p.item { font-size:19px; margin-left:3.2em; line-height:1.55; }
.atm p.item::before { content:'· '; }
/* ---- 组织结构图(第7页) ---- */
.oc-group { position:absolute; left:50%; transform:translateX(-50%); top:140px;
            border:2px solid #000; background:#fff; font-size:20px; font-weight:700;
            padding:6px 26px; z-index:3; }
.oc-note { position:absolute; right:150px; top:64px; width:330px; border:2px solid #000;
           background:#fff; font-size:14.5px; line-height:1.55; padding:8px 12px; z-index:3; }
.oc-grid { position:absolute; left:40px; right:40px; top:230px; z-index:2;
           display:grid; grid-template-columns:repeat(4, 1fr); gap:14px 18px; align-items:start; }
.ctable { border:1.5px solid #000; background:#fff; font-size:13px; }
.ctable .t { background:#FFC000; color:#111; font-weight:700; font-size:15px;
             text-align:center; padding:2px 6px; }
.ctable table { width:100%; border-collapse:collapse; table-layout:fixed; }
.ctable th { background:#D9D9D9; font-weight:700; font-size:12.5px; padding:1px 3px;
             border:1px solid #7f7f7f; }
.ctable td { border:1px solid #7f7f7f; font-size:12.5px; padding:1px 3px; height:24px;
             word-wrap:break-word; vertical-align:middle; }
.ctable td.name { text-align:center; background:#e8e8e8; }
.ctable tr.partner td { font-size:11.5px; height:auto; color:#1a1a1a; line-height:1.4; }
/* 密度自适应: 组织结构图四表估高超页容时收紧 */
.oc-grid.dense .ctable .t { font-size:12px; padding:1px 3px; }
.oc-grid.dense .ctable th { font-size:9.5px; padding:0 1px; }
.oc-grid.dense .ctable td { font-size:10px; height:13px; padding:0 1px;
                            line-height:1.15; }
.oc-grid.dense .ctable tr.partner td { font-size:9.5px; }
"""


def shell(body, title=None, cur=None, full_bg=None):
    """内容页: 白底 + 底部页脚条; full_bg 指定时作为整页背景(封面)"""
    nav = ''.join('<span class="%s">%s</span>' % ('cur' if m == cur else '', m) for m in MAPS)
    head = ('<div class="page-title">%s</div><div class="nav">%s</div>' % (esc(title), nav)
            if title else '')
    bg = '<img class="bg" src="%s">' % b64(full_bg) if full_bg else ''
    footer = '' if full_bg else '<img class="footer-strip" src="%s">' % b64('footer_strip.png')
    return '<div class="slide">%s%s%s%s</div>' % (bg, head, body, footer)


def s_cover(meta):
    body = ('<div class="cv-t1">%s</div>'
            '<div class="cv-t2">“四张地图”</div>'
            '<div class="cv-pl">PL：%s %s</div>'
            '<img class="cv-logo" src="%s">'
            % (esc(meta.get('group_name', '')), esc(meta.get('pl_name', '')),
               esc(meta.get('pl_id', '')), b64('cover_logo.png')))
    return shell(body, full_bg='bg_cover.png')


def s_end():
    return shell('<div class="thanks">Thank you.</div>')


def _prefix_w(prefix):
    """估算加粗前缀像素宽(CJK 16px, 半角 9px), 用于悬挂缩进"""
    return sum(16 if ord(c) > 0x2000 else 9 for c in prefix) + 2


def _hang_p(prefix, rest, extra_style=''):
    """悬挂缩进段落: 首行顶格(前缀加粗), 换行对齐到前缀后内容起点"""
    prefix = str(prefix)
    if not prefix.endswith('：'):
        prefix += '：'
    w = _prefix_w(prefix)
    return ('<p style="padding-left:%dpx;text-indent:-%dpx;%s"><b>%s</b>%s</p>'
            % (w, w, extra_style, esc(prefix), esc(rest)))


def s_business(spec):
    items = (spec.get('business_map') or {}).get('items') or []
    parts = []
    for it in items:
        parts.append('<h3>%s</h3>' % esc(it['header']))
        for sub in it.get('subs') or []:
            if isinstance(sub, dict):
                text = str(sub.get('text', ''))
                lead = sub.get('lead')
                if lead:
                    parts.append('<p><b>%s</b>%s</p>' % (esc(lead), esc(text)))
                    continue
                # 无显式 lead 时: "前缀：内容" 且前缀较短, 前缀自动加粗
                i = text.find('：')
                if 0 < i <= 14:
                    parts.append('<p><b>%s：</b>%s</p>' % (esc(text[:i]), esc(text[i + 1:])))
                else:
                    parts.append('<p>%s</p>' % esc(text))
            else:
                t = str(sub)
                i = t.find('：')
                if 0 < i <= 14:
                    parts.append('<p><b>%s：</b>%s</p>' % (esc(t[:i]), esc(t[i + 1:])))
                else:
                    parts.append('<p>%s</p>' % esc(t))
    if not parts:
        parts = ['<p>（待补充）</p>']
    return shell('<div class="biz">%s</div>' % ''.join(parts), '业务地图', '业务地图')


def _name_len(txt):
    """有效宽度: CJK 记 1, ASCII 记 0.55"""
    return sum(1.0 if ord(c) > 0x2E7F else 0.55 for c in str(txt or ''))


def _lines(txt, cpl):
    """按每行 cpl 个有效字符估行数"""
    return max(1, int(-(-_name_len(txt) // cpl)))


def _multi_name(f):
    """初稿常见"多人挤一格"(模板原版一格一人)——姓名列需自适应加宽"""
    sections = f.get('sections') or [{'members': f.get('members') or []}]
    return max((len(str(m.get('name', '')))
                for sec in sections for m in (sec.get('members') or [])), default=0) > 10


def _feature_table(f):
    landing = bool(f.get('landing'))
    sections = f.get('sections') or [{'members': f.get('members') or [],
                                      'partners': f.get('partners')}]
    all_members = [m for sec in sections for m in (sec.get('members') or [])]
    has_sub = any(m.get('sub') for m in all_members)
    has_grade = any(m.get('grade') for m in all_members)
    cols = (['特性', '子任务'] if has_sub else ['特性']) + ['角色', '姓名'] \
        + (['人岗/任职/年限'] if has_grade else []) + (['落地'] if landing else [])
    # 人岗/任职/年限全空时省略该列(数据填上后自动恢复); 子任务模式=特性 rowspan+子任务列
    if has_sub:
        pairs = [('特性', '23%'), ('子任务', '33%'), ('角色', '11%'), ('姓名', '33%'),
                 ('人岗/任职/年限', '25%'), ('落地', '21%')]
    elif _multi_name(f):
        pairs = [('特性', '29%'), ('角色', '11%'), ('姓名', '30%'),
                 ('人岗/任职/年限', '30%'), ('落地', '21%')]
    else:
        pairs = [('特性', '37%'), ('角色', '13%'), ('姓名', '20%'),
                 ('人岗/任职/年限', '30%'), ('落地', '21%')]
    if not has_grade:
        pairs = [p for p in pairs if p[0] != '人岗/任职/年限']
    if not landing:
        pairs = [p for p in pairs if p[0] != '落地']
    cols = [p[0] for p in pairs]
    widths = [p[1] for p in pairs]
    rows = []
    first = True
    for sec in sections:
        if sec.get('subtitle'):
            rows.append('<tr class="st"><td colspan="%d">%s</td></tr>'
                        % (len(cols), esc(sec['subtitle'])))
        if first:
            rows.append('<tr>%s</tr>' % ''.join('<th>%s</th>' % c for c in cols))
            first = False
        mems = sec.get('members') or []
        # 姓名/角色/职级/胜任度完全一致的连续行合并姓名格(待定占位不合并)
        nspans, skip = {}, set()

        def _nkey(m):
            return (m.get('name'), m.get('role'), m.get('grade'), m.get('competency'))
        i2 = 0
        while i2 < len(mems):
            j2 = i2 + 1
            nm = str(mems[i2].get('name', ''))
            if nm and nm not in ('（待定）', '(待定)'):
                while j2 < len(mems) and mems[j2].get('name') and \
                        _nkey(mems[j2]) == _nkey(mems[i2]):
                    j2 += 1
            if j2 - i2 > 1:
                nspans[i2] = j2 - i2
                skip.update(range(i2 + 1, j2))
            i2 = j2
        i = 0
        r = 0
        while i < len(mems):
            # 子任务模式下, 特性相同的连续行合并特性格
            j = i + 1
            if has_sub:
                while j < len(mems) and mems[j].get('feature', '') == mems[i].get('feature', ''):
                    j += 1
            grp = mems[i:j] if has_sub else [mems[i]]
            for k, m in enumerate(grp):
                name = esc(m.get('name', ''))
                comp = COMPETENCY.get(m.get('competency') or '')
                style = ' style="background:#%s"' % comp if comp else ''
                cells = []
                if k == 0:
                    cells.append('<td rowspan="%d">%s</td>' % (len(grp), esc(m.get('feature', '')))
                                 if len(grp) > 1 else '<td>%s</td>' % esc(m.get('feature', '')))
                if has_sub:
                    cells.append('<td class="subcell">%s</td>' % esc(m.get('sub', '')))
                cells.append('<td style="text-align:center">%s</td>' % esc(m.get('role', '')))
                if r in nspans:
                    cells.append('<td class="name" rowspan="%d"%s>%s</td>'
                                 % (nspans[r], style, name))
                elif r not in skip:
                    cells.append('<td class="name"%s>%s</td>' % (style, name))
                if has_grade:
                    cells.append('<td style="text-align:center">%s</td>'
                                 % esc(m.get('grade', '')))
                if landing:
                    cells.append('<td>%s</td>' % esc(m.get('landing', '')))
                rows.append('<tr>%s</tr>' % ''.join(cells))
                r += 1
            i = j
        if sec.get('partners') is not None:
            rows.append('<tr class="partner"><td colspan="%d">合作团队：%s</td></tr>'
                        % (len(cols), esc(sec['partners'])))
    if not any('partner' in r for r in rows):
        rows.append('<tr class="partner"><td colspan="%d">合作团队：%s</td></tr>'
                    % (len(cols), esc(f.get('partners', ''))))
    colgroup = ''.join('<col style="width:%s">' % w for w in widths)
    w = f.get('w')
    style = ' style="width:%dpx"' % int(w * 128) if w else ''
    return ('<div class="ftable"%s><div class="t">%s</div><table><colgroup>%s</colgroup>%s'
            '</table></div>' % (style, esc(f.get('title', '')), colgroup, ''.join(rows)))


def _est_height(f):
    """估算特性表渲染高度(px), 用于两列均衡(按较窄左列的最坏情况)"""
    h = 30 + 22   # 标题 + 表头
    sections = f.get('sections') or [{'members': f.get('members') or []}]
    multi = _multi_name(f)
    for sec in sections:
        if sec.get('subtitle'):
            h += 20
        for m in sec.get('members') or []:
            h += 23
            if m.get('sub'):
                # 子任务模式: 特性格 rowspan 合并只占一行, 每行按子任务文字计价
                h += 14 * (_lines(m.get('sub', ''), 12) - 1)
            else:
                # 特性/姓名换行都计价: 特性列宽 41%/30%, 姓名列单人 1 行、多人格 ~11 字/行
                h += 14 * (_lines(m.get('feature', ''), 11 if multi else 15) - 1)
            h += 19 * (_lines(m.get('name', ''), 11 if multi else 99) - 1)
        if sec.get('partners') is not None:
            h += 20 + (16 if _name_len(sec['partners']) > 24 else 0)
    if not any((s.get('partners') is not None) for s in sections):
        h += 20 + (16 if _name_len(f.get('partners', '')) > 24 else 0)
    return h


def s_org(spec):
    features = (spec.get('org_map') or {}).get('features') or []
    legend = ''.join('<div style="background:#%s%s">%s</div>' % (
        c, ';color:#fff' if c == 'FF0000' else '', esc(t))
        for c, t in [('92D050', '胜任度高'), ('FFFF00', '胜任'),
                     ('FFC000', '基本胜任'), ('FF0000', '暂不胜任')])
    tables = [_feature_table(f) for f in features]
    # 列分配: feature 显式 col(0/1/2) 优先, 2=底部居中; 未指定的按估算高度降序贪心
    cols = ([], [])
    bottoms = []
    totals = [0, 0]
    auto = []
    for f, t in zip(features, tables):
        c = f.get('col')
        if c in (2, 3):
            bottoms.append(t)
        elif c in (0, 1):
            cols[c].append(t)
            totals[c] += _est_height(f)
        else:
            auto.append((_est_height(f), t))
    for w, t in sorted(auto, key=lambda x: -x[0]):
        c = 0 if totals[0] <= totals[1] else 1
        cols[c].append(t)
        totals[c] += w
    # 密度自适应: 双列容量≈左568/右598px, 估高(23px行距口径)超容量时启用紧凑密度
    dense = ' dense' if max(totals + [0, 0]) > 430 else ''
    # 底部横带: 显式宽度 = 左列517 + 列距21 + 右列首表宽(可能w缩宽让位图例),
    # space-between 使首表对齐左列、末表右缘对齐右列首表右缘
    bw = ''
    band = ''
    if bottoms:
        first_r = next((f for f in features if f.get('col') == 1), None)
        rw = int(first_r['w'] * 128) if first_r and first_r.get('w') else 681
        bw = ' style="width:%dpx"' % (517 + 21 + rw)
        band = '<div class="org-bottom"%s>%s</div>' % (bw, ''.join(bottoms))
    body = ('<div class="legend">%s</div>'
            '<div class="org-wrap%s">'
            '<div class="org-body"><div class="org-col l">%s</div>'
            '<div class="org-col r">%s</div></div>'
            '%s</div>'
            % (legend, dense, ''.join(cols[0]), ''.join(cols[1]), band))
    return shell(body, '组织地图', '组织地图')


def _cell_html(v, role=False):
    """单元格: 支持 [red]前缀=红色加粗(如缺口预警)"""
    v = str(v if v is not None else '')
    cls = ' class="role"' if role else ''
    if v.startswith('[red]'):
        return '<td%s style="color:#C00000;font-weight:700">%s</td>' % (cls, esc(v[5:]))
    return '<td%s>%s</td>' % (cls, esc(v))


def _merged_trs(rows_spec, first_col_role=True):
    """第一列空串 = 延续上行(纵向合并 rowspan)"""
    norm, merges, prev = [], {}, None
    for r in rows_spec:
        if r and r[0] == '' and prev is not None:
            merges[prev] += 1
            norm.append((r, True))
        else:
            norm.append((r, False))
            merges[len(norm) - 1] = 1
            prev = len(norm) - 1
    trs = []
    for i, (r, skip) in enumerate(norm):
        items = list(r)
        tds = []
        if merges.get(i, 1) > 1:
            tds.append('<td class="role" rowspan="%d">%s</td>' % (merges[i], esc(items[0])))
            items = items[1:]
        elif skip:
            items = items[1:]
        elif items:
            tds.append(_cell_html(items[0], role=first_col_role))
            items = items[1:]
        tds += [_cell_html(v) for v in items]
        trs.append('<tr>%s</tr>' % ''.join(tds))
    return ''.join(trs)


def s_talent(spec):
    tm = spec.get('talent_map') or {}
    out = []
    if tm.get('positions'):
        rows = _merged_trs(tm['positions'])
        cols = ''.join('<col style="width:%s">' % w
                       for w in ('12%', '30%', '11%', '31%', '8%', '8%'))
        out.append(f'<table><colgroup>{cols}</colgroup>'
                   '<tr><th class="red">岗位类型</th><th class="red">核心职责</th>'
                   '<th class="red">职级分布</th><th class="red">经验要求</th>'
                   '<th class="red">当前人数</th><th class="red">缺口</th></tr>'
                   f'{rows}</table>')
    if tm.get('hiring'):
        rows = _merged_trs(tm['hiring'])
        cols = ''.join('<col style="width:%s">' % w
                       for w in ('20%', '35%', '15%', '30%'))
        out.append(f'<table><colgroup>{cols}</colgroup>'
                   '<tr><th class="gray">岗位</th><th class="gray">方向</th>'
                   '<th class="gray">人力需求</th><th class="gray">引入策略</th></tr>'
                   f'{rows}</table>')
    if not out:
        out.append('<p>（待补充）</p>')
    out.append('<div class="out">输出 &amp; 淘汰</div><div class="pend">待审视……</div>')
    return shell('<div class="tal">%s</div>' % ''.join(out), '人才地图', '人才地图')


def s_atmosphere(spec):
    sections = (spec.get('atmosphere_map') or {}).get('sections') or []
    parts = ['<div class="atm">']
    if not sections:
        parts.append('<div class="kt">关键任务：</div><p class="item">（待补充）</p>')
    else:
        parts.append('<div class="kt">关键任务：</div>')
        for sec in sections:
            if sec.get('title'):
                parts.append('<div class="sec">%s</div>' % esc(sec['title']))
            if sec.get('statement'):
                parts.append('<div class="stmt">%s</div>' % esc(sec['statement']))
            for blk in sec.get('blocks') or []:
                if blk.get('header'):
                    parts.append('<div class="blk">%s</div>' % esc(blk['header']))
                for it in blk.get('items') or []:
                    if isinstance(it, dict):
                        lead = '<b>%s</b>' % esc(it['lead']) if it.get('lead') else ''
                        parts.append('<p class="item">%s%s</p>' % (lead, esc(it['text'])))
                    else:
                        parts.append('<p class="item">%s</p>' % esc(it))
    parts.append('</div>')
    return shell('<div class="atm-box">%s</div>' % ''.join(parts), '氛围地图', '氛围地图')


def _compact_table(f):
    """组织结构图紧凑表: 橙黄标题条; 子任务模式 5 列(特性 rowspan), 否则 4 列"""
    sections = f.get('sections') or [{'members': f.get('members') or [],
                                      'partners': f.get('partners')}]
    all_members = [m for sec in sections for m in (sec.get('members') or [])]
    has_sub = any(m.get('sub') for m in all_members)
    has_grade = any(m.get('grade') for m in all_members)
    multi = _multi_name(f)
    # 人岗/任职/年限全空时紧凑表省略该列(数据填上后自动恢复), 宽度让给姓名/子任务
    grade_col = ['人岗/任职/年限'] if has_grade else []
    if has_sub:
        cols = ['特性', '子任务', '角色', '姓名'] + grade_col
        widths = ['26%', '32%', '12%', '30%'] if not has_grade else ['26%', '26%', '10%', '28%', '10%']
    else:
        cols = ['特性', '角色', '姓名'] + grade_col
        if has_grade:
            # 紧凑表整表仅~290px: 多人挤一格时姓名列加宽、基本空置的人岗列收窄, 避免竖摞撑高
            widths = ['32%', '13%', '27%', '28%'] if multi else ['33%', '15%', '25%', '27%']
        else:
            widths = ['35%', '14%', '51%'] if multi else ['38%', '14%', '48%']
    rows = []
    first = True
    for sec in sections:
        if first:
            rows.append('<tr>%s</tr>' % ''.join('<th>%s</th>' % c for c in cols))
            first = False
        mems = sec.get('members') or []
        i = 0
        while i < len(mems):
            # 子任务模式下, 特性相同的连续行合并特性格
            j = i + 1
            if has_sub:
                while j < len(mems) and mems[j].get('feature', '') == mems[i].get('feature', ''):
                    j += 1
            grp = mems[i:j] if has_sub else [mems[i]]
            for k, m in enumerate(grp):
                name = esc(m.get('name', ''))
                comp = COMPETENCY.get(m.get('competency') or '')
                style = ' style="background:#%s"' % comp if comp else ''
                cells = []
                if k == 0:
                    cells.append('<td rowspan="%d">%s</td>' % (len(grp), esc(m.get('feature', '')))
                                 if len(grp) > 1 else '<td>%s</td>' % esc(m.get('feature', '')))
                if has_sub:
                    cells.append('<td>%s</td>' % esc(m.get('sub', '')))
                cells += ['<td style="text-align:center">%s</td>' % esc(m.get('role', '')),
                          '<td class="name"%s>%s</td>' % (style, name)]
                if has_grade:
                    cells.append('<td style="text-align:center">%s</td>' % esc(m.get('grade', '')))
                rows.append('<tr>%s</tr>' % ''.join(cells))
            i = j
        if sec.get('partners') is not None:
            rows.append('<tr class="partner"><td colspan="%d">%s</td></tr>'
                        % (len(cols), esc(sec['partners'])))
    if not any('partner' in r for r in rows):
        rows.append('<tr class="partner"><td colspan="%d">%s</td></tr>'
                    % (len(cols), esc(f.get('partners', ''))))
    colgroup = ''.join('<col style="width:%s">' % w for w in widths)
    return ('<div class="ctable"><div class="t">%s</div><table><colgroup>%s</colgroup>%s'
            '</table></div>' % (esc(f.get('title', '')), colgroup, ''.join(rows)))


def s_orgchart(spec):
    """组织结构图页: 组名盒子+连接线+紧凑成员表(自动从 org_map 派生, org_map_v2 可覆盖)"""
    om = spec.get('org_map_v2') or {}
    features = om.get('features')

    def _merge_sub(members):
        """紧凑表把同特性子任务行折叠回一行: 特性（子1、子2…）, 姓名取并集(过滤待定占位)"""
        out = []
        for m in members:
            prev = out[-1] if out else None
            if m.get('sub') and prev is not None and prev.get('feature') == m.get('feature'):
                prev['sub'] = '%s、%s' % (prev.get('sub', ''), m['sub'])
                have = [n for n in str(prev.get('name', '')).split('、') if n]
                add = [n for n in str(m.get('name', '')).split('、')
                       if n and n not in have and n not in ('（待定）', '(待定)')]
                prev['name'] = '、'.join(have + add)
            else:
                out.append(dict(m))
        for m in out:
            if m.get('sub'):
                m['feature'] = '%s（%s）' % (m['feature'], m['sub'])
                del m['sub']
        return out

    def _prep(members):
        return _merge_sub([{k: v for k, v in m.items() if k != 'landing'}
                           for m in (members or [])])

    if features is None:
        features = []
        for f in (spec.get('org_map') or {}).get('features') or []:
            if f.get('p7') is False:
                continue   # 该专题不派生到组织结构图页(如公共事务类)
            g = {k: v for k, v in f.items() if k not in ('col', 'w', 'landing', 'p7')}
            if g.get('sections'):
                g['sections'] = [dict(s, members=_prep(s.get('members')))
                                 for s in g['sections']]
            elif g.get('members'):
                g['members'] = _prep(g['members'])
            features.append(g)
    if not features:
        features = [{'title': '（待补充）', 'members': [], 'partners': ''}]
    group = om.get('group')
    if not group:
        gn = str(spec.get('meta', {}).get('group_name', ''))
        group = re.sub(r'^.*?(?:技术开发|技术研发)', '', gn) or gn
    # 连接线: 组盒→水平线→各上排表中心 (第一行最多4张)
    row1 = features[:4]
    n1 = max(len(row1), 1)
    L, R = 40, 1240
    cw = (R - L - (n1 - 1) * 18) / n1
    centers = [L + cw / 2 + i * (cw + 18) for i in range(n1)]
    lines = ['<div style="position:absolute;left:%.0fpx;top:183px;width:2px;height:20px;background:#000;z-index:2"></div>'
             % (640 - 1)]
    if n1 > 1:
        lines.append('<div style="position:absolute;left:%.0fpx;top:203px;width:%.0fpx;height:2px;background:#000;z-index:2"></div>'
                     % (centers[0], centers[-1] - centers[0]))
    for cx in centers:
        lines.append('<div style="position:absolute;left:%.0fpx;top:203px;width:2px;height:26px;background:#000;z-index:2"></div>'
                     % (cx - 1))
    tables = ''.join(_compact_table(f) for f in features)
    note = ('人员胜任度：指人员绩效输出现状与其应承担的岗位要求的绩效输出之间差距。'
            '是与岗位要求相比，而非实际从事的工作。')
    # 密度自适应: 四表估高总量超页容时收紧行距字号
    dense = ' dense' if sum(_est_height(f) for f in features) > 800 else ''
    body = ('<div class="oc-group">%s</div>%s'
            '<div class="oc-note">%s</div>'
            '<div class="oc-grid%s">%s</div>'
            % (esc(group), ''.join(lines), esc(note), dense, tables))
    return shell(body, '组织地图', '组织地图')


def render(spec, out_path, only_slide=None):
    meta = spec.get('meta') or {}
    slides = [s_cover(meta), s_business(spec), s_org(spec), s_talent(spec),
              s_atmosphere(spec), s_end(), s_orgchart(spec)]
    if only_slide is not None:
        slides = [slides[only_slide - 1]]
    doc = ('<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">\n'
           '<title>%s四张地图</title>\n<style>%s</style></head>\n<body>\n%s\n</body></html>'
           % (esc(meta.get('group_name', '')), CSS, ''.join(slides)))
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    return out_path


def main():
    ap = argparse.ArgumentParser(description='四张地图 HTML 渲染器(验收用)')
    ap.add_argument('--spec', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--slide', type=int, default=None,
                    help='只渲染第 N 页(1封面 2业务 3组织 4人才 5氛围 6结束页)')
    args = ap.parse_args()
    with open(args.spec, 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f) or {}
    print('OK ->', render(spec, args.out, args.slide))


if __name__ == '__main__':
    main()
