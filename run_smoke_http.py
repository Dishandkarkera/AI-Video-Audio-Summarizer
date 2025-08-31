"""Orchestrated HTTP smoke test.
Starts the FastAPI server in a subprocess, polls for readiness, exercises core endpoints,
prints concise results, then shuts the server down.

Run from project root:
  python run_smoke_http.py --port 8000

Exit code 0 = success, non‑zero = failure.
"""
from __future__ import annotations
import argparse, subprocess, sys, time, requests, json, os, signal, textwrap
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
BACKEND = ROOT / 'backend'

def start_server(port: int, host: str) -> subprocess.Popen:
    env = os.environ.copy()
    # Ensure backend on PYTHONPATH for 'app' package resolution when using run_api helper.
    existing = env.get('PYTHONPATH','')
    parts = [str(BACKEND)] + ([existing] if existing else [])
    env['PYTHONPATH'] = os.pathsep.join(parts)
    cmd = [sys.executable, 'run_api.py', '--port', str(port), '--host', host]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc

def stream_new_lines(proc: subprocess.Popen, store: list[str]):
    # Non‑blocking-ish read of any available lines.
    if proc.stdout is None:
        return
    while True:
        try:
            line = proc.stdout.readline()
        except Exception:
            break
        if not line:
            break
        store.append(line)
        if len(store) > 4000:  # cap
            del store[:1000]
        # Print server lines selectively (omit very chatty whisper progress lines)
        if 'frames/s' in line:
            continue
        print('[SERVER]', line.rstrip())

def poll_ready(base: str, timeout: float = 40.0):
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            r = requests.get(base + '/')
            if r.status_code == 200:
                return True
        except Exception as e:
            last_err = e
        time.sleep(0.8)
    raise RuntimeError(f'Server not ready within {timeout}s: {last_err}')

def run_smoke(base: str):
    results = {}
    # Generate small tone file
    import wave, math, struct, io
    buf = io.BytesIO()
    fr=16000; dur=1.0; amp=16000; freq=440; n=int(fr*dur)
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
        for i in range(n):
            val=int(amp*math.sin(2*math.pi*freq*i/fr))
            w.writeframes(struct.pack('<h', val))
    buf.seek(0)

    r = requests.get(base + '/')
    results['root'] = (r.status_code, r.json())

    files = {'file': ('tone.wav', buf, 'audio/wav')}
    r = requests.post(base + '/media/upload', files=files)
    results['upload'] = (r.status_code, r.text[:200])
    if r.ok:
        media_id = r.json().get('id')
        r_t = requests.get(f'{base}/media/{media_id}/transcript')
        results['transcript'] = (r_t.status_code, len(r_t.text))
        r_s = requests.get(f'{base}/media/{media_id}/summary')
        summ_trim = r_s.text[:400]
        results['summary'] = (r_s.status_code, summ_trim)
        r_search = requests.get(f'{base}/media/{media_id}/search', params={'q':'test'})
        results['search'] = (r_search.status_code, r_search.text[:200])
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--keep', action='store_true', help='Leave server running after tests')
    args = ap.parse_args()

    base = f'http://{args.host}:{args.port}'
    print(f'[INFO] Starting server on {base}')
    proc = start_server(args.port, args.host)
    log_lines: list[str] = []
    try:
        # Poll logs while waiting
        t_start = time.time()
        while proc.poll() is None and time.time() - t_start < 2.0:
            stream_new_lines(proc, log_lines)
            time.sleep(0.2)
        poll_ready(base)
        print('[INFO] Server ready, executing smoke test...')
        stream_new_lines(proc, log_lines)
        results = run_smoke(base)
        print('\n===== SMOKE RESULTS =====')
        for k, v in results.items():
            print(f'{k.upper()}:', v[0], '->', v[1])
        # Basic success heuristic
        if results.get('upload', (0,''))[0] != 200:
            raise SystemExit(2)
        print('[INFO] Smoke test completed successfully.')
    finally:
        if not args.keep:
            if proc.poll() is None:
                print('[INFO] Terminating server subprocess...')
                try:
                    if os.name == 'nt':
                        proc.terminate()  # SIGTERM emulation on Windows
                    else:
                        proc.send_signal(signal.SIGINT)
                except Exception:
                    pass
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
        else:
            print('[INFO] --keep specified, leaving server running (PID', proc.pid, ')')

if __name__ == '__main__':
    main()
