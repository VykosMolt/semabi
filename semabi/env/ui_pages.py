"""Three radically different UIs over the same hidden domain, with label modes.

Only the DOM the browser renders is visible to the compiler. Hidden object ids
are kept in JS closures and never written into the DOM.
"""
from __future__ import annotations

import hashlib

UIS = ("kanban", "table", "list")
LABEL_MODES = ("plain", "obscured", "misleading")

LABELS: dict[str, dict[str, dict[str, str]]] = {
    "kanban": {
        "plain": dict(
            title="Board", new_lane_ph="New lane name", add_lane="Add lane", rename="Rename", ok="OK",
            delete_lane="Delete lane", done_toggle="Done", menu="Options", move="Move", remove="Remove",
            new_card_ph="New card", add_card="Add card", error="That didn't work.",
        ),
        "misleading": dict(
            title="Board", new_lane_ph="Search", add_lane="Import", rename="Delete", ok="Cancel",
            delete_lane="Export", done_toggle="Pin", menu="Share", move="Copy", remove="Save",
            new_card_ph="Filter", add_card="Archive", error="Saved.",
        ),
    },
    "table": {
        "plain": dict(
            title="Worklog", categories="Categories", rename_cat="Rename", ok="Apply", delete_cat="Delete",
            new_cat_ph="Category name", add_cat="New category", col_entry="Entry", col_cat="Category",
            col_status="Status", col_actions="Actions", status_open="Open", status_closed="Closed",
            close="Close", reopen="Reopen", trash="Trash", new_entry_ph="Entry title", insert="Insert",
            error="Operation rejected.",
        ),
        "misleading": dict(
            title="Worklog", categories="Tags", rename_cat="Merge", ok="Discard", delete_cat="Star",
            new_cat_ph="Search tags", add_cat="Sync", col_entry="Owner", col_cat="Priority",
            col_status="Size", col_actions="Links", status_open="Large", status_closed="Small",
            close="Shrink", reopen="Grow", trash="Duplicate", new_entry_ph="Comment", insert="Reply",
            error="Done.",
        ),
    },
    "list": {
        "plain": dict(
            title="Notes", folders="Folders", new_folder="New folder", rename_folder="Rename folder",
            remove_folder="Remove folder", st_open="open", st_done="finished", finish="Finish",
            unfinish="Unfinish", move="Move…", discard="Discard", new_note_ph="Note text",
            add_note="Add note", pick_folder="Select a folder.", create="Create", cancel="Cancel",
            confirm="Confirm", move_to="Move to", error="Not allowed.", rename_ph="New name", save="Save",
        ),
        "misleading": dict(
            title="Notes", folders="Recent", new_folder="Log out", rename_folder="Duplicate folder",
            remove_folder="Open folder", st_open="pinned", st_done="unpinned", finish="Pin",
            unfinish="Unpin", move="Print…", discard="Save", new_note_ph="Search",
            add_note="Go", pick_folder="Welcome.", create="Cancel", cancel="Create",
            confirm="Back", move_to="Share with", error="Success.", rename_ph="Search", save="Delete",
        ),
    },
}


def labels_for(ui: str, mode: str) -> dict[str, str]:
    if mode == "plain" or mode == "misleading":
        return LABELS[ui][mode]
    if mode == "obscured":
        out = {}
        for k in LABELS[ui]["plain"]:
            h = hashlib.sha1(f"{ui}:{k}".encode()).hexdigest()
            out[k] = f"{h[:2]}{int(h[2:6], 16) % 90 + 10}"
        return out
    raise KeyError(mode)


COMMON_JS = r"""
let S = null, V = {};
function el(tag, props, ...kids){ const e=document.createElement(tag); for(const [k,v] of Object.entries(props||{})){ if(v==null) continue; if(k==='on'){ for(const [ev,f] of Object.entries(v)) e.addEventListener(ev,f);} else if(k==='text'){ e.textContent=v;} else if(k==='checked'){ e.checked=!!v; } else if(k==='value'){ e.value=v; } else e.setAttribute(k,v);} for(const k of kids){ if(k!=null) e.appendChild(typeof k==='string'?document.createTextNode(k):k);} return e; }
async function api(op,args){ const r=await fetch('/api/op',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({op,args})}); const j=await r.json(); V.error = j.ok?null:L.error; await load(); }
async function load(){ S=await (await fetch('/api/state')).json(); render(); }
function num(id){ return parseInt(id.slice(1)); }
function projects(){ return S.objects.filter(o=>o.type==='Project').sort((a,b)=>num(a.id)-num(b.id)); }
function tasks(pid){ return S.objects.filter(o=>o.type==='Task' && (pid==null || S.rels.belongs_to[o.id]===pid)).sort((a,b)=>num(a.id)-num(b.id)); }
function alertBox(){ return V.error? el('div',{role:'alert',text:V.error}) : null; }
window.addEventListener('DOMContentLoaded', load);
"""

