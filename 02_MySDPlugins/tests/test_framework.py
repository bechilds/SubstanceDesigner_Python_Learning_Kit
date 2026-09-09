# -*- coding: utf-8 -*-
"""框架回归：依赖闭包、独立产物/MG 导入、资源与生命周期。

这些测试使用无 Qt 的 SD stub，不代表 SD13/16 实机验证。
"""

import ast
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1] / 'MaxSDPlugins'
SPEC = importlib.util.spec_from_file_location('tested_exporter', ROOT / 'output_tools/exporter.py')
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)


class ExportTests(unittest.TestCase):
    def test_invalid_dependency_does_not_overwrite_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'plugin'
            root.mkdir()
            module = root / 'broken.py'
            module.write_text('from .missing import value\n', encoding='utf-8')
            (root / 'sdcompat.py').write_text('', encoding='utf-8')
            out = Path(temp) / 'existing.py'
            out.write_text('# keep\n', encoding='utf-8')
            with mock.patch.object(EXPORTER, 'plugin_root', return_value=root):
                ok, _ = EXPORTER.export_modules([module], out)
                self.assertFalse(ok)
                self.assertEqual(out.read_text(encoding='utf-8'), '# keep\n')
                module.write_text('return 1\n', encoding='utf-8')
                ok, _ = EXPORTER.export_modules([module], out)
                self.assertFalse(ok)
                self.assertEqual(out.read_text(encoding='utf-8'), '# keep\n')

    def test_only_selected_window_is_exposed(self):
        sd = types.ModuleType('sd')
        sd.__path__ = []
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(sys.modules, {'sd': sd}):
            out = Path(temp) / 'bundle.py'
            ok, message = EXPORTER.export_modules([ROOT / 'switch_manager/window.py'], out)
            self.assertTrue(ok, message)
            namespace = {'__name__': 'host_import'}
            exec(compile(out.read_text(encoding='utf-8'), str(out), 'exec'), namespace)
            try:
                self.assertEqual(set(namespace['maxsd_activate']()), {'switch_manager_window'})
            finally:
                self.assertTrue(namespace['maxsd_shutdown']())

    def test_dependency_closure(self):
        _, _, sources, _ = EXPORTER.build_plan([ROOT / 'switch_manager/window.py'])
        self.assertIn('output.output_data', sources)
        self.assertIn('expose_param_sorting.sorting_window', sources)
        self.assertIn('shared.lifecycle', sources)
        self.assertNotIn('MaxSDPlugin', sources)

    def test_outside_source_rejected(self):
        with self.assertRaises(ValueError):
            EXPORTER.build_plan([ROOT.parent / 'AGENTS.md'])

    def test_every_feature_exports_and_imports(self):
        paths = [path for path in EXPORTER.catalog(ROOT).values()
                 if path.name != '__init__.py']
        sd = types.ModuleType('sd')
        sd.__path__ = []
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(sys.modules, {'sd': sd}):
            out = Path(temp) / 'bundle.py'
            ok, message = EXPORTER.export_modules(paths, out)
            self.assertTrue(ok, message)
            namespaces = []
            try:
                for _ in range(2):
                    namespace = {'__name__': 'host_import'}
                    exec(compile(out.read_text(encoding='utf-8'), str(out), 'exec'), namespace)
                    namespaces.append(namespace)
                    batch = sys.modules[namespace['_MAXSD_PKG'] + '.batch_merge_tex_channel.logic']
                    self.assertTrue(Path(batch.default_sbs_path()).is_file())
                    self.assertTrue(Path(batch.__file__).is_file())
                    self.assertIn('switch_manager_window', namespace['maxsd_activate']())
                self.assertNotEqual(namespaces[0]['_MAXSD_PKG'], namespaces[1]['_MAXSD_PKG'])
            finally:
                for namespace in namespaces:
                    self.assertTrue(namespace['maxsd_shutdown']())
                    self.assertFalse(Path(namespace['_maxsd_root']).exists())

    def test_mg_all_imports_and_stable_names(self):
        paths = [path for path in EXPORTER.catalog(ROOT).values() if path.name != '__init__.py']
        sd = types.ModuleType('sd')
        sd.__path__ = []
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(sys.modules, {'sd': sd}):
            ok, message = EXPORTER.export_modules_to_mg(paths, temp)
            self.assertTrue(ok, message)
            manifest = json.loads((Path(temp) / 'maxsd_export_manifest.json').read_text(encoding='utf-8'))
            old_path = list(sys.path)
            sys.path[:0] = [temp] + [str(path) for path in Path(temp).iterdir() if path.is_dir()]
            try:
                for name in manifest['modules'].values():
                    importlib.import_module(name)
                batch = sys.modules[manifest['modules']['batch_merge_tex_channel.logic']]
                self.assertTrue(Path(batch.default_sbs_path()).exists())
            finally:
                sys.path[:] = old_path
                for name in manifest['modules'].values():
                    sys.modules.pop(name, None)
            names = EXPORTER._mg_names(EXPORTER.catalog(ROOT))
            self.assertEqual(names['output.output_data'], 'LG_MaxSD_output_data')
            self.assertEqual(names['switch_manager.logic'], 'LG_MaxSD_switch_manager_logic')

    def test_ast_rewrite_multiline_alias_and_comment(self):
        source = 'from ..output import (\n    output_data as data,\n)  # 保留注释\ntext = "MaxSDPlugin"\n'
        modules = {'output.output_data': None, 'output': None}
        names = {'output.output_data': 'LG_MaxSD_output_data', 'output': 'LG_MaxSD_output'}
        result = EXPORTER.rewrite_mg_source(source, 'switch_manager.logic', False, modules, names)
        self.assertIn('import LG_MaxSD_output_data as data', result)
        self.assertIn('# 保留注释', result)
        self.assertIn('"MaxSDPlugin"', result)


