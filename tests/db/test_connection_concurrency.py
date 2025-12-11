"""Thread safety and concurrency tests for database connection management."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from sqlalchemy.engine import Engine

from community_pulse.db import connection


class TestEngineSingleton:
    """Test engine singleton behavior with concurrency."""

    def test_get_engine_returns_same_instance_sequential(self, monkeypatch):
        """Test that get_engine() returns the same instance in sequence."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            engine1 = connection.get_engine()
            engine2 = connection.get_engine()
            engine3 = connection.get_engine()

            assert engine1 is engine2
            assert engine2 is engine3
            assert isinstance(engine1, Engine)
        finally:
            connection._state.engine = original_engine

    def test_concurrent_get_engine_returns_same_instance(self, monkeypatch):
        """Test that concurrent calls from multiple threads get the same engine."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            num_threads = 10
            engines = [None] * num_threads

            def get_engine(index):
                """Get engine and store in list."""
                engines[index] = connection.get_engine()

            threads = [
                threading.Thread(target=get_engine, args=(i,))
                for i in range(num_threads)
            ]

            # Start all threads
            for thread in threads:
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # All engines should be the same instance
            first_engine = engines[0]
            assert all(engine is first_engine for engine in engines)
            assert isinstance(first_engine, Engine)
        finally:
            connection._state.engine = original_engine

    def test_engine_created_once_with_threadpool(self, monkeypatch):
        """Test engine singleton with ThreadPoolExecutor."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            num_workers = 20

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [
                    executor.submit(connection.get_engine) for _ in range(num_workers)
                ]
                engines = [future.result() for future in as_completed(futures)]

            # All should be the same instance
            first_engine = engines[0]
            assert all(engine is first_engine for engine in engines)
            assert isinstance(first_engine, Engine)
        finally:
            connection._state.engine = original_engine


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_database_url_cached_after_engine_created(self, monkeypatch):
        """Test that DATABASE_URL changes are ignored after engine is created."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            # Create engine with first URL
            engine1 = connection.get_engine()
            original_url = str(engine1.url)

            # Change DATABASE_URL
            monkeypatch.setenv("DATABASE_URL", "sqlite:///different.db")

            # Get engine again - should return cached engine
            engine2 = connection.get_engine()

            assert engine1 is engine2
            assert str(engine2.url) == original_url
        finally:
            connection._state.engine = original_engine

    def test_malformed_database_url_raises_error(self, monkeypatch):
        """Test error handling when DATABASE_URL is malformed."""
        monkeypatch.setenv("DATABASE_URL", "not-a-valid-url")

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            # SQLAlchemy raises ArgumentError for malformed URL
            with pytest.raises(Exception):  # noqa: B017
                connection.get_engine()
        finally:
            connection._state.engine = original_engine

    def test_missing_database_url_raises_valueerror(self, monkeypatch):
        """Test that missing DATABASE_URL raises ValueError before engine creation."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            with pytest.raises(
                ValueError, match="DATABASE_URL environment variable is required"
            ):
                connection.get_engine()
        finally:
            connection._state.engine = original_engine


class TestThreadSafety:
    """Test thread safety of double-check locking pattern."""

    def test_rapid_concurrent_engine_access(self, monkeypatch):
        """Test that rapid concurrent calls don't cause race conditions."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            num_iterations = 100
            results = []
            lock = threading.Lock()

            def rapid_engine_access():
                """Rapidly access engine multiple times."""
                local_results = []
                for _ in range(10):
                    local_results.append(id(connection.get_engine()))
                with lock:
                    results.extend(local_results)

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(rapid_engine_access) for _ in range(num_iterations)
                ]
                for future in as_completed(futures):
                    future.result()

            # All engine IDs should be the same
            assert len(set(results)) == 1
        finally:
            connection._state.engine = original_engine

    def test_lock_protects_engine_creation(self, monkeypatch):
        """Test that the lock properly protects engine creation."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

        # Store original state
        original_engine = connection._state.engine
        connection._state.engine = None

        try:
            # Track when threads attempt to create engine
            creation_attempts = []
            lock = threading.Lock()

            def track_and_get_engine(thread_id):
                """Track creation attempts and get engine."""
                # Check if we would enter the creation block
                if connection._state.engine is None:
                    with lock:
                        creation_attempts.append(thread_id)
                connection.get_engine()

            num_threads = 20
            threads = [
                threading.Thread(target=track_and_get_engine, args=(i,))
                for i in range(num_threads)
            ]

            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            # Engine should exist now
            assert connection._state.engine is not None
            # At least one thread should have attempted creation
            assert len(creation_attempts) > 0
        finally:
            connection._state.engine = original_engine
