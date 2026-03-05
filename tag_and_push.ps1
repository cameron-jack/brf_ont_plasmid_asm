$VER = "v3.04.000"
$DATE = "Date: {0}" -f (Get-Date)

$COMMENT = @"
* New: dedicated script to run pipeline on Gadi
* New: uses Chopper to handle read filtering instead of NanoFilt
* New: generates launch and run scripts for Gadi
"@

Move-Item -Path "changelog.txt" -Destination "changelog_old.txt"
Set-Content -Path "changelog.txt" -Value $VER
Add-Content -Path "changelog.txt" -Value $DATE
Add-Content -Path "changelog.txt" -Value $COMMENT
Add-Content -Path "changelog.txt" -Value ""
Get-Content -Path "changelog_old.txt" | Add-Content -Path "changelog.txt"
Remove-Item -Path "changelog_old.txt"

git add -u
$MSG = $COMMENT
git commit -m $MSG
git tag -a $VER -m $MSG

git push
git push origin $VER
