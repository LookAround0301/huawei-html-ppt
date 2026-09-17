# -*- coding: utf-8 -*-
"""
四张地图生成器: spec.yaml + template.pptx -> <组名>四张地图.pptx
基于模板克隆, 保留华为官方版式/主题/背景/导航, 只替换内容。
"""
import sys, io, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from copy import deepcopy
import yaml
from pptx import Presentation
from pptx.util import Inches
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn

A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
# 胜任度 -> 姓名单元格填充色(与模板图例一致)
COMPETENCY_COLORS = {
    '高': '92D050', '胜任度高': '92D050',
    '胜任': 'FFFF00',
    '基本': 'FFC000', '基本胜任': 'FFC000',
    '不胜任': 'FF0000', '暂不胜任': 'FF0000',
}
MAP_TITLES = ('业务地图', '组织地图', '人才地图', '氛围地图')

# ---------- 底层 XML 工具 ----------

def set_run_text(r_el, text):
    """替换 <a:r> 的文本(保留 rPr 格式)"""
    for t in r_el.findall(qn('a:t')):
        r_el.remove(t)
    t = parse_xml('<a:t xmlns:a="%s"/>' % A_NS)
    t.text = str(text)
    r_el.append(t)

def cell_set_text(cell, text):
    """重写单元格文本; 多行(\\n)拆多段; 格式取自本单元格首个带 run 的段落"""
    txBody = cell.text_frame._txBody
    paras = txBody.findall(qn('a:p'))
    donor = next((pe for pe in paras if pe.findall(qn('a:r'))), None)
    for pe in paras:
        txBody.remove(pe)
    base = None
    if donor is not None:
        base = deepcopy(donor)
        for r in base.findall(qn('a:r'))[1:]:
            base.remove(r)
        for br in base.findall(qn('a:br')):
            base.remove(br)
    lines = [''] if text in (None, '') else str(text).split('\n')
    for line in lines:
        pe = deepcopy(base) if base is not None else parse_xml('<a:p xmlns:a="%s"/>' % A_NS)
        rs = pe.findall(qn('a:r'))
        if not rs and base is not None:
            rs = [deepcopy(base.findall(qn('a:r'))[0])]
            pe.append(rs[0])
        if rs:
            set_run_text(rs[0], line)   # 空行也覆写, 清除模板样例残留文本
        txBody.append(pe)

def set_cell_fill(cell, hexcolor):
    """设置单元格填充; hexcolor=None 清除填充"""
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ('a:solidFill', 'a:gradFill', 'a:blipFill', 'a:pattFill', 'a:grpFill', 'a:noFill'):
        for el in tcPr.findall(qn(tag)):
            tcPr.remove(el)
    if hexcolor:
        tcPr.append(parse_xml(
            '<a:solidFill xmlns:a="%s"><a:srgbClr val="%s"/></a:solidFill>' % (A_NS, hexcolor)))

def dedupe_ids(slide):
    """只修正重复的 cNvPr id(避免动到动画引用的 spid)"""
    seen, nxt = set(), 2
    for cNvPr in slide._element.iter(qn('p:cNvPr')):
        cur = int(cNvPr.get('id'))
        if cur in seen:
            while nxt in seen:
                nxt += 1
            cNvPr.set('id', str(nxt))
            seen.add(nxt)
        else:
            seen.add(cur)

def frame_set_pos(el, x=None, y=None, w=None, h=None):
    xfrm = el.find(qn('p:xfrm'))
    if xfrm is None:
        return
    off, ext = xfrm.find(qn('a:off')), xfrm.find(qn('a:ext'))
    if x is not None and off is not None:
        off.set('x', str(int(Inches(x))))
    if y is not None and off is not None:
        off.set('y', str(int(Inches(y))))
    if w is not None and ext is not None:
        ext.set('cx', str(int(Inches(w))))
    if h is not None and ext is not None:
        ext.set('cy', str(int(Inches(h))))

def wrap_shape(slide, el):
    for sh in slide.shapes:
        if sh._element is el:
            return sh
    return None

def row_h(tr, inches):
    tr.set('h', str(int(Inches(inches))))

# ---------- 段落级文本重建(业务/氛围地图) ----------

