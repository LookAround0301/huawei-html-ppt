"""Adapter contracts; optional real dependency tests require INFRA_IO_ROOT."""
from pathlib import Path
import copy
import json
import os
import sys
import tempfile
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/huawei-html-ppt/scripts'))
import diagram_adapter as bridge
import ppt


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def svg(self, body):
        path=self.path/'test.svg';path.write_text(body);return path
    def test_host_only_depends_on_adapter_contract(self):
        host=(ROOT/'skills/huawei-html-ppt/scripts/ppt.py').read_text()
        renderer=(ROOT/'skills/huawei-html-ppt/scripts/render_style_deck.py').read_text()
        for text in (host,renderer):
            for implementation_detail in ('technical-architecture-diagrams','technical-diagram-options',bridge.PIN,'select_options.py','diagram_tool.py','export.mjs'):
                self.assertNotIn(implementation_detail,text)
        self.assertEqual(bridge.tool_contract()['api_version'],1)
        self.assertEqual(bridge.tool_contract()['dependency']['commit'],bridge.PIN)
    def test_plain_default_both_branches(self):
        for intent in ('model','report'):
            p=bridge.plan({'intent':intent})
            self.assertEqual(p['palette'],'huawei-plain');self.assertEqual(p['status'],'planned_not_rendered')
        self.assertNotEqual(bridge.plan({'intent':'model'})['package'],bridge.plan({'intent':'report'})['package'])
    def test_unknown_and_mixed_intent_do_not_guess(self):
        for intent in ('mixed','auto','Kimi',None):
            with self.assertRaises(ValueError):bridge.plan({'intent':intent})
    def test_explicit_palette(self):
        self.assertEqual(bridge.plan({'intent':'model','palette':'blue-neutral'})['palette'],'blue-neutral')
        with self.assertRaises(ValueError):bridge.plan({'intent':'report','palette':'unknown'})
    def test_invalid_theme(self):
        for value in ({'accent':'red'},{'accent':'#000;}'},{'other':'#FFFFFF'},'blue'):
            with self.assertRaises(ValueError):bridge.theme(value)
    def test_theme_shared_with_formal_style(self):
        css=bridge.theme_css({'accent':'#336699','background':'#FDFDFD'})
        for token in ('--brand:#336699','--pr-red:#336699','.project-report.slide','background:#FDFDFD'):
            self.assertIn(token,css)
    def test_override_precedence(self):
        req={'intent':'report','theme':{'accent':'#336699'},'custom_tokens':{'accent':{'primary':'#222222'}}}
        self.assertEqual(bridge.palette_overrides(req,bridge.plan(req))['accent']['primary'],'#222222')
    def test_report_palette_preserves_semantics_and_geometry(self):
        doc={'semantic':{'facts':[{'id':'f'}]},'views':[{'canvas':{'width':100,'height':100},'glyphs':[{'id':'g','x':3,'palette_role':'state'}],'paths':[{'id':'p','points':[[1,2],[3,4]]}]}]}
        tokens={'background':{'canvas':'#FFFFFF','panel':'#EEEEEE'},'line':{'default':'#555555','strong':'#333333'},'accent':{'primary':'#C00000'},'text':{'primary':'#111111'},'state':{'fill':'#EEEEEE','stroke':'#777777'}}
        actual=bridge.report_palette(doc,tokens)
        self.assertEqual(actual['semantic'],doc['semantic']);self.assertEqual(actual['views'][0]['glyphs'][0]['x'],3)
        self.assertEqual(actual['views'][0]['paths'][0]['points'],[[1,2],[3,4]])
        self.assertNotIn('style',doc['views'][0]['glyphs'][0])
    def test_layout_contract_is_forwarded_not_reimplemented(self):
        rule={'id':'future-external-rule','priority':'new-value','nested':{'untouched':True}}
        self.assertEqual(bridge.route_layout_preferences({'parts':[{'layout_preference':rule}]}),[rule])
        for bad in ({}, {'parts':[]}, {'parts':[{}]}):
            with self.assertRaises(ValueError):bridge.route_layout_preferences(bad)
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(bridge.plan({'intent':'model'})['layout_guidance_status'],'requires_pinned_dependency')
    @unittest.skipUnless(os.environ.get('INFRA_IO_ROOT'),'optional pinned external dependency not configured')
    def test_actual_plan_forwards_external_layout_preference(self):
        model=bridge.plan({'intent':'model'}); report=bridge.plan({'intent':'report'})
        self.assertEqual(model['layout_preferences'][0]['id'],'vertical-backbone-side-detail')
        self.assertEqual(model['layout_preferences'][0]['priority'],'preferred_not_mandatory')
        self.assertEqual(report['layout_preferences'][0]['id'],'task-appropriate')
        self.assertEqual(model['layout_guidance_status'],'from_pinned_skill')
    def test_explicit_tikz_backend(self):
        plan=bridge.plan({'intent':'model','model_backend':'tikz'})
        self.assertEqual(plan['model_backend'],'tikz')
        self.assertIn('tex: reviewed native source',plan['required_inputs'])
        with self.assertRaises(ValueError):bridge.plan({'intent':'report','model_backend':'tikz'})
        with self.assertRaises(ValueError):bridge.plan({'intent':'model','model_backend':'shell'})
    def test_tex_source_and_theme_binding(self):
        source=self.path/'a.drawio';source.write_text('<mxGraphModel/>');tex=self.path/'a.tex';tex.write_text('reviewed native source')
        req={'intent':'model','model_backend':'tikz'};chosen=bridge.plan(req)
        manifest={'source_master_sha256':bridge.sha(source),'native_tex_sha256':bridge.sha(tex),'theme_tokens':chosen['theme'],'palette':chosen['palette'],'custom_tokens':{},'page':0,'language_profile':chosen['language_profile'],'source_review':{'reviewer':'agent','result':'pass','rationale':'Checked authored synthetic topology'}}
        bridge.checked_tex_manifest(manifest,source,tex,req,chosen)
        for key,value in [('source_master_sha256','bad'),('native_tex_sha256','bad'),('theme_tokens',{}),('language_profile','old'),('source_review',{})]:
            changed=dict(manifest);changed[key]=value
            with self.assertRaises(ValueError):bridge.checked_tex_manifest(changed,source,tex,req,chosen)
    def synthetic_tikz_render(self, suffix='.drawio'):
        """Exercise adapter evidence only; never compile TeX or launch a browser."""
        source=self.path/('source'+suffix)
        source.write_text('<mxGraphModel><root><mxCell id="n" value="A" text_role="node_label"/></root></mxGraphModel>')
        tex=self.path/'source.tex';tex.write_text('Synthetic adapter fixture; not compilable TeX.')
        color_map=self.path/'map.json';color_map.write_text('{}')
        manifest_path=self.path/'review.json';output=self.path/'output'
        req={'intent':'model','model_backend':'tikz','input':str(source),'color_map':str(color_map),
             'tex':str(tex),'tex_manifest':str(manifest_path),'trusted_tex':True}
        chosen=bridge.plan(req)
        bridge.save(manifest_path,{'source_master_sha256':bridge.sha(source),'native_tex_sha256':bridge.sha(tex),
            'source_color_map_sha256':bridge.sha(color_map),'theme_tokens':chosen['theme'],
            'palette':chosen['palette'],'custom_tokens':{},'page':0,'language_profile':chosen['language_profile'],
            'source_review':{'reviewer':'agent','result':'pass','rationale':'Synthetic adapter regression, not real source approval.'}})
        def fake_run(command, **kwargs):
            script=Path(command[1]).name
            arg=lambda flag:Path(command[command.index(flag)+1])
            if script=='resolve_palette.py':
                bridge.save(arg('--output'),{'tokens':bridge.palette_overrides(req,chosen)})
            elif script=='route_request.py':
                bridge.save(arg('--output'),{'parts':[{'layout_preference':{'id':'synthetic-preference'}}]})
            elif script=='apply_palette.py':
                arg('--output').write_bytes(Path(command[2]).read_bytes())
            elif script=='check_language.py':
                bridge.save(arg('--output'),{'profile':chosen['language_profile'],
                    'input_sha256':bridge.sha(arg('--input')),'status':'needs_review',
                    'contract_status':'pass','semantic_review':'not_run','errors':[]})
            elif script=='render_model_tikz.py':
                artifacts=arg('--out-dir');artifacts.mkdir()
                (artifacts/'figure.tex').write_bytes(arg('--input').read_bytes())
                for name,content in [('figure.svg','<svg/>'),('figure.pdf','synthetic fixture'),
                                     ('figure.png','synthetic fixture'),('render-qa.json','{}')]:
                    (artifacts/name).write_text(content)
            return CompletedProcess(command,0,'','')
        with patch.object(bridge,'dependency',return_value=self.path/'dependency'), \
                patch.object(bridge.subprocess,'run',side_effect=fake_run):
            result=bridge.render(req,output)
        return result,output
    def test_tikz_uppercase_source_extension_roundtrips(self):
        result,output=self.synthetic_tikz_render('.DRAWIO')
        self.assertTrue((output/'authored.drawio').is_file())
        self.assertFalse((output/'authored.DRAWIO').exists())
        bridge.read_generated(result['blocks'][0])
    def test_tikz_nonobject_review_fails_cleanly(self):
        result,output=self.synthetic_tikz_render()
        review=output/'tex-source-review.json';review.write_text('[]')
        evidence=bridge.read(output/'invocation.json')
        evidence['tex_source_review']['sha256']=bridge.sha(review)
        bridge.save(output/'invocation.json',evidence)
        with self.assertRaisesRegex(ValueError,'TeX source review must be an object'):
            bridge.read_generated(result['blocks'][0])
    def test_svg_local_use_is_nonrecursive(self):
        bridge.checked_svg(self.svg('<svg><defs><g id="glyph"><path/></g></defs><use href="#glyph"/></svg>'))
        for body in ('<svg><use href="https://example.org/glyph"/></svg>','<svg><use href="#missing"/></svg>','<svg><g id="loop"><use href="#loop"/></g><use href="#loop"/></svg>','<svg><g id="a"><use href="#a"/></g><path id="a"/><use href="#a"/></svg>'):
            with self.assertRaises(ValueError):bridge.checked_svg(self.svg(body))
    def test_svg_local_fragment(self):
        bridge.checked_svg(self.svg('<svg xmlns="http://www.w3.org/2000/svg"><path marker-end="url(&quot;#a&quot;)"/></svg>'))
    def test_svg_active_and_external_rejected(self):
        for body in ('<script/>','<animateTransform/>','<foreignObject/>','<image href="https://example.org/a.png"/>','<path onclick="x()"/>','<path fill="url(https://example.org/a)"/>','<path style="fill:u\\72l(https://example.org/a)"/>','<path fill="url(&#10;https://example.org/a)"/>'):
            with self.assertRaises(ValueError):bridge.checked_svg(self.svg('<svg>'+body+'</svg>'))
    def test_svg_processing_instructions_and_entities(self):
        for body in ('<?xml-stylesheet href="https://example.org/a"?><svg/>','<!DOCTYPE svg><svg/>','<svg>'):
            with self.assertRaises(ValueError):bridge.checked_svg(self.svg(body))
    def test_drawio_external_resource_rejected(self):
        for attr in ('style="image=https://example.org/a"','link="https://example.org"','value="&lt;img src=x&gt;"'):
            path=self.path/'a.drawio';path.write_text('<mxGraphModel><root><mxCell '+attr+'/></root></mxGraphModel>')
            with self.assertRaises(ValueError):bridge.checked_drawio(path)
    def test_utf16_and_bad_manifest(self):
        path=self.path/'test.svg';path.write_bytes('<?xml version="1.0" encoding="utf-16"?><!DOCTYPE svg><svg/>'.encode('utf-16'))
        with self.assertRaises(ValueError):bridge.checked_svg(path)
        for encoding in ('utf-16-le','utf-16-be'):
            path.write_bytes('<?xml-stylesheet href="https://example.org"?><svg/>'.encode(encoding))
            with self.assertRaises(ValueError):bridge.checked_svg(path)
        path.write_text('<svg/>');inv=self.path/'invocation.json';inv.write_text('[]')
        with self.assertRaises(ValueError):bridge.read_generated({'path':str(path),'invocation':str(inv),'alt':'test'})
    def test_selected_model_page(self):
        path=self.path/'test.drawio';out=self.path/'selected.drawio'
        path.write_text('<mxfile><diagram><mxGraphModel pageWidth="100"><root/></mxGraphModel></diagram><diagram><mxGraphModel pageWidth="200"><root/></mxGraphModel></diagram></mxfile>')
        bridge.select_model_page(path,out,1);self.assertIn('pageWidth="200"',out.read_text())
        for page in (-1,True,2,'0'):
            with self.assertRaises(ValueError):bridge.select_model_page(path,out,page)
    def test_language_qa_is_bound_and_not_semantic_approval(self):
        source=self.path/'source.json';source.write_text('{}');path=self.path/'qa.json'
        qa={'profile':bridge.LOCK['language_profile'],'input_sha256':bridge.sha(source),'status':'needs_review','contract_status':'pass','semantic_review':'not_run','errors':[]}
        path.write_text(json.dumps(qa));self.assertEqual(bridge.checked_language_qa(path,source,bridge.LOCK['language_profile'])['status'],'needs_review')
        for key,value in [('input_sha256','wrong'),('profile','old'),('status','pass'),('contract_status','fail'),('semantic_review','passed'),('errors',None),('errors',{}),('errors',''),('errors',False)]:
            changed=dict(qa);changed[key]=value;path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):bridge.checked_language_qa(path,source,bridge.LOCK['language_profile'])
    def test_plan_requires_current_language_profile(self):
        self.assertEqual(bridge.plan({'intent':'report'})['language_profile'],bridge.LOCK['language_profile'])
        with self.assertRaises(ValueError):bridge.plan({'intent':'report','language_profile':'old-policy'})
    def test_missing_evidence(self):
        path=self.svg('<svg/>');inv=self.path/'invocation.json';inv.write_text('{}')
        with self.assertRaises(ValueError):bridge.read_generated({'path':str(path),'invocation':str(inv),'alt':'test'})
    def test_evidence_hash_and_failure(self):
        path=self.svg('<svg/>');inv=self.path/'invocation.json'
        ev={'schema_version':2,'status':'rendered','intent':'model','target':'ppt','package':'technical-architecture-diagrams','dependency':{'commit':bridge.PIN,'repository':bridge.REPOSITORY},'calls':[{'tool':'skills/technical-architecture-diagrams/scripts/'+file,'operation':op,'status':'ok','returncode':0} for file,op in [('resolve_palette.py','resolve-palette'),('route_request.py','route'),('apply_palette.py','apply-model-palette'),('check_language.py','check-language'),('drawio_runtime/export.mjs','render-model')]], 'artifacts':[{'path':'test.svg','sha256':bridge.sha(path)}]}
        source=self.path/'prepared.drawio';source.write_text('<mxGraphModel/>')
        qa=self.path/'language-qa.json';qa.write_text(json.dumps({'profile':bridge.LOCK['language_profile'],'input_sha256':bridge.sha(source),'status':'needs_review','contract_status':'pass','semantic_review':'not_run','errors':[]}))
        ev['language_profile']=bridge.LOCK['language_profile'];ev['language_qa']={'path':qa.name,'sha256':bridge.sha(qa),'input_path':source.name,'input_sha256':bridge.sha(source),'status':'needs_review','contract_status':'pass','semantic_review':'not_run'}
        inv.write_text(json.dumps(ev));bridge.read_generated({'path':str(path),'invocation':str(inv),'alt':'test'})
        path.write_text('<svg><rect/></svg>')
        with self.assertRaises(ValueError):bridge.read_generated({'path':str(path),'invocation':str(inv),'alt':'test'})
        ev['status']='failed';inv.write_text(json.dumps(ev))
        with self.assertRaises(ValueError):bridge.read_generated({'path':str(path),'invocation':str(inv),'alt':'test'})
    def test_plan_exposes_tools(self):
        req=ppt.read(ROOT/'examples/insight-request.json');req['state_dir']=str(self.path/'state')
        self.assertEqual(ppt.plan(req)['diagram_tools']['render'],'diagram-render')
    @unittest.skipUnless(os.environ.get('INFRA_IO_ROOT'),'optional pinned external dependency not configured')
    def test_actual_report_calls_and_html_embedding(self):
        root=Path(os.environ['INFRA_IO_ROOT']);req={'intent':'report','input':str(root/'skills/technical-diagram-options/examples/toy-mapping.language.diagram.json'),'task':str(root/'skills/technical-diagram-options/examples/toy-mapping.task.json')}
        result=bridge.render(req,self.path/'diagram');ev=bridge.read(result['invocation'])
        self.assertEqual(len(ev['calls']),6);self.assertTrue(all(x['returncode']==0 for x in ev['calls']))
        request=ppt.read(ROOT/'examples/insight-request.json');request['state_dir']=str(self.path/'state')
        request['deck']['slides']=request['deck']['slides'][:1]
        request['deck']['slides'][0]['panels']=[{'title':'Generated diagram','blocks':result['blocks']}]
        html=Path(ppt.render(request,self.path/'deck')['html']).read_text()
        self.assertIn('data:image/svg+xml;base64,',html)
        request['deck']['theme']=None
        ppt.render(request,self.path/'null-theme')
        request['deck']['theme']={'accent':'#336699'}
        with self.assertRaises(ValueError):ppt.render(request,self.path/'wrong-theme')
        with self.assertRaises(ValueError):bridge.render(req,self.path/'diagram')

if __name__=='__main__':unittest.main()
