"""Add native OOXML PivotTables where the workbook authoring API lacks export support.

Only pivot parts/relationships are added. Existing cells, formulas and styles remain intact.
"""
from pathlib import Path
import json
from zipfile import ZipFile,ZIP_DEFLATED
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
ET.register_namespace('',NS);ET.register_namespace('r',REL)
def el(tag,attrs=None,parent=None):
    node=ET.Element('{'+NS+'}'+tag,{k:str(v) for k,v in (attrs or {}).items()})
    if parent is not None:parent.append(node)
    return node
def xml(node):return ET.tostring(node,encoding='utf-8',xml_declaration=True)

def main():
    target=ROOT/'excel/RevPulse_Validation_Audit.xlsx'
    data=json.loads((ROOT/'.local/artifact/workbook_input.json').read_text())
    with ZipFile(target) as z:parts={n:z.read(n) for n in z.namelist()}
    if 'xl/pivotTables/pivotTable1.xml' in parts:
        existing=ET.fromstring(parts['xl/pivotTables/pivotTable1.xml']).attrib.get('name')
        if existing=='RegionalInvoicing':
            print('RevPulse native PivotTables already packaged; rerun the workbook builder to refresh their inputs')
            return
        raise ValueError('Unexpected existing PivotTables; refusing to replace them')
    wb=ET.fromstring(parts['xl/workbook.xml']);rels=ET.fromstring(parts['xl/_rels/workbook.xml.rels']);types=ET.fromstring(parts['[Content_Types].xml'])
    sheets=wb.find('{'+NS+'}sheets');pivot_sheet_index=next(i+1 for i,s in enumerate(sheets) if s.attrib['name']=='Audit_Pivots')
    sheet_path=f'xl/worksheets/sheet{pivot_sheet_index}.xml';sheet=ET.fromstring(parts[sheet_path])
    pivot_caches=el('pivotCaches',parent=wb);pivot_parts=el('pivotParts',{'count':2},sheet)
    sheet_rels=ET.Element('{'+PKG+'}Relationships')
    customers={r[0]:r for r in data['customers']}
    invoice_rows=[[r[0],customers[r[1]][2],r[5]] for r in data['invoices']]
    payment_rows=[[r[0],r[2],r[3]] for r in data['delays']]
    # Cache source points to actual full tables, with shared strings matching source values.
    full_invoice=[r+[customers[r[1]][2],customers[r[1]][3]] for r in data['invoices']]
    specs=[('RegionalInvoicing','Cleaned_Master',full_invoice,['Invoice ID','Customer ID','Issue date','Due date','Plan','Amount INR','Outstanding INR','Days overdue','Region','Channel'],8,5,'B4:C9','sum','Invoiced INR'),
           ('PlanPaymentDelay','Payments',data['delays'],['Event ID','Invoice ID','Plan','Delay days'],2,3,'F4:G8','average','Average delay days')]
    for index,(name,source,rows,headers,row_field,value_field,location,subtotal,caption) in enumerate(specs,1):
        cache_id=index-1;rid=f'rIdRevPulseCache{index}'
        el('pivotCache',{'cacheId':cache_id,'{'+REL+'}id':rid},pivot_caches)
        ET.SubElement(rels,'{'+PKG+'}Relationship',{'Id':rid,'Type':REL+'/pivotCacheDefinition','Target':f'pivotCache/pivotCacheDefinition{index}.xml'})
        cache=el('pivotCacheDefinition',{'{'+REL+'}id':'rId1','recordCount':len(rows),'refreshOnLoad':0,'createdVersion':6,'refreshedVersion':6,'minRefreshableVersion':3})
        cs=el('cacheSource',{'type':'worksheet'},cache)
        last=chr(64+len(headers));el('worksheetSource',{'ref':f'A1:{last}{len(rows)+1}','sheet':source},cs)
        fields=el('cacheFields',{'count':len(headers)},cache);shared=[]
        for col,header in enumerate(headers):
            field=el('cacheField',{'name':header,'numFmtId':0},fields)
            values=list(dict.fromkeys(r[col] for r in rows));numeric=all(isinstance(v,(int,float)) for v in values)
            shared.append({v:i for i,v in enumerate(values)})
            items=el('sharedItems',{'count':len(values),'containsString':0 if numeric else 1,'containsNumber':1 if numeric else 0,'containsSemiMixedTypes':0},field)
            for value in values:el('n' if numeric else 's',{'v':value},items)
        records=el('pivotCacheRecords',{'count':len(rows)})
        for row in rows:
            record=el('r',parent=records)
            for col,value in enumerate(row):el('x',{'v':shared[col][value]},record)
        definition=el('pivotTableDefinition',{'name':name,'cacheId':cache_id,'dataCaption':'Values','rowGrandTotals':1,'colGrandTotals':1,'compact':0,'compactData':0,'gridDropZones':0,'createdVersion':6,'updatedVersion':6,'minRefreshableVersion':3})
        el('location',{'ref':location,'firstHeaderRow':1,'firstDataRow':1,'firstDataCol':1},definition)
        pfields=el('pivotFields',{'count':len(headers)},definition)
        categories=sorted(shared[row_field])
        for col in range(len(headers)):
            attrs={'showAll':0}
            if col==row_field:attrs.update(axis='axisRow',defaultSubtotal=0)
            if col==value_field:attrs['dataField']=1
            field=el('pivotField',attrs,pfields)
            if col==row_field:
                items=el('items',{'count':len(categories)+1},field)
                for category in categories:el('item',{'x':shared[col][category]},items)
                el('item',{'t':'default'},items)
        rf=el('rowFields',{'count':1},definition);el('field',{'x':row_field},rf)
        ri=el('rowItems',{'count':len(categories)+1},definition)
        for i in range(len(categories)):
            item=el('i',parent=ri);el('x',{'v':i},item)
        item=el('i',{'t':'grand'},ri);el('x',parent=item)
        ci=el('colItems',{'count':1},definition);item=el('i',parent=ci);el('x',parent=item)
        df=el('dataFields',{'count':1},definition);el('dataField',{'name':caption,'fld':value_field,'subtotal':subtotal,'baseField':0,'baseItem':0},df)
        el('pivotTableStyleInfo',{'name':'PivotStyleMedium9','showRowHeaders':1,'showColHeaders':1,'showRowStripes':0,'showColStripes':0,'showLastColumn':1},definition)
        parts[f'xl/pivotCache/pivotCacheDefinition{index}.xml']=xml(cache)
        parts[f'xl/pivotCache/pivotCacheRecords{index}.xml']=xml(records)
        cr=ET.Element('{'+PKG+'}Relationships');ET.SubElement(cr,'{'+PKG+'}Relationship',{'Id':'rId1','Type':REL+'/pivotCacheRecords','Target':f'pivotCacheRecords{index}.xml'})
        parts[f'xl/pivotCache/_rels/pivotCacheDefinition{index}.xml.rels']=xml(cr)
        parts[f'xl/pivotTables/pivotTable{index}.xml']=xml(definition)
        pr=ET.Element('{'+PKG+'}Relationships');ET.SubElement(pr,'{'+PKG+'}Relationship',{'Id':'rId1','Type':REL+'/pivotCacheDefinition','Target':f'../pivotCache/pivotCacheDefinition{index}.xml'})
        parts[f'xl/pivotTables/_rels/pivotTable{index}.xml.rels']=xml(pr)
        el('pivotPart',{'{'+REL+'}id':f'rIdPivot{index}'},pivot_parts)
        ET.SubElement(sheet_rels,'{'+PKG+'}Relationship',{'Id':f'rIdPivot{index}','Type':REL+'/pivotTable','Target':f'../pivotTables/pivotTable{index}.xml'})
        for folder,file,kind in [('pivotCache',f'pivotCacheDefinition{index}.xml','pivotCacheDefinition'),('pivotCache',f'pivotCacheRecords{index}.xml','pivotCacheRecords'),('pivotTables',f'pivotTable{index}.xml','pivotTable')]:
            ET.SubElement(types,'{'+CT+'}Override',{'PartName':f'/xl/{folder}/{file}','ContentType':f'application/vnd.openxmlformats-officedocument.spreadsheetml.{kind}+xml'})
    parts['xl/workbook.xml']=xml(wb);parts['xl/_rels/workbook.xml.rels']=xml(rels);parts['[Content_Types].xml']=xml(types);parts[sheet_path]=xml(sheet)
    parts[f'xl/worksheets/_rels/sheet{pivot_sheet_index}.xml.rels']=xml(sheet_rels)
    temporary=target.with_suffix('.tmp.xlsx')
    with ZipFile(temporary,'w',ZIP_DEFLATED) as z:
        for name,body in parts.items():z.writestr(name,body)
    temporary.replace(target)
    print('Added two native PivotTables with caches and source references')

if __name__=='__main__':main()
