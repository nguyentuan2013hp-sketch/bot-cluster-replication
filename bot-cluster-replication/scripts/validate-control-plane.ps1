param(
  [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'
Push-Location $Root
try {
  python -m unittest discover -s tests -v
  python -m control_plane.cli demo | Out-Null
  Write-Output 'Lauren method control-plane checks: passed'
}
finally {
  Pop-Location
}
