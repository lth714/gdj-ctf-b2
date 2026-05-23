# Launch an installed CTF VM
# Usage: powershell -ExecutionPolicy Bypass -File launch-vm.ps1 <vm-id> [-NetMode tap|user]
# Example: .\launch-vm.ps1 a1
#          .\launch-vm.ps1 a2 -NetMode user

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("a1","a2","b1","b2","c1","c2")]
    [string]$VmId,
    [ValidateSet("tap","user")]
    [string]$NetMode = "tap"
)

$QEMU = "D:\environment\qemu\qemu-system-x86_64.exe"
$VMS_DIR = "E:\vibecoding\gdj_ctf\vms"
$DISK = Join-Path $VMS_DIR "ctfd-$VmId.qcow2"

if (-not (Test-Path $QEMU)) {
    Write-Host "[ERROR] QEMU not found: $QEMU" -ForegroundColor Red
    pause; exit 1
}
if (-not (Test-Path $DISK)) {
    Write-Host "[ERROR] Disk not found: $DISK" -ForegroundColor Red
    Write-Host "Run .\create-base.ps1 first"
    pause; exit 1
}

# Resource allocation
if ($VmId.EndsWith("2")) {
    $RAM = 4096; $VCPU = 2; $Type = "Internal"
} else {
    $RAM = 2048; $VCPU = 1; $Type = "DMZ"
}

# SSH port mapping (user mode)
$sshPorts = @{a1=2201; a2=2202; b1=2203; b2=2204; c1=2205; c2=2206}
$sshPort = $sshPorts[$VmId]

Write-Host "============================================"
Write-Host " Start ctfd-$VmId ($Type)" -ForegroundColor Green
Write-Host " RAM: ${RAM}MB  vCPU: $VCPU"
Write-Host "============================================"

# Network setup
if ($NetMode -eq "user") {
    Write-Host " Network: NAT (Internet=YES, SSH=localhost:$sshPort)" -ForegroundColor Cyan
    $netArgs = "-nic", "user,model=virtio,hostfwd=tcp::${sshPort}-:22"
} else {
    $tap = Get-NetAdapter -Name "*TAP*" -ErrorAction SilentlyContinue
    if (-not $tap) {
        Write-Host " [WARN] TAP not found, falling back to NAT" -ForegroundColor Yellow
        Write-Host " Network: NAT (SSH=localhost:$sshPort)" -ForegroundColor Cyan
        $netArgs = "-nic", "user,model=virtio,hostfwd=tcp::${sshPort}-:22"
    } else {
        Write-Host " Network: TAP bridge" -ForegroundColor Cyan
        $netArgs = "-nic", "tap,ifname=TAP-Windows Adapter V9,model=virtio"
    }
}

Write-Host " Accelerator: WHPX" -ForegroundColor Cyan

$qemuArgs = @(
    "-accel", "whpx",
    "-m", $RAM.ToString(),
    "-smp", $VCPU.ToString(),
    "-drive", "file=$DISK,format=qcow2,if=virtio"
) + $netArgs + @(
    "-display", "gtk",
    "-name", "ctfd-$VmId"
)

Write-Host ""
Write-Host "[*] Starting QEMU..." -ForegroundColor Yellow
$proc = Start-Process -FilePath $QEMU -ArgumentList $qemuArgs -PassThru
$proc.WaitForExit()

Write-Host "[*] ctfd-$VmId stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
