"""Paper navigation checks use synthetic content only, never reference reports."""
from copy import deepcopy
import base64
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'skills/huawei-html-ppt/scripts'))
import paper_report
import ppt


class PaperReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='paper-report-test-')
        self.path = Path(self.tmp.name)
        sample = ppt.read(REPO / 'examples/insight-request.json')['deck']['slides'][0]
        self.chapters = []
        for identity, title in [('innovation', '核心创新'), ('design', '设计与机制'), ('results', '实验结果')]:
            slide = deepcopy(sample)
            slide['title'] = title
            self.chapters.append({'id': identity, 'title': title, 'slides': [slide]})
        self.deck = paper_report.assemble('合成测试论文分析报告', self.chapters)

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, deck=None):
        return {'content_kind': 'paper-analysis', 'deck': deck or self.deck,
                'state_dir': str(self.path / 'state')}

    def test_first_use_routes_and_loads_scoped_guidance(self):
        for request in [{'text': '请制作一份论文分析报告'},
                        {'text': '制作论文分析报告，使用 PDCP 风格封面和逐章高亮目录'},
                        {'content_kind': 'paper-analysis'}]:
            plan = ppt.plan({**request, 'state_dir': str(self.path / 'state')})
            self.assertEqual(plan['route']['style'], 'insight-analysis')
            self.assertEqual(plan['report_kind'], 'paper-analysis')
            self.assertIn('paper.structure@1', plan['unit_refs'])
            self.assertTrue(any(c['id'] == 'paper-frontmatter' for c in plan['components']))
        regular = ppt.plan({'style': 'insight-analysis', 'text': '模型对比', 'state_dir': str(self.path / 'state')})
        self.assertIsNone(regular['report_kind'])
        self.assertNotIn('paper.structure@1', regular['unit_refs'])
        explicit = ppt.plan({'text': '论文分析报告', 'style': 'technical-project', 'state_dir': str(self.path / 'state')})
        self.assertEqual(explicit['route']['style'], 'technical-project')
        self.assertIsNone(explicit['report_kind'])

    def test_composition_is_complete_and_does_not_mutate_input(self):
        self.assertNotIn('chapter_id', self.chapters[0]['slides'][0])
        self.assertTrue(ppt.validate(self.deck)['ok'])
        slides = self.deck['slides']
        self.assertEqual(slides[0]['role'], 'cover')
        self.assertEqual(len(slides), 1 + 2 * len(self.chapters))
        for index, chapter in enumerate(self.chapters):
            self.assertEqual(slides[1 + 2 * index]['active_chapter'], chapter['id'])
            self.assertEqual(slides[2 + 2 * index]['chapter_id'], chapter['id'])
        self.chapters[1]['slides'].append(deepcopy(self.chapters[1]['slides'][0]))
        deck = paper_report.assemble('Multi-page chapter', self.chapters)
        self.assertEqual(sum(s['layout'] == 'paper-agenda' for s in deck['slides']), 3)
        self.assertTrue(ppt.validate(deck)['ok'])

    def test_render_keeps_full_deck_and_highlights_one_chapter(self):
        self.deck['slides'][0]['title'] = '<Title>\n论文分析报告'
        self.deck['slides'][0]['notes'] = {'private': 'HIDDEN_NOTE'}
        result = ppt.render(self.request(), self.path / 'out')
        html = Path(result['html']).read_text(encoding='utf-8')
        visible = html.split('<script type="application/json" id="deck-model">')[0]
        self.assertEqual(ppt.read(result['deck'])['slides'], self.deck['slides'])
        pages = re.findall(r'<article\b.*?</article>', visible, re.S)
        self.assertEqual(len(pages), 7)
        self.assertIn('&lt;Title&gt;', pages[0])
        self.assertNotIn('HIDDEN_NOTE', visible)
        self.assertIn('HIDDEN_NOTE', html)
        for index, page in enumerate(pages):
            self.assertIn(f'{index + 1:02d} / 07', page)
            if 'class="slide paper-agenda"' in page:
                self.assertEqual(page.count('aria-current="step"'), 1)
                for chapter in self.chapters:
                    self.assertIn(chapter['title'], page)
                self.assertNotIn('insight-conclusion', page)
        self.assertIn('insight-conclusion', pages[2])

    def test_missing_or_misordered_sections_are_rejected(self):
        variants = []
        deck = deepcopy(self.deck); deck['slides'][1]['active_chapter'] = 'unknown'; variants.append(deck)
        deck = deepcopy(self.deck); deck['chapters'][1]['id'] = 'innovation'; variants.append(deck)
        deck = deepcopy(self.deck); deck['slides'][2]['chapter_id'] = 'results'; variants.append(deck)
        deck = deepcopy(self.deck); deck['slides'][0], deck['slides'][2] = deck['slides'][2], deck['slides'][0]; variants.append(deck)
        deck = deepcopy(self.deck); deck['slides'].pop(2); variants.append(deck)
        deck = deepcopy(self.deck); deck['slides'].pop(3); variants.append(deck)
        deck = deepcopy(self.deck); deck['slides'][0]['role'] = 'chapter-navigation'; variants.append(deck)
        for deck in variants:
            with self.subTest(deck=deck):
                self.assertFalse(ppt.validate(deck)['ok'])
                with self.assertRaises(ValueError):
                    ppt.render(self.request(deck), self.path / 'invalid')

    def test_content_conclusion_is_still_required(self):
        self.deck['slides'][2].pop('conclusion')
        self.assertFalse(ppt.validate(self.deck)['ok'])

    def test_optional_local_background_embeds_only_local_bytes(self):
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0i8AAAAASUVORK5CYII=')
        asset = self.path / 'synthetic.png'
        asset.write_bytes(png)
        self.deck['slides'][0]['background'] = {'path': str(asset), 'alt': 'Synthetic background', 'source': {'kind': 'synthetic-test'}}
        result = ppt.render(self.request(), self.path / 'image')
        html = Path(result['html']).read_text(encoding='utf-8')
        self.assertIn('data:image/png;base64,' + base64.b64encode(png).decode('ascii'), html)
        for bad in ['https://example.invalid/private.png', str(self.path / 'missing.png')]:
            self.deck['slides'][0]['background']['path'] = bad
            self.assertFalse(ppt.validate(self.deck)['ok'])


if __name__ == '__main__':
    unittest.main()
