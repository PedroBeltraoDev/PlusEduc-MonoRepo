import sys
from pymongo import MongoClient
c=MongoClient('mongodb://localhost:27017')
src=c['escola_db']; dst_name=sys.argv[1] if len(sys.argv)>1 else 'pluseduc_sprint8_eval'
assert dst_name!='escola_db'
c.drop_database(dst_name)
dst=c[dst_name]
for name in src.list_collection_names():
    docs=list(src[name].find({}))
    if docs: dst[name].insert_many(docs)
    for ix in src[name].list_indexes():
        if ix['name']=='_id_': continue
        key=list(ix['key'].items()); kw={k:v for k,v in ix.items() if k not in('key','v','ns')}
        dst[name].create_index(key,**kw)
print('cloned',dst_name,{k:dst[k].count_documents({}) for k in dst.list_collection_names()})
