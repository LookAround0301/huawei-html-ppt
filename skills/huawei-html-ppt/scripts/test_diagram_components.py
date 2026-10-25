"""Behavior tests with synthetic inputs; these do not claim visual acceptance."""
import copy
import sys
import unittest
import tempfile
import re
from pathlib import Path
sys.dont_write_bytecode=True
from diagram_components import Diagram
from diagram_audit import audit

class ComponentTests(unittest.TestCase):
    def moe(self):
        d=Diagram('Synthetic MoE')
        p=d.use('moe-routing','m',10,30,800,230,hidden=2048,intermediate=1024,experts=32,top_k=2,shared=1)
        d.contract('mechanism',paths=[[p['input'],p['experts'],p['output']],[p['input'],p['shared'],p['output']]])
        return d

    def test_component_replay_and_two_actual_branches(self):
        self.assertTrue(audit(self.moe().data,True)['ok'])

    def test_missing_shared_path_fails_even_if_boxes_remain(self):
        d=self.moe().data
        d['graph']['edges']=[e for e in d['graph']['edges'] if e['source']!='m.shared']
        self.assertFalse(audit(d,True)['ok'])

    def test_manual_geometry_cannot_pass_as_component_reuse(self):
        d=self.moe().data;d['elements'][0]['x']+=2
        self.assertFalse(audit(d,True)['ok'])

    def test_later_parameter_edits_invalidate_generated_geometry(self):
        d=self.moe().data;d['graph']['uses'][0]['params']['top_k']=3
        self.assertFalse(audit(d,True)['ok'])

    def test_cache_needs_both_read_and_write(self):
        d=Diagram('Synthetic cache')
        p=d.use('pooled-sparse-attention','s',0,0,740,324,pool=2,top_k=512,index_dim=64,cache_label='Demo cache')
        d.contract('mechanism',paths=[[p['input'],p['main'],p['attn']]])
        self.assertTrue(audit(d.data,True)['ok'])
        d.data['graph']['edges']=[e for e in d.data['graph']['edges'] if e['source']!='s.main']
        self.assertFalse(audit(d.data,True)['ok'])

    def test_declared_zoom_needs_a_visible_connection(self):
        d=self.moe();d.frame('detail',840,30,260,250,'Demo')
        d.contract('mechanism',zooms=[['m.experts','detail']])
        self.assertFalse(audit(d.data,True)['ok'])
        d.connect('m.experts','detail',kind='zoom')
        self.assertTrue(audit(d.data,True)['ok'])

    def test_residual_matrix_receives_all_streams(self):
        d=Diagram('Synthetic residual')
        p=d.use('mhc-mixer','h',0,0,980,374,streams=4,hidden=2048)
        d.contract('mechanism',paths=[[p[f'x{i}'],p['res'],p['output']] for i in range(4)])
        self.assertTrue(audit(d.data,True)['ok'])

    def test_memory_remaining_is_not_claimed_available(self):
        d=Diagram('Synthetic capacity')
        d.use('memory-budget','b',0,0,420,88,title='Demo only',capacity=64,segments=[{'label':'weight','gib':30}],unresolved=['workspace'])
        self.assertEqual(d.data['graph']['nodes']['b.budget']['known_total'],30)
        self.assertIn('未必可用',str(d.data))

    def transfer(self):
        d=Diagram('Synthetic state transfer')
        p=d.use('pd-state-transfer','pd',0,0,880,260,
                p={'nodes':2,'cards_per_node':2,'ranks_per_node':4,'parallel':'PP2 / TP4'},
                d={'nodes':3,'cards_per_node':2,'ranks_per_node':4,'parallel':'DP3 / TP4'},
                states=['主缓存','递归状态'])
        d.contract('mechanism',paths=[[p['p'],p['states'],p['d']]])
        return d

    def test_pd_transfer_counts_physical_cards_separately(self):
        d=self.transfer()
        self.assertTrue(audit(d.data,True)['ok'])
        self.assertEqual(d.data['graph']['nodes']['pd.p']['devices'],{'nodes':2,'physical_cards':4,'ranks':8})
        self.assertEqual(d.data['graph']['nodes']['pd.d']['devices'],{'nodes':3,'physical_cards':6,'ranks':12})

    def test_pd_transfer_requires_complete_state_handoff(self):
        d=self.transfer().data
        d['graph']['edges']=[e for e in d['graph']['edges'] if e['target']!='pd.d']
        self.assertFalse(audit(d,True)['ok'])

    def test_pd_transfer_rejects_unknown_or_invalid_counts_and_empty_states(self):
        valid={'nodes':2,'cards_per_node':2,'ranks_per_node':4,'parallel':'PP2 / TP4'}
        for field,value in [('nodes',0),('cards_per_node',True),('ranks_per_node',1.5)]:
            bad={**valid,field:value}
            with self.assertRaises(ValueError):
                Diagram('Bad counts').use('pd-state-transfer','pd',0,0,880,260,p=bad,d=valid,states=['状态'])
        with self.assertRaises(ValueError):
            Diagram('No states').use('pd-state-transfer','pd',0,0,880,260,p=valid,d=valid,states=[])

    def test_contract_required_only_for_new_reports(self):
        legacy={'title':'Old','width':100,'height':100,'elements':[]}
        self.assertTrue(audit(legacy)['ok'])
        self.assertFalse(audit(legacy,True)['ok'])

    def test_repeated_diagrams_have_local_arrow_markers(self):
        import ppt
        diagram=self.moe().data
        slide={'title':'Demo','layout':'insight-mechanism','conclusion':'Synthetic geometry test',
               'panels':[{'title':'Demo','blocks':[{'type':'diagram','data':diagram},{'type':'diagram','data':copy.deepcopy(diagram)}]}]}
        with tempfile.TemporaryDirectory() as folder:
            result=ppt.render({'style':'insight-analysis','state_dir':str(Path(folder)/'state'),
              'deck':{'title':'Demo','style':'insight-analysis','slides':[slide,copy.deepcopy(slide)]}},Path(folder)/'out')
            text=Path(result['html']).read_text(encoding='utf-8')
            definitions=re.findall(r'<marker id="([^"]+)"',text)
            refs=re.findall(r'marker-end="url\(#([^\)]+)\)"',text)
            self.assertEqual(len(definitions),len(set(definitions)))
            self.assertTrue(set(refs)<=set(definitions))

if __name__=='__main__':unittest.main()
