"""Public regression tests use synthetic data only; no visual-acceptance claims."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest
from xml.etree import ElementTree

sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'skills/huawei-html-ppt/scripts'))
import ppt
import route_request
import check_package


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ppt-runtime-test-')
        self.path=Path(self.temp.name)
        self.insight=ppt.read(REPO/'examples/insight-request.json')
        self.project=ppt.read(REPO/'examples/project-request.json')
        for request in (self.insight,self.project):request['state_dir']=str(self.path/'state')

    def tearDown(self):self.temp.cleanup()

    def test_route_purpose_and_explicit_style(self):
        self.assertEqual(route_request.route('PCP/DCP 原理分享')['style'],'insight-analysis')
        self.assertEqual(route_request.route('PCP/DCP 技术项目 PDCP 进展评审')['style'],'technical-project')
        self.assertEqual(route_request.route('PDCP',explicit='insight-analysis')['style'],'insight-analysis')
        self.assertEqual(route_request.route('模型分析',purpose='approval')['style'],'technical-project')
        self.assertIsNone(route_request.route('做一份PPT')['style'])

    def test_style_conflict_fails(self):
        self.insight['style']='technical-project'
        with self.assertRaises(ValueError):ppt.plan(self.insight)

    def test_examples_render_and_notes_stay_hidden(self):
        for key,request in [('insight',self.insight),('project',self.project)]:
            marker='SYNTHETIC_NOTE_NOT_VISIBLE'
            request['deck']['slides'][0]['notes']={'private_note':marker}
            result=ppt.render(request,self.path/key)
            text=Path(result['html']).read_text(encoding='utf-8')
            visible=text.split('<script type="application/json" id="deck-model">')[0]
            self.assertNotIn(marker,visible)
            self.assertIn(marker,text)
            self.assertEqual(ppt.read(result['deck'])['slides'],request['deck']['slides'])
            self.assertIn('viewer-toolbar',text)

    def test_required_conclusion_and_table_shape(self):
        deck=copy.deepcopy(self.insight['deck']);deck['slides'][0]['conclusion']=''
        self.assertFalse(ppt.validate(deck)['ok'])
        deck=copy.deepcopy(self.insight['deck'])
        deck['slides'][0]['panels'][0]['blocks'][0]['rows'][0].append('extra')
        self.assertFalse(ppt.validate(deck)['ok'])

    def test_safe_output_name(self):
        self.insight['deck']['title']='../escape'
        with self.assertRaises(ValueError):ppt.render(self.insight,self.path/'output')

    def test_panel_widths_control_columns_and_reject_invalid_values(self):
        slide=self.insight['deck']['slides'][0]
        slide['panels']=[copy.deepcopy(slide['panels'][0]) for _ in range(2)]
        slide['panel_widths']=[1.5,1]
        self.assertTrue(ppt.validate(self.insight['deck'])['ok'])
        result=ppt.render(self.insight,self.path/'widths')
        self.assertIn('grid-template-columns:1.5fr 1fr',Path(result['html']).read_text(encoding='utf-8'))
        for widths in ([1], [0,1], [-1,1], [True,1], [float('nan'),1],
                       [float('inf'),1], '1 1', ['1',1]):
            with self.subTest(widths=widths):
                slide['panel_widths']=widths
                self.assertFalse(ppt.validate(self.insight['deck'])['ok'])

    def test_diagram_outputs_share_geometry(self):
        component=ppt.read(REPO/'skills/huawei-html-ppt/assets/units/cache-state-lanes.json')['diagram']
        slide=self.insight['deck']['slides'][0]
        slide['layout']='insight-mechanism'
        slide['panels']=[{'title':'图形接口测试','blocks':[{'type':'diagram','data':component}]}]
        ppt.render(self.insight,self.path/'diagram')
        svg=ElementTree.parse(self.path/'diagram/diagrams/01-1.svg').getroot()
        drawio=ElementTree.parse(self.path/'diagram/diagrams/01-1.drawio').getroot()
        self.assertEqual(svg.get('viewBox'),f"0 0 {component['width']} {component['height']}")
        self.assertEqual(len(drawio.findall('.//mxCell')),len(component['elements'])+2)

    def test_chart_numeric_axis_requires_order(self):
        self.insight['deck']['slides'][0]['panels']=[{'title':'趋势','blocks':[{'type':'chart','data':{
            'kind':'line','x':[1,4,2],'series':[{'name':'demo','values':[2,4,3]}]}}]}]
        self.assertFalse(ppt.validate(self.insight['deck'])['ok'])
        self.insight['deck']['slides'][0]['panels'][0]['blocks'][0]['data']['x']=[1,2,4]
        self.assertTrue(ppt.validate(self.insight['deck'])['ok'])

    def candidate(self):
        unit={'id':'test.preference','revision':1,'kind':'preference','styles':['insight-analysis'],
              'when':{'scenario':'demo'},'rule':{'guidance':'Synthetic test rule; scoped to the demo only.'},'provenance':[]}
        req={'state_dir':str(self.path/'state'),'task_state':'completed','base_revision':0,'unit':unit,
             'evidence':[{'kind':'user-feedback','text':'Synthetic unit-test fixture; not a real user instruction.'}]}
        return req

    def test_ungrounded_and_running_feedback_rejected(self):
        req=self.candidate();req['evidence']=[]
        with self.assertRaises(ValueError):ppt.feedback(req)
        req=self.candidate();req['task_state']='running'
        with self.assertRaises(ValueError):ppt.feedback(req)

    def test_candidate_isolation_promotion_and_rollback(self):
        req=self.candidate();cid=ppt.feedback(req)['candidate_id']
        self.assertNotIn('test.preference@1',ppt.plan(self.insight)['unit_refs'])
        action={'state_dir':req['state_dir'],'candidate_id':cid}
        with self.assertRaises(ValueError):ppt.promote(action)
        case=self.path/'case.json';ppt.save(case,self.insight)
        ppt.evaluate({**action,'cases':[str(case)],'output_dir':str(self.path/'evaluation')})
        with self.assertRaises(ValueError):ppt.review({**action,'reviewer':'agent','result':'pass',
            'visual_checked':False,'rationale':'No visual check.'})
        # Temporary protocol fixture, not evidence of real visual acceptance.
        ppt.review({**action,'reviewer':'agent','result':'pass','visual_checked':True,
                    'rationale':'Synthetic state-machine fixture only; does not certify visual quality.'})
        event=ppt.promote(action)
        self.assertIn('test.preference@1',ppt.plan(self.insight)['unit_refs'])
        self.project['style']='technical-project'
        self.assertNotIn('test.preference@1',ppt.plan(self.project)['unit_refs'])
        with self.assertRaises(ValueError):ppt.feedback(req)
        ppt.rollback({'state_dir':req['state_dir'],'event_id':event['event_id']})
        self.assertNotIn('test.preference@1',ppt.plan(self.insight)['unit_refs'])

    def test_modified_replay_invalidates_review(self):
        req=self.candidate();cid=ppt.feedback(req)['candidate_id']
        action={'state_dir':req['state_dir'],'candidate_id':cid}
        case=self.path/'case.json';ppt.save(case,self.insight)
        result=ppt.evaluate({**action,'cases':[str(case)],'output_dir':str(self.path/'evaluation')})
        Path(result['cases'][0]['html']).write_text('changed',encoding='utf-8')
        with self.assertRaises(ValueError):ppt.check_evaluation(ppt.load_state(req['state_dir'])['candidates'][cid])

    def test_portable_core(self):
        self.assertTrue(check_package.check()['ok'])


if __name__=='__main__':unittest.main()
