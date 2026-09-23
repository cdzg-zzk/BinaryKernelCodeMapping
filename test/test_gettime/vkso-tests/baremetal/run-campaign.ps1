# Run the existing Clocktime campaign from an interactive Windows PowerShell.
# SSH key login is required. sudo may prompt through ssh -tt; unattended use
# additionally requires the research machine's sudo policy to allow it.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$User = 'zzk',
    [string]$RemoteDir = '/home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal',
    [int]$Port = 22,
    [int]$BootTimeoutSeconds = 600,
    [int]$PollSeconds = 8,
    [int]$MaxCases = 0,
    [switch]$Unattended
)

$ErrorActionPreference = 'Stop'
if ($RemoteDir -notmatch '^/[A-Za-z0-9._/-]+$' -or
    $User -notmatch '^[A-Za-z0-9._-]+$' -or
    $Server -notmatch '^[A-Za-z0-9._-]+$' -or
    $Port -lt 1 -or $Port -gt 65535 -or
    $BootTimeoutSeconds -lt 30 -or $PollSeconds -lt 1 -or $MaxCases -lt 0) {
    throw 'Invalid SSH target, remote directory, port, or timeout.'
}

$target = "${User}@${Server}"
$sshArgs = @('-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
             '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3',
             '-p', [string]$Port)
$ttyArg = if ($Unattended) { '-T' } else { '-tt' }
$script:LastSshCode = 0

function Invoke-SSHText([string]$command) {
    $lines = & ssh.exe @sshArgs -T $target $command
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "SSH command exited $code`: $command" }
    return (@($lines) -join "`n")
}

function Invoke-SSHConsole([string]$command) {
    & ssh.exe @sshArgs $ttyArg $target $command
    $script:LastSshCode = $LASTEXITCODE
}

function Get-Field([string]$text, [string]$name) {
    $match = [regex]::Match($text, "(?m)^$([regex]::Escape($name))=([^`r`n]+)`r?$")
    if (-not $match.Success) { throw "Missing $name in remote output: $text" }
    return $match.Groups[1].Value
}

function Get-Token([string]$text, [string]$name) {
    $match = [regex]::Match($text, "(?:^|\s)$([regex]::Escape($name))=([^\s]+)")
    if (-not $match.Success) { throw "Missing $name in remote output: $text" }
    return $match.Groups[1].Value
}

function Get-CampaignState {
    $text = Invoke-SSHText "cd $RemoteDir && ./experiment.sh status"
    $state = Get-Field $text 'status'
    if ($state -notin @('active', 'complete')) {
        throw "Campaign is $state; run experiment.sh begin on the server first."
    }
    $record = [pscustomobject]@{
        Status = $state
        Completed = [int](Get-Field $text 'completed_boots')
        Mode = $null
        Case = $null
    }
    if ($state -eq 'active') {
        $record.Mode = Get-Token $text 'next_mode'
        $record.Case = Get-Token $text 'next_case'
        if ($record.Mode -notin @('read', 'update') -or
            $record.Case -notin @('raw-normal', 'vkso-normal',
                                  'raw-no-retpoline', 'vkso-no-retpoline')) {
            throw "Unexpected next case: $text"
        }
    }
    return $record
}

function Get-BootIdentity {
    $text = Invoke-SSHText 'printf "BOOT_ID="; cat /proc/sys/kernel/random/boot_id; printf "KERNEL="; uname -r; printf "CMDLINE="; cat /proc/cmdline'
    $cmdline = Get-Field $text 'CMDLINE'
    $image = [regex]::Match($cmdline, '(?:^|\s)BOOT_IMAGE=([^\s]+)')
    if (-not $image.Success) { throw "Missing BOOT_IMAGE in: $cmdline" }
    return [pscustomobject]@{
        BootId = Get-Field $text 'BOOT_ID'
        Kernel = Get-Field $text 'KERNEL'
        Image = ($image.Groups[1].Value -split '/')[-1]
    }
}

