"""
Property-based tests for Reporter module
Tests Property 7: Report Persistence Round-Trip
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime
from hypothesis import given, strategies as st, settings
from modules.reporter import Reporter, ScamReport

class TestReporterProperties:
    """Property-based tests for reporter module"""
    
    def setup_method(self):
        """Set up temporary directory and reporter for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.log_path = os.path.join(self.temp_dir, "test.log")
        self.reporter = Reporter(self.db_path, self.log_path)
    
    def teardown_method(self):
        """Clean up temporary directory"""
        # Close any open database connections
        if hasattr(self, 'reporter'):
            # Force close any open connections by creating a new connection and closing it
            try:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                conn.close()
            except:
                pass
        
        # Try to remove directory, ignore errors on Windows
        try:
            shutil.rmtree(self.temp_dir)
        except PermissionError:
            # On Windows, sometimes files are still locked
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass  # Ignore cleanup errors in tests
    
    @given(
        final_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        visual_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        liveness_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        audio_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        detected_keywords=st.text(max_size=200),
        phone_number=st.one_of(st.none(), st.text(min_size=10, max_size=15)),
        notes=st.one_of(st.none(), st.text(max_size=500))
    )
    @settings(max_examples=20)
    def test_report_persistence_round_trip(self, final_score, visual_score, liveness_score, 
                                         audio_score, detected_keywords, phone_number, notes):
        """
        **Feature: kavalan-lite, Property 7: Report Persistence Round-Trip**
        
        For any ScamReport saved to the database, querying the database by ID
        should return an equivalent report with all fields preserved.
        """
        # Create original report
        original_report = ScamReport(
            final_score=final_score,
            visual_score=visual_score,
            liveness_score=liveness_score,
            audio_score=audio_score,
            detected_keywords=detected_keywords,
            phone_number=phone_number,
            notes=notes
        )
        
        # Save report to database
        report_id = self.reporter.save_report(original_report)
        
        # Retrieve report by ID
        retrieved_report = self.reporter.get_report_by_id(report_id)
        
        # Property 7: Round-trip preservation
        assert retrieved_report is not None, "Report should be retrievable after saving"
        assert retrieved_report.id == report_id, f"ID mismatch: {retrieved_report.id} != {report_id}"
        
        # Verify all numeric fields are preserved (with floating point tolerance)
        assert abs(retrieved_report.final_score - original_report.final_score) < 1e-10, \
            f"Final score not preserved: {retrieved_report.final_score} != {original_report.final_score}"
        assert abs(retrieved_report.visual_score - original_report.visual_score) < 1e-10, \
            f"Visual score not preserved: {retrieved_report.visual_score} != {original_report.visual_score}"
        assert abs(retrieved_report.liveness_score - original_report.liveness_score) < 1e-10, \
            f"Liveness score not preserved: {retrieved_report.liveness_score} != {original_report.liveness_score}"
        assert abs(retrieved_report.audio_score - original_report.audio_score) < 1e-10, \
            f"Audio score not preserved: {retrieved_report.audio_score} != {original_report.audio_score}"
        
        # Verify string fields are preserved
        assert retrieved_report.detected_keywords == original_report.detected_keywords, \
            f"Keywords not preserved: '{retrieved_report.detected_keywords}' != '{original_report.detected_keywords}'"
        assert retrieved_report.phone_number == original_report.phone_number, \
            f"Phone number not preserved: '{retrieved_report.phone_number}' != '{original_report.phone_number}'"
        assert retrieved_report.notes == original_report.notes, \
            f"Notes not preserved: '{retrieved_report.notes}' != '{original_report.notes}'"
        
        # Verify timestamp is preserved (within reasonable tolerance)
        if original_report.timestamp and retrieved_report.timestamp:
            time_diff = abs((retrieved_report.timestamp - original_report.timestamp).total_seconds())
            assert time_diff < 1.0, f"Timestamp not preserved: diff={time_diff}s"
    
    @given(
        reports_data=st.lists(
            st.tuples(
                st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),  # final_score
                st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),  # visual_score
                st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),  # liveness_score
                st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),  # audio_score
                st.text(max_size=50)  # detected_keywords
            ),
            min_size=1, max_size=10
        )
    )
    @settings(max_examples=10)
    def test_multiple_reports_persistence(self, reports_data):
        """
        **Feature: kavalan-lite, Property 7: Report Persistence Round-Trip (Extended)**
        
        For any list of ScamReports saved to the database, all should be
        retrievable and preserve their data correctly.
        """
        saved_ids = []
        original_reports = []
        
        # Save all reports
        for final_score, visual_score, liveness_score, audio_score, keywords in reports_data:
            report = ScamReport(
                final_score=final_score,
                visual_score=visual_score,
                liveness_score=liveness_score,
                audio_score=audio_score,
                detected_keywords=keywords
            )
            original_reports.append(report)
            report_id = self.reporter.save_report(report)
            saved_ids.append(report_id)
        
        # Retrieve all reports
        retrieved_reports = self.reporter.get_reports(limit=len(reports_data))
        
        # Property: All reports should be retrievable
        assert len(retrieved_reports) == len(reports_data), \
            f"Not all reports retrieved: {len(retrieved_reports)} != {len(reports_data)}"
        
        # Property: Each report should preserve its data
        for i, retrieved in enumerate(retrieved_reports):
            # Reports are returned in reverse chronological order, so we need to match by ID
            assert retrieved.id in saved_ids, f"Retrieved report ID {retrieved.id} not in saved IDs"
            
            # Find corresponding original report
            original_idx = saved_ids.index(retrieved.id)
            original = original_reports[original_idx]
            
            # Verify data preservation
            assert abs(retrieved.final_score - original.final_score) < 1e-10, \
                f"Final score not preserved for report {retrieved.id}"
            assert retrieved.detected_keywords == original.detected_keywords, \
                f"Keywords not preserved for report {retrieved.id}"
    
    def test_database_schema_consistency(self):
        """
        **Feature: kavalan-lite, Property 7: Report Persistence Round-Trip (Schema)**
        
        The database schema should be consistent and support all required operations.
        """
        # Test that database was initialized correctly
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check that table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scam_reports'")
            table_exists = cursor.fetchone() is not None
            assert table_exists, "scam_reports table should exist"
            
            # Check that indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_timestamp'")
            timestamp_index_exists = cursor.fetchone() is not None
            assert timestamp_index_exists, "timestamp index should exist"
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_final_score'")
            score_index_exists = cursor.fetchone() is not None
            assert score_index_exists, "final_score index should exist"
    
    def test_report_filtering_property(self):
        """
        **Feature: kavalan-lite, Property 7: Report Persistence Round-Trip (Filtering)**
        
        Reports should be filterable by score and retrievable correctly.
        """
        # Create reports with different scores
        low_score_report = ScamReport(final_score=3.0, visual_score=2.0, liveness_score=3.0, audio_score=4.0)
        high_score_report = ScamReport(final_score=9.0, visual_score=8.0, liveness_score=9.0, audio_score=10.0)
        
        # Save both reports
        low_id = self.reporter.save_report(low_score_report)
        high_id = self.reporter.save_report(high_score_report)
        
        # Test filtering by minimum score
        all_reports = self.reporter.get_reports(min_score=0.0)
        high_score_reports = self.reporter.get_reports(min_score=8.0)
        
        # Property: Filtering should work correctly
        assert len(all_reports) == 2, f"Should retrieve 2 reports with min_score=0.0: {len(all_reports)}"
        assert len(high_score_reports) == 1, f"Should retrieve 1 report with min_score=8.0: {len(high_score_reports)}"
        assert high_score_reports[0].id == high_id, "High score report should be retrieved"
        assert high_score_reports[0].final_score >= 8.0, "Retrieved report should meet score criteria"
    
    def test_statistics_consistency_property(self):
        """
        **Feature: kavalan-lite, Property 7: Report Persistence Round-Trip (Statistics)**
        
        Database statistics should be consistent with saved data.
        """
        # Save some test reports
        reports = [
            ScamReport(final_score=5.0, visual_score=4.0, liveness_score=5.0, audio_score=6.0),
            ScamReport(final_score=9.0, visual_score=8.0, liveness_score=9.0, audio_score=10.0),
            ScamReport(final_score=7.0, visual_score=6.0, liveness_score=7.0, audio_score=8.0)
        ]
        
        for report in reports:
            self.reporter.save_report(report)
        
        # Get statistics
        stats = self.reporter.get_statistics()
        
        # Property: Statistics should be consistent
        assert stats['total_reports'] == 3, f"Total reports should be 3: {stats['total_reports']}"
        assert stats['high_risk_reports'] == 1, f"High risk reports should be 1: {stats['high_risk_reports']}"
        
        # Calculate expected average
        expected_avg = (5.0 + 9.0 + 7.0) / 3
        assert abs(stats['average_score'] - expected_avg) < 0.01, \
            f"Average score incorrect: {stats['average_score']} != {expected_avg}"
        
        expected_alert_rate = (1 / 3) * 100  # 33.3%
        assert abs(stats['alert_rate'] - expected_alert_rate) < 0.1, \
            f"Alert rate incorrect: {stats['alert_rate']} != {expected_alert_rate}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])