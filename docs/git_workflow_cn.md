# Git 学习与实战工作流指南（面向多设备 & 学习项目）

适用人群：刚开始使用 Git、需要在多台设备间同步本学习项目或未来扩展到协作。

---
## 目录
1. 为什么使用 Git
2. 核心概念速懂（10 分钟）
3. 环境准备与配置
4. 首次创建与推送（本地已有项目）
5. 多设备克隆与保持同步
6. 日常最小循环工作流
7. 提交（Commit）最佳实践与语义前缀
8. 分支（Branch）策略（简单到进阶）
9. 多远程（Gitee + GitHub + NAS）
10. 忽略文件与 .gitignore
11. 大文件与 Git LFS
12. 标签（Tag）与版本里程碑
13. 冲突（Conflict）处理流程
14. 常见问题 & 排错
15. 数据备份与恢复策略
16. 安全注意事项（SSH Key / 代理）
17. 提交历史查看与回滚
18. 推荐学习路线
19. 速查表（Cheat Sheet）

---
## 1. 为什么使用 Git
- 版本历史：可以回到任意时间点。
- 多设备同步：push/pull 即可迁移工作。
- 实验分支：大胆尝试，不污染主线。
- 备份：同步到 Gitee / GitHub / NAS。
- 记录学习：提交信息即“成长日志”。

## 2. 核心概念速懂（10 分钟）
| 概念 | 含义 | 类比 |
|------|------|------|
| 仓库（Repository） | 代码版本数据库 | 项目时间机器 |
| 提交（Commit） | 一次快照+描述 | 存档点 |
| 分支（Branch） | 一条独立时间线 | 平行发展剧情 |
| HEAD | 当前指向的提交/分支 | 你的视角位置 |
| 远程（Remote） | 在线或局域网仓库别名 | 云/服务器 |
| 克隆（Clone） | 下载仓库副本 | 复制工程档案 |
| 拉取（Pull） | 把远程更新取回并合并 | 同步他人进度 |
| 推送（Push） | 上传本地提交到远程 | 发布更新 |
| 合并（Merge） | 把分支变化合到一起 | 融合剧情 |
| 变基（Rebase） | 重新排列提交基础 | 重写历史结构 |
| 标签（Tag） | 重要节点标记 | 里程碑旗帜 |

## 3. 环境准备与配置
```bash
git --version
# 基础身份
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
# 推荐：Windows 下避免换行差异
git config --global core.autocrlf input
# 默认分支名称
git config --global init.defaultBranch main
# 显示漂亮日志（可选）
git config --global alias.lg "log --oneline --graph --decorate --all"
```

### 生成 SSH Key（推荐 SSH 方式）
```bash
ssh-keygen -t ed25519 -C "你的邮箱"   # 旧系统可用 -t rsa -b 4096
```
复制公钥内容（`~/.ssh/id_ed25519.pub` 或 `C:\Users\你\.ssh\id_ed25519.pub`）到 Gitee/GitHub → SSH Keys。
测试：
```bash
ssh -T git@gitee.com
```

## 4. 首次创建与推送（本地已有项目）
```bash
git init
git add .
git commit -m "chore: initial commit"
git remote add origin git@gitee.com:用户名/仓库.git
git push -u origin main
```

## 5. 多设备克隆与保持同步
另一台设备：
```bash
git clone git@gitee.com:用户名/仓库.git
cd 仓库名
git pull   # 确保最新
```
切换设备前：一定 push；新设备：先 pull。

## 6. 日常最小循环工作流
```
(拉取) git pull --rebase origin main
(修改代码)
(查看状态) git status
(暂存) git add 文件/目录 或 git add .
(提交) git commit -m "feat: 添加节点遍历示例"
(推送) git push origin main
```
若有分支：在分支上执行同样流程。回到 main：`git checkout main && git pull --rebase`。

## 7. 提交最佳实践
- 一次提交只做“一件有意义的事情”。
- 信息格式：`<type>: <描述>`。
- 描述使用动词现在时：add / fix / update / refactor / remove。
- 不要堆积“超大提交”（可拆）。

常用前缀：
| type | 说明 | 示例 |
|------|------|------|
| feat | 新功能/脚本 | feat: 添加参数批量重命名脚本 |
| fix | 修复问题 | fix: 修复节点遍历空引用错误 |
| docs | 文档/注释 | docs: 更新 Git 工作流文档 |
| refactor | 重构不改功能 | refactor: 抽离节点过滤函数 |
| chore | 配置/杂项 | chore: 添加 .gitignore |
| test | 测试相关 | test: 增加参数解析用例 |
| perf | 性能优化 | perf: 缓存已解析节点 |

## 8. 分支策略
最简单：只用 main。（学习阶段足够）

进阶（推荐）：
- main：稳定可用
- feat/xxx：新功能实验
- fix/xxx：问题修复

