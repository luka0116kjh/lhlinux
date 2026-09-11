# Integration test: requires an existing lhlinux WSL with Python 3; no AI calls.
#Requires -Version 7.3
$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot '../scripts/Invoke-Lhlinux.ps1'
$expected = @('space value', '', 'unicode: 한글', 'a"b', '$(touch INJECTED)', '; echo no', 'C:\ends\')
$actual = & $wrapper -Command (@('python3', '-c', 'import json,sys; print(json.dumps(sys.argv[1:]))') + $expected)
if ($LASTEXITCODE -ne 0) { throw 'Wrapper failed.' }
$decoded = @($actual | ConvertFrom-Json)
if (($decoded | ConvertTo-Json -Compress) -cne ($expected | ConvertTo-Json -Compress)) {
    throw "Argument round trip failed: $actual"
}
Write-Host 'PASS literal arguments, empty string, quotes, Unicode'
$directory = & $wrapper -Directory /tmp -Command @('pwd')
if ($LASTEXITCODE -ne 0 -or $directory -ne '/tmp') { throw 'Linux directory was not preserved.' }
Write-Host 'PASS Linux directory'
$hostDirectory = & $wrapper -Command @('pwd')
$converted = & wsl.exe -d lhlinux --exec wslpath -a (Get-Location).Path
if ($LASTEXITCODE -ne 0 -or $hostDirectory -ne $converted) { throw 'Windows directory was not preserved.' }
Write-Host 'PASS Windows directory'
$PSNativeCommandUseErrorActionPreference = $true
& $wrapper -Command @('python3', '-c', 'import sys; sys.exit(37)')
if ($LASTEXITCODE -ne 37) { throw 'Linux exit code was lost.' }
Write-Host 'PASS Linux exit code'
$global:LASTEXITCODE = 0
