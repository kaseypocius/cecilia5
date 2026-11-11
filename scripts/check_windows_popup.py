#!/usr/bin/env python3
"""Run the real Windows popup regression and reject missing/skipped coverage."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
NATIVE_TEST = (
    'test_popup_menu.NativePopupMenuTests.'
    'test_thread_updates_arrive_before_menu_closes_without_mouse_input'
)


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.append(test.id())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'platform': sys.platform,
        'os': platform.platform(),
        'python': sys.version,
        'commit': os.environ.get('GITHUB_SHA'),
        'run_url': (
            f"{os.environ.get('GITHUB_SERVER_URL')}/"
            f"{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/"
            f"{os.environ.get('GITHUB_RUN_ID')}"
        ) if os.environ.get('GITHUB_RUN_ID') else None,
        'source_sha256': {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ('Resources/PopupMenu.py', 'tests/test_popup_menu.py')
        },
        'status': 'blocked',
    }
    try:
        if sys.platform != 'win32':
            raise RuntimeError('Native Windows is required; Linux/Wine cannot certify this test.')
        if os.environ.get('CECILIA_GUI_TESTS') != '1':
            raise RuntimeError('Set CECILIA_GUI_TESTS=1 to enable the native GUI test.')
        import wx

        report['wx_version'] = wx.version()
        suite = unittest.defaultTestLoader.discover(
            str(ROOT / 'tests'), pattern='test_popup_menu.py')
        result = unittest.TextTestRunner(
            verbosity=2, resultclass=RecordingResult).run(suite)
        report.update(
            tests_run=result.testsRun,
            passed=result.passed,
            skipped=[(test.id(), reason) for test, reason in result.skipped],
            failures=[(test.id(), detail) for test, detail in result.failures],
            errors=[(test.id(), detail) for test, detail in result.errors],
            native_test_passed=NATIVE_TEST in result.passed,
        )
        ok = (result.wasSuccessful() and not result.skipped
              and report['native_test_passed'])
        report['status'] = 'passed' if ok else 'failed'
    except Exception as error:
        report['reason'] = f'{type(error).__name__}: {error}'
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
