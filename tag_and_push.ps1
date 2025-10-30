$VER = "v3.03.000"
$DATE = "Date: {0}" -f (Get-Date)

$COMMENT = @"
* New: updated to v1.8 of the core pipeline
* Fixed: Now uses suggested plasmid size from initial samplesheet
* Fixed: moves unfiltered FASTQ to unfiltered_data folder for client before a run
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
