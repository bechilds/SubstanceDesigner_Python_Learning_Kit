#!/usr/bin/env bash
# 初始化/配置本地 Git 仓库并推送到远程 (Gitee + 可选 GitHub)
# 用法示例：
#   bash scripts/setup_git_remote.sh --gitee git@gitee.com:username/repo.git
#   bash scripts/setup_git_remote.sh --gitee git@gitee.com:u/repo.git --github git@github.com:u/repo.git --force
#   bash scripts/setup_git_remote.sh --gitee git@nas:/srv/git/repo.git --create-bare user@nas:/srv/git/repo.git

set -euo pipefail

GITEE=""; GITHUB=""; FORCE=0; SKIP_PUSH=0; MAIN_BRANCH="main"; INITIAL_MSG="chore: initial commit"; CREATE_BARE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gitee) GITEE="$2"; shift 2;;
    --github) GITHUB="$2"; shift 2;;
    --force) FORCE=1; shift;;
    --skip-push) SKIP_PUSH=1; shift;;
    --branch) MAIN_BRANCH="$2"; shift 2;;
    --msg) INITIAL_MSG="$2"; shift 2;;
    --create-bare) CREATE_BARE="$2"; shift 2;;
    -h|--help)
      echo "用法: $0 --gitee <url> [--github <url>] [--force] [--skip-push] [--branch main] [--msg message] [--create-bare user@host:/path/repo.git]"; exit 0;;
    *) echo "未知参数: $1"; exit 1;;
  esac
done

if [[ -z "$GITEE" ]]; then
  echo "[ERROR] 必须提供 --gitee 远程地址"; exit 1
fi

step(){ echo -e "\033[36m[+] $1\033[0m"; }
warn(){ echo -e "\033[33m[!] $1\033[0m"; }
run(){ echo -e "    > $*"; eval "$*"; }

# 1. 初始化
if [[ ! -d .git ]]; then
  step "初始化 Git 仓库"
  run git init
  # 设置默认分支
  git symbolic-ref HEAD refs/heads/$MAIN_BRANCH 2>/dev/null || true
else
  step ".git 已存在，跳过 init"
fi

# 2. 初始提交
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  if [[ $FORCE -eq 1 ]]; then
    step "强制创建初始提交"
    run git add .
    run git commit -m "$INITIAL_MSG" || true
  else
    step "已有提交，跳过初始提交"
  fi
else
  step "创建初始提交"
  run git add .
  run git commit -m "$INITIAL_MSG" || true
fi

# 3. 配置 origin
if git remote get-url origin >/dev/null 2>&1; then
  current=$(git remote get-url origin)
  if [[ "$current" != "$GITEE" ]]; then
    warn "更新 origin: $current -> $GITEE"
    run git remote set-url origin "$GITEE"
  else
    step "origin 已指向目标"
  fi
else
  step "添加 origin: $GITEE"
  run git remote add origin "$GITEE"
fi

# 4. GitHub 远程
if [[ -n "$GITHUB" ]]; then
  if git remote get-url github >/dev/null 2>&1; then
    gh=$(git remote get-url github)
    if [[ "$gh" != "$GITHUB" ]]; then
      warn "更新 github: $gh -> $GITHUB"
      run git remote set-url github "$GITHUB"
    else
      step "github 已配置"
    fi
  else
    step "添加 github: $GITHUB"
    run git remote add github "$GITHUB"
  fi
fi

# 5. 远端创建裸仓库
if [[ -n "$CREATE_BARE" ]]; then
  step "尝试远端创建裸仓库: $CREATE_BARE"
  host="${CREATE_BARE%%:*}"; path="${CREATE_BARE#*:}"
  run ssh "$host" "mkdir -p $(dirname $path); if [ ! -d $path ]; then git init --bare $path; fi"
fi

# 6. 推送
if [[ $SKIP_PUSH -eq 0 ]]; then
  step "推送到 origin ($MAIN_BRANCH)"
  run git push -u origin "$MAIN_BRANCH" || true
  if [[ -n "$GITHUB" ]]; then
    step "推送到 github ($MAIN_BRANCH)"
    run git push -u github "$MAIN_BRANCH" || true
  fi
else
  warn "跳过推送 (--skip-push)"
fi

step "完成 ✅"
