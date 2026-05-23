# Quick Test VM — single QEMU VM with NAT networking
# Usage: powershell -ExecutionPolicy Bypass -File quick-test.ps1

$QEMU = "D:\environment\qemu\qemu-system-x86_64.exe"
$QEMU_IMG = "D:\environment\qemu\qemu-img.exe"
$ISO = "E:\mirror\ubuntu-20.04.6-live-server-amd64.iso"
$DISK = "E:\vibecoding\gdj_ctf\vms\test-ubuntu.qcow2"

if (-not (Test-Path $QEMU)) {
    Write-Host "[ERROR] QEMU not found: $QEMU" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path $ISO)) {
    Write-Host "[ERROR] ISO not found: $ISO" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

New-Item -ItemType Directory -Force -Path "E:\vibecoding\gdj_ctf\vms" | Out-Null

if (-not (Test-Path $DISK)) {
    Write-Host "[*] Creating test disk (20G)..." -ForegroundColor Yellow
    & $QEMU_IMG create -f qcow2 $DISK 20G
} else {
    Write-Host "[*] Test disk already exists" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================"
Write-Host " QEMU Quick Test VM" -ForegroundColor Green
Write-Host "============================================"
Write-Host ""
Write-Host " Network: user-mode (NAT)"
Write-Host " Internet: YES (apt install works)"
Write-Host " SSH:     ssh ctfadmin@localhost -p 2222"
Write-Host ""
Write-Host " During Ubuntu install:"
Write-Host "   - Language: English"
Write-Host "   - CHECK [*] Install OpenSSH server"
Write-Host "   - User: ctfadmin / Ctf@2024#Setup"
Write-Host ""
Write-Host " Close QEMU window to stop VM."
Write-Host "============================================"
Write-Host ""

Read-Host "Press Enter to start VM"

$qemuArgs = @(
    "-accel", "whpx",
    "-m", "2048",
    "-smp", "2",
    "-boot", "order=d",
    "-drive", "file=$DISK,format=qcow2,if=virtio",
    "-cdrom", $ISO,
    "-nic", "user,model=virtio,hostfwd=tcp::2222-:22",
    "-display", "gtk",
    "-name", "CTF-Test-VM"
)

Write-Host "[*] Starting QEMU..." -ForegroundColor Yellow
Write-Host "[*] After install, SSH via: ssh ctfadmin@localhost -p 2222" -ForegroundColor Cyan

$proc = Start-Process -FilePath $QEMU -ArgumentList $qemuArgs -PassThru -WindowStyle Normal
$proc.WaitForExit()

Write-Host ""
Write-Host "[*] VM stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
