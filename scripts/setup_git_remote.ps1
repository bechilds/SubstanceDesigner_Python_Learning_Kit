<#!
.SYNOPSIS
  初始化（若未初始化）当前目录为 Git 仓库，配置远程（Gitee / 可选 GitHub），并首次推送。

.DESCRIPTION
  - 检查是否已有 .git 目录
  - 可选创建初始提交
  - 添加/更新 origin 远程（Gitee 或自定义）
  - 可选添加 github 远程
  - 可选推送标签
  - 支持参数化

.EXAMPLE
  ./setup_git_remote.ps1 -Gitee git@gitee.com:username/repo.git
  ./setup_git_remote.ps1 -Gitee git@gitee.com:username/repo.git -GitHub git@github.com:username/repo.git -ForceInitialCommit
  ./setup_git_remote.ps1 -Gitee git@gitee.com:username/repo.git -CreateBareOnHost user@nas:/srv/git/sd_learning.git

.NOTES
  适用于 Windows PowerShell / PowerShell Core。
#>

param(
    [Parameter(Mandatory=$true)] [string]$Gitee,
    [string]$GitHub,
    [switch]$ForceInitialCommit,
    [switch]$SkipPush,
    [string]$MainBranch = "main",
    [string]$InitialMessage = "chore: initial commit",
    [string]$CreateBareOnHost  # 例如 user@nas:/srv/git/sd_learning.git
)

function Write-Step($msg){ Write-Host "[+] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[!] $msg" -ForegroundColor Yellow }
function Run($cmd){ Write-Host "    > $cmd" -ForegroundColor DarkGray; Invoke-Expression $cmd }

# 1. 初始化仓库
if(-not (Test-Path .git)){
    Write-Step "初始化 Git 仓库"
    Run "git init"
    Run "git symbolic-ref HEAD refs/heads/$MainBranch" 2>$null
} else { Write-Step ".git 已存在，跳过 init" }

# 2. 检查是否有提交
$hasCommit = (git rev-parse --verify HEAD 2>$null) -ne $null
if(-not $hasCommit -or $ForceInitialCommit){
    Write-Step "创建初始提交"
    Run "git add ."
    Run "git commit -m '$InitialMessage'" 2>$null
} else { Write-Step "已有提交，跳过初始提交" }

# 3. 配置 origin
$originUrl = git remote get-url origin 2>$null
if($originUrl){
    if($originUrl -ne $Gitee){
        Write-Warn "origin 已存在 ($originUrl)，更新为: $Gitee"
        Run "git remote set-url origin $Gitee"
    } else { Write-Step "origin 已配置为目标地址" }
} else {
    Write-Step "添加 origin: $Gitee"
    Run "git remote add origin $Gitee"
}

# 4. 可选 GitHub
if($GitHub){
    $ghUrl = git remote get-url github 2>$null
    if($ghUrl){
        if($ghUrl -ne $GitHub){
            Write-Warn "github 远程已存在 ($ghUrl)，更新为: $GitHub"
            Run "git remote set-url github $GitHub"
        } else { Write-Step "github 远程已配置" }
    } else {
        Write-Step "添加 github 远程: $GitHub"
        Run "git remote add github $GitHub"
    }
}

# 5. 可选在远端创建裸仓库（通过 SSH 执行）
if($CreateBareOnHost){
    Write-Step "尝试在远端创建裸仓库: $CreateBareOnHost"
    $parts = $CreateBareOnHost.Split(':',2)
    if($parts.Count -eq 2){
        $host = $parts[0]; $path = $parts[1]
        Run "ssh $host 'mkdir -p $(Split-Path -Parent $path); if [ ! -d $path ]; then git init --bare $path; fi'"
    } else { Write-Warn "CreateBareOnHost 格式不正确，应为 user@host:/absolute/path/repo.git" }
}

# 6. 推送
if(-not $SkipPush){
    Write-Step "推送到 origin ($MainBranch)"
    Run "git push -u origin $MainBranch"
    if($GitHub){
        Write-Step "推送到 github ($MainBranch)"
        Run "git push -u github $MainBranch"
    }
} else { Write-Warn "已跳过推送 (--SkipPush)" }

Write-Host "完成 ✅" -ForegroundColor Green
