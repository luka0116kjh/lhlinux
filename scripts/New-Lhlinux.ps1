[CmdletBinding()]
param([string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'lhlinux\WSL'), [switch]$Resume)
$ErrorActionPreference = 'Stop'
$distro = 'lhlinux'
$repo = Split-Path -Parent $PSScriptRoot
$cache = Join-Path $InstallRoot 'downloads'
$destination = Join-Path $InstallRoot $distro
$distros = ((& wsl.exe --list --quiet) -join "`n").Replace([string][char]0, '')
if ($LASTEXITCODE -ne 0) { throw 'Cannot list WSL distributions.' }
$exists = ($distros -split "`n" | ForEach-Object { $_.Trim() }) -contains $distro
if ($exists -and -not $Resume) { throw 'lhlinux already exists. Use -Resume only for an instance created by this project.' }
if (-not $exists) {
    if (Test-Path -LiteralPath $destination) { throw "Destination already exists: $destination" }
    New-Item -ItemType Directory -Force -Path $cache | Out-Null
    $baseUrl = 'https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release'
    $archive = 'ubuntu-base-24.04.4-base-amd64.tar.gz'
    $archivePath = Join-Path $cache $archive
    & curl.exe -fL --retry 3 --output (Join-Path $cache 'SHA256SUMS') "$baseUrl/SHA256SUMS"
    if ($LASTEXITCODE -ne 0) { throw 'Checksum download failed.' }
    $line = Get-Content -LiteralPath (Join-Path $cache 'SHA256SUMS') | Where-Object { $_ -match ([regex]::Escape($archive) + '$') }
    if (@($line).Count -ne 1) { throw 'Expected one Ubuntu checksum.' }
    $expected = ($line -split '\s+')[0]
    $cacheValid = (Test-Path -LiteralPath $archivePath -PathType Leaf) -and
        ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -eq $expected)
    if (-not $cacheValid) {
        $partialPath = "$archivePath.part"
        & curl.exe -fL --retry 3 --output $partialPath "$baseUrl/$archive"
        if ($LASTEXITCODE -ne 0) { throw 'Ubuntu download failed.' }
        if ((Get-FileHash -LiteralPath $partialPath -Algorithm SHA256).Hash -ne $expected) { throw 'Ubuntu checksum mismatch.' }
        Move-Item -LiteralPath $partialPath -Destination $archivePath -Force
    }
    & wsl.exe --import $distro $destination $archivePath --version 2
    if ($LASTEXITCODE -ne 0) { throw 'WSL import failed.' }
}
$linuxRepo = (& wsl.exe -d $distro -u root --exec wslpath -a $repo.Replace('\', '/')).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve workspace path.' }
& wsl.exe -d $distro -u root -- bash "$linuxRepo/scripts/bootstrap.sh"
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap failed; fix the error and rerun with -Resume.' }
$passwordStatus = & wsl.exe -d $distro -u root --exec passwd -S admin
if ($LASTEXITCODE -ne 0) { throw 'Cannot read admin password status.' }
if (($passwordStatus -split '\s+')[1] -ne 'P') {
    Write-Host 'Choose your admin password. Input is hidden and is not saved in the repository.'
    & wsl.exe -d $distro -u root --exec passwd admin
    if ($LASTEXITCODE -ne 0) { throw 'Password setup failed; rerun with -Resume.' }
}
& wsl.exe --terminate $distro
if ($LASTEXITCODE -ne 0) { throw 'Cannot restart lhlinux.' }
Start-Sleep -Seconds 3
& wsl.exe -d $distro -u root -- bash "$linuxRepo/scripts/install-tools.sh"
if ($LASTEXITCODE -ne 0) { throw 'Tool installation failed; fix the error and rerun with -Resume.' }
& wsl.exe -d $distro -- bash -lc lhlinux-check
if ($LASTEXITCODE -ne 0) { throw 'Verification failed.' }
Write-Host 'Ready: wsl -d lhlinux --cd ~'
