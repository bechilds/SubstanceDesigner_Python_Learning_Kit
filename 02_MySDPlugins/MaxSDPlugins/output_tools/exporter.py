# -*- coding: utf-8 -*-
"""无 Qt/SD 依赖的导出层：依赖闭包、资源、独立脚本与 MG 输出。

独立脚本保留真实包结构和相对 import，避免源码文本替换导致缺失符号。
MG 使用 AST 定位 import，仅改写导入语句，保留其余源代码与设置名称。
"""

import ast
import base64
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile


def plugin_root():
    return Path(__file__).resolve().parents[1]


def catalog(root):
    result = {}
    for path in root.rglob('*.py'):
        rel = path.relative_to(root)
        if any(part.startswith('.') or part == '__pycache__' for part in rel.parts):
            continue
        parts = list(rel.with_suffix('').parts)
        if parts[-1] == '__init__':
            parts.pop()
        name = '.'.join(parts)
        if name and name not in ('MaxSDPlugin', 'menu'):
            result[name] = path
    return result


def _base(name, is_package, node):
    parts = name.split('.') if is_package else name.split('.')[:-1]
    if node.level > len(parts) + 1:
        raise ValueError(f'{name}: 相对 import 超出插件根目录')
    parts = parts[:len(parts) - node.level + 1]
    if node.module:
        parts += node.module.split('.')
    return '.'.join(parts)


