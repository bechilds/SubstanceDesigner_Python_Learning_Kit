import sys#sys 是 Python 的一个内置标准库，它的名字是 "System"（系统）的缩写。它提供了一个访问由 Python 解释器使用或维护的变量和函数的途径。你可以把它想象成 Python 解释器本身的 “控制面板” 或**“状态监视器”**。通过 sys 模块，你可以获取到很多关于当前运行环境的信息，比如 Python 版本、操作系统平台，以及我们这里用到的——已加载的模块列表。

# 打印 PySide2 是否已加载
print(f"PySide2 是否已加载: {'PySide2' in sys.modules}")
#sys.modules 是什么？这是 sys 模块里一个非常重要的变量。它是一个字典 (Dictionary)。它就像一个 “模块缓存” 或**“已加载模块登记表”**。每当你的 Python 程序执行一个 import 语句（比如 import math）时，Python 解释器会做两件事：
# 找到并加载 math 模块到内存中。
# 在这个 sys.modules 字典里添加一个条目，key 是模块名 'math'，value 是加载后的 math 模块对象本身。
# 下次如果再有代码执行 import math，Python 会先检查 sys.modules 这个“登记表”，发现 'math' 已经在了，就直接从缓存中获取，而不会重新加载一遍，这样可以大大提高效率。
#'PySide2' in sys.modules
# 这是什么操作？
# 这是 Python 中检查一个键 (key) 是否存在于一个字典 (dictionary) 中的标准语法。
# 它的返回值是什么？
# 一个布尔值：True 或 False。
# 如何理解？
# 这行代码的意思就是：“请到 sys.modules 这个‘已加载模块登记表’里看一看，有没有一个叫做 'PySide2' 的键？”
# 如果有，说明 PySide2 模块在之前的某个时间点已经被加载过了，表达式返回 True。
# 如果没有，说明到目前为止还没有加载过 PySide2，表达式返回 False。

# 打印 PySide6 是否已加载
print(f"PySide6 是否已加载: {'PySide6' in sys.modules}")



# print(f"...")
# f"..." 是什么？
# 这被称为 f-string (Formatted String Literals)，是 Python 3.6+ 版本引入的一种非常方便的字符串格式化方法。
# 它如何工作？
# 它允许你直接在字符串中嵌入用花括号 {} 包裹起来的 Python 表达式。在运行时，花括号里的表达式会被求值，其结果会直接转换成字符串并插入到那个位置。
# 在本例中:
# f"PySide2 是否已加载: {'PySide2' in sys.modules}"
# Python 先计算花括号里的表达式 {'PySide2' in sys.modules}，得到结果 True 或 False。
# 然后将这个结果转换成字符串 'True' 或 'False'。
# 最后，将它拼接到整个字符串中，最终打印出 PySide2 是否已加载: True 或 PySide2 是否已加载: False。

