# 高级教程 B：批量重命名选中节点（Batch Rename Selected Nodes）

> 目标：在 LGNode 插件菜单中增加一个动作，对当前图（Graph）中**选中的多个节点**批量重命名，并支持添加前缀 / 后缀 / 自动编号。
>
> 难度：★☆☆（基础进阶）  
> 适合：已经完成基础菜单插件并希望做第一个“实用操作”功能的你。

---
## 你将学到
- 如何获取当前活动图（Graph）
- 如何获取当前选中节点列表
- 如何读取和修改节点 Identifier（名称）
- 如何构建简单的命名规则（前缀 / 后缀 / 序号）
- 如何在失败时做安全回退

---
## 1. 背景知识
Substance Designer 中 **节点 ID（Identifier）** 是图里显示的节点名称。我们可以通过：
- `app.getUIMgr().getCurrentGraph()` 或通过 `sd.getContext()` 取得 Graph 管理路径
- Graph 对象可提供 `getSelectedNodes()`（部分版本需要 UI 管理器协助）

> 注意：某些版本中只能通过 UI 层访问当前选择。如果你遇到空列表，请先确认你真的框选了节点，并且焦点在 Graph 编辑窗口。

---
## 2. 功能设计
我们要添加一个菜单项：`LGNode > Batch > Rename Selected Nodes...`
执行后：
1. 弹出一个简单输入对话框（前缀、后缀、起始序号、是否保留原名）
2. 对每个选中节点应用命名规则：`前缀 + (原名或基名) + 序号 + 后缀`
3. 序号可自动递增（支持填充位数比如 001, 002）
4. 在控制台和日志打印结果

---
## 3. 代码示例（可直接集成）
将下列核心逻辑整合进你的 `LGNodeLibrary` 类；或参考本教程附带的例子文件：`examples/lgnode_batch_rename.py`。

```python
from PySide2 import QtWidgets
import sd
import re

class BatchRenamer:
    def __init__(self, log_func=print):
        self._log = log_func

    def run(self):
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        ui_mgr = app.getQtForPythonUIMgr()
        graph = ui_mgr.getCurrentGraph()
        if graph is None:
            self._log('[BatchRename] 没有活动的 Graph。')
            QtWidgets.QMessageBox.warning(ui_mgr.getMainWindow(), 'Batch Rename', '没有找到当前图 (Graph)。')
            return

        nodes = list(graph.getSelectedNodes())
        if not nodes:
            self._log('[BatchRename] 没有选中节点。')
            QtWidgets.QMessageBox.information(ui_mgr.getMainWindow(), 'Batch Rename', '请先选择至少一个节点。')
            return

        dlg = BatchRenameDialog(ui_mgr.getMainWindow())
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        cfg = dlg.get_config()
        self._apply(nodes, cfg)

    def _apply(self, nodes, cfg):
        pad = cfg['padding']
        start = cfg['start_index']
        prefix = cfg['prefix']
        suffix = cfg['suffix']
        use_original = cfg['keep_original']

        for i, node in enumerate(nodes):
            original_id = node.getIdentifier()
            base = original_id if use_original else cfg['base_name'] or 'Node'
            number = str(start + i).zfill(pad)
            new_id = f"{prefix}{base}{number}{suffix}"
            # 清理非法字符（可选）
            new_id = re.sub(r'[^A-Za-z0-9_\-]', '_', new_id)
            try:
                node.setIdentifier(new_id)
                self._log(f"[BatchRename] {original_id} -> {new_id}")
            except Exception as e:
                self._log(f"[BatchRename] 重命名失败 {original_id}: {e}")

class BatchRenameDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Batch Rename Nodes')
        self.setMinimumWidth(320)

        self.prefix_edit = QtWidgets.QLineEdit('')
        self.base_edit = QtWidgets.QLineEdit('Base')
        self.keep_original_chk = QtWidgets.QCheckBox('使用原节点名作为中间部分 (忽略 Base)')
        self.suffix_edit = QtWidgets.QLineEdit('')
        self.start_spin = QtWidgets.QSpinBox(); self.start_spin.setValue(1)
        self.padding_spin = QtWidgets.QSpinBox(); self.padding_spin.setRange(1,6); self.padding_spin.setValue(2)

        form = QtWidgets.QFormLayout()
        form.addRow('前缀 Prefix:', self.prefix_edit)
        form.addRow('基础 Base 名:', self.base_edit)
        form.addRow('', self.keep_original_chk)
        form.addRow('后缀 Suffix:', self.suffix_edit)
        form.addRow('起始序号 Start:', self.start_spin)
        form.addRow('数字位数 Padding:', self.padding_spin)

        btn_ok = QtWidgets.QPushButton('确定')
        btn_cancel = QtWidgets.QPushButton('取消')
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        h = QtWidgets.QHBoxLayout(); h.addStretch(1); h.addWidget(btn_ok); h.addWidget(btn_cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(h)

    def get_config(self):
        return {
            'prefix': self.prefix_edit.text(),
            'base_name': self.base_edit.text(),
            'suffix': self.suffix_edit.text(),
            'start_index': self.start_spin.value(),
            'padding': self.padding_spin.value(),
            'keep_original': self.keep_original_chk.isChecked(),
        }
```

### 在菜单中注册
在你的插件 `onInitializeSDUIMgr` 里添加：
```python
batch_menu = self._menu.addMenu('Batch')
rename_action = QtWidgets.QAction('Rename Selected Nodes...', self._menu)
rename_action.triggered.connect(lambda: BatchRenamer(self._log if hasattr(self,'_log') else print).run())
batch_menu.addAction(rename_action)
```

---
## 4. 运行示例
1. 选中 3 个节点（名字假设：`blend1`, `blend2`, `blend3`）
2. 设置：前缀 `LG_`，Base = `Layer`，起始 1，位数 3，后缀 `_A`，不勾选“使用原节点名”
3. 结果：
   - `LG_Layer001_A`
   - `LG_Layer002_A`
   - `LG_Layer003_A`

如果勾选“使用原节点名”：
- `LG_blend1001_A`（Base 会被忽略，直接用原名 + 编号）

---
## 5. 常见问题 (Troubleshooting)
| 问题 | 说明 | 解决 |
|------|------|------|
| 选中节点为空 | 焦点不在 Graph 或未选中 | 重点选节点再执行 |
| 重命名失败 | 节点锁定 / Designer 状态异常 | 单独尝试一个节点 / 重启 |
| 中文或特殊字符被替换 | 正则清理了非 ASCII | 可修改正则允许中文 |
| 多次执行编号续接 | 起始值记得手动调整 | 设置新的 start_index |

---
## 6. 扩展练习
- 添加“预览结果”按钮（先列出新名字，再确认）
- 支持“只改前缀”或“只改后缀”模式
- 记录上一次对话框输入（写入 JSON）
- 增加“撤销”功能：缓存原名列表，提供一次性还原

---
## 7. 附：安全性建议
批量操作前不要随手保存，可在 Designer 内试运行；如要大量修改生产文件，请先复制工程。

---
完成！继续前往：**教程 C：节点模板批量创建**。
