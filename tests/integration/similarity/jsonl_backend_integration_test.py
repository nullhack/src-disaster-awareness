"""Integration tests for ContentSimilarityMatcher with JSONLBackend."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from disaster_surveillance_reporter.similarity._types import SimilarityScore
from disaster_surveillance_reporter.similarity.matcher import (
    FuzzyContentSimilarityMatcher,
)
from disaster_surveillance_reporter.storage.jsonl import JSONLBackend


class TestJSONLBackendIntegration:
    """Test ContentSimilarityMatcher integration with JSONLBackend."""

    def test_given_existing_incidents_when_upserting_with_duplicates_then_should_merge_incidents(
        self,
    ):
        """
        Given: Existing incidents in JSONL file
        When: Upserting new incidents with similarity matcher detecting duplicates
        Then: Should merge duplicates and append new incidents
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "incidents"
            backend = JSONLBackend(storage_path)

            # Create existing incidents file
            today_path = storage_path / "2026-04-10"
            today_path.mkdir(parents=True)
            existing_file = today_path / "incidents.jsonl"

            existing_incidents = [
                {
                    "title": "M7.2 Earthquake Tokyo",
                    "description": "Major earthquake near Tokyo",
                    "location": "Tokyo, Japan",
                    "date": "2026-04-10",
                    "source_url": "http://example.com/1",
                    "priority": "High",
                    "incident_id": "existing_001",
                }
            ]

            with Path(existing_file).open("w") as f:
                f.writelines(json.dumps(incident) + "\n" for incident in existing_incidents)

            # New incidents with one duplicate and one new
            new_incidents = [
                {
                    "title": "M7.2 Earthquake Tokyo Japan",  # Very similar - should be duplicate
                    "description": "Major earthquake near Tokyo region",
                    "location": "Tokyo, Japan",
                    "date": "2026-04-10",
                    "source_url": "http://example.com/2",
                    "priority": "High",
                    "incident_id": "new_001",
                },
                {
                    "title": "Disease Outbreak Nigeria",  # New incident
                    "description": "Health emergency in Nigeria",
                    "location": "Lagos, Nigeria",
                    "date": "2026-04-10",
                    "source_url": "http://example.com/3",
                    "priority": "Medium",
                    "incident_id": "new_002",
                },
            ]

            # Create similarity matcher
            mock_strategy = Mock()
            similarity_matcher = FuzzyContentSimilarityMatcher(
                strategy=mock_strategy, threshold=0.8
            )

            # Mock similarity calculations
            def mock_calculate_similarity(content1, content2):
                if (
                    "Tokyo" in content1.title
                    and "Tokyo" in content2.title
                    and content1.incident_id != content2.incident_id
                ):
                    return SimilarityScore(
                        0.95, 0.90, 1.0, 0.952, 0.8
                    )  # High similarity
                return SimilarityScore(0.1, 0.1, 0.1, 0.1, 0.8)  # Low similarity

            similarity_matcher.calculate_similarity = Mock(
                side_effect=mock_calculate_similarity
            )

            # Perform upsert
            backend.upsert(new_incidents, similarity_matcher)

            # Read back all incidents
            stored_incidents = backend.read("2026-04-10")

            # Should have 2 incidents total (duplicate merged, new added)
            assert len(stored_incidents) == 2

            # Check that Tokyo incident was merged (should have some fields from both)
            tokyo_incidents = [
                inc for inc in stored_incidents if "Tokyo" in inc["title"]
            ]
            assert len(tokyo_incidents) == 1

            # Check that Nigeria incident was added
            nigeria_incidents = [
                inc for inc in stored_incidents if "Nigeria" in inc["title"]
            ]
            assert len(nigeria_incidents) == 1

    def test_given_no_existing_incidents_when_upserting_then_should_create_new_file(
        self,
    ):
        """
        Given: No existing incidents in JSONL file
        When: Upserting new incidents
        Then: Should create new file with all incidents
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "incidents"
            backend = JSONLBackend(storage_path)

            new_incidents = [
                {
                    "title": "New Incident 1",
                    "description": "Description 1",
                    "location": "Location 1",
                    "date": "2026-04-10",
                    "incident_id": "new_001",
                },
                {
                    "title": "New Incident 2",
                    "description": "Description 2",
                    "location": "Location 2",
                    "date": "2026-04-10",
                    "incident_id": "new_002",
                },
            ]

            # Create mock similarity matcher (no duplicates)
            mock_strategy = Mock()
            similarity_matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)
            similarity_matcher.calculate_similarity = Mock(
                return_value=SimilarityScore(0.1, 0.1, 0.1, 0.1, 0.8)  # No duplicates
            )

            # Perform upsert
            backend.upsert(new_incidents, similarity_matcher)

            # Verify file was created with all incidents
            stored_incidents = backend.read("2026-04-10")
            assert len(stored_incidents) == 2

    def test_given_large_dataset_when_upserting_then_should_perform_efficiently(self):
        """
        Given: Large dataset for upsert operation
        When: Upserting with similarity matching
        Then: Should perform within reasonable time bounds
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "incidents"
            backend = JSONLBackend(storage_path)

            # Create existing incidents
            existing_incidents = [
                {
                    "title": f"Existing Incident {i}",
                    "description": f"Existing description {i}",
                    "location": f"Location {i}",
                    "date": "2026-04-10",
                    "incident_id": f"existing_{i:03d}",
                }
                for i in range(50)  # 50 existing incidents
            ]

            # Store existing incidents first
            backend.write(existing_incidents)

            # Create new incidents (some duplicates)
            new_incidents = [
                {
                    "title": f"New Incident {i}"
                    if i >= 25
                    else f"Existing Incident {i}",  # First 25 are duplicates
                    "description": f"New description {i}",
                    "location": f"Location {i}",
                    "date": "2026-04-10",
                    "incident_id": f"new_{i:03d}",
                }
                for i in range(50)  # 50 new incidents
            ]

            # Fast mock strategy
            mock_strategy = Mock()
            mock_strategy.match.return_value = 0.5  # Medium similarity
            similarity_matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)

            # Mock similarity to make first 25 duplicates
            def mock_calculate_similarity(content1, content2):
                if content1.title.replace("New", "Existing") == content2.title:
                    return SimilarityScore(0.95, 0.90, 1.0, 0.952, 0.8)  # Duplicate
                return SimilarityScore(0.1, 0.1, 0.1, 0.1, 0.8)  # Not duplicate

            similarity_matcher.calculate_similarity = Mock(
                side_effect=mock_calculate_similarity
            )

            # Perform upsert with timing
            import time

            start_time = time.time()
            backend.upsert(new_incidents, similarity_matcher)
            elapsed_time = time.time() - start_time

            # Should complete within reasonable time
            assert elapsed_time < 10.0  # Generous bound for 100 total incidents

            # Verify results
            stored_incidents = backend.read("2026-04-10")
            # Should have 75 incidents (50 existing + 25 new unique, 25 duplicates merged)
            assert len(stored_incidents) == 75

    def test_given_upsert_without_similarity_matcher_when_called_then_should_raise_error(
        self,
    ):
        """
        Given: Upsert method called without similarity matcher
        When: Method is invoked
        Then: Should raise ValueError
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "incidents"
            backend = JSONLBackend(storage_path)

            new_incidents = [
                {
                    "title": "Test",
                    "description": "Test",
                    "date": "2026-04-10",
                    "incident_id": "test_001",
                }
            ]

            with pytest.raises(ValueError, match="similarity_matcher is required"):
                backend.upsert(new_incidents, None)

    def test_given_corrupted_existing_file_when_upserting_then_should_handle_gracefully(
        self,
    ):
        """
        Given: Corrupted existing JSONL file
        When: Upserting new incidents
        Then: Should handle gracefully and create new file
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "incidents"
            backend = JSONLBackend(storage_path)

            # Create corrupted file
            today_path = storage_path / "2026-04-10"
            today_path.mkdir(parents=True)
            existing_file = today_path / "incidents.jsonl"

            with Path(existing_file).open("w") as f:
                f.write('{"valid": "json"}\n')
                f.write("invalid json line\n")  # Corrupted line
                f.write('{"another": "valid"}\n')

            new_incidents = [
                {
                    "title": "New Incident",
                    "description": "Description",
                    "location": "Location",
                    "date": "2026-04-10",
                    "incident_id": "new_001",
                }
            ]

            # Mock similarity matcher
            mock_strategy = Mock()
            similarity_matcher = FuzzyContentSimilarityMatcher(strategy=mock_strategy)
            similarity_matcher.calculate_similarity = Mock(
                return_value=SimilarityScore(0.1, 0.1, 0.1, 0.1, 0.8)
            )

            # Should handle corrupted file gracefully
            backend.upsert(new_incidents, similarity_matcher)

            # Should have stored new incident
            stored_incidents = backend.read("2026-04-10")
            assert len(stored_incidents) >= 1  # At least the new incident

    def test_given_merge_strategy_when_upserting_duplicates_then_should_preserve_important_fields(
        self,
    ):
        """
        Given: Duplicate incidents with different field values
        When: Upserting with merge strategy
        Then: Should preserve important fields from both incidents
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "incidents"
            backend = JSONLBackend(storage_path)

            # Existing incident
            existing_incidents = [
                {
                    "title": "M7.2 Earthquake Tokyo",
                    "description": "Original description",
                    "location": "Tokyo, Japan",
                    "date": "2026-04-10",
                    "source_url": "http://original.com",
                    "priority": "High",
                    "incident_id": "original_001",
                    "magnitude": 7.2,
                }
            ]

            backend.write(existing_incidents)

            # New incident with additional/updated fields
            new_incidents = [
                {
                    "title": "M7.2 Earthquake Tokyo Japan",
                    "description": "Updated description with more details",
                    "location": "Tokyo, Japan",
                    "date": "2026-04-10",
                    "source_url": "http://updated.com",
                    "priority": "Critical",  # Updated priority
                    "incident_id": "updated_001",
                    "casualties": 50,  # New field
                    "depth": "10km",  # New field
                }
            ]

            # Mock high similarity (duplicate)
            mock_strategy = Mock()
            similarity_matcher = FuzzyContentSimilarityMatcher(
                strategy=mock_strategy, threshold=0.8
            )
            similarity_matcher.calculate_similarity = Mock(
                return_value=SimilarityScore(
                    0.95, 0.90, 1.0, 0.952, 0.8
                )  # High similarity
            )

            backend.upsert(new_incidents, similarity_matcher)

            # Verify merge results
            stored_incidents = backend.read("2026-04-10")
            assert len(stored_incidents) == 1  # Should have merged

            merged_incident = stored_incidents[0]

            # Should preserve new/updated fields
            assert "casualties" in merged_incident  # New field added
            assert "depth" in merged_incident  # New field added
            assert merged_incident["priority"] == "Critical"  # Updated field

            # Should preserve original fields
            assert merged_incident["magnitude"] == 7.2  # Original field preserved
