# -*- coding: utf-8 -*-
"""无需 SD 的静态检查和 unittest；不会导入或修改真实 Designer 场景。"""

from pathlib import Path
import sys
import unittest


def main():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / 'MaxSDPlugins').rglob('*.py'))
    for path in paths:
        source = path.read_text(encoding='utf-8')
        compile(source, str(path), 'exec')
    print(f'Syntax OK: {len(paths)} Python files')
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
