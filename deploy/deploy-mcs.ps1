<#
.SYNOPSIS
  Orchestrates the deployment of MCS-OS and MCS-ERP to the Contabo VPS running Coolify.
.DESCRIPTION
  - Validates secrets in mcs-deploy.secrets.env
  - Generates secure random credentials if left empty and persists them back
  - Establishes SSH connection to the server
  - Uploads provision-mcs.sh and environment payload
  - Runs idempotent server-side provisioning (Cloudflare ingress, Coolify projects, Frappe site creation)
.EXAMPLE
  .\deploy\deploy-mcs.ps1 -SecretsFile .\deploy\mcs-deploy.secrets.env
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)] [string] $SecretsFile = "$PSScriptRoot\mcs-deploy.secrets.env",
  [string] $SshKey = "$env:USERPROFILE\.ssh\tvinsights_vps",
  [string] $Python = "python",
  [string] $GithubRepoOS = "ainatunde/mcs-os",
  [string] $GithubRepoERP = "ainatunde/MCS-ERP",
  [string] $GitBranch = "main"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$utf8 = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path $SecretsFile)) {
  throw "Secrets file not found: $SecretsFile. Copy mcs-deploy.secrets.env.example to $SecretsFile and fill in credentials."
}

function Read-EnvFile([string]$path) {
  $map = [ordered]@{}
  foreach ($line in [IO.File]::ReadAllLines($path)) {
    if ($line -match '^\s*([A-Z0-9_]+)\s*=(.*)$') { $map[$Matches[1]] = $Matches[2].Trim() }
  }
  $map
}

