#!/usr/bin/env bash
# plasmid_run_cleanup_v8.sh
# Safer cleanup for plasmid run folders with optional dry-run and backups.
# Author: Ziyang Zhang with Claude

set -Eeuo pipefail
IFS=$'\n\t'

usage() {
  cat <<'USAGE'
Usage: cleanup [-n|--dry-run] [-b|--backup] FOLDER
  -n, --dry-run   Show actions without deleting/renaming anything.
  -b, --backup    Copy targets into a timestamped backup folder before deletion.
USAGE
}

DRY_RUN=false
BACKUP=false
FOLDER=""

# ---- Parse args ----
while (( $# )); do
  case "${1:-}" in
    -n|--dry-run) DRY_RUN=true; shift ;;
    -b|--backup)  BACKUP=true;  shift ;;
    -h|--help)    usage; exit 0 ;;
    -* ) echo "Invalid option: $1" >&2; usage; exit 1 ;;
    *  ) FOLDER="$1"; shift ;;
  esac
done

if [[ -z "${FOLDER:-}" ]]; then
  echo "Error: FOLDER is required." >&2
  usage
  exit 1
fi
if [[ ! -d "$FOLDER" ]]; then
  echo "Error: Folder '$FOLDER' does not exist." >&2
  exit 1
fi

LOG_FILE="$FOLDER/cleanup.log"
SUMMARY_FILE="$FOLDER/cleanup_summary.txt"
: > "$SUMMARY_FILE"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "$(timestamp) - $*" | tee -a "$LOG_FILE"; }
summ() { echo "$*" >> "$SUMMARY_FILE"; }

# ---- Backup root ----
BACKUP_ROOT=""
if $BACKUP; then
  BACKUP_ROOT="$FOLDER/.cleanup_backups/$(date '+%Y%m%d_%H%M%S')"
  mkdir -p "$BACKUP_ROOT"
fi

relpath_from_folder() {
  local path="$1"
  # Strip leading FOLDER/ to make relative path
  local rel="${path#"$FOLDER"/}"
  echo "$rel"
}

backup_path() {
  local path="$1"
  $BACKUP || return 0
  local rel; rel="$(relpath_from_folder "$path")"
  local dest="$BACKUP_ROOT/$rel"
  mkdir -p "$(dirname "$dest")"
  if [[ -d "$path" ]]; then
    cp -a "$path" "$dest"
  else
    cp -a "$path" "$dest"
  fi
  summ "Backed up: $path -> $dest"
}

delete_path() {
  local path="$1"
  backup_path "$path"
  if $DRY_RUN; then
    log "[DRY-RUN] Would delete: $path"
    summ "[DRY-RUN] Would delete: $path"
  else
    if [[ -d "$path" ]]; then
      rm -rf -- "$path"
    else
      rm -f -- "$path"
    fi
    log "Deleted: $path"
    summ "Deleted: $path"
  fi
}

# delete_direct: always deletes immediately, ignores --dry-run and --backup
delete_direct() {
  local path="$1"
  if $DRY_RUN; then
    log "[WARNING] --dry-run is active but this deletion will still proceed: $path"
    summ "[WARNING] --dry-run is active but this deletion will still proceed: $path"
  fi
  if [[ -d "$path" ]]; then
    rm -rf -- "$path"
  else
    rm -f -- "$path"
  fi
  log "Deleted (direct): $path"
  summ "Deleted (direct): $path"
}

rename_dir() {
  local src="$1" dst="$2"
  if $DRY_RUN; then
    log "[DRY-RUN] Would rename: $(basename "$src") -> $(basename "$dst")"
    summ "[DRY-RUN] Would rename: $(basename "$src") -> $(basename "$dst")"
  else
    mv -- "$src" "$dst"
    log "Renamed: $(basename "$src") -> $(basename "$dst")"
    summ "Renamed: $(basename "$src") -> $(basename "$dst")"
  fi
}

log "Starting cleanup in folder: $FOLDER"
$DRY_RUN && log "Dry-run mode enabled. No files will be deleted (except direct deletions — see warnings)."
$BACKUP && log "Backup mode enabled. Backups: $BACKUP_ROOT"

# ---- 1) Delete run_*.qsub files (directly inside $FOLDER only) ----
log "Deleting run_*.qsub files…"
while IFS= read -r -d '' file; do
  delete_path "$file"
done < <(find "$FOLDER" -maxdepth 1 -type f -name 'run_*.qsub' -print0)