def run_color(p):
    try:
        if p.runs[0].font.color and p.runs[0].font.color.type is not None:
            return str(p.runs[0].font.color.rgb)
    except Exception:
        pass
    return None

def _make_para(proto_p, text, lead=None):
    """由原型段落克隆出新 <a:p>; lead=加粗前缀"""
    pe = deepcopy(proto_p._p)
    runs = pe.findall(qn('a:r'))
    for br in pe.findall(qn('a:br')):
        pe.remove(br)
    if lead is not None and len(runs) >= 2:
        for r in runs[2:]:
            pe.remove(r)
        rs = pe.findall(qn('a:r'))
        set_run_text(rs[0], lead)
        set_run_text(rs[1], text)
        return pe
    for r in runs[1:]:
        pe.remove(r)
    rs = pe.findall(qn('a:r'))
    if rs:
        set_run_text(rs[0], lead + text if lead else text)
    return pe

def rebuild_text_frame(text_frame, para_els):
    txBody = text_frame._txBody
    for pe in txBody.findall(qn('a:p')):
        txBody.remove(pe)
    for el in para_els:
        txBody.append(el)

# ---------- slide 定位 ----------

def slide_title(slide):
    for sh in slide.shapes:
        if sh.has_text_frame:
            t = sh.text_frame.text.strip()
            if t in MAP_TITLES and sh.top is not None and sh.top < Inches(0.5) \
               and sh.left is not None and sh.left < Inches(1.0):
                return t
    return None

def find_slides(prs):
    found = {}
    for slide in prs.slides:
        t = slide_title(slide)
        if t is None:
            continue
        if t == '组织地图' and '组织地图' in found:
            found['org_v2'] = slide
        else:
            found[t] = slide
    return found

# ---------- 封面 ----------

def fill_cover(slide, meta):
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        if '四张地图' not in sh.text_frame.text:
            continue
        for p in sh.text_frame.paragraphs:
            ptxt = p.text
            if '四张地图' in ptxt:
                continue
            if 'PL' in ptxt:
                runs = p.runs
                if len(runs) >= 3:
                    set_run_text(runs[1]._r, '：%s ' % meta.get('pl_name', ''))
                    if meta.get('pl_id'):
                        set_run_text(runs[2]._r, str(meta['pl_id']))
                    else:
                        runs[2]._r.getparent().remove(runs[2]._r)
                elif runs:
                    set_run_text(runs[0]._r,
                                 'PL：%s %s' % (meta.get('pl_name', ''), meta.get('pl_id', '')))
            elif ptxt:
                runs = p.runs
                if runs:
                    for r in runs[1:]:
                        r._r.getparent().remove(r._r)
                    set_run_text(runs[0]._r, meta.get('group_name', ptxt))
        return

# ---------- 业务地图 ----------

def fill_business(slide, spec):
    items = (spec.get('business_map') or {}).get('items') or []
    target = None
    for sh in slide.shapes:
        if sh.has_text_frame and sh.height > Inches(3) and len(sh.text_frame.paragraphs) > 5:
            target = sh
            break
    if target is None:
        raise RuntimeError('业务地图正文文本框未找到')
    protos = {}
    for p in target.text_frame.paragraphs:
        if not p.runs:
            continue
        r0 = p.runs[0]
        if run_color(p) == 'C00000' and 'red' not in protos:
            protos['red'] = p
        elif r0.font.bold and len(p.runs) > 1 and 'lead' not in protos:
            protos['lead'] = p
        elif not r0.font.bold and 'plain' not in protos:
            protos['plain'] = p
    if 'red' not in protos or 'plain' not in protos:
        raise RuntimeError('业务地图段落原型缺失: %s' % list(protos))
    if not items:   # 未提供则清空为占位, 避免残留模板内容
        rebuild_text_frame(target.text_frame, [_make_para(protos['plain'], '（待补充）')])
        return
    out = []
    for it in items:
        out.append(_make_para(protos['red'], it['header']))
        for sub in it.get('subs') or []:
            if isinstance(sub, dict):
                if sub.get('lead') and 'lead' in protos:
                    out.append(_make_para(protos['lead'], sub['text'], lead=sub['lead']))
                else:
                    out.append(_make_para(protos['plain'], (sub.get('lead') or '') + sub['text']))
            else:
                out.append(_make_para(protos['plain'], str(sub)))
    rebuild_text_frame(target.text_frame, out)

