# Release the API image: quality gates, optional commit and push, docker build and push.
# Run from the repository root, with Docker Desktop running and logged in to Docker Hub:
#   .\deploy\publish-api.ps1 -Tag v4
#   .\deploy\publish-api.ps1 -Tag v3 -CommitMessage "..." -Paths a.py,b.py
# It never reads .env and never prints secrets. The data in data/serving/v1 and
# data/analytics/v1 must already be built locally: the image copies them in.
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [string]$Image = "xuxutinha777/anac-flight-intelligence-api",
    [string]$CommitMessage = "",
    [string[]]$Paths = @(),
    [string]$Branch = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Step([string]$Name, [scriptblock]$Command) {
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Failed: $Name (exit $LASTEXITCODE)" }
}

$python = ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Create the virtual environment first (see README, Run locally)." }
foreach ($folder in "data\serving\v1", "data\analytics\v1") {
    if (-not (Test-Path "$folder\*")) { throw "$folder is empty: build the data before the image." }
}

Step "Tests" { & $python -m pytest -q }
Step "Lint" { & $python -m ruff check src tests }
Step "Format" { & $python -m ruff format --check src tests }
Step "Types" { & $python -m mypy }

if ($CommitMessage) {
    if ($Paths.Count -eq 0) { throw "-Paths lists the files to commit." }
    # PowerShell names ignore case, so the current branch needs a name other than the parameter.
    $current = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($Branch -and $current -ne $Branch) { throw "On branch $current, expected $Branch." }
    Write-Host "`n==> git status on $current" -ForegroundColor Cyan
    git status --short
    # Only the listed files may be committed: anything else already staged stops the release.
    $foreign = @(git diff --cached --name-only | Where-Object { $_ -and ($Paths -notcontains $_) })
    if ($foreign.Count -gt 0) { throw "Other files are staged, commit aborted: $($foreign -join ', ')" }
    Step "Stage $($Paths.Count) files" { git add -- $Paths }
    $staged = @(git diff --cached --name-only)
    if ($staged.Count -eq 0) {
        Write-Host "Nothing new to commit: the files are already committed."
    } else {
        # A file, not -m: Windows PowerShell splits a message with quotes into separate arguments.
        $messageFile = Join-Path ([System.IO.Path]::GetTempPath()) "anac-release-message.txt"
        [System.IO.File]::WriteAllText($messageFile, $CommitMessage, (New-Object System.Text.UTF8Encoding $false))
        try { Step "Commit on $current" { git commit -F $messageFile } }
        finally { Remove-Item $messageFile -ErrorAction SilentlyContinue }
    }
    Step "Push $current" { git push origin $current }
    Write-Host "Commit: $((git rev-parse --short HEAD).Trim())"
}

Step "Docker daemon" { docker info --format "{{.ServerVersion}}" }
Step "Build ${Image}:$Tag" { docker build -f deploy/api/Dockerfile -t "${Image}:$Tag" . }
Step "Smoke test" {
    $id = (docker run -d --rm -p 18000:8000 "${Image}:$Tag").Trim()
    try {
        $ok = $false
        foreach ($attempt in 1..30) {
            Start-Sleep -Seconds 1
            try {
                $health = Invoke-RestMethod "http://127.0.0.1:18000/health" -TimeoutSec 3
                if ($health.data.ok) { $ok = $true; break }
            } catch { }
        }
        if (-not $ok) { docker logs $id; throw "The container did not answer /health." }
        Write-Host "health ok"
    } finally { docker stop $id | Out-Null }
    $global:LASTEXITCODE = 0
}
Step "Push ${Image}:$Tag" { docker push "${Image}:$Tag" }

Write-Host "`nPublished ${Image}:$Tag" -ForegroundColor Green
Write-Host "Render: Settings -> Image URL -> docker.io/${Image}:$Tag -> Save, then deploy."
