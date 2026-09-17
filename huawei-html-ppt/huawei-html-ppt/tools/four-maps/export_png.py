# -*- coding: utf-8 -*-
"""导出 PPTX 每页为 PNG: python export_png2.py <pptx> <outdir>"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import win32com.client

src = os.path.abspath(sys.argv[1])
outdir = os.path.abspath(sys.argv[2])
os.makedirs(outdir, exist_ok=True)
app = win32com.client.Dispatch('PowerPoint.Application')
pres = app.Presentations.Open(src, ReadOnly=True, WithWindow=False)
try:
    pres.Export(outdir, 'PNG', 1600, 900)
    print('exported:', sorted(os.listdir(outdir)))
finally:
    pres.Close()