class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in self.callbacks:
            callback()


class Dialog:
    def __init__(self):
        self.finished, self.destroyed = Signal(), Signal()
        self._running = False
        self.shown = 0

    def setAttribute(self, *_args):
        pass

    def isMinimized(self):
        return False

    def show(self):
        self.shown += 1

    def raise_(self):
        pass

    def activateWindow(self):
        pass

    def close(self):
        self.finished.emit()
        return True


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.name = '_maxsd_test_package'
        self.package = types.ModuleType(self.name)
        self.package.__path__ = [str(ROOT)]
        sys.modules[self.name] = self.package
        self.compat = importlib.import_module(self.name + '.sdcompat')
        self.lifecycle = importlib.import_module(self.name + '.shared.lifecycle')
        self.compat.QtWidgets = object()
        self.compat.QtCore = types.SimpleNamespace(Qt=types.SimpleNamespace(WA_DeleteOnClose=55))
        self.compat._isvalid_fn = lambda: None

    def tearDown(self):
        for name in list(sys.modules):
            if name == self.name or name.startswith(self.name + '.'):
                sys.modules.pop(name, None)

    def test_singleton_busy_and_delayed_destruction(self):
        owner = {}
        first = self.lifecycle.show_dialog('test', Dialog, owner)
        self.assertIs(first, self.lifecycle.show_dialog('test', Dialog, owner))
        first._running = True
        self.assertFalse(self.lifecycle.close_all_dialogs())
        first._running = False
        self.assertTrue(self.lifecycle.close_all_dialogs())
        self.assertIsNone(owner['_dialog_ref'])
        second = self.lifecycle.show_dialog('test', Dialog, owner)
        first.destroyed.emit()
        self.assertIs(owner['_dialog_ref'], second)

    def test_reload_rebinds_compat_and_parent_attributes(self):
        with mock.patch.dict(sys.modules, {'sd': types.ModuleType('sd')}):
            main = importlib.import_module(self.name + '.MaxSDPlugin')
            old = self.compat
            main._reload_feature_modules()
            self.assertIsNot(main.sdcompat, old)
            self.assertIs(self.package.sdcompat, main.sdcompat)
            self.assertNotIn(self.name + '.shared.lifecycle', sys.modules)

    def test_api_exception_is_caught_without_swallowing_interrupt(self):
        class APIError(BaseException):
            pass
        stub = types.ModuleType('sd.api.apiexception')
        stub.APIException = APIError
        with mock.patch.dict(sys.modules, {'sd.api.apiexception': stub}):
            spec = importlib.util.spec_from_file_location('test_compat_errors', ROOT / 'sdcompat.py')
            compat = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(compat)
            self.assertTrue(issubclass(APIError, compat.SD_API_ERRORS))
            self.assertFalse(issubclass(KeyboardInterrupt, compat.SD_API_ERRORS))
            graph = types.SimpleNamespace(getNodeFromId=mock.Mock(side_effect=APIError('bad node')))
            ok, message = compat.focus_node(graph, 'node', app=object())
            self.assertFalse(ok)
            self.assertIn('bad node', message)

    def test_batch_escape_and_close_request_cancel_before_destruction(self):
        # 直接提取控制流测试，不伪造整套 Qt；真实信号/事件仍须宿主验证。
        tree = ast.parse((ROOT / 'batch_merge_tex_channel/window.py').read_text(encoding='utf-8'))
        methods = [node for node in ast.walk(tree)
                   if isinstance(node, ast.FunctionDef) and node.name in (
                       'reject', 'closeEvent', '_browse_source', '_browse_output', '_browse_sbs',
                       '_scan', '_inspect_processor', '_mark_processor_unchecked', '_set_all_checked')]
        namespace = {}
        exec(compile(ast.Module(body=methods, type_ignores=[]), 'batch-close-guards', 'exec'), namespace)
        dialog = types.SimpleNamespace(_running=True, _request_cancel=mock.Mock())
        event = types.SimpleNamespace(ignore=mock.Mock())
        namespace['reject'](dialog)
        namespace['closeEvent'](dialog, event)
        self.assertEqual(dialog._request_cancel.call_count, 2)
        event.ignore.assert_called_once()
        for name in ('_browse_source', '_browse_output', '_browse_sbs', '_scan',
                     '_inspect_processor', '_mark_processor_unchecked'):
            namespace[name](dialog)  # 若无运行锁，会访问未提供的 Qt/资源对象并失败。
        namespace['_set_all_checked'](dialog, True)


if __name__ == '__main__':
    unittest.main()
