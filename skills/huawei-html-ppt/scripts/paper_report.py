"""Compose and render paper front matter without bundling reference material."""
from copy import deepcopy
from html import escape
import re

from source_images import image_html, read_image

KIND = 'paper-analysis'
LAYOUTS = {'paper-cover': 'cover', 'paper-agenda': 'chapter-navigation'}


def requested(request):
    """Use caller intent, never instructions extracted from source documents."""
    if any(value == KIND for value in (
        request.get('content_kind'), request.get('context', {}).get('report_kind'),
        request.get('deck', {}).get('report_kind'),
    )):
        return True
    return bool(re.search(r'论文(?:分析|汇报|解读|研读)', request.get('text', '')))


def assemble(title, chapters, cover=None):
    """Each chapter supplies id, title and authored content slides; preserve order."""
    chapters = deepcopy(chapters)
    title_page = {'title': title if title.endswith('论文分析报告') else title + '\n论文分析报告'}
    title_page.update(deepcopy(cover or {}))
    title_page.update(layout='paper-cover', role='cover')
    slides = [title_page]
    headings = []
    for chapter in chapters:
        identity = chapter['id']
        headings.append({'id': identity, 'title': chapter['title']})
        slides.append({'title': '目录', 'layout': 'paper-agenda',
                       'role': 'chapter-navigation', 'active_chapter': identity})
        for slide in chapter['slides']:
            slide['chapter_id'] = identity
            slides.append(slide)
    deck = {'title': title, 'style': 'insight-analysis', 'report_kind': KIND,
            'chapters': headings, 'slides': slides}
    errors = validate_structure(deck)
    if errors:
        raise ValueError('; '.join(errors))
    return deck


def validate_structure(deck):
    """Validate the navigation-to-content mapping, not scientific correctness."""
    if deck.get('report_kind') != KIND and not any(
        slide.get('layout') in LAYOUTS for slide in deck.get('slides', [])
    ):
        return []
    errors = []
    chapters = deck.get('chapters', [])
    has_agenda = any(slide.get('layout') == 'paper-agenda' for slide in deck.get('slides', []))
    if has_agenda or deck.get('report_kind') == KIND:
        if not isinstance(chapters, list) or not 1 <= len(chapters) <= 8:
            return ['paper report needs 1-8 top-level chapters; group related sections before rendering']
        if any(not isinstance(c, dict) or not isinstance(c.get('id'), str) or not c['id'].strip()
               or not isinstance(c.get('title'), str) or not c['title'].strip() for c in chapters):
            return ['paper chapters need nonempty string id and title']
        ids = [c['id'] for c in chapters]
        if len(set(ids)) != len(ids):
            return ['paper chapter ids must be unique']
    else:
        ids = []
    for n, slide in enumerate(deck.get('slides', []), 1):
        layout = slide.get('layout')
        if layout not in LAYOUTS:
            continue
        prefix = f'slide {n}: '
        if deck.get('style') != 'insight-analysis':
            errors.append(prefix + 'paper front matter belongs to insight-analysis')
        if slide.get('role', LAYOUTS[layout]) != LAYOUTS[layout]:
            errors.append(prefix + 'front-matter role does not match layout')
        if slide.get('panels') or slide.get('conclusion'):
            errors.append(prefix + 'cover and agenda are navigation pages, not analysis panels')
        if layout == 'paper-agenda' and slide.get('active_chapter') not in ids:
            errors.append(prefix + 'active_chapter must reference deck.chapters')
        if layout == 'paper-cover':
            if 'date' in slide and not isinstance(slide['date'], str):
                errors.append(prefix + 'cover date must be text')
            if slide.get('background') is not None:
                try:
                    read_image(slide['background'])
                except (ValueError, OSError) as exc:
                    errors.append(prefix + str(exc))
    if deck.get('report_kind') != KIND:
        return errors
    slides = deck.get('slides', [])
    if not slides or slides[0].get('layout') != 'paper-cover':
        errors.append('paper report must start with its cover')
    if sum(s.get('layout') == 'paper-cover' for s in slides) != 1:
        errors.append('paper report needs exactly one leading cover')
    cursor = 1
    for identity in ids:
        if cursor >= len(slides) or slides[cursor].get('layout') != 'paper-agenda' or slides[cursor].get('active_chapter') != identity:
            errors.append(f'chapter {identity}: place its agenda immediately before its content')
            break
        cursor += 1
        start = cursor
        while cursor < len(slides) and slides[cursor].get('layout') not in LAYOUTS:
            if slides[cursor].get('chapter_id') != identity:
                errors.append(f'slide {cursor + 1}: chapter_id does not match the preceding agenda')
            cursor += 1
        if cursor == start:
            errors.append(f'chapter {identity}: needs at least one content slide')
    if cursor != len(slides):
        errors.append('paper report pages must follow the complete chapter order')
    return errors


def render_frontmatter(slide, deck, number, logo):
    title = escape(slide['title'])
    if slide['layout'] == 'paper-cover':
        background = slide.get('background')
        backdrop = '<div class="cover-backdrop" aria-hidden="true">' + image_html(background) + '</div>' if background else ''
        date = f'<p class="cover-date">日期：{escape(slide["date"])}</p>' if slide.get('date') else ''
        body = f'{backdrop}<h1>{title}</h1><div class="cover-accent" aria-hidden="true"></div>{date}'
        css = 'paper-cover'
    else:
        rows = []
        for i, chapter in enumerate(deck['chapters'], 1):
            current = chapter['id'] == slide['active_chapter']
            attrs = ' class="current" aria-current="step"' if current else ''
            rows.append(f'<li{attrs}><span class="chapter-number">{i}.</span><span>{escape(chapter["title"])}</span></li>')
        body = f'<h1>{title}</h1><div class="agenda-rule"></div><ol class="chapter-list">{"".join(rows)}</ol>'
        css = 'paper-agenda'
    return (f'<article class="slide {css}" data-slide="{number}" data-layout="{slide["layout"]}">'
            f'{body}<footer><span>{number:02d} / {len(deck["slides"]):02d}　 Huawei Confidential</span>'
            f'<img alt="HUAWEI" src="data:image/png;base64,{logo}"></footer></article>')
