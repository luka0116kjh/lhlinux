# No real WSL, downloads, or imports: external commands are replaced below.
$ErrorActionPreference = 'Stop'
$installer = Join-Path $PSScriptRoot '../scripts/New-Lhlinux.ps1'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('lhlinux-installer-' + [guid]::NewGuid())
$null = New-Item -ItemType Directory -Path $testRoot
$archive = 'ubuntu-base-24.04.4-base-amd64.tar.gz'
$fixture = Join-Path $testRoot 'fixture'
[IO.File]::WriteAllText($fixture, 'verified archive')
$expected = (Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash
$installerTestState = @{ Expected = $expected; Archive = $archive }

function wsl.exe {
    if ($args[0] -eq '--list') { $global:LASTEXITCODE = 0; return }
    if ($args[0] -eq '--import') {
        $installerTestState.Imported = $true
        if ((Get-FileHash -LiteralPath $args[3] -Algorithm SHA256).Hash -ne $installerTestState.Expected) {
            throw 'TEST: attempted to import an unverified archive'
        }
        # End the test at the import boundary.
        $global:LASTEXITCODE = 1
        return
    }
    throw 'TEST: unexpected WSL invocation'
}

function curl.exe {
    $output = $args[[Array]::IndexOf($args, '--output') + 1]
    if ($args[-1] -like '*/SHA256SUMS') {
        [IO.File]::WriteAllText($output, "$($installerTestState.Expected)  $($installerTestState.Archive)`n")
    } else {
        $installerTestState.Downloaded = $true
        if ($installerTestState.DownloadFailure) { $global:LASTEXITCODE = 22; return }
        [IO.File]::WriteAllText($output, $installerTestState.Payload)
    }
    $global:LASTEXITCODE = 0
}

function Test-DownloadCase {
    param([string]$Name, [string]$Cache, [string]$Payload, [bool]$Failure,
          [bool]$WantDownload, [bool]$WantImport, [string]$WantError)
    $caseRoot = Join-Path $testRoot $Name
    $downloads = Join-Path $caseRoot 'downloads'
    $null = New-Item -ItemType Directory -Path $downloads -Force
    $archivePath = Join-Path $downloads $archive
    if ($Cache) { [IO.File]::WriteAllText($archivePath, $Cache) }
    $installerTestState.Payload = $Payload
    $installerTestState.DownloadFailure = $Failure
    $installerTestState.Downloaded = $false
    $installerTestState.Imported = $false
    $caught = ''
    try { & $installer -InstallRoot $caseRoot } catch { $caught = $_.Exception.Message }
    if ($caught -ne $WantError -or $installerTestState.Downloaded -ne $WantDownload -or $installerTestState.Imported -ne $WantImport) {
        throw "${Name}: error=$caught, downloaded=$($installerTestState.Downloaded), imported=$($installerTestState.Imported)"
    }
    if (-not $WantImport -and (Test-Path -LiteralPath $archivePath)) {
        if ([IO.File]::ReadAllText($archivePath) -ne $Cache) { throw "${Name}: cache changed on failure" }
    }
    Write-Host "PASS $Name"
}

try {
    Test-DownloadCase 'new' '' 'verified archive' $false $true $true 'WSL import failed.'
    Test-DownloadCase 'cached' 'verified archive' '' $true $false $true 'WSL import failed.'
    Test-DownloadCase 'interrupted' 'partial archive' 'verified archive' $false $true $true 'WSL import failed.'
    Test-DownloadCase 'mismatch' 'partial archive' 'wrong archive' $false $true $false 'Ubuntu checksum mismatch.'
    Test-DownloadCase 'failed' '' '' $true $true $false 'Ubuntu download failed.'
} finally {
    $resolvedRoot = [IO.Path]::GetFullPath($testRoot)
    $tempPrefix = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (-not $resolvedRoot.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path -Leaf $resolvedRoot) -notlike 'lhlinux-installer-*') {
        throw 'Refusing cleanup outside the test temporary directory.'
    }
    Remove-Item -LiteralPath $resolvedRoot -Recurse -Force
}
