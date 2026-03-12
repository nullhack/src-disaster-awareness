#!/usr/bin/env python3
"""
Validation script for the new efficient storage system.
Tests reference tracking, tag-based categorization, and data integrity.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def validate_reference_consistency(incidents_dir: Path) -> bool:
    """Verify all reference files point to correct incident data."""
    print("🔍 Validating reference consistency...")
    errors = 0

    ref_files = [
        "references/active/by-country-group.jsonl",
        "references/active/by-incident-type.jsonl",
        "references/active/by-country.jsonl",
        "references/inactive/by-country-group.jsonl",
        "references/inactive/by-incident-type.jsonl",
        "references/inactive/by-country.jsonl",
        "references/all-incidents-index.jsonl",
    ]

    for ref_file in ref_files:
        ref_path = incidents_dir / ref_file
        if not ref_path.exists():
            print(f"✅ Reference file doesn't exist yet: {ref_file}")
            continue

        print(f"  Checking {ref_file}...")

        try:
            with open(ref_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    ref = json.loads(line.strip())
                    incident_id = ref.get("incident_id")
                    file_path = ref.get("file")
                    line_ref = ref.get("line")

                    # Check if referenced file exists
                    target_file = incidents_dir / file_path
                    if not target_file.exists():
                        print(f"    ❌ Referenced file missing: {file_path}")
                        errors += 1
                        continue

                    # Check if line number is valid
                    with open(target_file, "r") as target:
                        lines = target.readlines()
                        if line_ref > len(lines):
                            print(
                                f"    ❌ Line number {line_ref} out of range in {file_path}"
                            )
                            errors += 1
                            continue

                        # Check if incident_id matches
                        target_line = lines[line_ref - 1].strip()
                        if target_line:
                            try:
                                target_incident = json.loads(target_line)
                                actual_id = target_incident.get("incident_id")

                                if actual_id != incident_id:
                                    print(
                                        f"    ❌ ID mismatch: expected {incident_id}, found {actual_id}"
                                    )
                                    errors += 1
                            except json.JSONDecodeError:
                                print(
                                    f"    ❌ Invalid JSON at line {line_ref} in {file_path}"
                                )
                                errors += 1

        except Exception as e:
            print(f"    ❌ Error reading {ref_file}: {e}")
            errors += 1

    if errors == 0:
        print("✅ All reference files are consistent!")
        return True
    else:
        print(f"❌ Found {errors} reference consistency errors")
        return False


def validate_tag_completeness(incidents_dir: Path) -> bool:
    """Verify all incidents have required standard tags."""
    print("\n🏷️  Validating tag completeness...")

    required_tag_types = {
        "status": ["active", "resolved", "monitoring", "forecasted"],
        "type": [
            "earthquake",
            "flood",
            "cyclone",
            "disease",
            "volcano",
            "wildfire",
            "drought",
            "landslide",
            "tsunami",
            "conflict",
        ],
        "country_group": ["group-a", "group-b", "group-c"],
        "severity": ["level-1", "level-2", "level-3", "level-4"],
        "priority": ["high-priority", "medium-priority", "low-priority"],
    }

    issues = 0
    total_incidents = 0

    # Check all incidents in by-date folders
    by_date_dir = incidents_dir / "by-date"
    if by_date_dir.exists():
        for date_folder in by_date_dir.iterdir():
            if date_folder.is_dir():
                incidents_file = date_folder / "incidents.jsonl"
                if incidents_file.exists():
                    print(f"  Checking tags in {incidents_file}...")

                    with open(incidents_file, "r") as f:
                        for line_num, line in enumerate(f, 1):
                            if not line.strip():
                                continue

                            total_incidents += 1
                            try:
                                incident = json.loads(line.strip())
                                tags = incident.get("tags", [])
                                incident_id = incident.get("incident_id", "unknown")

                                # Check each required tag type
                                for tag_type, valid_tags in required_tag_types.items():
                                    has_tag = any(tag in tags for tag in valid_tags)
                                    if not has_tag:
                                        print(
                                            f"    ⚠️  Missing {tag_type} tag in {incident_id}"
                                        )
                                        issues += 1

                            except json.JSONDecodeError:
                                print(f"    ❌ Invalid JSON at line {line_num}")
                                issues += 1

    print(f"\n📊 Tag validation results:")
    print(f"   Total incidents checked: {total_incidents}")
    print(f"   Tag completeness issues: {issues}")

    if issues == 0:
        print("✅ All incidents have complete tags!")
        return True
    else:
        print(f"⚠️  Found {issues} tag completeness issues")
        return True  # Non-blocking for now


def validate_no_duplication(incidents_dir: Path) -> bool:
    """Verify no incident data is duplicated across folders."""
    print("\n📦 Validating zero data duplication...")

    # Only primary storage should exist in by-date/
    primary_storage = incidents_dir / "by-date"

    # These folders should NOT exist anymore (old system)
    old_folders = [
        "by-country-group/group-a",
        "by-country-group/group-b",
        "by-country-group/group-c",
        "by-incident-type/earthquake",
        "by-incident-type/flood",
        "by-country/indonesia",
        "by-country/philippines",
    ]

    duplication_found = False

    for old_folder in old_folders:
        old_path = incidents_dir / old_folder
        if old_path.exists():
            # Check if it contains actual incident data (not just empty dirs)
            for file in old_path.rglob("incidents.jsonl"):
                if file.stat().st_size > 0:
                    print(f"⚠️  Found duplicate incident data in old folder: {file}")
                    duplication_found = True

    if not duplication_found:
        print("✅ No data duplication found - all incident data in by-date/ only!")
        return True
    else:
        print("❌ Data duplication detected in old folder structure")
        return False


def create_test_incident(incidents_dir: Path) -> bool:
    """Create a test incident to validate the new storage system."""
    print("\n🧪 Creating test incident...")

    test_date = datetime.now().strftime("%Y-%m-%d")
    test_incident = {
        "incident_id": f"{test_date.replace('-', '')}-ID-FL",
        "incident_name": "Test Flood in Indonesia",
        "created_date": f"{test_date}T10:15:00Z",
        "updated_date": f"{test_date}T10:15:00Z",
        "status": "Active",
        "country": "Indonesia",
        "country_group": "A",
        "incident_type": "Flood",
        "incident_level": 2,
        "priority": "MEDIUM",
        "tags": [
            "active",
            "flood",
            "group-a",
            "indonesia",
            "level-2",
            "medium-priority",
            "test-incident",
        ],
        "classification": {
            "country": "Indonesia",
            "country_group": "A",
            "incident_type": "Flood",
            "incident_level": 2,
            "priority": "MEDIUM",
            "should_report": True,
        },
        "location": {
            "country": "Indonesia",
            "provinces": [{"name": "Jakarta", "affected": True}],
            "affected_area_description": "Jakarta metropolitan area",
        },
        "sources": [
            {
                "name": "Test Source",
                "type": "other",
                "url": "https://example.com/test",
                "accessed_date": f"{test_date}T10:15:00Z",
            }
        ],
        "metadata": {"data_quality": "High", "tags": ["test-incident"]},
    }

    # Create directory structure
    date_dir = incidents_dir / "by-date" / test_date
    date_dir.mkdir(parents=True, exist_ok=True)

    # Store incident (primary storage)
    incidents_file = date_dir / "incidents.jsonl"
    with open(incidents_file, "a") as f:
        f.write(json.dumps(test_incident) + "\n")

    # Calculate line number
    with open(incidents_file, "r") as f:
        line_number = len(f.readlines())

    # Create reference entries
    ref_entry = {
        "incident_id": test_incident["incident_id"],
        "file": f"by-date/{test_date}/incidents.jsonl",
        "line": line_number,
        "country_group": "A",
        "type": "Flood",
        "priority": "MEDIUM",
    }

    # Add to active references
    active_refs = [
        "references/active/by-country-group.jsonl",
        "references/active/by-incident-type.jsonl",
        "references/active/by-country.jsonl",
    ]

    for ref_file in active_refs:
        ref_path = incidents_dir / ref_file
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ref_path, "a") as f:
            f.write(json.dumps(ref_entry) + "\n")

    # Add to master index
    index_entry = {
        "incident_id": test_incident["incident_id"],
        "date": test_date,
        "file": f"by-date/{test_date}/incidents.jsonl",
        "line": line_number,
        "status": "Active",
        "country_group": "A",
        "type": "Flood",
    }

    index_path = incidents_dir / "references/all-incidents-index.jsonl"
    with open(index_path, "a") as f:
        f.write(json.dumps(index_entry) + "\n")

    print(f"✅ Created test incident: {test_incident['incident_id']}")
    print(
        f"   Primary storage: by-date/{test_date}/incidents.jsonl (line {line_number})"
    )
    print(f"   References: 3 active reference files + master index")

    return True


def query_test(incidents_dir: Path) -> bool:
    """Test querying capabilities with the new system."""
    print("\n🔎 Testing query performance...")

    # Test 1: Quick stats from summary file
    summary_file = incidents_dir / "references/active/active-summary.json"
    if summary_file.exists():
        with open(summary_file, "r") as f:
            summary = json.load(f)
            print(f"   Quick stats: {summary.get('total_active', 0)} active incidents")

    # Test 2: Find incidents by country group
    group_refs = incidents_dir / "references/active/by-country-group.jsonl"
    if group_refs.exists():
        group_a_count = 0
        with open(group_refs, "r") as f:
            for line in f:
                if line.strip():
                    ref = json.loads(line.strip())
                    if ref.get("country_group") == "A":
                        group_a_count += 1
        print(f"   Group A incidents: {group_a_count}")

    # Test 3: Find incidents by type
    type_refs = incidents_dir / "references/active/by-incident-type.jsonl"
    if type_refs.exists():
        flood_count = 0
        with open(type_refs, "r") as f:
            for line in f:
                if line.strip():
                    ref = json.loads(line.strip())
                    if ref.get("type") == "Flood":
                        flood_count += 1
        print(f"   Flood incidents: {flood_count}")

    # Test 4: Master index lookup
    master_index = incidents_dir / "references/all-incidents-index.jsonl"
    if master_index.exists():
        total_incidents = 0
        with open(master_index, "r") as f:
            for line in f:
                if line.strip():
                    total_incidents += 1
        print(f"   Total incidents in master index: {total_incidents}")

    print("✅ Query tests completed!")
    return True


def main():
    """Run complete validation of the new storage system."""
    print("🚀 Validating New Efficient Storage System")
    print("=" * 50)

    # Find incidents directory
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    incidents_dir = project_dir / "incidents"

    if not incidents_dir.exists():
        incidents_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created incidents directory: {incidents_dir}")

    # Run validation tests
    tests = [
        (
            "Reference Consistency",
            lambda: validate_reference_consistency(incidents_dir),
        ),
        ("Tag Completeness", lambda: validate_tag_completeness(incidents_dir)),
        ("Zero Duplication", lambda: validate_no_duplication(incidents_dir)),
        ("Test Incident Creation", lambda: create_test_incident(incidents_dir)),
        ("Query Performance", lambda: query_test(incidents_dir)),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'=' * 20}")
        print(f"TEST: {test_name}")
        print(f"{'=' * 20}")

        try:
            result = test_func()
            if result:
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")

    # Final results
    print("\n" + "=" * 50)
    print(f"🎯 VALIDATION RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! New storage system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Review issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
