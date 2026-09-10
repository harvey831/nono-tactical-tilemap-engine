from pathlib import Path
from pypdf import PdfReader
import csv,json,re,unicodedata,hashlib,collections
root=Path('study_radiographer')
rows=list(csv.DictReader((root/'sources/manifest_5years.csv').open(encoding='utf-8-sig')))
out=root/'index'; out.mkdir(exist_ok=True)
raw=root/'text'; raw.mkdir(exist_ok=True)
subjects={}
questions=[]; keys=[]; reports=[]; corrections=[]
rules={
 '核衰變與核種平衡':r'衰變|蛻變|正子|電子捕[捉獲]|母核|子核|secular|transient equilibrium',
 '半衰期與活度':r'半衰期|活度|活度|衰變常數|half.life|Bq|貝克|居里',
 '光子與物質交互作用':r'康普|光電效應|合調|成對|光分解|Compton|photoelectric|pair production',
 '衰減與屏蔽':r'衰減|半值層|什一值層|HVL|TVL|屏蔽|逆平方|反平方',
 'X光產生與能譜':r'制動輻射|特性輻射|特性X|鎢靶|陽極|陰極|X光管|X 光管|濾片|濾過|射質',
 '輻射量與劑量學':r'kerma|克馬|吸收劑量|等價劑量|有效劑量|曝露|曝露|游離腔|劑量計|cGy|Gy|侖琴',
 '偵檢器與計數統計':r'偵檢器|計數器|計數率|閃爍|光電倍增|蓋革|NaI|HPGe|FWHM|標準差|泊松|Poisson',
 '輻射防護與法規':r'防護|游離輻射|工作人員|管制區|主管機關|劑量限|ALARA|法第|規定|許可',
 '放射生物學':r'DNA|染色體|細胞存活|修復|氧效應|OER|RBE|LET|隨機效應|確定效應|輻射敏感|細胞週期',
 'CT原理與技術':r'\bCT\b|電腦斷層|Hounsfield|螺旋|pitch|CTDI',
 'MRI原理與技術':r'\bMRI?\b|磁振|磁共振|k.space|梯度|自旋|拉莫|Larmor|射頻|T1|T2|TR\b|TE\b',
 '超音波原理與技術':r'超音波|超聲|ultrasound|Doppler|都卜勒|音波|聲阻抗',
 '影像品質與數位影像':r'解析度|訊雜比|雜訊|像素|灰階|MTF|DQE|DICOM|PACS|傅立葉|矩陣|取樣|假影',
 '底片與影像接受器':r'底片|增感屏|顯影|CR\b|DR\b|平板偵檢|光密度|感光',
 '核醫PET':r'\bPET\b|正子斷層|互毀|符合|coincidence|FDG',
 '核醫SPECT與加馬攝影機':r'SPECT|加馬攝影|伽馬攝影|gamma camera|準直儀',
 '放射藥物與核種製備':r'放射藥|放射性藥|標記|迴旋|產生器|generator|Tc|I-123|I-131|99m|鍀',
 '核醫器官檢查':r'腎圖|腎臟閃爍|骨骼掃描|甲狀腺攝取|心肌灌注|肝膽|肺灌注|肺通氣',
 '放射治療計畫與劑量':r'PDD|TMR|SSD|IMRT|VMAT|MLC|治療計畫|劑量分布|深度劑量|楔形|射束|DVH|靶體積|PTV|CTV|GTV',
 '放療設備與品保':r'直線加速器|直線加速|linac|機械等中心|平坦度|平整度|品質保證|品保|校正',
 '近接與特殊放療':r'近接|brachy|質子治療|重粒子|立體定位|全身照射|全皮膚',
 '癌症與臨床放療':r'癌|腫瘤|淋巴瘤|分期|TNM|化學治療|chemotherapy',
 '攝影擺位與投照':r'投照|擺位|攝影姿勢|軸位|斜位|側位|正位|AP\b|PA\b|method|中心射線',
 '對比劑與特殊攝影':r'對比劑|顯影劑|鋇劑|血管攝影|尿路攝影|灌腸|乳房攝影|透視',
 '骨骼肌肉解剖與病理':r'骨|肌肉|關節|韌帶|肌腱|脊椎|脊柱',
 '神經系統':r'神經|腦|脊髓|小腦|丘腦|髓鞘',
 '心血管系統':r'心臟|心室|心房|主動脈|冠狀|心肌|血壓|心搏',
 '呼吸系統':r'肺|氣管|支氣管|呼吸|肺泡',
 '消化系統':r'食道|胃|小腸|大腸|十二指腸|肝臟|胰|膽囊|消化',
 '泌尿與生殖系統':r'腎臟|腎小|輸尿管|膀胱|尿道|子宮|卵巢|睪丸|攝護腺',
 '內分泌與代謝':r'荷爾蒙|激素|內分泌|甲狀腺|腎上腺|胰島素|糖尿病',
 '血液免疫與一般病理':r'紅血球|白血球|血小板|免疫|抗體|發炎|壞死|凋亡|血栓|栓塞'
}
for row in rows:
 p=Path(row['path']); doc=PdfReader(p)
 cache=raw/f"{row['exam']}_{row['subject']}_{row['type']}.txt"
 if cache.exists() and cache.stat().st_size:
  pages=re.split(r'(?:^|\n\n)=== PDF PAGE \d+ ===\n',cache.read_text(encoding='utf-8'))[1:]
 else:
  pages=[re.sub(r'[\ud800-\udfff]', '\uFFFD', page.extract_text() or '') for page in doc.pages]
 rel=p.relative_to(root).as_posix()
 (raw/f"{row['exam']}_{row['subject']}_{row['type']}.txt").write_text('\n\n'.join(f'=== PDF PAGE {i+1} ===\n{x}' for i,x in enumerate(pages)),encoding='utf-8')
 if row['type']!='Q': continue
 text='\n'.join(pages)
 subject_match=re.search(r'科目名稱[：:]\s*([^\n]+)',text)
 subject=subject_match.group(1).strip() if subject_match else '需核對科目'
 canonical={'0104':'基礎醫學（包括解剖學、生理學與病理學）','11':'基礎醫學（包括解剖學、生理學與病理學）','22':'醫學物理學與輻射安全','33':'放射線器材學（包括磁振學與超音波學）','44':'放射線診斷原理與技術學','55':'放射線治療原理與技術學','66':'核子醫學診療原理與技術學','0108':'基礎醫學（包括解剖學、生理學與病理學）','0601':'醫學物理學與輻射安全','0602':'放射線器材學（包括磁振學與超音波學）','0603':'放射線診斷原理與技術學','0604':'放射線治療原理與技術學','0605':'核子醫學診療原理與技術學'}[row['subject']]
 assert canonical.split('（')[0] in re.sub(r'\s','',text[:2000]),(p,subject)
 subject=canonical
 subjects[(row['exam'],row['subject'])]=subject
 # Anchored to each printed question number; keep page positions for checking originals.
 offsets=[]; cursor=0
 for i,t in enumerate(pages): offsets.append(cursor); cursor+=len(t)+1
 matches=list(re.finditer(r'(?m)^\s*(\d{1,2})\s*[.．、]\s*',text))
 all_matches=matches
 matches=[]; discarded=[]
 for m in all_matches:
  if int(m.group(1))==len(matches)+1: matches.append(m)
  else: discarded.append(text[m.start():m.start()+100])
 # The rejected candidates were decimal fragments from wrapped formulas, not question numbers.
 if any(not re.match(r'\s*\d+[.．]\d',frag) for frag in discarded):
  raise ValueError(f'Unexpected extra question marker: {p}: {discarded}')
 nums=[int(m.group(1)) for m in matches]
 valid=nums==list(range(1,81))
 report={'exam':row['exam'],'year':row['year'],'sitting':row['sitting'],'subject_code':row['subject'],'subject':subject,'pdf':rel,'pages':len(pages),'found_questions':len(matches),'sequence_1_80':valid,'discarded_decimal_fragments':discarded,'source_url':row['url'],'answer_pdf':None,'correction_pdf':None}
 for typ,field in [('S','answer_pdf'),('M','correction_pdf')]:
  candidate=p.with_name(p.stem[:-1]+typ+'.pdf')
  if candidate.exists(): report[field]=candidate.relative_to(root).as_posix()
 reports.append(report)
 if not valid: continue
 for k,m in enumerate(matches):
  end=matches[k+1].start() if k+1<len(matches) else len(text)
  body=text[m.start():end].strip()
  start_page=max(i for i,o in enumerate(offsets) if o<=m.start())+1
  end_page=max(i for i,o in enumerate(offsets) if o<end)+1
  tags=[label for label,pattern in rules.items() if re.search(pattern,unicodedata.normalize('NFKC',body),re.I)]
  qid=f"{row['year']}-{row['sitting']}-{row['subject']}-{k+1:02}"
  questions.append({'id':qid,'exam':row['exam'],'subject':subject,'number':k+1,'pdf':rel,'page_start':start_page,'page_end':end_page,'text_extracted':body,'topic_candidates':tags,'tag_status':'keyword_candidates_require_tutor_review','transcription_status':'unreviewed_extraction','visual_check_required':True,'unreadable_characters':body.count('\uFFFD'),'figure_keyword':bool(re.search(r'如圖|下圖|附圖|圖中|下表|圖示',body))})
 # Extract table rows only; corrections are retained verbatim for tutor checking.
 ap=root/(report['correction_pdf'] or report['answer_pdf'])
 at='\n'.join(pg.extract_text() or '' for pg in PdfReader(ap).pages)
 answer_tokens=[]
 for line in at.splitlines():
  if re.match(r'^\s*答案\s+',line):
   answer_tokens.extend(re.findall(r'[ABCD#]',unicodedata.normalize('NFKC',line.split('答案',1)[1])))
 note_start=re.search(r'第\s*\d+\s*題',at)
 notes=at[note_start.start():].strip() if note_start else ''
 if report['correction_pdf']: corrections.append({'exam':row['exam'],'subject':subject,'pdf':report['correction_pdf'],'notes':notes})
 report['answer_token_count']=len(answer_tokens)
 for k in range(80):
  token=answer_tokens[k] if len(answer_tokens)==80 else None
  keys.append({'id':f"{row['year']}-{row['sitting']}-{row['subject']}-{k+1:02}",'answer_token':token,'answer_pdf':ap.relative_to(root).as_posix(),'correction_notes':notes if token=='#' else '', 'grading_status':'check_correction_note' if token=='#' else ('table_extracted_check_pdf' if token else 'unparsed_check_pdf')})
for name,data in [('questions.jsonl',questions),('teacher_answers.jsonl',keys)]:
 with (out/name).open('w',encoding='utf-8') as f:
  for item in data:f.write(json.dumps(item,ensure_ascii=False)+'\n')
(out/'papers.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'corrections.json').write_text(json.dumps(corrections,ensure_ascii=False,indent=2),encoding='utf-8')
with (out/'question_topics.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['id','subject','topic_candidates','pdf','page_start','page_end','status'])
 for q in questions:w.writerow([q['id'],q['subject'],';'.join(q['topic_candidates']),q['pdf'],q['page_start'],q['page_end'],q['tag_status']])
summary={'papers':len(reports),'questions_extracted':len(questions),'invalid_sequences':[r for r in reports if not r['sequence_1_80']],'unparsed_answer_tables':[r['pdf'] for r in reports if r.get('answer_token_count')!=80],'topic_candidates_nonempty':sum(bool(q['topic_candidates']) for q in questions),'correction_documents':len(corrections)}
(out/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))