# ---------- 组织地图 ----------

def _header_row(tbl):
    """在前3行内找表头行(首格'特性'), 返回该行单元格文本列表或 None"""
    for r in list(tbl.rows)[:3]:
        cells = [c.text.strip() for c in r.cells]
        if cells and cells[0] == '特性' and '角色' in cells:
            return cells
    return None

def is_feature_table(sh):
    """特性组表(含带副标题行的变体), 排除导航/图例"""
    if not getattr(sh, 'has_table', False):
        return False
    tbl = sh.table
    if len(tbl.columns) == 1 or len(tbl.rows) < 3:
        return False
    return _header_row(tbl) is not None

def _feature_sections(feature):
    """归一化: sections=[{subtitle?, members, partners?}]; 支持扁平 members/partners 写法"""
    if feature.get('sections'):
        return feature['sections']
    sec = {'members': feature.get('members') or []}
    if feature.get('partners') is not None:
        sec['partners'] = feature['partners']
    if feature.get('subtitle'):
        sec['subtitle'] = feature['subtitle']
    return [sec]

# 列宽比例(特性/角色/姓名/人岗[/落地]), 按目标宽度缩放, 保证与框架宽度一致
COL_RATIOS_STD = [0.44, 0.15, 0.19, 0.22]
COL_RATIOS_LANDING = [0.36, 0.10, 0.14, 0.19, 0.21]
COL_RATIOS_SUB = [0.23, 0.30, 0.12, 0.20, 0.15]   # 特性/子任务/角色/姓名/人岗

def set_col_widths(el, col_w, n_cols, sub=False):
    ratios = (COL_RATIOS_SUB if sub else COL_RATIOS_LANDING) if n_cols == 5 else COL_RATIOS_STD
    if len(ratios) != n_cols:  # 意外列数则等分
        ratios = [1.0 / n_cols] * n_cols
    grid = el.find('.//' + qn('a:tblGrid'))
    cols = grid.findall(qn('a:gridCol'))
    for gc, r in zip(cols, ratios):
        gc.set('w', str(int(Inches(col_w * r))))