KANBAN_JS = r"""
function render(){
  const root=document.getElementById('app'); root.innerHTML='';
  root.appendChild(el('h1',{text:L.title}));
  {const ab=alertBox(); if(ab) root.appendChild(ab);}
  const newLane=el('input',{placeholder:L.new_lane_ph,type:'text'});
  root.appendChild(el('div',{class:'toolbar'}, newLane, el('button',{text:L.add_lane,on:{click:()=>api('create_project',{name:newLane.value})}})));
  const lanes=el('div',{class:'lanes'});
  for(const p of projects()){
    const head=el('div',{class:'head'});
    if(V.renaming===p.id){ const inp=el('input',{type:'text',value:p.attrs.name}); head.appendChild(inp); head.appendChild(el('button',{text:L.ok,on:{click:()=>{V.renaming=null; api('rename_project',{project:p.id,name:inp.value});}}})); }
    else { head.appendChild(el('h2',{text:p.attrs.name})); head.appendChild(el('button',{text:L.rename,on:{click:()=>{V.renaming=p.id; V.menu=null; render();}}})); }
    head.appendChild(el('button',{text:L.delete_lane,on:{click:()=>api('delete_project',{project:p.id})}}));
    const cards=el('div',{class:'cards'});
    for(const t of tasks(p.id)){
      const cb=el('input',{type:'checkbox',checked:t.attrs.done,'aria-label':L.done_toggle,on:{change:()=>api(t.attrs.done?'reopen_task':'complete_task',{task:t.id})}});
      const card=el('article',{class:'card'}, cb, el('span',{text:t.attrs.title}), el('button',{text:L.menu,on:{click:()=>{V.menu=(V.menu===t.id?null:t.id); V.renaming=null; render();}}}));
      if(V.menu===t.id){
        const sel=el('select',{});
        for(const q of projects()) sel.appendChild(el('option',{value:q.id,text:q.attrs.name}));
        sel.value=S.rels.belongs_to[t.id];
        card.appendChild(el('div',{class:'menu'}, sel, el('button',{text:L.move,on:{click:()=>{V.menu=null; api('move_task',{task:t.id,project:sel.value});}}}), el('button',{text:L.remove,on:{click:()=>{V.menu=null; api('delete_task',{task:t.id});}}})));
      }
      cards.appendChild(card);
    }
    const newCard=el('input',{placeholder:L.new_card_ph,type:'text'});
    lanes.appendChild(el('section',{class:'lane'}, head, cards, el('div',{class:'foot'}, newCard, el('button',{text:L.add_card,on:{click:()=>api('create_task',{project:p.id,title:newCard.value})}}))));
  }
  root.appendChild(lanes);
}
"""

TABLE_JS = r"""
function render(){
  const root=document.getElementById('app'); root.innerHTML='';
  root.appendChild(el('h1',{text:L.title}));
  {const ab=alertBox(); if(ab) root.appendChild(ab);}
  const cats=el('ul',{});
  for(const p of projects()){
    const li=el('li',{});
    if(V.renaming===p.id){ const inp=el('input',{type:'text',value:p.attrs.name}); li.appendChild(inp); li.appendChild(el('button',{text:L.ok,on:{click:()=>{V.renaming=null; api('rename_project',{project:p.id,name:inp.value});}}})); }
    else { li.appendChild(el('span',{text:p.attrs.name})); li.appendChild(el('button',{text:L.rename_cat,on:{click:()=>{V.renaming=p.id; render();}}})); }
    li.appendChild(el('button',{text:L.delete_cat,on:{click:()=>api('delete_project',{project:p.id})}}));
    cats.appendChild(li);
  }
  const newCat=el('input',{placeholder:L.new_cat_ph,type:'text'});
  root.appendChild(el('section',{}, el('h2',{text:L.categories}), cats, el('div',{}, newCat, el('button',{text:L.add_cat,on:{click:()=>api('create_project',{name:newCat.value})}}))));
  const tbl=el('table',{});
  tbl.appendChild(el('thead',{}, el('tr',{}, el('th',{text:L.col_entry}), el('th',{text:L.col_cat}), el('th',{text:L.col_status}), el('th',{text:L.col_actions}))));
  const tb=el('tbody',{});
  for(const t of tasks(null)){
    const sel=el('select',{});
    for(const q of projects()) sel.appendChild(el('option',{value:q.id,text:q.attrs.name}));
    sel.value=S.rels.belongs_to[t.id];
    sel.addEventListener('change',()=>api('move_task',{task:t.id,project:sel.value}));
    const st=el('td',{}, el('span',{text:t.attrs.done?L.status_closed:L.status_open}), el('button',{text:t.attrs.done?L.reopen:L.close,on:{click:()=>api(t.attrs.done?'reopen_task':'complete_task',{task:t.id})}}));
    tb.appendChild(el('tr',{}, el('td',{}, el('span',{text:t.attrs.title})), el('td',{}, sel), st, el('td',{}, el('button',{text:L.trash,on:{click:()=>api('delete_task',{task:t.id})}}))));
  }
  tbl.appendChild(tb);
  const newEntry=el('input',{placeholder:L.new_entry_ph,type:'text'});
  const newSel=el('select',{});
  for(const q of projects()) newSel.appendChild(el('option',{value:q.id,text:q.attrs.name}));
  tbl.appendChild(el('tfoot',{}, el('tr',{}, el('td',{}, newEntry), el('td',{}, newSel), el('td',{}), el('td',{}, el('button',{text:L.insert,on:{click:()=>api('create_task',{project:newSel.value,title:newEntry.value})}})))));
  root.appendChild(tbl);
}
"""

