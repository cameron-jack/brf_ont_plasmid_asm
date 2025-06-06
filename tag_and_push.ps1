$VER = "v3.01.000"
$DATE = "Date: {0}" -f (Get-Date)

$COMMENT = @"
* NEW: custom script for max-length filtering FASTQ files
* CHANGED: expected plasmid length is now required in the sample sheet
* CHANGED: reads are now filter by length +/- 2K bp of the expected plasmid length
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
