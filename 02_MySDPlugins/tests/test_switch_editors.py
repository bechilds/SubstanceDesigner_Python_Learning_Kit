# -*- coding: utf-8 -*-
"""不加载 SD 的边界回归；真实发布格式另用 Adobe cooker 验证。"""
import ast
import contextlib
from pathlib import Path
from types import SimpleNamespace
import unittest


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    sNew = classmethod(lambda cls, value=None: cls(value))


class Property:
    def __init__(self, key, group="EyeGroup", kind="bool", editor="", pin=False):
        self.key, self.group, self.kind = key, group, kind
        self.editor, self.pin, self.value = editor, pin, False

    def getId(self):
        return self.key

    def getType(self):
        return SimpleNamespace(getId=lambda: self.kind)

    def isConnectable(self):
        return self.pin


class Graph:
    def __init__(self, props=(), failure=""):
        self.props = {p.key: p for p in props}
        self.failure = failure
        self.writes = []

    def getProperties(self, category):
        return list(self.props.values())

    def getPropertyFromId(self, key, category):
        return self.props.get(key)

    def newProperty(self, key, kind, category):
        prop = Property(key)
        self.props[key] = prop
        return prop

    def deleteProperty(self, prop):
        del self.props[prop.key]

    def getPropertyAnnotationValueFromId(self, prop, key):
        return Value(prop.editor)

    def setPropertyAnnotationValueFromId(self, prop, key, value):
        self.writes.append((prop.key, key, value.get()))
        if self.failure == "raise":
            raise RuntimeError("unsupported editor")
        if self.failure != "ignore":
            prop.editor = value.get()

    def setPropertyValue(self, prop, value):
        prop.value = value.get()


class SwitchEditorTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'MaxSDPlugins/switch_manager/logic.py'
        names = {'create_boolean_switch', '_ensure_boolean_editor',
                 'repair_boolean_switch_editors', '_is_boolean_parameter', '_error_text'}
        tree = ast.parse(path.read_text(encoding='utf-8'))
        tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        self.ns = dict(SDPropertyCategory=SimpleNamespace(Input=0), SDTypeBool=Value,
                       SDValueBool=Value, SDValueString=Value, _SD_API_ERRORS=(Exception,),
                       _undo_group=lambda name: contextlib.nullcontext(),
                       _read_group=lambda graph, prop: prop.group,
                       _set_text_setting=lambda *args: (True, []))
        exec(compile(tree, str(path), 'exec'), self.ns)

    def test_creation_sets_editor_and_keeps_initial_value(self):
        for initial in (True, False):
            graph = Graph()
            self.ns['create_boolean_switch'](graph, '02', '02', 'EyeGroup', initial)
            self.assertEqual(graph.writes, [('02', 'editor', 'buttons')])
            self.assertIs(graph.props['02'].value, initial)

    def test_failed_or_ignored_editor_write_removes_new_property(self):
        for failure in ('raise', 'ignore'):
            old = Property('01', editor='buttons')
            graph = Graph([old], failure)
            with self.assertRaises(RuntimeError):
                self.ns['create_boolean_switch'](graph, '02', '02', 'EyeGroup')
            self.assertEqual(graph.props, {'01': old})

    def test_repair_scope_preserves_existing_editors_and_values(self):
        props = [Property('01', editor='buttons'), Property('02'),
                 Property('03', editor='dropdownlist'), Property('04', group='Other'),
                 Property('05', kind='int'), Property('06', pin=True)]
        graph = Graph(props)
        result = self.ns['repair_boolean_switch_editors'](graph, 'EyeGroup')
        self.assertEqual(result, {'updated': ['02'], 'skipped': ['01', '03'], 'failed': []})
        self.assertEqual(graph.writes, [('02', 'editor', 'buttons')])
        self.assertTrue(all(p.value is False for p in props))
        self.assertEqual(self.ns['repair_boolean_switch_editors'](graph, 'EyeGroup')['updated'], [])

    def test_repair_failure_is_not_reported_as_success(self):
        result = self.ns['repair_boolean_switch_editors'](Graph([Property('02')], 'ignore'), 'EyeGroup')
        self.assertEqual(result['updated'], [])
        self.assertEqual(result['failed'][0][0], '02')

    def test_duplicate_creation_and_empty_group_do_not_write(self):
        graph = Graph([Property('01')])
        with self.assertRaises(ValueError):
            self.ns['create_boolean_switch'](graph, '01', '01', 'EyeGroup')
        self.ns['repair_boolean_switch_editors'](graph, '')
        self.assertEqual(graph.writes, [])
