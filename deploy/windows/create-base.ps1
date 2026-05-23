# Create 6 qcow2 disks for CTF VMs (15GB each)
# Usage: powershell -ExecutionPolicy Bypass -File create-base.ps1

$QEMU_IMG = "D:\environment\qemu\qemu-img.exe"
$VMS_DIR = "E:\vibecoding\gdj_ctf\vms"

if (-not (Test-Path $QEMU_IMG)) {
    Write-Host "[ERROR] qemu-img.exe not found: $QEMU_IMG" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "============================================"
Write-Host " Create 6 CTF VM Disks" -ForegroundColor Green
Write-Host "============================================"
Write-Host ""
Write-Host "Target: $VMS_DIR"
Write-Host ""

New-Item -ItemType Directory -Force -Path $VMS_DIR | Out-Null

$vms = @("a1", "a2", "b1", "b2", "c1", "c2")
foreach ($vm in $vms) {
    $disk = Join-Path $VMS_DIR "ctfd-$vm.qcow2"
    if (Test-Path $disk) {
        Write-Host "  [SKIP] ctfd-$vm.qcow2 already exists" -ForegroundColor Gray
    } else {
        Write-Host "  [CREATE] ctfd-$vm.qcow2 (15G)..." -ForegroundColor Yellow
        & $QEMU_IMG create -f qcow2 $disk 15G 2>&1 | Out-Null
        Write-Host "    -> $disk" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[DONE] All 6 disks ready." -ForegroundColor Green
Write-Host "Next: .\launch-installer.ps1 <vm-id>"
Write-Host "Example: .\launch-installer.ps1 a1"
Read-Host "Press Enter to exit"
