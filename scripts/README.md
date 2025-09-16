# 您的自定义脚本文件夹

这个文件夹是用来存放您自己编写的 Substance Designer Python 脚本的地方。

## 📁 文件夹用途

- 存放您根据教程学习后创建的自定义脚本
- 保存修改过的示例脚本
- 存放针对您特定需求开发的工具脚本

## 💡 脚本命名建议

为了便于管理，建议使用以下命名规则：

- `my_[功能描述].py` - 个人脚本
- `cleanup_[具体清理内容].py` - 清理相关脚本
- `batch_[批处理内容].py` - 批处理脚本
- `auto_[自动化内容].py` - 自动化脚本

例如：
- `my_parameter_organizer.py` - 参数整理器
- `cleanup_unused_nodes.py` - 清理未使用节点
- `batch_export_textures.py` - 批量导出纹理
- `auto_connect_nodes.py` - 自动连接节点

## 🔧 脚本模板

您可以复制以下模板来开始创建新脚本：

```python
"""
脚本名称: [在此描述脚本功能]
作者: [您的名字]
创建日期: [日期]
功能描述: [详细描述这个脚本的作用]

使用方法:
1. 在 Substance Designer 中打开 .sbs 文件
2. 在脚本编辑器中运行此脚本
3. 按照提示操作
"""

import sd
from sd.api.sdproperty import *

def main():
    """
    主函数 - 在此编写您的脚本逻辑
    """
    print("🚀 启动自定义脚本...")
    
    try:
        # 连接到 Substance Designer
        context = sd.getContext()
        app = context.getSDApplication()
        package_mgr = app.getPackageMgr()
        
        # 获取当前包
        packages = package_mgr.getUserPackages()
        if not packages:
            print("❌ 未找到已加载的包，请先打开一个 .sbs 文件")
            return
        
        current_package = packages[0]
        print(f"📦 当前包: {current_package.getFilePath()}")
        
        # 获取当前图形
        graphs = current_package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        if not graphs:
            print("❌ 未找到图形")
            return
        
        current_graph = graphs[0]
        print(f"📊 当前图形: {current_graph.getIdentifier()}")
        
        # 在此处添加您的脚本逻辑
        # =================================
        
        print("这里是您的自定义代码区域")
        
        # =================================
        
        print("✅ 脚本执行完成!")
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        print("💡 请检查 Substance Designer 是否正在运行并且已加载材质文件")

if __name__ == "__main__":
    main()
```

## 📚 从哪里开始

1. **先完成教程** - 确保您已经完成了 `tutorials/` 文件夹中的所有教程
2. **研究示例** - 仔细阅读 `examples/` 文件夹中的示例脚本
3. **复制修改** - 从复制示例脚本开始，然后根据需要修改
4. **逐步扩展** - 从简单功能开始，逐步添加更复杂的功能

## 🎯 建议的第一个脚本

尝试创建一个简单的信息显示脚本：

```python
# my_material_info.py
# 显示当前材质的基本信息

import sd
from sd.api.sdproperty import *

def show_material_info():
    context = sd.getContext()
    app = context.getSDApplication()
    package_mgr = app.getPackageMgr()
    
    packages = package_mgr.getUserPackages()
    if packages:
        package = packages[0]
        graphs = package.getChildrenOfType(sd.api.sdgraph.SDGraph)
        
        if graphs:
            graph = graphs[0]
            nodes = graph.getNodes()
            params = graph.getExposedParameters()
            
            print(f"材质信息:")
            print(f"- 文件: {package.getFilePath()}")
            print(f"- 图形: {graph.getIdentifier()}")
            print(f"- 节点数量: {len(nodes)}")
            print(f"- 暴露参数: {len(params)}")

if __name__ == "__main__":
    show_material_info()
```

祝您编程愉快！🎨

---

## 🧩 版本控制辅助脚本

本文件夹包含两个快速配置 Git 远程与初始推送的脚本：

| 文件 | 作用 |
|------|------|
| `setup_git_remote.ps1` | Windows/PowerShell 脚本：初始化仓库、添加 Gitee/GitHub 远程、可选在远端创建裸仓库并推送 |
| `setup_git_remote.sh` | Linux / macOS / WSL Bash 版本功能相同 |

### PowerShell 使用示例
```powershell
./scripts/setup_git_remote.ps1 -Gitee git@gitee.com:用户名/仓库.git -GitHub git@github.com:用户名/仓库.git -ForceInitialCommit
```

### Bash 使用示例
```bash
bash scripts/setup_git_remote.sh --gitee git@gitee.com:用户名/仓库.git --github git@github.com:用户名/仓库.git --force
```

### 参数说明（部分）
- Gitee / --gitee  必填，主远程
- GitHub / --github  可选备份远程
- ForceInitialCommit / --force  没有提交或强制重新提交初始
- CreateBareOnHost / --create-bare  通过 SSH 在远端创建裸仓库（若不存在）
- SkipPush / --skip-push  仅配置不推送

### 快速工作流
1. 先写脚本/学习内容
2. 运行上述脚本初始化并推送
3. 在另一台设备 `git clone ...`
4. 按最小循环：`pull → 修改 → add → commit → push`

更多对比详见：`docs/version_control_options.md`

---
