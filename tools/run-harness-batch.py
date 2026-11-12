import subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
SP = sys.argv[1]; B = f'{SP}/blindset'; P = f'{SP}/v5photos'
A = sorted(f'{P}/{f}' for f in os.listdir(P) if f.endswith('.jpg')); Bo = A[::-1]
jobs = [(j, o) for j in sys.argv[2:] for o in 'ab']
def run(jo):
    j, o = jo
    with open(f'{B}/{j}/harness-{o}.out', 'w') as out:
        subprocess.run(['node', f'{SP}/harness/run.mjs', f'{B}/{j}/app/dist', f'{B}/{j}/harness', o] + (A if o == 'a' else Bo), stdout=out, stderr=subprocess.STDOUT, timeout=1200)
    print(j, o, 'done', open(f'{B}/{j}/harness-{o}.out').read().strip().splitlines()[-1][:140], flush=True)
with ThreadPoolExecutor(3) as ex: list(ex.map(run, jobs))