function Wait-NewBoot([string]$oldBootId, [string]$expectedImage) {
    $deadline = (Get-Date).AddSeconds($BootTimeoutSeconds)
    do {
        Start-Sleep -Seconds $PollSeconds
        try { $boot = Get-BootIdentity }
        catch {
            # SSH may be down while the machine reboots. Malformed output from
            # a reachable server is a real error and must not be hidden.
            if ($_.Exception.Message -notlike 'SSH command exited*') { throw }
            continue
        }
        if ($boot.BootId -eq $oldBootId) { continue }
        if ($boot.Kernel -ne '5.15.198' -or $boot.Image -ne $expectedImage) {
            throw "Wrong boot: kernel=$($boot.Kernel) image=$($boot.Image); expected $expectedImage"
        }
        return $boot
    } while ((Get-Date) -lt $deadline)
    throw "No new boot with $expectedImage within $BootTimeoutSeconds seconds. Check the server and GRUB before retrying."
}

try {
    $collectedThisRun = 0
    while ($true) {
        $state = Get-CampaignState
        Write-Host "completed_boots=$($state.Completed) status=$($state.Status)"
        if ($state.Status -eq 'complete') { break }

        $expectedImage = if ($state.Mode -eq 'read') {
            "vkso-final-$($state.Case)-5.15.198.bzImage"
        } else {
            "vkso-update-$($state.Case)-5.15.198.bzImage"
        }
        $boot = Get-BootIdentity
        if ($boot.Kernel -ne '5.15.198' -or $boot.Image -ne $expectedImage) {
            Write-Host "BOOT $($state.Mode):$($state.Case) (currently $($boot.Image))"
            Invoke-SSHConsole "cd $RemoteDir && ./experiment.sh boot $($state.Mode):$($state.Case)"
            # A reboot often closes SSH with exit 255. Trust the new boot ID
            # and exact BOOT_IMAGE, rather than that connection's exit code.
            if ($script:LastSshCode -notin @(0, 255)) {
                try { $stillUp = Get-BootIdentity } catch { $stillUp = $null }
                if ($null -ne $stillUp -and $stillUp.BootId -eq $boot.BootId) {
                    throw "boot command exited $script:LastSshCode without rebooting."
                }
            }
            $boot = Wait-NewBoot $boot.BootId $expectedImage
            Write-Host "New boot: $($boot.BootId) $($boot.Image)"
        } else {
            Write-Host "Current boot already matches $expectedImage; collect without another reboot."
        }

        Write-Host "COLLECT $($state.Mode):$($state.Case)"
        Invoke-SSHConsole "cd $RemoteDir && ./experiment.sh collect $($state.Mode):$($state.Case)"
        $collectCode = $script:LastSshCode
        $after = Get-CampaignState
        if ($after.Completed -ne $state.Completed + 1) {
            throw "collect exited $collectCode and completed_boots did not advance. Inspect the server before retrying."
        }
        if ($collectCode -ne 0) {
            Write-Warning "SSH exited $collectCode, but the server confirms this collect was counted."
        }
        Write-Host "COLLECT PASS: completed_boots=$($after.Completed)"
        $collectedThisRun++
        if ($MaxCases -gt 0 -and $collectedThisRun -ge $MaxCases) { break }
    }

    $finalState = Get-CampaignState
    if ($finalState.Status -eq 'complete') {
        Write-Host 'Campaign complete; aggregating raw results.'
        $summary = Invoke-SSHText "cd $RemoteDir && ./experiment.sh aggregate"
        Write-Host $summary
    } else {
        Write-Host "Stopped after $collectedThisRun case(s); completed_boots=$($finalState.Completed). Re-run to resume."
    }
}
catch {
    [Console]::Error.WriteLine("Campaign stopped: $($_.Exception.Message)")
    exit 1
}
