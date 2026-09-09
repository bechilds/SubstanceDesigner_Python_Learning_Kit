# -*- coding: utf-8 -*-
"""审核发现的数据边界回归；不操作真实 Designer 或源资源。"""
import ast
import contextlib
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1] / 'MaxSDPlugins'


def load_functions(file, names, namespace):
    tree = ast.parse((ROOT / file).read_text(encoding='utf-8'))
    nodes = [node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), file, 'exec'), namespace)
    return namespace


class ScopeTests(unittest.TestCase):
    def setUp(self):
        ns = load_functions('switch_manager/logic.py', {'get_graph_scope'},
                            {'os': os, '_SD_API_ERRORS': (Exception,)})
        self.scope = ns['get_graph_scope']
        self.a = self.graph('package-a', 'graph')
        self.b = self.graph('package-b', 'graph')
        self.logic = SimpleNamespace(get_current_graph=lambda: self.a,
                                     get_graph_scope=self.scope)
        for name in ('create_boolean_switch', 'repair_boolean_switch_editors',
                     'assign_switch', 'update_parameter_values', 'clear_visible_if'):
            setattr(self.logic, name, Mock(return_value={'updated': ['value'], 'failed': []}))
        self.box = SimpleNamespace(Yes=1, No=0, question=Mock(return_value=1),
                                   information=Mock())
        ns = load_functions('switch_manager/window.py', {
            '_checked_graph', '_create_switch', '_repair_switch_editors',
            '_apply_switch', '_apply_value_changes', '_clear_visible_if'},
            {'logic': self.logic, 'QtWidgets': SimpleNamespace(QMessageBox=self.box)})
        cls = type('Dialog', (), {key: value for key, value in ns.items()
                                  if key.startswith('_') and callable(value)})
        self.dialog = cls()
        self.dialog._scope = self.scope(self.a)
        self.dialog._warn = Mock()
        self.dialog._refresh = Mock()
        self.dialog.windowTitle = lambda: 'review'
        self.dialog._current_switch_id = lambda: 'enabled'
        self.dialog._checked_ids = lambda: ['value']
        self.dialog._changed_values = lambda: [{'id': 'value', 'value': '0.9', 'type': 'float'}]
        self.dialog._switch_group = SimpleNamespace(currentText=lambda: 'group')

    @staticmethod
    def graph(uid, identifier, path=''):
        package = SimpleNamespace(getUID=lambda: uid, getFilePath=lambda: path)
        return SimpleNamespace(getPackage=lambda: package, getIdentifier=lambda: identifier)

    def test_all_writes_reject_changed_or_unavailable_graph(self):
        for graph in (self.b, self.graph('package-a', 'other'), None):
            self.logic.get_current_graph = lambda: graph
            for method in ('_create_switch', '_repair_switch_editors', '_apply_switch',
                           '_apply_value_changes', '_clear_visible_if'):
                getattr(self.dialog, method)()
        for name in ('create_boolean_switch', 'repair_boolean_switch_editors',
                     'assign_switch', 'update_parameter_values', 'clear_visible_if'):
            getattr(self.logic, name).assert_not_called()
        self.dialog._refresh.assert_not_called()  # 禁止顺带保存错误的 Package。

    def test_same_graph_allows_value_write(self):
        self.dialog._apply_value_changes()
        self.logic.update_parameter_values.assert_called_once_with(
            self.a, self.dialog._changed_values())
        self.dialog._refresh.assert_called_once_with(sync_package=True)

    def test_graph_switch_during_confirmation_is_rechecked(self):
        def switch(*args):
            self.logic.get_current_graph = lambda: self.b
            return 1
        self.box.question.side_effect = switch
        for method in ('_apply_switch', '_clear_visible_if'):
            self.logic.get_current_graph = lambda: self.a
            getattr(self.dialog, method)()
        self.logic.assign_switch.assert_not_called()
        self.logic.clear_visible_if.assert_not_called()

    def test_scope_handles_unsaved_and_duplicate_package_ids(self):
        self.assertNotEqual(self.scope(self.a), self.scope(self.b))
        self.assertNotEqual(self.scope(self.graph('uid', 'g', 'a.sbs')),
                            self.scope(self.graph('uid', 'g', 'b.sbs')))
        self.assertIsNone(self.scope(SimpleNamespace()))


