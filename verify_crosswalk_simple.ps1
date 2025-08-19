# Simple Crosswalk Verification Script
Write-Host "🔍 DRAFTKINGS CROSSWALK VERIFICATION" -ForegroundColor Cyan
Write-Host "=================================================="

try {
    # Load the data files
    Write-Host "📁 Loading data files..." -ForegroundColor Yellow
    
    $dk = Import-Csv "data\DKSalaries.csv"
    $ext = Import-Csv "data\external_ids.csv" | Where-Object { $_.provider -eq 'draftkings' }
    $aliases = Import-Csv "data\aliases.csv" | Where-Object { $_.source -eq 'draftkings' }
    
    Write-Host "✓ Loaded $($dk.Count) DK players" -ForegroundColor Green
    Write-Host "✓ Loaded $($ext.Count) DK external ID mappings" -ForegroundColor Green
    Write-Host "✓ Loaded $($aliases.Count) DK aliases" -ForegroundColor Green
    
    # Normalize IDs for comparison
    $dkIDs = $dk | Where-Object { $_.ID } | ForEach-Object { $_.ID.ToString().Trim() } | Sort-Object -Unique
    $mapIDs = $ext | Where-Object { $_.provider_player_id } | ForEach-Object { $_.provider_player_id.ToString().Trim() } | Sort-Object -Unique
    
    Write-Host "`n📊 COVERAGE ANALYSIS" -ForegroundColor Cyan
    Write-Host "-------------------------"
    
    # Calculate coverage
    $common = Compare-Object $dkIDs $mapIDs -IncludeEqual -ExcludeDifferent | Select-Object -ExpandProperty InputObject
    $coveragePct = [math]::Round(($common.Count * 100.0) / $dkIDs.Count, 2)
    
    Write-Host "DK slate players: $($dkIDs.Count)"
    Write-Host "Covered by crosswalk: $($common.Count)"
    Write-Host "Coverage percentage: $coveragePct%"
    
    # Check for duplicates
    Write-Host "`n🔍 QUALITY CHECKS" -ForegroundColor Cyan
    Write-Host "--------------------"
    
    # Duplicate DK IDs in crosswalk
    $dupByDK = $ext | Group-Object provider_player_id | Where-Object { $_.Count -gt 1 }
    if ($dupByDK.Count -gt 0) {
        Write-Host "❌ Duplicate DK IDs in crosswalk: $($dupByDK.Count)" -ForegroundColor Red
        $dupByDK | ForEach-Object { Write-Host "  - DK ID $($_.Name) appears $($_.Count) times" }
    } else {
        Write-Host "✓ No duplicate DK IDs" -ForegroundColor Green
    }
    
    # Missing DK IDs
    $missing = Compare-Object $dkIDs $mapIDs | Where-Object { $_.SideIndicator -eq '<=' }
    if ($missing.Count -gt 0) {
        Write-Host "`n❌ MISSING DK IDs ($($missing.Count) total)" -ForegroundColor Red
        Write-Host "Sample missing IDs (first 10):"
        
        $missing | Select-Object -First 10 | ForEach-Object {
            $dkPlayer = $dk | Where-Object { $_.ID.ToString().Trim() -eq $_.InputObject } | Select-Object -First 1
            if ($dkPlayer) {
                $playerInfo = "ID: $($dkPlayer.ID) | $($dkPlayer.Name) | $($dkPlayer.Position) | $($dkPlayer.TeamAbbrev)"
                Write-Host "  - $playerInfo"
            }
        }
        
        # Save full list to file
        $missingDetails = @()
        $missing | ForEach-Object {
            $dkPlayer = $dk | Where-Object { $_.ID.ToString().Trim() -eq $_.InputObject } | Select-Object -First 1
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
        Write-Host "`n💾 Full missing list saved to: reports\missing_dk_ids.csv" -ForegroundColor Yellow
    } else {
        Write-Host "✓ All DK IDs are covered!" -ForegroundColor Green
    }
    
    # Summary recommendation
    Write-Host "`n🎯 RECOMMENDATION" -ForegroundColor Cyan
    Write-Host "--------------------"
    
    if ($coveragePct -ge 99 -and $dupByDK.Count -eq 0) {
        Write-Host "✅ EXCELLENT! Your crosswalk is ready to use." -ForegroundColor Green
        Write-Host "   → Proceed with entity_id-based joins" -ForegroundColor Green
        Write-Host "   → Stop using fuzzy name matching" -ForegroundColor Green
    } elseif ($coveragePct -ge 95) {
        Write-Host "⚠️  GOOD but needs minor fixes:" -ForegroundColor Yellow
        Write-Host "   → Add $($missing.Count) missing players to external_ids.csv" -ForegroundColor Yellow
    } else {
        Write-Host "❌ NEEDS WORK before using:" -ForegroundColor Red
        Write-Host "   → Coverage too low ($coveragePct%). Add missing players." -ForegroundColor Red
        Write-Host "   → Consider regenerating crosswalk files" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ Error running verification: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure data files exist in the 'data' directory" -ForegroundColor Yellow
}

Write-Host "`n=================================================="
Write-Host "Verification complete! 🏁" -ForegroundColor Cyan
