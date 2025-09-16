# 版本控制与多设备同步方案概览

面向本项目（Substance Designer Python 学习）的多设备与备份需求，下面总结常见方案、适用场景、优缺点与快速上手命令。

## 🧭 什么时候需要版本控制？
- 在两台或更多设备之间保持脚本一致
- 希望回溯早期版本 / 防止误删
- 想记录学习过程（提交日志）
- 准备与他人协作或展示

## 🥇 首选方案：Git（Gitee + 可选 GitHub 备份）
| 特性 | 说明 |
|------|------|
| 分布式 | 每台机器完整历史，离线可 commit |
| 分支灵活 | 可尝试实验脚本不影响主线 |
| 生态广 | 文档/社区最多 |
| 适合 | 学习、个人成长、以后协作 |

### 本地已有项目首次推送（Gitee 示例）
```bash
git init
git add .
git commit -m "chore: initial commit"
git remote add origin git@gitee.com:你的用户名/仓库名.git
git push -u origin main
```

### 另一设备获取
```bash
git clone git@gitee.com:你的用户名/仓库名.git
```

### 日常循环
```bash
git pull --rebase origin main
# 修改...
git add .
git commit -m "feat: 添加节点操作示例"
git push origin main
```

### 可选：GitHub 备份
```bash
git remote add github git@github.com:yourname/repo.git
git push -u github main
```

## 🥈 备选方案：SVN（集中式）
| 特性 | 说明 |
|------|------|
| 集中式 | 服务器保存完整历史，工作副本只取需要内容 |
| 线性历史 | 流程简单：update → 编辑 → commit |
| 分支成本高 | 不适合频繁分支实验 |
| 适合 | 想体验传统集中模式 / 线性流程 |

### 创建仓库（服务器或 NAS 上）
```bash
svnadmin create /data/svn/sd_learning
svnserve -d -r /data/svn   # 默认端口 3690
```

### 客户端检出与提交
```bash
svn checkout svn://服务器地址/sd_learning
# 修改文件
svn update
svn commit -m "feat: 添加参数示例"
```

## 🧪 不推荐：直接用 NAS / 云同步盘 共享工作目录
| 问题 | 原因 |
|------|------|
| Git `.git` 目录损坏 | 同步冲突 / 局部写入被覆盖 |
| 历史混乱 | 未按版本控制流程操作 |
| 难以回滚 | 没有标准提交记录 |

正确做法：在 NAS 上放“远程仓库”（Git 裸仓库 / SVN 仓库），每台设备 clone/checkout。

## 🗄️ 在 NAS 上作为 Git 远程
### 创建裸仓库（SSH 登录 NAS）
```bash
mkdir -p /srv/git && cd /srv/git
git init --bare sd_learning.git
```
### 本地添加远程
```bash
git remote add origin ssh://user@nas:/srv/git/sd_learning.git
git push -u origin main
```

## 🔑 SSH 快速配置
```bash
ssh-keygen -t ed25519 -C "你的邮箱"
# 将公钥添加到 Gitee / GitHub / NAS SSH 账户
ssh -T git@gitee.com
```

## 📄 建议 `.gitignore`
```
__pycache__/
*.pyc
.vscode/
*.tmp
logs/
*.sbsauto
# 按需：若不想跟踪体积大的 .sbsar
# *.sbsar
```

## 🪤 常见坑
| 坑 | 说明 | 规避 |
|----|------|------|
| push 前不 pull | 远端有更新会冲突 | 先 `git pull --rebase` |
| 提交信息全是 update | 回顾困难 | 使用语义前缀（feat/fix/docs/chore） |
| 同步工具占用 `.git` | 索引锁定 / pack 损坏 | 不放同步盘；用远程仓库 |
| SVN 直接 file:// 多人写 | 锁与原子操作风险 | 用 svnserve/Apache |

## 🏷 提交信息模板
```
feat: 新增 xxx 脚本
fix: 修复 xxx 报错
docs: 更新使用说明
refactor: 重构 xxx 结构
chore: 调整配置或初始化
```

## 🔄 Git LFS（大文件: 可选）
```bash
git lfs install
git lfs track "*.sbsar"
```

## 🧰 最小速记
- Git：`pull → 改 → add → commit → push`
- SVN：`update → 改 → commit`

## ❓ 选择指南
| 你现在主要做什么 | 建议 |
|------------------|------|
| 学习 / 试验脚本演进 | Git |
| 只想简单线性同步 | Git（也可 SVN） |
| 以后会协作 / 开源 | Git 必选 |
| 对集中式模型好奇 | SVN 体验一下 |

## ✅ 推荐默认路线
1. 初始化 Git（本地）
2. 推送到 Gitee
3. 另设备 clone
4. 日常按最小循环同步
5. 重要阶段打 tag + 可选 GitHub 备份

---
需要更详细 Git / SVN 独立教程或自动化脚本？继续提需求即可。