def build_feature_table(slide, proto_el, feature, x, y, col_w):
    """克隆原型表格元素 -> 生成一个特性组表; 返回(新元素, 估算高度in)
    行序: 标题 / [副标题] / 表头(一次) / 成员... / [合作团队] (按 section 重复)
    成员带 sub 字段时用 5 列原型并重写表头(特性/子任务/角色/姓名/人岗)"""
    el = deepcopy(proto_el)
    proto_el.getparent().append(el)
    frame_set_pos(el, x=x, y=y, w=col_w)
    sections0 = _feature_sections(feature)
    has_sub = any(m.get('sub') for sec in sections0 for m in (sec.get('members') or []))
    n_cols = len(proto_el.findall('.//' + qn('a:gridCol')))
    set_col_widths(el, col_w, n_cols, sub=(has_sub and n_cols == 5))
    sh = wrap_shape(slide, el)
    if sh is None:
        raise RuntimeError('克隆表格失败')
    tbl_el = sh.table._tbl
    trs = tbl_el.findall(qn('a:tr'))
    title_tr, header_tr, partner_tr, member_proto = trs[0], trs[1], trs[-1], trs[2]
    for tr in trs[3:-1]:
        tbl_el.remove(tr)
    sections = _feature_sections(feature)
    landing = bool(feature.get('landing'))

    cell_set_text(sh.table.rows[0].cells[0], feature.get('title', ''))
    row_h(title_tr, 0.19)
    row_h(header_tr, 0.135)
    if has_sub and n_cols == 5:
        for ci, t in enumerate(['特性', '子任务', '角色', '姓名', '人岗/任职/年限']):
            cell_set_text(sh.table.rows[1].cells[ci], t)

    # 拼装行计划: (类型, 载荷)
    plan = []
    for si, sec in enumerate(sections):
        if sec.get('subtitle'):
            plan.append(('S', sec['subtitle']))
        if si == 0:
            plan.append(('H', None))
        for m in sec.get('members') or []:
            plan.append(('M', m))
        if sec.get('partners') is not None:
            plan.append(('P', sec['partners']))
    if not any(k == 'P' for k, _ in plan):
        plan.append(('P', sections[-1].get('partners', '')))

    # 依次插入行
    heights = {'S': 0.12, 'M': 0.125, 'P': 0.11}
    anchor = title_tr
    for kind, _payload in plan:
        if kind == 'S':
            tr = deepcopy(title_tr)
        elif kind == 'H':
            tr = header_tr
        elif kind == 'M':
            tr = deepcopy(member_proto)
        else:
            tr = deepcopy(partner_tr)
        anchor.addnext(tr)
        anchor = tr
        if kind != 'H':
            row_h(tr, heights[kind])
    tbl_el.remove(member_proto)
    tbl_el.remove(partner_tr)

    # 填内容: rows[0]=标题, 之后与 plan 对齐
    for row, (kind, payload) in zip(list(sh.table.rows)[1:], plan):
        if kind == 'S':
            cell_set_text(row.cells[0], payload)
        elif kind == 'M':
            m = payload
            vals = [m.get('feature', '')]
            if has_sub and len(row.cells) == 5:
                vals.append(m.get('sub', ''))
            vals += [m.get('role', ''), m.get('name', ''), m.get('grade', '')]
            if landing:
                vals.append(m.get('landing', ''))
            for ci, v in enumerate(vals[:len(row.cells)]):
                cell_set_text(row.cells[ci], v)
            if len(row.cells) > 2:
                set_cell_fill(row.cells[2], COMPETENCY_COLORS.get(m.get('competency') or ''))
        elif kind == 'P':
            cell_set_text(row.cells[0], ('合作团队：%s' % payload) if payload else '')

    n_m = sum(1 for k, _ in plan if k == 'M')
    n_s = sum(1 for k, _ in plan if k == 'S')
    n_p = sum(1 for k, _ in plan if k == 'P')
    wrap_extra = sum(0.12 for k, payload in plan
                     if k == 'M' and (len(payload.get('feature', '')) > 24
                                      or len(payload.get('sub', '')) > 22))
    est = 0.19 + 0.12 * n_s + 0.135 + 0.125 * n_m + 0.11 * n_p + wrap_extra + 0.03
    set_table_fonts(sh)
    return el, est

def set_table_fonts(sh, body_pt=6.75, title_pt=7.5, header_pt=6.5, partner_pt=6.0):
    """整表统一字号(与 HTML 紧凑密度对齐): 标题/表头/成员/合作团队分级"""
    from pptx.util import Pt as _Pt
    rows = list(sh.table.rows)
    for ri, row in enumerate(rows):
        pt = (title_pt if ri == 0 else header_pt if ri == 1
              else partner_pt if ri == len(rows) - 1 else body_pt)
        for cell in row.cells:
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = _Pt(pt)

def fill_org_map(slide, spec):
    features = (spec.get('org_map') or {}).get('features') or []
    # 原型: 4列(标准) / 5列(带"落地") — 先识别, 供克隆
    proto_std = proto_landing = None
    feature_tables = []
    for sh in list(slide.shapes):
        if not getattr(sh, 'has_table', False):
            continue
        if is_feature_table(sh):
            feature_tables.append(sh)
            header = _header_row(sh.table)
            if '落地' in header and proto_landing is None:
                proto_landing = sh
            elif len(sh.table.columns) == 4 and proto_std is None:
                proto_std = sh
    if not features:   # 未提供则删除全部特性表, 避免残留模板人员信息
        for sh in feature_tables:
            sh._element.getparent().remove(sh._element)
        return
    if proto_std is None:
        raise RuntimeError('组织地图缺少 4 列表格原型')

    # 两列瀑布布局(等宽, 便于 COM 阶段跨列均衡)
    cols_x, cols_w = (0.12, 5.00), (4.80, 4.80)
    totals = [0.0, 0.0]
    y0 = 0.73
    for f in features:
        sections_f = _feature_sections(f)
        has_sub = any(m.get('sub') for sec in sections_f for m in (sec.get('members') or []))
        proto = (proto_landing._element
                 if (proto_landing and (f.get('landing') or has_sub)) else proto_std._element)
        c = f.get('col') if f.get('col') in (0, 1) else (0 if totals[0] <= totals[1] else 1)
        _, est = build_feature_table(slide, proto, f, cols_x[c], y0 + totals[c], cols_w[c])
        totals[c] += est + 0.10

    # 删除全部旧特性表(含原型)
    for sh in feature_tables:
        sh._element.getparent().remove(sh._element)
    dedupe_ids(slide)

