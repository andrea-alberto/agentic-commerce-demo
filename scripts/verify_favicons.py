import urllib.request

ports = [4200, 4201, 4202, 4203]
files = ['favicon.svg?v=2026', 'favicon-32x32.png?v=2026', 'favicon-16x16.png?v=2026', 'favicon.ico?v=2026']

all_ok = True
for p in ports:
    for f in files:
        url = f'http://localhost:{p}/{f}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 Chrome/130.0.0.0'})
            with urllib.request.urlopen(req) as r:
                data = r.read()
                ct = r.headers.get('Content-Type')
                print(f"[OK]   port {p} {f:<30} -> {r.status} | {ct} | {len(data)} bytes")
        except Exception as e:
            all_ok = False
            print(f"[FAIL] port {p} {f:<30} -> {e}")

if all_ok:
    print("\nALL PORTS AND ALL FAVICON FORMATS ARE 100% OPERATIONAL!")
