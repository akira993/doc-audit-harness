#!/usr/bin/env python3
"""PLAN §8 スコープ検査（boss 用）。SCOPE_COMMIT / BOSS_COMMIT を env で受ける。exit 1 で違反。"""
import subprocess,sys,os,hashlib,fnmatch,stat
T='tasks/route/2026-08-28-issues-56-60/'
def show(c,p): return subprocess.run(['git','show',f'{c}:{p}'],capture_output=True,text=True,check=True).stdout
def z(cmd): return [p for p in subprocess.run(cmd,capture_output=True,text=True,check=True).stdout.split('\0') if p]
allow={l.strip() for l in show(os.environ['SCOPE_COMMIT'],T+'allowlist.txt').splitlines() if l.strip() and not l.startswith('#')}|{T+'release-handoff.sh'}
logs=[T+'*-session.log',T+'*-prompt.md',T+'*-answer.md',T+'investigate-*',T+'*.log',T+'*-report.md',T+'stage*']
boss_docs=[T+n for n in ('PLAN.md','REVIEW.md','allowlist.txt','baseline-hashes.txt','59-design-note.md','scope-check.py')]
bad=[]
changed=set(z(['git','diff','--name-only','-z','dfdb8a9','HEAD']))
st=z(['git','status','--porcelain=v1','-z','--untracked-files=all']); i=0
while i<len(st):
    code,path=st[i][:2],st[i][3:]; changed.add(path)
    if 'R' in code: i+=1; changed.add(st[i])
    i+=1
for p in sorted(changed):
    if p.startswith(('.mdq/','.claude/worktrees/')) or '__pycache__/' in p or any(fnmatch.fnmatch(p,g) for g in logs): continue
    if p in boss_docs:
        ref=subprocess.run(['git','show',f"{os.environ['BOSS_COMMIT']}:{p}"],capture_output=True).stdout
        if open(p,'rb').read()!=ref: bad.append(p+' (boss doc modified)')
        continue
    if p not in allow: bad.append(p)
roots=['.envrc','.gitignore','.claude/settings.local.json','data','.serena','docs/superpowers']
def enum():
    out={}
    for r in roots:
        paths=[r] if not os.path.isdir(r) else [os.path.join(d,f) for d,_,fs in os.walk(r) for f in fs]
        for p in paths:
            if not os.path.lexists(p): continue
            s=os.lstat(p); kind='symlink' if stat.S_ISLNK(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'other'
            h=hashlib.sha256(open(p,'rb').read()).hexdigest() if kind=='file' else hashlib.sha256(os.readlink(p).encode() if kind=='symlink' else b'').hexdigest()
            out[p]=(h,oct(stat.S_IMODE(s.st_mode)),kind)
    return out
base={}
for line in show(os.environ['SCOPE_COMMIT'],T+'baseline-hashes.txt').splitlines():
    h,m,k,p=line.split('  ',3); base[p]=(h,m,k)
cur=enum()
for p in sorted(set(base)|set(cur)):
    if base.get(p)!=cur.get(p): bad.append(p+' (protected root changed: %s -> %s)'%(base.get(p),cur.get(p)))
print('\n'.join(bad) or 'scope-clean'); sys.exit(1 if bad else 0)
