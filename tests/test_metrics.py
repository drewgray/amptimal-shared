"""Tests for Prometheus metrics instrumentation helper."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from amptimal_shared.metrics import instrument_app


class TestInstrumentApp:
    def test_instruments_fastapi_app(self):
        with patch("amptimal_shared.metrics.Instrumentator") as MockInstrumentator:
            mock_instance = MagicMock()
            mock_instance.instrument.return_value = mock_instance
            mock_instance.expose.return_value = mock_instance
            MockInstrumentator.return_value = mock_instance

            app = FastAPI()
            result = instrument_app(app)

            MockInstrumentator.assert_called_once_with(
                excluded_handlers=["/health", "/ready", "/metrics"],
            )
            mock_instance.instrument.assert_called_once_with(app)
            mock_instance.expose.assert_called_once_with(app, endpoint="/metrics")
            assert result is mock_instance

    def test_custom_metrics_path(self):
        with patch("amptimal_shared.metrics.Instrumentator") as MockInstrumentator:
            mock_instance = MagicMock()
            mock_instance.instrument.return_value = mock_instance
            mock_instance.expose.return_value = mock_instance
            MockInstrumentator.return_value = mock_instance

            app = FastAPI()
            instrument_app(app, metrics_path="/internal/metrics")

            mock_instance.expose.assert_called_once_with(app, endpoint="/internal/metrics")

    def test_custom_excluded_handlers(self):
        with patch("amptimal_shared.metrics.Instrumentator") as MockInstrumentator:
            mock_instance = MagicMock()
            mock_instance.instrument.return_value = mock_instance
            mock_instance.expose.return_value = mock_instance
            MockInstrumentator.return_value = mock_instance

            app = FastAPI()
            instrument_app(app, excluded_handlers=["/health", "/ping"])

            MockInstrumentator.assert_called_once_with(
                excluded_handlers=["/health", "/ping"],
            )

    def test_returns_instrumentator_for_customization(self):
        with patch("amptimal_shared.metrics.Instrumentator") as MockInstrumentator:
            mock_instance = MagicMock()
            mock_instance.instrument.return_value = mock_instance
            mock_instance.expose.return_value = mock_instance
            MockInstrumentator.return_value = mock_instance

            app = FastAPI()
            result = instrument_app(app)

            # Caller can further customize the instrumentator
            assert result is mock_instance