# ---------- 人才地图 ----------

def fill_talent(slide, spec):
    tm = spec.get('talent_map') or {}
    for sh in slide.shapes:
        if not getattr(sh, 'has_table', False):
            continue
        header = [c.text.strip() for c in sh.table.rows[0].cells]
        if header[:2] == ['岗位类型', '核心职责']:
            rows_spec = tm.get('positions') or []
        elif header[:2] == ['岗位', '方向']:
            rows_spec = tm.get('hiring') or []
        else:
            continue
        tbl_el = sh.table._tbl
        trs = tbl_el.findall(qn('a:tr'))
        header_tr, proto_tr = trs[0], trs[1]
        for tr in trs[2:]:
            tbl_el.remove(tr)
        anchor = header_tr
        for _ in rows_spec:
            ntr = deepcopy(proto_tr)
            anchor.addnext(ntr)
            anchor = ntr
        tbl_el.remove(proto_tr)
        for ri, rvals in enumerate(rows_spec):
            row = sh.table.rows[ri + 1]
            for ci, cell in enumerate(row.cells):
                cell_set_text(cell, rvals[ci] if ci < len(rvals) else '')

# ---------- 氛围地图 ----------

def fill_atmosphere(slide, spec):
    sections = (spec.get('atmosphere_map') or {}).get('sections') or []
    target = None
    for sh in slide.shapes:
        if sh.has_text_frame and '关键任务' in sh.text_frame.text:
            target = sh
            break
    if target is None:
        raise RuntimeError('氛围地图文本框未找到')
    tf = target.text_frame
    sec_t = blk_t = stmt = item_p = lead_p = red_h = None
    for p in tf.paragraphs:
        if not p.runs:
            continue
        r0 = p.runs[0]
        bold = bool(r0.font.bold)
        if run_color(p) == 'C00000' and red_h is None:
            red_h = p
            continue
        if p.level == 0 and bold:
            if (r0.font.name or '') == '宋体' and stmt is None:
                stmt = p
            elif sec_t is None:
                sec_t = p
        elif p.level == 1:
            if bold:
                if len(p.runs) == 1 and blk_t is None:
                    blk_t = p
                elif len(p.runs) > 1 and lead_p is None:
                    lead_p = p
            elif item_p is None:
                item_p = p
    if red_h is None:
        raise RuntimeError('氛围地图缺少"关键任务"红色段落原型')
    if not sections:   # 未提供则清空为占位, 避免残留模板内容
        ph = sec_t if sec_t is not None else red_h
        rebuild_text_frame(tf, [deepcopy(red_h._p), _make_para(ph, '（待补充）')])
        return
    out = [deepcopy(red_h._p)]
    for sec in sections:
        if sec_t is not None:
            out.append(_make_para(sec_t, sec.get('title', '')))
        if sec.get('statement') and stmt is not None:
            out.append(_make_para(stmt, sec['statement']))
        for blk in sec.get('blocks') or []:
            if blk.get('header') and blk_t is not None:
                out.append(_make_para(blk_t, blk['header']))
            for it in blk.get('items') or []:
                if isinstance(it, dict) and it.get('lead') and lead_p is not None:
                    out.append(_make_para(lead_p, it.get('text', ''), lead=it['lead']))
                elif isinstance(it, dict):
                    out.append(_make_para(item_p, (it.get('lead') or '') + it.get('text', '')))
                elif item_p is not None:
                    out.append(_make_para(item_p, str(it)))
    rebuild_text_frame(tf, out)

