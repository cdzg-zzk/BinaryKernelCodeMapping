param(
    [ValidateRange(1, 100)][int]$Blocks = 8,
    [ValidateRange(1, 20)][int]$Repeats = 3,
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$RunId = ("native-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
)
$ErrorActionPreference = "Stop"
$Target = "zzk@10.177.21.196"
$Port = 50145
$PackageRoot = "/home/zzk/BinaryKernelCodeMapping/test/evaluation-local/packages/iso9660-native-20261029"
$ResultRoot = "/home/zzk/BinaryKernelCodeMapping/test/evaluation-local/runs/iso9660"
$DownloadDirectory = Join-Path (Get-Location) "iso9660-results"
New-Item -ItemType Directory -Force -Path $DownloadDirectory | Out-Null

Write-Host "Run: $RunId; blocks=$Blocks; repeats=$Repeats"
Write-Host "Enter the SSH/sudo password at the terminal prompts."
$RemoteCommand = "cd '$PackageRoot' && sudo bash run.sh --output '$ResultRoot/$RunId' --blocks $Blocks --repeats $Repeats"
& ssh -t -p $Port $Target $RemoteCommand
$RunExitCode = $LASTEXITCODE

# The runner writes a diagnostic archive on failure as well as on success.
$LocalArchive = Join-Path $DownloadDirectory "$RunId.tar.gz"
& scp -P $Port "${Target}:$ResultRoot/$RunId.tar.gz" $LocalArchive
$CopyExitCode = $LASTEXITCODE
if ($CopyExitCode -ne 0) {
    throw "Result download failed. Inspect $ResultRoot/$RunId on benchmark. SSH exit code: $RunExitCode"
}
Write-Host "Downloaded: $LocalArchive"
if ($RunExitCode -ne 0) {
    throw "Experiment stopped with exit code $RunExitCode; the diagnostic archive was retained."
}
Write-Host "Finished. result.json records completion; summary.json contains paired time ratios."
