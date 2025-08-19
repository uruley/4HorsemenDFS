Write-Host "Checking crosswalk files..." -ForegroundColor Green

# Load files
$dk = Import-Csv "data\DKSalaries.csv"
$ext = Import-Csv "data\external_ids.csv"
$aliases = Import-Csv "data\aliases.csv"

Write-Host "DK players: $($dk.Count)"
Write-Host "External IDs: $($ext.Count)"
Write-Host "Aliases: $($aliases.Count)"

# Check DraftKings coverage
$dkIds = $dk.ID | Sort-Object -Unique
$dkExtIds = $ext | Where-Object { $_.source_name -eq 'draftkings' } | Select-Object -ExpandProperty external_id | Sort-Object -Unique

Write-Host "`nDK IDs in salary file: $($dkIds.Count)"
Write-Host "DK IDs in external_ids: $($dkExtIds.Count)"

# Find missing
$missing = $dkIds | Where-Object { $_ -notin $dkExtIds }
Write-Host "Missing DK IDs: $($missing.Count)"

if ($missing.Count -gt 0) {
    Write-Host "`nMissing players details:"
    foreach ($missingId in $missing) {
        $dkPlayer = $dk | Where-Object { $_.ID -eq $missingId } | Select-Object -First 1
        if ($dkPlayer) {
            Write-Host "  ID: $($dkPlayer.ID) | $($dkPlayer.Name) | $($dkPlayer.Position) | $($dkPlayer.TeamAbbrev)"
        }
    }
}

# Check coverage percentage
$coverage = [math]::Round((($dkIds.Count - $missing.Count) * 100.0) / $dkIds.Count, 2)
Write-Host "`nCoverage: $coverage%"

# Check for duplicates
$duplicates = $ext | Where-Object { $_.source_name -eq 'draftkings' } | Group-Object external_id | Where-Object { $_.Count -gt 1 }
Write-Host "Duplicate DK IDs: $($duplicates.Count)"

# Save missing to file
if ($missing.Count -gt 0) {
    $missingDetails = @()
    foreach ($missingId in $missing) {
        $dkPlayer = $dk | Where-Object { $_.ID -eq $missingId } | Select-Object -First 1
        if ($dkPlayer) {
            $missingDetails += [PSCustomObject]@{
                ID = $dkPlayer.ID
                Name = $dkPlayer.Name
                Position = $dkPlayer.Position
                TeamAbbrev = $dkPlayer.TeamAbbrev
                Salary = $dkPlayer.Salary
            }
        }
    }
    
    if (-not (Test-Path "reports")) { New-Item -ItemType Directory -Path "reports" }
    $missingDetails | Export-Csv "reports\missing_dk_ids.csv" -NoTypeInformation
    Write-Host "`n💾 Missing players saved to: reports\missing_dk_ids.csv"
}
