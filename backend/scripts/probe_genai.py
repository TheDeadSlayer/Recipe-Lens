import subprocess, sys

# Install into the running environment
result = subprocess.run(
    [sys.executable, '-m', 'pip', 'install', 'google-genai', '--quiet', '--user'],
    capture_output=True, text=True
)
print('pip stdout:', result.stdout[-300:] if result.stdout else '')
print('pip stderr:', result.stderr[-500:] if result.stderr else '')
print('pip rc:', result.returncode)

# Force reload sys.path to find user-installed packages
import site
importlib_path = site.getusersitepackages()
if importlib_path not in sys.path:
    sys.path.insert(0, importlib_path)

import importlib.metadata
matches = [(k, v) for k, v in importlib.metadata.packages_distributions().items()
           if 'genai' in k.lower() or 'generativ' in k.lower()]
print('matching packages:', matches[:20])

try:
    from google import genai
    print('import OK, genai.__file__:', genai.__file__)
    print('genai attrs:', [a for a in dir(genai) if not a.startswith('_')])
    print('Client attrs:', [a for a in dir(genai.Client) if not a.startswith('_')])
except Exception as e:
    print('import error:', e)
