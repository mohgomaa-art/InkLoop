#!/usr/bin/env python3
"""
InkLoop Manga Output Image Collector
====================================
Collects all rendered manga and comic output images across the workspace
(from `runs/`, `backend/runs/`, and `scratch/`) into a single consolidated folder:
`all_manga_output_images/`.

Constraints:
- Strictly excludes any .pdf files.
- Preserves all original source files in their original locations.
- Maps hash-addressed artifact_store objects back to descriptive human-readable names
  using runs/artifact_store/registry.db.
- Disambiguates filename collisions deterministically with context prefixes or suffixes.
- Generates comprehensive manifest.json and manifest.csv files with metadata,
  file sizes, SHA-256 hashes, source origins, and duplication tags.
"""

import os
import sys
import csv
import json
import shutil
import hashlib
import sqlite3
import re
from pathlib import Path
from collections import defaultdict


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def clean_filename(name: str) -> str:
    # Remove illegal Windows filename characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', name)
    # Strip spaces and dots at the ends
    return cleaned.strip(" .")


def categorize_image(name: str, src_path: str) -> str:
    name_lower = name.lower()
    path_lower = src_path.lower()
    if "composite" in name_lower or "composite" in path_lower:
        return "page_composite"
    elif "export" in path_lower or "export" in name_lower:
        return "page_export"
    elif "turnaround" in name_lower or "bust" in name_lower or "expression" in name_lower:
        return "character_model_sheet"
    elif "panel" in name_lower or "panel" in path_lower:
        return "panel_artwork"
    elif "preview" in name_lower or "preview" in path_lower:
        return "style_preview"
    elif "scratch" in path_lower:
        return "proof_or_scratch_render"
    elif "reference" in path_lower or "reference" in name_lower:
        return "character_reference"
    else:
        return "manga_generation"


