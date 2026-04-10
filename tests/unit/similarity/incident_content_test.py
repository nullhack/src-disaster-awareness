"""Tests for IncidentContent value object."""

import pytest

from disaster_surveillance_reporter.similarity._types import IncidentContent


class TestIncidentContent:
    """Test IncidentContent value object behavior."""

    def test_given_complete_incident_data_when_created_then_should_store_all_fields(
        self,
    ):
        """
        Given: Complete incident data with all required fields
        When: IncidentContent is created
        Then: Should store all fields correctly
        """
        content = IncidentContent(
            title="M7.2 Earthquake near Tokyo",
            description="A magnitude 7.2 earthquake struck near Tokyo, Japan at 14:30 UTC",
            location="Tokyo, Japan",
            incident_id="gdacs_20260410_001",
        )

        assert content.title == "M7.2 Earthquake near Tokyo"
        assert (
            content.description
            == "A magnitude 7.2 earthquake struck near Tokyo, Japan at 14:30 UTC"
        )
        assert content.location == "Tokyo, Japan"
        assert content.incident_id == "gdacs_20260410_001"

    def test_given_incident_dict_when_creating_from_dict_then_should_extract_fields(
        self,
    ):
        """
        Given: Incident dictionary with standard fields
        When: Creating IncidentContent from dict
        Then: Should extract and map fields correctly
        """
        incident_dict = {
            "title": "Disease Outbreak in Nigeria",
            "description": "ProMED report of cholera outbreak in Lagos state",
            "location": "Lagos, Nigeria",
            "incident_id": "promed_20260410_002",
            "date": "2026-04-10",  # Extra field should be ignored
            "source": "ProMED",  # Extra field should be ignored
        }

        content = IncidentContent.from_dict(incident_dict)

        assert content.title == "Disease Outbreak in Nigeria"
        assert content.description == "ProMED report of cholera outbreak in Lagos state"
        assert content.location == "Lagos, Nigeria"
        assert content.incident_id == "promed_20260410_002"

    def test_given_prototype_high_similarity_incidents_when_created_then_should_match_test_data(
        self,
    ):
        """
        Given: High similarity incidents from prototype validation
        When: IncidentContent is created
        Then: Should match prototype test fixture data
        """
        # Using prototype test data for high similarity (0.952 score)
        incident1 = IncidentContent(
            title="WHO Health Alert - Disease Outbreak China",
            description="World Health Organization reports disease outbreak in China region",
            location="China",
            incident_id="who_20260410_001",
        )

        incident2 = IncidentContent(
            title="WHO Alert Disease Outbreak China Regional",
            description="WHO health alert for regional disease outbreak in China",
            location="China",
            incident_id="who_20260410_002",
        )

        # These should be very similar based on prototype data
        assert incident1.title != incident2.title  # Different but similar
        assert "WHO" in incident1.title and "WHO" in incident2.title
        assert "China" in incident1.location and "China" in incident2.location

    def test_given_prototype_medium_similarity_incidents_when_created_then_should_match_test_data(
        self,
    ):
        """
        Given: Medium similarity incidents from prototype validation (0.716 score)
        When: IncidentContent is created
        Then: Should match prototype test fixture data
        """
        incident1 = IncidentContent(
            title="M4.5 Earthquake Japan",
            description="Magnitude 4.5 earthquake recorded in Japan region",
            location="Japan",
            incident_id="gdacs_20260410_003",
        )

        incident2 = IncidentContent(
            title="M4.7 Earthquake Japan Region",
            description="M4.7 earthquake in Japan regional area",
            location="Japan",
            incident_id="gdacs_20260410_004",
        )

        # These should be moderately similar based on prototype data
        assert "Japan" in incident1.title and "Japan" in incident2.title
        assert "M4." in incident1.title and "M4." in incident2.title
        assert incident1.incident_id != incident2.incident_id

    def test_given_prototype_low_similarity_incidents_when_created_then_should_be_different(
        self,
    ):
        """
        Given: Low similarity incidents from prototype validation (0.129 score)
        When: IncidentContent is created
        Then: Should be clearly different as in test fixtures
        """
        incident1 = IncidentContent(
            title="Earthquake Japan",
            description="Seismic activity reported in Japan",
            location="Japan",
            incident_id="gdacs_20260410_005",
        )

        incident2 = IncidentContent(
            title="Disease Outbreak Nigeria",
            description="Health emergency reported in Nigeria",
            location="Nigeria",
            incident_id="promed_20260410_003",
        )

        # These should be completely different
        assert incident1.location != incident2.location
        assert "Japan" not in incident2.title
        assert "Nigeria" not in incident1.title
        assert "Earthquake" not in incident2.title
        assert "Disease" not in incident1.title

    def test_given_missing_fields_in_dict_when_creating_from_dict_then_should_handle_gracefully(
        self,
    ):
        """
        Given: Incident dictionary with missing fields
        When: Creating IncidentContent from dict
        Then: Should handle missing fields gracefully with empty strings
        """
        incomplete_dict = {
            "title": "Incomplete Incident",
            "incident_id": "test_001",
            # Missing description and location
        }

        content = IncidentContent.from_dict(incomplete_dict)

        assert content.title == "Incomplete Incident"
        assert content.incident_id == "test_001"
        assert content.description == ""  # Should default to empty
        assert content.location == ""  # Should default to empty

    def test_given_empty_strings_when_created_then_should_store_empty_values(self):
        """
        Given: IncidentContent with empty string values
        When: Created with empty fields
        Then: Should store empty strings correctly
        """
        content = IncidentContent(
            title="", description="", location="", incident_id="empty_001"
        )

        assert content.title == ""
        assert content.description == ""
        assert content.location == ""
        assert content.incident_id == "empty_001"

    def test_given_incident_content_when_created_then_should_be_immutable(self):
        """
        Given: An IncidentContent instance
        When: Attempting to modify attributes
        Then: Should raise AttributeError (frozen dataclass)
        """
        content = IncidentContent(
            title="Test Incident",
            description="Test description",
            location="Test Location",
            incident_id="test_001",
        )

        with pytest.raises(AttributeError):
            content.title = "Modified Title"

    def test_given_real_gdacs_data_when_creating_from_dict_then_should_extract_correctly(
        self,
    ):
        """
        Given: Real GDACS incident data structure
        When: Creating IncidentContent from dict
        Then: Should extract fields matching GDACS adapter output
        """
        gdacs_incident = {
            "title": "M5.2 earthquake, 45km N of Kushiro, Japan",
            "description": "Earthquake of magnitude 5.2 occurred 45km N of Kushiro, Japan",
            "location": "Kushiro, Japan",
            "incident_id": "gdacs_earthquake_20260410_12345",
            "magnitude": 5.2,  # Extra GDACS-specific field
            "depth": "10km",  # Extra GDACS-specific field
            "source_url": "https://example.com",  # Extra field
        }

        content = IncidentContent.from_dict(gdacs_incident)

        assert content.title == "M5.2 earthquake, 45km N of Kushiro, Japan"
        assert "magnitude 5.2" in content.description
        assert content.location == "Kushiro, Japan"
        assert content.incident_id == "gdacs_earthquake_20260410_12345"

    def test_given_long_description_when_created_then_should_store_full_content(self):
        """
        Given: Incident with very long description
        When: IncidentContent is created
        Then: Should store full description (truncation handled in matching)
        """
        long_description = "This is a very long description " * 20  # ~600 chars

        content = IncidentContent(
            title="Long Description Test",
            description=long_description,
            location="Test Location",
            incident_id="long_001",
        )

        assert len(content.description) > 500
        assert content.description == long_description  # Full storage