class Preset:
    def __init__(self, fail_input=False):
        self.tags, self.inputs = '', []
        self.fail_input = fail_input

    def getUserTags(self):
        return self.tags

    def setUserTags(self, tags):
        self.tags = tags

    def getInputs(self):
        return [SimpleNamespace(getIdentifier=lambda key=key: key,
                                getValue=lambda value=value: value)
                for key, value in self.inputs]

    def addInput(self, key, value):
        if self.fail_input:
            raise RuntimeError('input failed')
        self.inputs.append((key, value))


class PresetGraph:
    def __init__(self, failure='', existing=True):
        self.preset = Preset() if existing else None
        if self.preset:
            self.preset.tags, self.preset.inputs = 'original tags', [('old', 0.1)]
        self.failure, self.creations = failure, 0

    def getPreset(self, label):
        return self.preset

    def deletePreset(self, label):
        self.preset = None

    def newPreset(self, label):
        self.creations += 1
        if self.failure == 'restore' or (self.failure == 'create' and self.creations == 1):
            raise RuntimeError('create failed')
        self.preset = Preset(self.failure == 'input' and self.creations == 1)
        return self.preset


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_functions('preset_recovery/logic.py', {
            '_snapshot_preset', '_restore_preset', 'create_or_replace_preset'},
            {'_SD_ERRORS': (Exception,), '_undo_group': lambda name: contextlib.nullcontext(),
             '_LOG': '[review]'})

    def test_creation_and_input_failure_restore_original_tags_and_values(self):
        for failure in ('create', 'input'):
            graph = PresetGraph(failure)
            with self.assertRaises(ValueError):
                self.ns['create_or_replace_preset'](graph, 'preset', [('new', 1)], True)
            self.assertEqual(graph.preset.tags, 'original tags')
            self.assertEqual(graph.preset.inputs, [('old', 0.1)])

    def test_recovery_failure_reports_both_failures(self):
        with self.assertRaisesRegex(ValueError, '写入失败.*恢复失败'):
            self.ns['create_or_replace_preset'](PresetGraph('restore'), 'preset', [('new', 1)], True)

    def test_new_preset_input_failure_removes_partial_preset(self):
        graph = PresetGraph('input', existing=False)
        with self.assertRaises(ValueError):
            self.ns['create_or_replace_preset'](graph, 'preset', [('new', 1)])
        self.assertIsNone(graph.preset)

    def test_successful_create_and_replace(self):
        for existing in (False, True):
            graph = PresetGraph(existing=existing)
            result = self.ns['create_or_replace_preset'](graph, 'preset', [('new', 1)], True)
            self.assertEqual(result, 'replaced' if existing else 'created')
            self.assertEqual(graph.preset.inputs, [('new', 1)])


class ResourceNameTests(unittest.TestCase):
    def test_hash_and_numbered_names_are_checked_case_insensitively(self):
        ns = load_functions('save_with_resource/save_with_resource.py', {'_copy_name'},
                            {'hashlib': hashlib, 'os': os})
        source = 'C:/c/foo.png'
        suffix = hashlib.sha1(source.lower().encode('utf-8')).hexdigest()[:8]
        used = set()
        sources = ['C:/a/foo.png', f'C:/b/foo_{suffix}.PNG',
                   f'C:/b/foo_{suffix}_2.png', source]
        names = [ns['_copy_name'](path, used) for path in sources]
        self.assertEqual(len({name.lower() for name in names}), len(sources))
        self.assertEqual(names[-1], f'foo_{suffix}_3.png')
