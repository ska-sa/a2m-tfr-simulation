"""Configuration models and TOML loading for the TFR simulation."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
import tomllib
from typing import Any, TypeVar


@dataclass(frozen=True)
class SimulationConfig:
    internal_sample_rate_hz: float = 1.0e9
    random_seed: int = 42


@dataclass(frozen=True)
class PulseSourceConfig:
    pulse_count: int = 30
    pulse_interval_s: float = 60.0e-9
    pulse_width_s: float = 5.0e-9
    amplitude: float = 1.0
    leading_guard_s: float = 200.0e-9
    trailing_guard_s: float = 200.0e-9

    @property
    def active_duration_s(self) -> float:
        return (self.pulse_count - 1) * self.pulse_interval_s + self.pulse_width_s

    @property
    def capture_duration_s(self) -> float:
        return self.leading_guard_s + self.active_duration_s + self.trailing_guard_s


@dataclass(frozen=True)
class ChannelConfig:
    reference_delay_s: float = 33.36e-9
    remote_delay_s: float = 90.39e-9
    reference_amplitude: float = 1.0
    remote_amplitude: float = 0.75
    snr_db: float = 20.0


@dataclass(frozen=True)
class FrontendConfig:
    rf_equivalent_bandwidth_hz: float = 275.0e6
    rx_gain_db: float = 20.0
    attenuation_db: float = 20.0
    detector_mode: str = "square_law"
    detector_lowpass_hz: float = 60.0e6
    filter_order: int = 6


@dataclass(frozen=True)
class ADCConfig:
    sample_rate_hz: float = 125.0e6
    bits: int = 12
    full_scale_v: float = 1.6

    def capture_size_bytes(self, duration_s: float) -> int:
        storage_bytes = 1 if self.bits <= 8 else 2 if self.bits <= 16 else 4
        return round(duration_s * self.sample_rate_hz) * storage_bytes


@dataclass(frozen=True)
class AlignmentConfig:
    expected_relative_delay_s: float = 57.03e-9
    search_half_width_s: float = 20.0e-9
    estimation_bandwidth_hz: float = 50.0e6


@dataclass(frozen=True)
class ScienceConfig:
    duration_s: float = 100.0e-6
    tone_frequency_hz: float = 20.0e6
    decimation_factor: int = 3
    free_running_clock_error_ppm: float = 1.0
    shared_clock_error_ppm: float = 0.0


@dataclass(frozen=True)
class TFRConfig:
    simulation: SimulationConfig = SimulationConfig()
    pulse_source: PulseSourceConfig = PulseSourceConfig()
    channel: ChannelConfig = ChannelConfig()
    frontend: FrontendConfig = FrontendConfig()
    adc: ADCConfig = ADCConfig()
    alignment: AlignmentConfig = AlignmentConfig()
    science: ScienceConfig = ScienceConfig()

    def validate(self) -> None:
        fs = self.simulation.internal_sample_rate_hz
        if fs <= 2 * self.frontend.detector_lowpass_hz:
            raise ValueError("internal sample rate must exceed twice the detector bandwidth")
        if fs < self.adc.sample_rate_hz:
            raise ValueError("internal sample rate must not be below the ADC sample rate")
        ratio = fs / self.adc.sample_rate_hz
        if abs(ratio - round(ratio)) > 1e-9:
            raise ValueError("internal/ADC sample-rate ratio must be an integer")
        if self.pulse_source.pulse_count < 1:
            raise ValueError("pulse_count must be positive")
        if self.pulse_source.pulse_width_s >= self.pulse_source.pulse_interval_s:
            raise ValueError("pulse width must be shorter than pulse interval")
        if not 2 <= self.adc.bits <= 32:
            raise ValueError("ADC resolution must be between 2 and 32 bits")
        if self.frontend.detector_mode not in {"square_law", "envelope"}:
            raise ValueError("detector_mode must be 'square_law' or 'envelope'")
        if self.science.decimation_factor < 1:
            raise ValueError("science decimation factor must be positive")
        science_nyquist_hz = self.adc.sample_rate_hz / self.science.decimation_factor / 2
        if self.science.tone_frequency_hz >= science_nyquist_hz:
            raise ValueError("science tone must be below the decimated Nyquist frequency")


ConfigType = TypeVar("ConfigType")


def _build(cls: type[ConfigType], values: dict[str, Any]) -> ConfigType:
    allowed = {field.name for field in fields(cls)}
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"unknown {cls.__name__} option(s): {', '.join(sorted(unknown))}")
    return cls(**values)


def load_config(path: str | Path) -> TFRConfig:
    """Load and validate a simulator configuration from TOML."""
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)
    sections = {
        "simulation": SimulationConfig,
        "pulse_source": PulseSourceConfig,
        "channel": ChannelConfig,
        "frontend": FrontendConfig,
        "adc": ADCConfig,
        "alignment": AlignmentConfig,
        "science": ScienceConfig,
    }
    unknown = set(raw) - set(sections)
    if unknown:
        raise ValueError(f"unknown config section(s): {', '.join(sorted(unknown))}")
    config = TFRConfig(**{name: _build(cls, raw.get(name, {})) for name, cls in sections.items()})
    config.validate()
    return config