LIST_JS = r"""
function render(){
  const root=document.getElementById('app'); root.innerHTML='';
  root.appendChild(el('h1',{text:L.title}));
  {const ab=alertBox(); if(ab) root.appendChild(ab);}
  const ps=projects();
  if(V.folder && !ps.find(p=>p.id===V.folder)) V.folder=null;
  const ul=el('ul',{});
  for(const p of ps){ ul.appendChild(el('li',{}, el('a',{href:'#',text:p.attrs.name,'aria-current':V.folder===p.id?'page':null,on:{click:(e)=>{e.preventDefault(); V.folder=p.id; V.dialog=null; render();}}}))); }
  root.appendChild(el('nav',{}, el('h2',{text:L.folders}), ul, el('button',{text:L.new_folder,on:{click:()=>{V.dialog={kind:'newfolder'}; render();}}})));
  const main=el('main',{});
  const p=ps.find(q=>q.id===V.folder);
  if(p){
    main.appendChild(el('h2',{text:p.attrs.name}));
    main.appendChild(el('button',{text:L.rename_folder,on:{click:()=>{V.dialog={kind:'rename',pid:p.id}; render();}}}));
    main.appendChild(el('button',{text:L.remove_folder,on:{click:()=>api('delete_project',{project:p.id})}}));
    const items=el('ul',{});
    for(const t of tasks(p.id)){
      items.appendChild(el('li',{}, el('span',{text:t.attrs.title}), el('em',{text:t.attrs.done?L.st_done:L.st_open}),
        el('button',{text:t.attrs.done?L.unfinish:L.finish,on:{click:()=>api(t.attrs.done?'reopen_task':'complete_task',{task:t.id})}}),
        el('button',{text:L.move,on:{click:()=>{V.dialog={kind:'move',tid:t.id,target:null}; render();}}}),
        el('button',{text:L.discard,on:{click:()=>api('delete_task',{task:t.id})}})));
    }
    main.appendChild(items);
    const inp=el('input',{placeholder:L.new_note_ph,type:'text'});
    main.appendChild(el('div',{}, inp, el('button',{text:L.add_note,on:{click:()=>api('create_task',{project:p.id,title:inp.value})}})));
  } else main.appendChild(el('p',{text:L.pick_folder}));
  root.appendChild(main);
  if(V.dialog){
    const d=el('div',{role:'dialog'});
    if(V.dialog.kind==='newfolder'){ const inp=el('input',{type:'text',placeholder:L.rename_ph}); d.appendChild(inp); d.appendChild(el('button',{text:L.create,on:{click:()=>{V.dialog=null; api('create_project',{name:inp.value});}}})); }
    else if(V.dialog.kind==='rename'){ const inp=el('input',{type:'text',value:ps.find(q=>q.id===V.dialog.pid).attrs.name}); d.appendChild(inp); d.appendChild(el('button',{text:L.save,on:{click:()=>{const pid=V.dialog.pid; V.dialog=null; api('rename_project',{project:pid,name:inp.value});}}})); }
    else if(V.dialog.kind==='move'){ d.appendChild(el('p',{text:L.move_to})); for(const q of ps){ const r=el('input',{type:'radio',name:'tgt',checked:V.dialog.target===q.id,on:{change:()=>{V.dialog.target=q.id;}}}); d.appendChild(el('label',{}, r, q.attrs.name)); } d.appendChild(el('button',{text:L.confirm,on:{click:()=>{const dd=V.dialog; V.dialog=null; if(dd.target) api('move_task',{task:dd.tid,project:dd.target}); else render();}}})); }
    d.appendChild(el('button',{text:L.cancel,on:{click:()=>{V.dialog=null; render();}}}));
    root.appendChild(d);
  }
}
"""

CSS = """
body{font-family:sans-serif;margin:16px} .lanes{display:flex;gap:16px} .lane{border:1px solid #888;padding:8px;min-width:200px}
.card{border:1px solid #ccc;margin:4px 0;padding:4px} table{border-collapse:collapse} td,th{border:1px solid #aaa;padding:4px}
[role=dialog]{border:2px solid #333;padding:12px;background:#fff;position:fixed;top:30%;left:30%} [role=alert]{color:#b00} nav{float:left;width:180px} main{margin-left:200px}
"""

_JS = {"kanban": KANBAN_JS, "table": TABLE_JS, "list": LIST_JS}


def render_page(ui: str, labels: str) -> str:
    if ui not in UIS:
        raise KeyError(ui)
    if labels not in LABEL_MODES:
        raise KeyError(labels)
    import json
    L = labels_for(ui, labels)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{L['title']}</title><style>{CSS}</style></head>
<body><div id="app"></div><script>const L={json.dumps(L)};{COMMON_JS}{_JS[ui]}</script></body></html>"""
