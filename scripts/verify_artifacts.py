"""Read-only XLSX feature/content verification (no workbook authoring)."""
from pathlib import Path
import json
import math
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'excel/RevPulse_Validation_Audit.xlsx'
formulas=openpyxl.load_workbook(path,data_only=False)
values=openpyxl.load_workbook(path,data_only=True)
checks={}
checks['two_native_pivots']=len(formulas['Audit_Pivots']._pivots)==2
checks['xlookup_enrichment']='XLOOKUP' in formulas['Cleaned_Master']['I2'].value
checks['data_validation']=len(formulas['Cleaned_Master'].data_validations.dataValidation)==2
checks['conditional_formatting']=len(formulas['Cleaned_Master'].conditional_formatting)>0
checks['frozen_headers']=formulas['Cleaned_Master'].freeze_panes=='A2'
diffs={cell:values['Reconciliation'][cell].value for cell in ['E5','E6','E7','E8','E13','E14','E15']}
checks['sql_reconciliation']=all(isinstance(v,(float,int)) and abs(v)<.005 for v in diffs.values())
errors=[]
for sheet in values:
    for row in sheet:
        for cell in row:
            if cell.data_type=='e':errors.append(f'{sheet.title}!{cell.coordinate}: {cell.value}')
checks['no_cached_formula_errors']=not errors
with ZipFile(path) as z:
    for filename in z.namelist():
        if filename.endswith('.xml') or filename.endswith('.rels'):ET.fromstring(z.read(filename))
checks['xml_well_formed']=True
report={'checks':checks,'reconciliation_differences':diffs,'errors':errors,'native_excel_edit_refresh':'Deferred by user: Office is unlicensed. Cached results and file structure are verified; these do not establish native recalculation.'}
(ROOT/'reports/workbook/verification.json').write_text(json.dumps(report,indent=2))
if not all(checks.values()):raise RuntimeError(report)
print(json.dumps(report,indent=2))