# ---- 2) Delete *.csv except *ref.csv ----
log "Deleting .csv files except *ref.csv…"
while IFS= read -r -d '' file; do
  delete_path "$file"
done < <(find "$FOLDER" -type f -name '*.csv' ! -name '*ref.csv' -print0)

# ---- 3) Delete 'work' subfolder if present ----
if [[ -d "$FOLDER/work" ]]; then
  log "Deleting 'work' folder…"
  delete_path "$FOLDER/work"
fi

# ---- 4) Clean each 'output*' folder (output, output_2, output_wofilter, etc.) ----
cleanup_output() {
  local output_folder="$1"
  log "Cleaning output folder: $output_folder"

  # Remove specific targets
  for target in "execution" "feature_table.txt"; do
    local path="$output_folder/$target"
    if [[ -e "$path" ]]; then
      delete_path "$path"
    fi
  done

  # Remove selected extensions
  local ext
  for ext in gbk maf json bcf; do
    while IFS= read -r -d '' f; do
      delete_path "$f"
    done < <(find "$output_folder" -type f -name "*.${ext}" -print0)
  done
}

# Recursively find all folders whose name starts with 'output'
while IFS= read -r -d '' outdir; do
  cleanup_output "$outdir"
done < <(find "$FOLDER" -type d -name 'output*' -print0)

# ---- 5) Delete *_filt.sh scripts inside subfolders (not $FOLDER root) ----
log "Deleting *_filt.sh files inside subfolders…"
while IFS= read -r -d '' file; do
  delete_path "$file"
done < <(find "$FOLDER" -mindepth 2 -type f -name '*_filt.sh' -print0)

# ---- 6) Clean barcode* folders: remove unfilt_barcode* files ----
log "Searching for barcode* folders…"
while IFS= read -r -d '' bcdir; do
  log "Cleaning barcode folder: $bcdir"
  while IFS= read -r -d '' f; do
    delete_path "$f"
  done < <(find "$bcdir" -maxdepth 1 -type f -name 'unfilt_barcode*' -print0)
done < <(find "$FOLDER" -type d -name 'barcode*' -print0)

# ---- 7) Process subfolders (hook preserved if you need per-subdir ops) ----
for dir in "$FOLDER"/*/; do
  [[ -d "$dir" ]] || continue
  log "Processing subfolder: $dir"
  # (Already handled output folders above)
done

# ---- 8) Optional: Rename subfolders with date prefix if folder matches plasmid_run_YYYYMMDD ----
if [[ "$(basename "$FOLDER")" =~ ^plasmid_run_([0-9]{8})$ ]]; then
  DATE_PREFIX="${BASH_REMATCH[1]}"
  log "Renaming immediate subfolders with date prefix: $DATE_PREFIX"
  for subdir in "$FOLDER"/*/; do
    [[ -d "$subdir" ]] || continue
    base_name="$(basename "$subdir")"
    # Skip already-prefixed, and skip the backup directory
    if [[ "$base_name" == ".cleanup_backups" || "$base_name" == ${DATE_PREFIX}_* ]]; then
      continue
    fi
    new_name="${FOLDER}/${DATE_PREFIX}_${base_name}"
    rename_dir "$subdir" "$new_name"
  done
fi

# ---- 9) Delete .nextflow folder or file (direct, no dry-run/backup) ----
# FIX: merged sections 8 and 10 from v6 — .nextflow cannot be both a file
# and a folder simultaneously, so we check each case explicitly.
log "Deleting .nextflow folder or file if present…"
if [[ -d "$FOLDER/.nextflow" ]]; then
  delete_direct "$FOLDER/.nextflow"
elif [[ -f "$FOLDER/.nextflow" ]]; then
  delete_direct "$FOLDER/.nextflow"
fi

# ---- 10) Delete .nextflow.log* files (direct, no dry-run/backup) ----
log "Deleting .nextflow.log* files…"
while IFS= read -r -d '' file; do
  delete_direct "$file"
done < <(find "$FOLDER" -maxdepth 1 -type f -name '.nextflow.log*' -print0)

# ---- 11) Delete plsmd_asm* tmp files (direct, no dry-run/backup) ----
log "Deleting plsmd_asm* tmp files…"
while IFS= read -r -d '' file; do
  delete_direct "$file"
done < <(find "$FOLDER" -maxdepth 1 -type f -name 'plsmd_asm*' -print0)

log "Cleanup and renaming completed."
log "Summary written to $SUMMARY_FILE"