def main():
    repo_root = Path(__file__).resolve().parent.parent
    dest_dir = repo_root / "all_manga_output_images"
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"InkLoop Image Collector initialized.")
    print(f"Destination: {dest_dir}")

    # 1. Load Registry DB asset mappings
    registry_db = repo_root / "runs" / "artifact_store" / "registry.db"
    managed_map = {}
    hash_map = defaultdict(list)
    if registry_db.exists():
        conn = sqlite3.connect(registry_db)
        c = conn.cursor()
        c.execute("""
            SELECT managed_path, original_filename, name, project_id, asset_type, content_sha256
            FROM assets
        """)
        for row in c.fetchall():
            managed_path, orig, name, proj, asset_type, content_sha = row
            best_name = orig or name
            if managed_path and best_name:
                norm_path = Path(managed_path).as_posix().lower()
                managed_map[norm_path] = (best_name, proj, asset_type)
            if content_sha and best_name:
                hash_map[content_sha.lower()].append((best_name, proj, asset_type))
        conn.close()
        print(f"Loaded {len(managed_map)} managed_path mappings and {len(hash_map)} sha256 mappings from registry.db.")

    # 2. Discover all candidate image files
    source_dirs = [
        repo_root / "runs",
        repo_root / "backend" / "runs",
        repo_root / "scratch",
    ]
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    candidate_files = []
    dest_posix = dest_dir.as_posix().lower()

    for sdir in source_dirs:
        if not sdir.exists():
            continue
        for p in sdir.rglob("*"):
            if not p.is_file():
                continue
            # Check extension
            ext = p.suffix.lower()
            if ext not in image_extensions:
                continue
            # Ensure not inside destination directory
            if p.as_posix().lower().startswith(dest_posix):
                continue
            candidate_files.append(p)

    print(f"Found {len(candidate_files)} image files across source directories.")

    # 3. Resolve target filenames and handle collisions
    used_names = set()
    manifest_records = []
    content_hash_counts = defaultdict(int)

    # First pass: compute hashes and find duplicate content
    file_metadata = []
    print("Computing hashes and preparing filenames...")
    for idx, src_path in enumerate(candidate_files, start=1):
        rel_src = src_path.relative_to(repo_root).as_posix()
        file_size = src_path.stat().st_size
        file_sha256 = compute_sha256(src_path)
        content_hash_counts[file_sha256] += 1

        # Determine best descriptive base name
        base_name = src_path.name
        project_id = ""
        p_posix = src_path.as_posix().lower()

        if "runs/artifact_store/objects" in p_posix:
            idx_obj = p_posix.find("objects/")
            sub_path = p_posix[idx_obj:]
            if sub_path in managed_map:
                candidate, proj, _ = managed_map[sub_path]
                base_name = candidate
                project_id = proj or ""
            elif file_sha256.lower() in hash_map:
                candidate, proj, _ = hash_map[file_sha256.lower()][0]
                base_name = candidate
                project_id = proj or ""

        # Clean base_name
        base_name = clean_filename(base_name)
        cand_p = Path(base_name)
        # Ensure extension matches actual file on disk
        if cand_p.suffix.lower() != src_path.suffix.lower():
            base_name = f"{cand_p.stem}{src_path.suffix.lower()}"

        file_metadata.append({
            "src_path": src_path,
            "rel_src": rel_src,
            "file_size": file_size,
            "file_sha256": file_sha256,
            "base_name": base_name,
            "project_id": project_id,
        })

    # Second pass: assign final unique destination filenames
    for item in file_metadata:
        src_path = item["src_path"]
        base_name = item["base_name"]
        rel_src = item["rel_src"]
        p_obj = Path(base_name)
        stem = p_obj.stem
        ext = src_path.suffix.lower()

        final_name = f"{stem}{ext}"

        if final_name in used_names:
            # Contextual disambiguation: try incorporating parent folder name if informative
            parent_name = clean_filename(src_path.parent.name)
            grandparent_name = clean_filename(src_path.parent.parent.name)
            context = ""
            if parent_name and parent_name not in ["objects", "panels", "runs"]:
                context = parent_name
            elif grandparent_name and grandparent_name not in ["objects", "runs"]:
                context = grandparent_name

            if context and f"{stem}_{context}{ext}" not in used_names:
                final_name = f"{stem}_{context}{ext}"
            else:
                counter = 1
                while True:
                    candidate = f"{stem}_{counter}{ext}" if not context else f"{stem}_{context}_{counter}{ext}"
                    if candidate not in used_names:
                        final_name = candidate
                        break
                    counter += 1

        used_names.add(final_name)
        item["dest_name"] = final_name

    # 4. Copy files to destination
    print(f"Copying {len(file_metadata)} files to {dest_dir}...")
    copied_count = 0
    total_bytes = 0

    for idx, item in enumerate(file_metadata, start=1):
        src_path = item["src_path"]
        dest_path = dest_dir / item["dest_name"]
        shutil.copy2(src_path, dest_path)
        copied_count += 1
        total_bytes += item["file_size"]

        category = categorize_image(item["dest_name"], item["rel_src"])
        is_dup = content_hash_counts[item["file_sha256"]] > 1

        record = {
            "destination_filename": item["dest_name"],
            "source_path": item["rel_src"],
            "source_directory": item["rel_src"].split("/")[0],
            "file_size_bytes": item["file_size"],
            "file_size_formatted": format_bytes(item["file_size"]),
            "sha256": item["file_sha256"],
            "extension": Path(item["dest_name"]).suffix.lower(),
            "category": category,
            "project_id": item["project_id"],
            "is_content_duplicate": is_dup,
        }
        manifest_records.append(record)

        if idx % 100 == 0 or idx == len(file_metadata):
            print(f"  Progress: {idx}/{len(file_metadata)} copied ({copied_count} total, {format_bytes(total_bytes)})...")

    # 5. Write manifest.json and manifest.csv
    manifest_json_path = dest_dir / "manifest.json"
    manifest_csv_path = dest_dir / "manifest.csv"

    summary_stats = {
        "total_files_collected": len(manifest_records),
        "total_size_bytes": total_bytes,
        "total_size_formatted": format_bytes(total_bytes),
        "unique_content_count": len(content_hash_counts),
        "files_with_duplicate_content": sum(1 for r in manifest_records if r["is_content_duplicate"]),
        "extensions_summary": {ext: sum(1 for r in manifest_records if r["extension"] == ext)
                               for ext in sorted(image_extensions)},
        "categories_summary": {cat: sum(1 for r in manifest_records if r["category"] == cat)
                               for cat in sorted({r["category"] for r in manifest_records})},
    }

    manifest_payload = {
        "summary": summary_stats,
        "files": manifest_records,
    }

    with open(manifest_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    fieldnames = [
        "destination_filename",
        "category",
        "file_size_formatted",
        "file_size_bytes",
        "extension",
        "source_path",
        "source_directory",
        "project_id",
        "is_content_duplicate",
        "sha256",
    ]
    with open(manifest_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in manifest_records:
            writer.writerow(r)

    print("\nCollection Complete!")
    print(f"Total files collected: {summary_stats['total_files_collected']}")
    print(f"Total size: {summary_stats['total_size_formatted']}")
    print(f"Unique images by SHA-256: {summary_stats['unique_content_count']}")
    print(f"Format breakdown: {summary_stats['extensions_summary']}")
    print(f"Category breakdown: {summary_stats['categories_summary']}")
    print(f"Manifests written: {manifest_json_path.name}, {manifest_csv_path.name}")


if __name__ == "__main__":
    main()
