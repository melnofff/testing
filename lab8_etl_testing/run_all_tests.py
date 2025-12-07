import subprocess, sys
tests = [
    'tests/test_etl.py',
    'test_data_quality.py',
    'test_performance.py'
]
all_ok = True
for t in tests:
    print('Running', t)
    res = subprocess.run([sys.executable, '-m', 'pytest', t, '-q'], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print('FAILED:', t)
        all_ok = False
if all_ok:
    print('ALL TESTS PASSED')
else:
    print('SOME TESTS FAILED')
