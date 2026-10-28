import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "PlusEduc-BE-Python"))
from app.main import app
from app.dependencies import get_current_user
def roles_of(call):
    if getattr(call,'__closure__',None) and call.__name__=='dependency':
        for c in call.__closure__:
            if isinstance(c.cell_contents,tuple): return tuple(c.cell_contents)
def walk(d,acc):
    for sub in d.dependencies:
        r=roles_of(sub.call)
        if r is not None: acc['roles']=r
        if sub.call is get_current_user: acc['auth']=True
        walk(sub,acc)
rows=[]
for inc in app.routes:
    rs = inc.original_router.routes if hasattr(inc,'original_router') else [inc]
    for r in rs:
        if not hasattr(r,'dependant'): continue
        acc={}; walk(r.dependant,acc)
        for m in sorted(r.methods - {'HEAD','OPTIONS'}):
            rows.append({'method':m,'path':r.path,'roles':list(acc['roles']) if 'roles' in acc else None,'auth':acc.get('auth',False)})
rows.sort(key=lambda x:(x['path'],x['method']))
json.dump(rows,open(sys.argv[1],'w'),indent=1)
for x in rows:
    print(f"{x['method']:7} {x['path']:68} {'ROLES='+'/'.join(x['roles']) if x['roles'] else ('AUTH-ANY' if x['auth'] else 'PUBLIC')}")
print(len(rows))