# ---------- 主流程 ----------

def delete_slide(prs, slide):
    id_lst = prs.slides._sldIdLst
    for sldId in list(id_lst):
        rId = sldId.get(qn('r:id'))
        try:
            if prs.part.rels[rId].target_part is slide.part:
                prs.part.drop_rel(rId)
                id_lst.remove(sldId)
                return True
        except KeyError:
            continue
    return False

def com_relayout(pptx_path):
    """PowerPoint COM 后处理: 按真实渲染高度重排组织地图特性表(两列各自纵向堆叠)。
    需要本机 PowerPoint; 不可用时跳过(仅位置估算略保守)。"""
    try:
        import win32com.client
    except ImportError:
        print('[relayout] pywin32 不可用, 跳过 COM 重排')
        return False
    import os
    app = None
    pres = None
    try:
        app = win32com.client.Dispatch('PowerPoint.Application')
        pres = app.Presentations.Open(os.path.abspath(pptx_path),
                                      ReadOnly=False, WithWindow=False)
        CONTENT_TOP = 52.6   # 0.73in
        GAP = 6.0            # 0.08in
        COL_X = (8.6, 360.0)   # 0.12in / 5.00in
        for slide in pres.Slides:
            title_texts = []
            tables = []
            for sh in slide.Shapes:
                if sh.HasTextFrame:
                    title_texts.append(sh.TextFrame.TextRange.Text.strip())
                if sh.HasTable:
                    t = sh.Table
                    if t.Rows.Count >= 3 and t.Columns.Count >= 4:
                        tables.append(sh)
            if '组织地图' not in title_texts or not tables:
                continue
            # 保持生成时的左右分列(与 HTML 版式一致), 各列内按 Top 重排纵向堆叠
            avail = pres.PageSetup.SlideHeight - CONTENT_TOP
            groups = {0: [], 1: []}
            for sh in sorted(tables, key=lambda s: s.Top):
                groups.setdefault(0 if sh.Left < 180 else 1, []).append(sh)
            for c in (0, 1):
                y = CONTENT_TOP
                col_h = sum(sh.Height + GAP for sh in groups.get(c, []))
                if col_h - GAP > avail:
                    print('[relayout] 警告: 组织地图第%d列内容 %.0fpt 超出可用 %.0fpt, 请精简内容'
                          % (c + 1, col_h - GAP, avail))
                for sh in groups.get(c, []):
                    sh.Left = COL_X[c]
                    sh.Top = y
                    y = sh.Top + sh.Height + GAP
        pres.Save()
        return True
    except Exception as e:
        print('[relayout] COM 重排失败: %s' % e)
        return False
    finally:
        try:
            if pres is not None:
                pres.Close()
        except Exception:
            pass

def generate(spec, template_path, out_path, relayout=True):
    prs = Presentation(template_path)
    slides = find_slides(prs)

    fill_cover(prs.slides[0], spec.get('meta') or {})
    for key, fn in (('业务地图', fill_business), ('组织地图', fill_org_map),
                    ('人才地图', fill_talent), ('氛围地图', fill_atmosphere)):
        if key in slides:
            fn(slides[key], spec)

    if 'org_v2' in slides:
        v2 = (spec.get('org_map_v2') or {}).get('features')
        if not v2:
            delete_slide(prs, slides['org_v2'])

    try:
        prs.core_properties.title = '%s四张地图' % (spec.get('meta') or {}).get('group_name', '')
    except Exception:
        pass
    prs.save(out_path)
    if relayout:
        com_relayout(out_path)
    return out_path

def main():
    ap = argparse.ArgumentParser(description='四张地图生成器')
    ap.add_argument('--spec', required=True, help='spec YAML 路径')
    ap.add_argument('--template', required=True, help='模板 pptx 路径')
    ap.add_argument('--out', required=True, help='输出 pptx 路径')
    ap.add_argument('--no-relayout', action='store_true', help='跳过 PowerPoint COM 重排版')
    args = ap.parse_args()
    with open(args.spec, 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f) or {}
    print('OK ->', generate(spec, args.template, args.out, relayout=not args.no_relayout))

if __name__ == '__main__':
    main()
