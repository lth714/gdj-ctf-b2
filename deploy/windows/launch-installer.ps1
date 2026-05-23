# Launch Ubuntu installer for a CTF VM
# Usage: powershell -ExecutionPolicy Bypass -File launch-installer.ps1 <vm-id>
# Example: .\launch-installer.ps1 a1

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("a1","a2","b1","b2","c1","c2")]
    [string]$VmId
)

$QEMU = "D:\environment\qemu\qemu-system-x86_64.exe"
$ISO = "E:\mirror\ubuntu-20.04.6-live-server-amd64.iso"
$VMS_DIR = "E:\vibecoding\gdj_ctf\vms"
$DISK = Join-Path $VMS_DIR "ctfd-$VmId.qcow2"

if (-not (Test-Path $QEMU)) {
    Write-Host "[ERROR] QEMU not found: $QEMU" -ForegroundColor Red
    pause; exit 1
}
if (-not (Test-Path $ISO)) {
    Write-Host "[ERROR] ISO not found: $ISO" -ForegroundColor Red
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

Write-Host "============================================"
Write-Host " Install Ubuntu on ctfd-$VmId ($Type)" -ForegroundColor Green
Write-Host " RAM: ${RAM}MB  vCPU: $VCPU"
Write-Host "============================================"
Write-Host ""
Write-Host " IMPORTANT during install:"
Write-Host "   - Language: English"
Write-Host "   - Network: DHCP (auto)"
Write-Host "   - CHECK [*] Install OpenSSH server"
Write-Host "   - Note the IP shown after install"
Write-Host ""

Read-Host "Press Enter to start installer"

# Detect TAP
$tap = Get-NetAdapter -Name "*TAP*" -ErrorAction SilentlyContinue
if ($tap) {
    Write-Host "[*] Network: TAP bridge (VM gets DHCP IP)" -ForegroundColor Cyan
    $netArgs = "-nic", "tap,ifname=TAP-Windows Adapter V9,model=virtio"
} else {
    Write-Host "[*] Network: NAT (Internet=YES, SSH=localhost:2222)" -ForegroundColor Cyan
    $netArgs = "-nic", "user,model=virtio,hostfwd=tcp::2222-:22"
}

Write-Host "[*] Accelerator: WHPX" -ForegroundColor Cyan
Write-Host "[*] Starting QEMU..." -ForegroundColor Yellow

$qemuArgs = @(
    "-accel", "whpx",
    "-m", $RAM.ToString(),
    "-smp", $VCPU.ToString(),
    "-boot", "order=d",
    "-drive", "file=$DISK,format=qcow2,if=virtio",
    "-cdrom", $ISO
) + $netArgs + @(
    "-display", "gtk",
    "-name", "ctfd-$VmId"
)

$proc = Start-Process -FilePath $QEMU -ArgumentList $qemuArgs -PassThru
$proc.WaitForExit()

Write-Host ""
Write-Host "[*] Installer closed for ctfd-$VmId" -ForegroundColor Yellow
Read-Host "Press Enter to exit"
