# Firewall Configuration Script for Distributed Deadlock System
# Run this script as Administrator on both laptops

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Distributed Deadlock System" -ForegroundColor Cyan
Write-Host "Firewall Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "1. Right-click on PowerShell" -ForegroundColor Yellow
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "3. Run this script again" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit
}

Write-Host "Running with Administrator privileges..." -ForegroundColor Green
Write-Host ""

# Display current IP address
Write-Host "Your current IP configuration:" -ForegroundColor Yellow
ipconfig | Select-String "IPv4"
Write-Host ""

# Confirm action
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  1. Allow inbound TCP connections on ports 5000 and 5001" -ForegroundColor White
Write-Host "  2. Create firewall rules for the distributed deadlock system" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "Do you want to continue? (Y/N)"

if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "Operation cancelled." -ForegroundColor Yellow
    pause
    exit
}

Write-Host ""
Write-Host "Configuring firewall..." -ForegroundColor Cyan

# Remove existing rules if they exist
Write-Host "Removing any existing rules..." -ForegroundColor Yellow
try {
    Remove-NetFirewallRule -DisplayName "Deadlock System Port 5000" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "Deadlock System Port 5001" -ErrorAction SilentlyContinue
} catch {
    # Ignore errors if rules don't exist
}

# Create new firewall rules
Write-Host "Creating firewall rule for port 5000..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "Deadlock System Port 5000" `
        -Direction Inbound `
        -LocalPort 5000 `
        -Protocol TCP `
        -Action Allow `
        -Profile Domain,Private,Public | Out-Null
    Write-Host "  Port 5000 configured successfully!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Could not configure port 5000" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Creating firewall rule for port 5001..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "Deadlock System Port 5001" `
        -Direction Inbound `
        -LocalPort 5001 `
        -Protocol TCP `
        -Action Allow `
        -Profile Domain,Private,Public | Out-Null
    Write-Host "  Port 5001 configured successfully!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Could not configure port 5001" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Firewall Configuration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify rules
Write-Host "Verifying firewall rules..." -ForegroundColor Yellow
$rules = Get-NetFirewallRule -DisplayName "Deadlock System*" | Select-Object DisplayName, Enabled, Direction

if ($rules) {
    Write-Host ""
    Write-Host "Active firewall rules:" -ForegroundColor Green
    $rules | Format-Table -AutoSize
} else {
    Write-Host "Warning: Could not verify firewall rules" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run this script on the other laptop" -ForegroundColor White
Write-Host "2. Note both laptops' IP addresses" -ForegroundColor White
Write-Host "3. Test network connection:" -ForegroundColor White
Write-Host "   python test_network.py" -ForegroundColor Yellow
Write-Host "4. Launch distributed system:" -ForegroundColor White
Write-Host "   python main.py --distributed" -ForegroundColor Yellow
Write-Host ""

# Test port availability
Write-Host "Testing port availability..." -ForegroundColor Yellow
$ports = @(5000, 5001)
foreach ($port in $ports) {
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $port)
        $listener.Start()
        $listener.Stop()
        Write-Host "  Port $port is available" -ForegroundColor Green
    } catch {
        Write-Host "  Port $port is already in use!" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Configuration complete! You can now run the distributed system." -ForegroundColor Green
Write-Host ""
pause