def dependencies(name, path, modules):
    """包括函数内部的延迟 import；无法解析的相对依赖直接阻止导出。"""
    source = path.read_text(encoding='utf-8')
    compile(source, str(path), 'exec')
    tree = ast.parse(source, filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        base = _base(name, path.name == '__init__.py', node)
        if base:
            if base not in modules:
                raise ValueError(f'{name}: 找不到依赖 {base}')
            found.add(base)
        for alias in node.names:
            child = '.'.join(filter(None, (base, alias.name)))
            if child in modules:
                found.add(child)
            elif not base:
                raise ValueError(f'{name}: 找不到根模块 {alias.name}')
    return found


def build_plan(module_paths, root=None):
    """校验输入并递归补齐模块及包入口。绝不执行插件代码。"""
    root = Path(root or plugin_root()).resolve()
    modules = catalog(root)
    by_path = {path.resolve(): name for name, path in modules.items()}
    selected = []
    for path in module_paths:
        resolved = Path(path).resolve()
        if resolved not in by_path:
            raise ValueError(f'不是可导出的插件模块: {path}')
        if by_path[resolved] not in selected:
            selected.append(by_path[resolved])
    if not selected:
        raise ValueError('未选择任何功能。')
    pending = selected + ['sdcompat']
    included = set()
    while pending:
        name = pending.pop()
        if name in included:
            continue
        if name not in modules:
            raise ValueError(f'找不到依赖: {name}')
        included.add(name)
        parts = name.split('.')
        pending.extend('.'.join(parts[:i]) for i in range(1, len(parts)))
        pending.extend(dependencies(name, modules[name], modules) - included)
    sources = {name: modules[name] for name in sorted(included)}
    resources = {}
    if any(name.startswith('batch_merge_tex_channel') for name in included):
        # 保留旧资源位置，避免破坏已有 SBS 链接。导出目录沿用相同布局。
        resource = root / 'BatchMergeTexChannel.sbs'
        if not resource.is_file():
            raise FileNotFoundError(f'缺少必需资源: {resource}')
        resources['BatchMergeTexChannel.sbs'] = resource
    return root, selected, sources, resources


def _atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def export_modules(module_paths, out_path, sd_version='auto'):
    """兼容旧签名；sd_version 保留，产物始终运行时适配 SD13/16。"""
    try:
        root, selected, sources, resources = build_plan(module_paths)
        if Path(out_path).resolve().is_relative_to(root):
            raise ValueError('请导出到插件源目录之外，避免覆盖源文件或被再次扫描。')
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('__init__.py', '# Synthetic package: no SD plugin registration\n')
            for path in sources.values():
                archive.write(path, path.relative_to(root).as_posix())
            for rel, path in resources.items():
                archive.write(path, rel)
        encoded = base64.b64encode(payload.getvalue()).decode('ascii')
        script = _BUNDLE_TEMPLATE.replace('__PAYLOAD__', repr(encoded)).replace(
            '__MODULES__', repr([name for name in sources if name != 'sdcompat'])).replace(
            '__ENTRIES__', repr(selected))
        compile(script, str(out_path), 'exec')
        _atomic_write(out_path, script.encode('utf-8'))
        return True, (f'已导出 {len(selected)} 个所选模块，补齐依赖后共 {len(sources)} 个模块、'
                      f'{len(resources)} 个资源。\n{out_path}\n'
                      '宿主调用 maxsd_activate() 取得入口；结束时调用 maxsd_shutdown()。')
    except Exception as error:
        return False, f'导出失败（未修改源代码）: {error}'


def _mg_names(modules):
    counts = {}
    for name in modules:
        leaf = name.rsplit('.', 1)[-1]
        counts[leaf] = counts.get(leaf, 0) + 1
    return {name: 'LG_MaxSD_' + (name.replace('.', '_') if counts[name.rsplit('.', 1)[-1]] > 1
                                else name.rsplit('.', 1)[-1]) for name in modules}


def rewrite_mg_source(source, name, is_package, modules, names):
    """保留注释、缩进和无关字符串；支持多行/别名/函数内部相对导入。"""
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        base = _base(name, is_package, node)
        statements = []
        for alias in node.names:
            child = '.'.join(filter(None, (base, alias.name)))
            if child in modules:
                statements.append(f'import {names[child]} as {alias.asname or alias.name}')
            elif base in names:
                imported = alias.name + (f' as {alias.asname}' if alias.asname else '')
                statements.append(f'from {names[base]} import {imported}')
            else:
                raise ValueError(f'{name}: 无法解析 import {base}/{alias.name}')
        def offset(line_number, byte_column):
            return offsets[line_number - 1] + len(
                lines[line_number - 1].encode('utf-8')[:byte_column].decode('utf-8'))
        edits.append((offset(node.lineno, node.col_offset),
                      offset(node.end_lineno, node.end_col_offset), '; '.join(statements)))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    compile(source, name, 'exec')
    return source


def export_modules_to_mg(module_paths, output_root):
    """自动补齐依赖后写 MG 文件；名称不随本次勾选组合变化。"""
    try:
        if not output_root:
            raise ValueError('未指定 MG 输出目录。')
        root, selected, sources, resources = build_plan(module_paths)
        target = Path(output_root).resolve()
        if target == root or target.is_relative_to(root):
            raise ValueError('MG 输出目录不能位于插件源目录内。')
        names = _mg_names(catalog(root))
        planned = {}
        for name, path in sources.items():
            rel = path.relative_to(root)
            # 包入口与其分类模块放在同一目录；宿主 loader 需要注册这些目录。
            dest = rel.parent / (names[name] + '.py')
            source = path.read_text(encoding='utf-8')
            planned[dest.as_posix()] = rewrite_mg_source(
                source, name, path.name == '__init__.py', sources, names).encode('utf-8')
        for rel, path in resources.items():
            planned[rel] = path.read_bytes()
        manifest = {
            'schema_version': 1, 'selected_modules': selected,
            'modules': {name: names[name] for name in sources},
            'files': sorted(planned), 'resources': sorted(resources),
            'note': '开发导出，不代表已经部署或完成 SD13/16 宿主验证；Start/LG_Tool 不自动修改。',
        }
        planned['maxsd_export_manifest.json'] = json.dumps(
            manifest, ensure_ascii=False, indent=2).encode('utf-8')
        # 所有源和 import 均先校验完成。逐文件原子写入；不是跨文件事务。
        written = []
        try:
            for rel, content in planned.items():
                _atomic_write(target / rel, content)
                written.append(rel)
        except OSError as error:
            return False, f'MG 写出中断: {error}\n已写出（请勿部署半成品）: ' + ', '.join(written)
        return True, (f'已输出 {len(sources)} 个模块、{len(resources)} 个资源到:\n{target}\n'
                      '依赖已自动补齐。请通过 MG loader 注册根目录与分类目录；'
                      'Start.py / LG_Tool.py 和正式发布台账仍需人工确认。')
    except Exception as error:
        return False, f'MG 导出失败: {error}'


_BUNDLE_TEMPLATE = '''# -*- coding: utf-8 -*-
"""MaxSD 开发导出：保留真实包、相对 import 和资源。需要 SD 宿主。"""
import base64 as _b64
import importlib as _importlib
import importlib.util as _util
import io as _io
import os as _os
import sys as _sys
import tempfile as _tempfile
import uuid as _uuid
import zipfile as _zipfile

_MAXSD_PKG = '_maxsd_bundle_' + _uuid.uuid4().hex
_maxsd_temp = _tempfile.TemporaryDirectory(prefix='MaxSD_export_')
_maxsd_root = _maxsd_temp.name
maxsd_show_windows = {}

def maxsd_shutdown():
    """关闭窗口、移除本导出物模块和临时资源；忙时返回 False。"""
    lifecycle = _sys.modules.get(_MAXSD_PKG + '.shared.lifecycle')
    if lifecycle is not None and not lifecycle.close_all_dialogs():
        return False
    for name in list(_sys.modules):
        if name == _MAXSD_PKG or name.startswith(_MAXSD_PKG + '.'):
            del _sys.modules[name]
    maxsd_show_windows.clear()
    _maxsd_temp.cleanup()
    return True

try:
    with _zipfile.ZipFile(_io.BytesIO(_b64.b64decode(__PAYLOAD__))) as archive:
        archive.extractall(_maxsd_root)
    spec = _util.spec_from_file_location(_MAXSD_PKG, _os.path.join(_maxsd_root, '__init__.py'),
                                         submodule_search_locations=[_maxsd_root])
    package = _util.module_from_spec(spec)
    _sys.modules[_MAXSD_PKG] = package
    spec.loader.exec_module(package)
    _maxsd_compat = _importlib.import_module(_MAXSD_PKG + '.sdcompat')
    _maxsd_compat.qt_patch()
    for name in __MODULES__:
        module = _importlib.import_module(_MAXSD_PKG + '.' + name)
        # 包入口与实现指向同一函数时，只保留原来的“分类_模块”键。
        if name in __ENTRIES__ and hasattr(module, 'show_window'):
            maxsd_show_windows[name.replace('.', '_')] = module.show_window
except BaseException:
    maxsd_shutdown()
    raise

def maxsd_activate(main_win=None):
    return maxsd_show_windows

def maxsd_show_all(main_win=None):
    shown = []
    for name, entry in list(maxsd_show_windows.items()):
        try:
            if entry(main_win) is not None:
                shown.append(name)
        except _maxsd_compat.SD_API_ERRORS as error:
            print('[MaxSD-export] 打开窗口失败:', name, _maxsd_compat.error_text(error))
    return shown

if __name__ == '__main__':
    print('[MaxSD-export] 窗口:', maxsd_show_all())
'''
