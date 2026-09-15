#Requires -Version 7.3
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [AllowEmptyString()]
    [string[]]$Command,
    [string]$Directory = (Get-Location).Path
)
$ErrorActionPreference = 'Stop'
# Standard argument passing preserves empty arguments, quotes and whitespace.
$PSNativeCommandArgumentPassing = 'Standard'
$PSNativeCommandUseErrorActionPreference = $false
if ([string]::IsNullOrWhiteSpace($Command[0])) { throw 'Command must name an executable.' }
if ([string]::IsNullOrWhiteSpace($Directory)) { throw 'Directory must not be empty.' }
if (-not $Directory.StartsWith('/') -and $Directory -ne '~') {
    $resolved = Get-Item -LiteralPath $Directory
    if (-not $resolved.PSIsContainer -or $resolved.PSProvider.Name -ne 'FileSystem') {
        throw 'Directory must be a filesystem directory.'
    }
    $Directory = $resolved.FullName
}
# WSL accepts absolute Windows paths, Linux paths and ~ with --cd.
# --exec bypasses shell startup and treats every supplied argument literally.
& wsl.exe -d lhlinux --cd $Directory --exec env NO_COLOR=1 TERM=dumb PAGER=cat GIT_PAGER=cat PYTHONUNBUFFERED=1 @Command
exit $LASTEXITCODE