示例：
```bash
git checkout -b feat/delete-exposed-params
# 工作...
git add . && git commit -m "feat: 初版删除暴露参数脚本"
git push -u origin feat/delete-exposed-params
# 合并回 main
git checkout main
git pull --rebase origin main
git merge feat/delete-exposed-params
git push origin main
```

## 9. 多远程（Gitee + GitHub + NAS）
```bash
# 添加 GitHub 备份
git remote add github git@github.com:用户名/仓库.git
# NAS 裸仓库
git remote add nas ssh://user@nas:/srv/git/sd_learning.git
# 推送
git push origin main
git push github main
git push nas main
```
查看：`git remote -v`

## 10. .gitignore（忽略不需跟踪文件）
根目录创建 `.gitignore`：
```
__pycache__/
*.pyc
.vscode/
*.tmp
logs/
*.sbsauto
# 如果不跟踪大材质文件：
# *.sbsar
```
已被跟踪的文件修改 ignore 后需：`git rm --cached 文件名`。

## 11. 大文件与 Git LFS
用于跟踪二进制大文件（如 .sbsar）。
```bash
git lfs install
git lfs track "*.sbsar"
cat .gitattributes   # 确认
git add .gitattributes *.sbsar
git commit -m "chore: track sbsar via LFS"
git push origin main
```

## 12. 标签（Tag）
用于里程碑：
```bash
git tag -a v0.1 -m "完成基础三章教程"
git push origin v0.1
```
列出：`git tag`。

## 13. 冲突处理
产生场景：远程有人修改你也修改的同一区域。
```bash
git pull --rebase origin main
# 冲突标记 <<<<<<< ======= >>>>>>>
# 手动编辑保留正确内容
git add 冲突文件.py
git rebase --continue   # 若是 merge 则 git commit
```
放弃 rebase：`git rebase --abort`。
快速查看冲突文件：`git status`。

## 14. 常见问题 & 排错
| 问题 | 原因 | 解决 |
|------|------|------|
| push 被拒绝 | 远程有新提交 | `git pull --rebase` 再 push |
| 出现 .lock 文件 | 上次操作中断 | 删除 `.git/index.lock`（确认无并发） |
| 提交混乱太多垃圾 | 随手 commit | 规范前缀 + 小步提交 |
| clone 很慢 | 网络限制 | 换时间段 / 代理 / 国内镜像 |
| 文件换行差异 | OS 差异 | `core.autocrlf input` + 统一 LF |

## 15. 备份与恢复
- 远程冗余：Gitee + GitHub 双推。
- 重要节点打标签。
- 定期本地 bundle：
```bash
git bundle create backup_$(date +%Y%m%d).bundle --all
```
恢复：
```bash
git clone backup_20250101.bundle repo_from_backup
```

## 16. 安全注意事项
- 不要泄露私钥（`id_ed25519`）。
- 不要把 `.ssh` 整个上传仓库。
- 使用 SSH 优先于 https（减少频繁输入密码）。
- 代理配置：
```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
# 取消
git config --global --unset http.proxy
```

## 17. 查看历史与回滚
```bash
git log --oneline --graph --decorate -n 15
# 自定义别名
git lg  # 若已配置 alias
# 查看某文件历史
git log -- filename.py
# 查看提交详情
git show <commit>
```
撤销最近未推送提交（保留修改）：
```bash
git reset --soft HEAD~1
```
彻底回退（丢弃更改，危险）：
```bash
git reset --hard HEAD~1
```
撤销已推送错误（推荐新提交方式）：
```bash
git revert <commit>
```

## 18. 推荐学习路线
1. 最小循环掌握
2. 提交信息规范
3. 分支与合并
4. 冲突解决
5. 多远程与备份
6. LFS（如果涉及大文件）
7. Rebase（保持历史整洁）

## 19. 速查表（Cheat Sheet）
| 任务 | 命令 |
|------|------|
| 初始化 | git init |
| 查看状态 | git status |
| 暂存文件 | git add 文件 / git add . |
| 提交 | git commit -m "feat: 描述" |
| 推送 | git push origin main |
| 拉取（优雅） | git pull --rebase origin main |
| 创建分支 | git checkout -b feat/xxx |
| 切换分支 | git checkout main |
| 合并分支 | git merge feat/xxx |
| 查看分支 | git branch -av |
| 查看日志 | git log --oneline --graph --decorate |
| 添加远程 | git remote add origin <url> |
| 查看远程 | git remote -v |
| 标签创建 | git tag -a v1.0 -m "说明" |
| 推送标签 | git push origin v1.0 |
| 忽略文件 | 编辑 .gitignore |
| 克隆 | git clone <url> |
| 回退上一个提交（保留文件） | git reset --soft HEAD~1 |
| 还原某提交 | git revert <commit> |

---
如果你希望：我可以继续生成英文版、精简速记版，或增加“常见错误演练”章节。告诉我下一步想要什么即可。 ✨
