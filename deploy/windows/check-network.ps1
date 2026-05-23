# Check QEMU network/acceleration status
# Usage: powershell -ExecutionPolicy Bypass -File check-network.ps1

Write-Host "============================================"
Write-Host " CTF Environment Check" -ForegroundColor Green
Write-Host "============================================"
Write-Host ""

# Check TAP adapter
Write-Host "[1] TAP Adapter:" -ForegroundColor Yellow
$tap = Get-NetAdapter -Name "*TAP*" -ErrorAction SilentlyContinue
if ($tap) {
    Write-Host "  [OK] TAP adapter found:" -ForegroundColor Green
    $tap | Format-Table Name, Status, InterfaceDescription
} else {
    Write-Host "  [MISSING] TAP-Windows adapter not installed" -ForegroundColor Red
    Write-Host "  Install: download OpenVPN, select TAP driver only"
    Write-Host "  Fallback: use NAT mode (user) for VMs"
}

Write-Host ""

# Check WHPX
Write-Host "[2] WHPX Acceleration:" -ForegroundColor Yellow
$hyperv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction SilentlyContinue
if ($hyperv -and $hyperv.State -eq "Enabled") {
    Write-Host "  [OK] Hyper-V enabled, WHPX available" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Hyper-V not enabled, TCG mode (slow)" -ForegroundColor Yellow
}

Write-Host ""

# Check QEMU
Write-Host "[3] QEMU:" -ForegroundColor Yellow
$qemuExe = "D:\environment\qemu\qemu-system-x86_64.exe"
if (Test-Path $qemuExe) {
    $ver = & $qemuExe --version 2>&1 | Select-Object -First 1
    Write-Host "  [OK] $ver" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] $qemuExe" -ForegroundColor Red
}

Write-Host ""

# Check ISO
Write-Host "[4] ISO:" -ForegroundColor Yellow
$isoPath = "E:\mirror\ubuntu-20.04.6-live-server-amd64.iso"
if (Test-Path $isoPath) {
    $size = (Get-Item $isoPath).Length / 1GB
    Write-Host "  [OK] Ubuntu 20.04 Server ISO ({0:N1} GB)" -f $size -ForegroundColor Green
} else {
    Write-Host "  [MISSING] $isoPath" -ForegroundColor Red
}

Write-Host ""

# Check active NICs
Write-Host "[5] Active NICs:" -ForegroundColor Yellow
Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Format-Table Name, LinkSpeed, InterfaceDescription

Write-Host ""
Read-Host "Press Enter to exit"