function New-Secret([int]$bytes = 24) {
  $b = New-Object byte[] $bytes
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  ($b | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Set-EnvValue([string]$path, [string]$key, [string]$value) {
  $text = [IO.File]::ReadAllText($path)
  if ($text -match "(?m)^$key=.*$") {
    $text = [regex]::Replace($text, "(?m)^$key=.*$", "$key=$value")
  } else {
    $text += "`n$key=$value`n"
  }
  [IO.File]::WriteAllText($path, $text, $utf8)
}

$cfg = Read-EnvFile $SecretsFile

# Validate required variables
$requiredKeys = @(
  "VPS_IP", "CF_API_TOKEN", "CF_ACCOUNT_ID", "CF_ZONE_DOMAIN",
  "OS_HOSTNAME", "ERP_HOSTNAME", "GITHUB_TOKEN"
)
foreach ($k in $requiredKeys) {
  if (-not $cfg[$k]) { throw "Missing mandatory key '$k' in $SecretsFile" }
}

# Auto-generate any blank passwords/tokens and persist back to the secrets file
if (-not $cfg.POSTGRES_PASSWORD) {
  $cfg.POSTGRES_PASSWORD = New-Secret 20
  Set-EnvValue $SecretsFile "POSTGRES_PASSWORD" $cfg.POSTGRES_PASSWORD
}
if (-not $cfg.DB_ROOT_PASSWORD) {
  $cfg.DB_ROOT_PASSWORD = New-Secret 20
  Set-EnvValue $SecretsFile "DB_ROOT_PASSWORD" $cfg.DB_ROOT_PASSWORD
}
if (-not $cfg.ADMIN_PASSWORD) {
  $cfg.ADMIN_PASSWORD = "Adm-" + (New-Secret 12) + "-X9!"
  Set-EnvValue $SecretsFile "ADMIN_PASSWORD" $cfg.ADMIN_PASSWORD
}
if (-not $cfg.MCS_CONTROL_API_TOKEN) {
  $cfg.MCS_CONTROL_API_TOKEN = New-Secret 32
  Set-EnvValue $SecretsFile "MCS_CONTROL_API_TOKEN" $cfg.MCS_CONTROL_API_TOKEN
}
if (-not $cfg.MCS_WEBHOOK_SECRET) {
  $cfg.MCS_WEBHOOK_SECRET = New-Secret 32
  Set-EnvValue $SecretsFile "MCS_WEBHOOK_SECRET" $cfg.MCS_WEBHOOK_SECRET
}

$user = if ($cfg.VPS_SSH_USER) { $cfg.VPS_SSH_USER } else { "root" }
$port = if ($cfg.VPS_SSH_PORT) { $cfg.VPS_SSH_PORT } else { "22" }
$target = "$user@$($cfg.VPS_IP)"
$knownHosts = "$env:USERPROFILE\.ssh\tvinsights_known_hosts"
$sshOpts = @("-i", $SshKey, "-p", $port, "-o", "StrictHostKeyChecking=accept-new",
             "-o", "UserKnownHostsFile=$knownHosts", "-o", "BatchMode=yes",
             "-o", "ServerAliveInterval=30", "-o", "ConnectTimeout=20")

Write-Host "==> Verifying SSH connectivity to $target..." -ForegroundColor Cyan
$ErrorActionPreference = "Continue"
& ssh @sshOpts $target "true" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "SSH key connection failed. Attempting fallback keys..." -ForegroundColor Yellow
  # Try default ~/.ssh/id_rsa or id_ed25519
  $fallbackKey = "$env:USERPROFILE\.ssh\id_ed25519"
  if (-not (Test-Path $fallbackKey)) { $fallbackKey = "$env:USERPROFILE\.ssh\id_rsa" }
  if (Test-Path $fallbackKey) {
    $sshOpts[1] = $fallbackKey
    & ssh @sshOpts $target "true" 2>$null
  }
  if ($LASTEXITCODE -ne 0) {
    throw "Unable to authenticate to $target via SSH. Check your SSH key path or network."
  }
}
$ErrorActionPreference = "Stop"
Write-Host "SSH connection OK." -ForegroundColor Green

Write-Host "==> Preparing provisioning bundle..." -ForegroundColor Cyan
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("mcs-" + [guid]::NewGuid())
New-Item -ItemType Directory $tmp | Out-Null

try {
  $provisionScript = [IO.File]::ReadAllText("$here\server\provision-mcs.sh") -replace "`r`n", "`n"
  [IO.File]::WriteAllText("$tmp\provision-mcs.sh", $provisionScript, $utf8)

  $keysToExport = @(
    "CF_API_TOKEN", "CF_ACCOUNT_ID", "CF_ZONE_DOMAIN", "TUNNEL_NAME",
    "OS_HOSTNAME", "ERP_HOSTNAME", "COOLIFY_HOSTNAME", "COOLIFY_ADMIN_EMAIL",
    "COOLIFY_ADMIN_PASSWORD", "GITHUB_TOKEN", "POSTGRES_PASSWORD", "DB_ROOT_PASSWORD",
    "ADMIN_PASSWORD", "MCS_CONTROL_API_TOKEN", "MCS_WEBHOOK_SECRET",
    "FRAPPE_WORKERS", "DB_BUFFER_POOL"
  )

  $lines = foreach ($k in $keysToExport) {
    "$k='" + ([string]$cfg[$k]).Replace("'", "'\''") + "'"
  }
  $lines += "GITHUB_REPO_OS='$GithubRepoOS'"
  $lines += "GITHUB_REPO_ERP='$GithubRepoERP'"
  $lines += "GIT_BRANCH='$GitBranch'"
  $lines += "VPS_SSH_PORT='$port'"

  [IO.File]::WriteAllText("$tmp\mcs-deploy.env", (($lines -join "`n") + "`n"), $utf8)

  Write-Host "==> Uploading files to server..." -ForegroundColor Cyan
  & scp -i $sshOpts[1] -P $port -o "UserKnownHostsFile=$knownHosts" -o BatchMode=yes `
    "$tmp\provision-mcs.sh" "$tmp\mcs-deploy.env" "${target}:/root/"
  if ($LASTEXITCODE -ne 0) { throw "SCP upload failed." }
}
finally {
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

Write-Host "==> Executing provisioning on $target..." -ForegroundColor Cyan
$sudo = if ($user -eq "root") { "" } else { "sudo -n " }

& ssh @sshOpts $target "chmod 700 /root/provision-mcs.sh; chmod 600 /root/mcs-deploy.env; ${sudo}/bin/bash /root/provision-mcs.sh /root/mcs-deploy.env; rc=`$?; shred -u /root/mcs-deploy.env 2>/dev/null || rm -f /root/mcs-deploy.env; exit `$rc"

$rc = $LASTEXITCODE
if ($rc -ne 0) {
  throw "Provisioning failed with exit code $rc. Inspect remote logs above."
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "  MCS DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "  MCS-OS:  https://$($cfg.OS_HOSTNAME)" -ForegroundColor Green
Write-Host "  MCS-ERP: https://$($cfg.ERP_HOSTNAME) (Administrator)" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
