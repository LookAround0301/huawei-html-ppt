"""Synthetic figures exercise original-byte embedding; no private images shipped."""
from pathlib import Path
import base64
import copy
import hashlib
from html.parser import HTMLParser
import json
import struct
import sys
import tempfile
import unittest
import zlib

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'skills/huawei-html-ppt/scripts'))
import ppt


class Images(HTMLParser):
    def __init__(self):
        super().__init__(); self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img': self.items.append(dict(attrs))


class SourceImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ppt-image-test-')
        self.path = Path(self.temp.name)
        def chunk(kind, data):
            return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
        self.png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 4, 2, 8, 2, 0, 0, 0))
        self.png += chunk(b'IDAT', zlib.compress((b'\0' + b'\xc0\0\0' * 4) * 2)) + chunk(b'IEND', b'')
        self.image = self.path / 'figure.png'; self.image.write_bytes(self.png)
        self.spec = {'type': 'image', 'path': str(self.image), 'alt': 'Synthetic wide figure',
                     'source': {'reference': 'SYNTHETIC_SOURCE_IN_NOTES', 'revision': 'fixture-v1'}}
        self.request = ppt.read(REPO / 'examples/project-request.json')
        self.request['state_dir'] = str(self.path / 'state')
        self.slide = self.request['deck']['slides'][0]
        self.slide['panels'] = [{'title': '原图', 'blocks': [self.spec]}]

    def tearDown(self): self.temp.cleanup()

    def test_original_bytes_survive_without_external_file_or_visible_source(self):
        result = ppt.render(self.request, self.path / 'output')
        self.image.unlink()
        document = Path(result['html']).read_text(encoding='utf-8')
        visible = document.split('<script type="application/json" id="deck-model">')[0]
        parser = Images(); parser.feed(visible)
        image = next(x for x in parser.items if x.get('alt') == self.spec['alt'])
        self.assertTrue(image['src'].startswith('data:image/png;base64,'))
        self.assertEqual(base64.b64decode(image['src'].split(',')[1]), self.png)
        self.assertEqual(image['data-source-sha256'], hashlib.sha256(self.png).hexdigest())
        self.assertNotIn('SYNTHETIC_SOURCE_IN_NOTES', visible)
        self.assertIn('object-fit:contain', document)
        saved = ppt.read(result['deck'])
        self.assertEqual(saved['slides'][0]['panels'][0]['blocks'][0]['source'], self.spec['source'])
        self.assertEqual(list((self.path / 'output/diagrams').glob('*')), [])

    def test_portfolio_accepts_original_instead_of_a_drawn_diagram(self):
        self.slide.clear()
        self.slide.update({'title': '项目原图', 'layout': 'project-portfolio', 'targets': ['完成原图复用'],
                           'milestones': [{'label': '原图检查', 'date': '演示', 'current': True}],
                           'topics': [{'name': '专题', 'image': self.spec, 'summary': '本地原图完整嵌入。',
                                       'progress_columns': [[{'name': '验证', 'text': '演示数据。'}]]}]})
        self.assertTrue(ppt.validate(self.request['deck'])['ok'])
        result = ppt.render(self.request, self.path / 'portfolio')
        self.assertIn('data:image/png;base64,', Path(result['html']).read_text(encoding='utf-8'))
        self.assertEqual(list((self.path / 'portfolio/diagrams').glob('*')), [])
        self.slide['topics'][0]['diagram'] = {'width': 1, 'height': 1, 'elements': []}
        self.assertFalse(ppt.validate(self.request['deck'])['ok'])

    def test_invalid_paths_missing_provenance_and_unsupported_files_are_rejected(self):
        for replacement in ({'path': 'https://example.invalid/image.png'}, {'path': 'relative.png'},
                            {'path': str(self.path / 'missing.png')}, {'source': {}}, {'alt': ''}):
            with self.subTest(replacement=replacement):
                original = copy.deepcopy(self.spec)
                self.spec.update(replacement)
                self.assertFalse(ppt.validate(self.request['deck'])['ok'])
                self.spec.clear(); self.spec.update(original)
        self.image.write_text('<svg onload="alert(1)"></svg>', encoding='utf-8')
        self.assertFalse(ppt.validate(self.request['deck'])['ok'])

    def test_source_figure_layout_routing_and_required_content(self):
        for kind in ('figure-overview', 'figure-evidence', 'figure-full'):
            with self.subTest(kind=kind):
                request = copy.deepcopy(self.request)
                slide = request['deck']['slides'][0]
                slide.pop('layout', None)
                slide['page_kind'] = kind
                if kind != 'figure-full':
                    slide['panels'].append({'title': '实现分析', 'blocks': [{'type': 'text', 'text': 'Synthetic analysis.'}]})
                deck = ppt.resolved_deck(request, ppt.plan(request))
                self.assertEqual(deck['slides'][0]['layout'], 'project-' + kind)
                self.assertTrue(ppt.validate(deck)['ok'])
                result = ppt.render(request, self.path / kind)
                self.assertIn('source-lightbox', Path(result['html']).read_text(encoding='utf-8'))
                deck['slides'][0]['panels'][0]['blocks'] = [{'type': 'text', 'text': 'No image'}]
                self.assertFalse(ppt.validate(deck)['ok'])

    def test_project_zoom_assets_do_not_change_insight_routing(self):
        request = ppt.read(REPO / 'examples/insight-request.json')
        request['state_dir'] = str(self.path / 'state')
        result = ppt.render(request, self.path / 'insight')
        self.assertNotIn('source-lightbox', Path(result['html']).read_text(encoding='utf-8'))
        request['deck']['slides'][0]['layout'] = 'project-figure-full'
        self.assertFalse(ppt.validate(request['deck'])['ok'])


if __name__ == '__main__': unittest.main()
