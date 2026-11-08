from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class StaticBuildAcceptance(unittest.TestCase):
    def test_publish_only_site_files(self):
        result = subprocess.run(['node', 'scripts/build.mjs'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        dist = ROOT / 'dist'
        self.assertEqual((dist / 'index.html').read_bytes(), (ROOT / 'index.html').read_bytes())
        expected = {'index.html', 'privacy.html', 'terms.html', 'favicon.svg', 'campaign.js', 'assets'}
        self.assertEqual({f.name for f in dist.iterdir()}, expected)
        self.assertEqual({p.name for p in (dist / 'assets').iterdir()}, {p.name for p in (ROOT / 'assets').iterdir() if p.suffix in ('.webp', '.woff2')})

if __name__ == '__main__':
    unittest.main()
