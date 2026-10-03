"""Run the authorized collection, archive discovery and live reports together."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from capture import now
from multi_report import generate


def main(output):
    out=Path(output).resolve()
    if (out/'STOP').exists():
        print('STOP exists; no requests started.');return
    scripts=Path(__file__).resolve().parent
    runs=out/'runs';runs.mkdir(exist_ok=True)
    tag=now().replace(':','-').replace('+','_')
    state={'started_at':now(),'status':'running','output':str(out),'log_prefix':tag}
    handles=[];jobs={}
    try:
        # Mark discovery active before the crawler can exhaust a short queue.
        marker=out/'discovery'/'student-pagination'/'RUNNING'
        marker.parent.mkdir(parents=True,exist_ok=True)
        marker.write_text(now(),encoding='utf8')
        for name,args in [('pagination',['student_pagination.py','--output',str(out)]),
                          ('capture',['multi_capture.py','--sites',str(out/'sites.json'),'--output',str(out),'--workers','33'])]:
            log=(runs/(tag+'-'+name+'.log')).open('w',encoding='utf8');handles.append(log)
            command=[sys.executable,str(scripts/args[0]),*args[1:]]
            jobs[name]=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            state[name+'_pid']=jobs[name].pid
        last=0
        while any(job.poll() is None for job in jobs.values()):
            if jobs['capture'].poll() not in (None,0):
                (out/'STOP').write_text('Capture failed; preserve queue and stop discovery.',encoding='utf8')
            if jobs['pagination'].poll() is not None:marker.unlink(missing_ok=True)
            if time.monotonic()-last>=60:
                generate(out)
                state.update(updated_at=now(),exit_codes={k:v.poll() for k,v in jobs.items()})
                (out/'run_status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
                last=time.monotonic()
            time.sleep(2)
        pending=generate(out,verify=True)
        codes={k:v.poll() for k,v in jobs.items()}
        state.update(finished_at=now(),exit_codes=codes,pending=pending,
            status='failed' if any(c!=0 for c in codes.values()) else ('stopped' if (out/'STOP').exists() else ('queue_exhausted' if not pending else 'incomplete')))
        (out/'run_status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(state,ensure_ascii=True),flush=True)
    finally:
        for handle in handles:handle.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    main(parser.parse_args().output)
