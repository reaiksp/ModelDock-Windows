"""Development-only: build static English catalogs using a local Ollama model."""
import ast
import http.client
import json
import re
import sys
from pathlib import Path

ROOTS=[Path(__file__).resolve().parents[1]/'modeldock']

def chinese(value):
    return bool(re.search(r'[\u4e00-\u9fff]',value))


def collect(root):
    result=set()
    def template(node, fields):
        if isinstance(node,ast.Constant) and isinstance(node.value,str): return node.value
        if isinstance(node,ast.JoinedStr): return ''.join(template(v,fields) for v in node.values)
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add): return template(node.left,fields)+template(node.right,fields)
        fields.append(node)
        return '{'+str(len(fields)-1)+'}'
    for file in root.glob('*.py'):
        if file.name in {'store.py','secrets.py','providers.py'}: continue
        tree=ast.parse(file.read_text('utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str): text=node.value
            elif isinstance(node,(ast.JoinedStr,ast.BinOp)):
                if isinstance(node,ast.BinOp) and not isinstance(node.op,ast.Add): continue
                text=template(node,[])
            else: continue
            if chinese(text) and len(text)<1600 and not any(x in text for x in ['只返回 JSON','"memories"','"entries"','INSERT INTO','CREATE TABLE','返回 JSON：']):
                result.add(text)
    result.update(['界面语言','AI 回复语言','跟随用户输入','你','助手','助手 · 正在生成','助手 · 已中断','你 · 已中断','简体中文','确定','取消','保存','关闭','是','否','删除','已启用','待确认','概述','评价 1–10','分析','原文证据','供应商','语言偏好已保存。'])
    return result


def request(messages):
    conn=http.client.HTTPConnection('127.0.0.1',11434,timeout=180)
    try:
        conn.request('POST','/api/chat',json.dumps({'model':MODEL,'messages':messages,'stream':False,'think':False,'format':'json','options':{'num_ctx':16384,'num_predict':4096,'temperature':0}}).encode(),{'Content-Type':'application/json'})
        response=conn.getresponse()
        data=json.loads(response.read())
        if response.status!=200 or data.get('error'): raise RuntimeError('Local translation request failed')
        return json.loads(data['message']['content'])
    finally: conn.close()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',default='qwen3.5-9b:latest')
    parser.add_argument('--peer',type=Path)
    args=parser.parse_args()
    MODEL=args.model
    if args.peer: ROOTS.append(args.peer)
    roots={root:collect(root) for root in ROOTS}
    existing={}
    for root in ROOTS:
        path=root/'translations.json'
        if path.exists(): existing.update(json.loads(path.read_text('utf-8')))
    override={'你':'You','助手':'Assistant','助手 · 正在生成':'Assistant · generating','助手 · 已中断':'Assistant · interrupted','你 · 已中断':'You · interrupted','简体中文':'简体中文','界面语言':'Interface language','AI 回复语言':'AI reply language','跟随用户输入':'Follow user input','待确认':'Pending review','已启用':'Approved','评价 1–10':'Score 1–10','概述':'Summary','分析':'Analysis','原文证据':'Evidence','本机 Ollama':'Local Ollama','通用对话':'General chat','代码开发':'Coding','均衡':'Balanced','速度优先':'Speed first','质量优先':'Quality first','确定':'OK','取消':'Cancel','保存':'Save','关闭':'Close','是':'Yes','否':'No','◫   部署工作台':'◫   Deployment','▦   模型中心':'▦   Models','◌   本地对话':'◌   Local chat','⌘   API 接入':'⌘   API access','≡   运行日志':'≡   Logs','◌   聊天主页':'◌   Chat','✧   人格工作室':'✧   Personalities','▤   记忆与用户':'▤   Memory & you','◇   黑话学习':'◇   Slang lab','⌘   连接设置':'⌘   Connections'}
    existing.update(override)
    todo=sorted(set().union(*roots.values())-existing.keys())
    print(f'{len(todo)} new UI strings, {sum(map(len,roots.values()))} per-app entries',flush=True)
    def save():
        for root,keys in roots.items():
            (root/'translations.json').write_text(json.dumps({key:existing[key] for key in sorted(keys) if key in existing},ensure_ascii=False,indent=2),'utf-8')
    for start in range(0,len(todo),12):
        batch=todo[start:start+12]
        prompt={'role':'system','content':'Translate Chinese desktop UI text into concise natural English. Return a JSON object mapping the SAME numeric IDs to translations. Keep every {0}, {1}, etc placeholder EXACTLY, including repeated placeholders. Keep model names, URLs, symbols and line breaks. Do not include explanations. All values must be strings. Avoid overly long button labels.'}
        body={str(i):value for i,value in enumerate(batch)}
        for attempt in range(3):
            data=request([prompt,{'role':'user','content':json.dumps(body,ensure_ascii=False)}])
            bad=[]
            for i,source in enumerate(batch):
                target=data.get(str(i))
                if not isinstance(target,str) or not target.strip() or chinese(target) or sorted(re.findall(r'\{\d+\}',source))!=sorted(re.findall(r'\{\d+\}',target)):
                    bad.append(i)
            if not bad: break
        if bad:
            print('Invalid translations: '+repr([batch[i] for i in bad]),flush=True)
            raise SystemExit(1)
        for i,source in enumerate(batch): existing[source]=data[str(i)]
        save()
        print(f'Translated {min(start+12,len(todo))}/{len(todo)}',flush=True)
    save()
