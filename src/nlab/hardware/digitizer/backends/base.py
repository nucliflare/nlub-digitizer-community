from abc import ABC, abstractmethod

import numpy as np


class ScopeBackend(ABC):
    """Abstract interface for scope hardware access. All units are hardware-native (samples, ADC counts)."""

    @abstractmethod
    def get_ip_version(self) -> int: ...

    @abstractmethod
    def get_mem_frame_size(self) -> int: ...

    @abstractmethod
    def get_enable(self) -> bool: ...

    @abstractmethod
    def set_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_dma_enable(self) -> bool: ...

    @abstractmethod
    def set_dma_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_trigger_level(self) -> int: ...

    @abstractmethod
    def set_trigger_level(self, val: int) -> None: ...

    @abstractmethod
    def get_edge(self) -> int: ...

    @abstractmethod
    def set_edge(self, val: int) -> None: ...

    @abstractmethod
    def get_pretrigger_samples(self) -> int: ...

    @abstractmethod
    def set_pretrigger_samples(self, val: int) -> None: ...

    @abstractmethod
    def get_frame_samples(self) -> int: ...

    @abstractmethod
    def set_frame_samples(self, val: int) -> None: ...

    @abstractmethod
    def get_dac_value(self) -> int: ...

    @abstractmethod
    def set_dac_value(self, val: int) -> None: ...

    @abstractmethod
    def read_frame(self) -> np.ndarray:
        """Returns int16 array of shape (n_samples,)."""
        ...


class MCABackend(ABC):
    """Abstract interface for MCA / DPP hardware access."""

    # ---- device info ----
    @abstractmethod
    def get_hw_version(self) -> int: ...

    @abstractmethod
    def get_sw_version(self) -> int: ...

    @abstractmethod
    def get_id_number(self) -> int: ...

    # ---- signal parameters ----
    @abstractmethod
    def get_dpp_trigger_level(self) -> int: ...

    @abstractmethod
    def set_dpp_trigger_level(self, val: int) -> None: ...

    @abstractmethod
    def get_pulse_polarity(self) -> int: ...

    @abstractmethod
    def set_pulse_polarity(self, val: int) -> None: ...

    @abstractmethod
    def get_bsln_window(self) -> int: ...

    @abstractmethod
    def set_bsln_window(self, val: int) -> None: ...

    @abstractmethod
    def get_dpp_pretrigger_samples(self) -> int: ...

    @abstractmethod
    def set_dpp_pretrigger_samples(self, val: int) -> None: ...

    @abstractmethod
    def get_dpp_frame_samples(self) -> int: ...

    @abstractmethod
    def set_dpp_frame_samples(self, val: int) -> None: ...

    # ---- acquisition control ----
    @abstractmethod
    def get_global_enable(self) -> bool: ...

    @abstractmethod
    def set_global_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_dpp_dma_enable(self) -> bool: ...

    @abstractmethod
    def set_dpp_dma_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_time_limit(self) -> int: ...

    @abstractmethod
    def set_time_limit(self, val: int) -> None: ...

    @abstractmethod
    def get_ext_trig_enable(self) -> bool: ...

    @abstractmethod
    def set_ext_trig_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_trg_source(self) -> int: ...

    @abstractmethod
    def set_trg_source(self, val: int) -> None: ...

    @abstractmethod
    def get_energy_bin(self) -> int: ...

    @abstractmethod
    def set_energy_bin(self, val: int) -> None: ...

    @abstractmethod
    def get_pileup_window(self) -> int: ...

    @abstractmethod
    def set_pileup_window(self, val: int) -> None: ...

    @abstractmethod
    def get_measurement_in_progress(self) -> bool: ...

    # ---- statistics (all read-only) ----
    @abstractmethod
    def get_pulse_deadtime(self) -> int: ...

    @abstractmethod
    def get_events_lost(self) -> int: ...

    @abstractmethod
    def get_count_rate(self) -> int: ...

    @abstractmethod
    def get_elapsed_time(self) -> int: ...

    @abstractmethod
    def get_pulse_overrange_counter(self) -> int: ...

    @abstractmethod
    def get_pulse_pileup_counter(self) -> int: ...

    @abstractmethod
    def get_energy_overrange_counter(self) -> int: ...

    @abstractmethod
    def get_energy_estimation_error(self) -> int: ...

    @abstractmethod
    def get_throughput_error_counter(self) -> int: ...

    # ---- FIR input LP filter ----
    @abstractmethod
    def get_lp_coeffs_size(self) -> int: ...

    @abstractmethod
    def set_lp_coeffs_preset(self, val: int) -> None: ...

    @abstractmethod
    def get_lp_coeffs(self) -> np.ndarray:
        """Returns int32 array of FIR coefficients."""
        ...

    @abstractmethod
    def set_lp_coeffs(self, coeffs: list[int]) -> None: ...

    # ---- IIR LP filter (read-only hardware register) ----
    @abstractmethod
    def get_iir_lp_average(self) -> int: ...

    # ---- temperature compensation ----
    @abstractmethod
    def get_temp_coeff(self) -> float: ...

    @abstractmethod
    def set_temp_coeff(self, val: float) -> None: ...

    @abstractmethod
    def get_temp_offset(self) -> int: ...

    @abstractmethod
    def set_temp_offset(self, val: int) -> None: ...

    # ---- edge detector ----
    @abstractmethod
    def get_edge_det_coeff(self) -> int: ...

    @abstractmethod
    def set_edge_det_coeff(self, val: int) -> None: ...

    # ---- CRRC2 shaping filter ----
    @abstractmethod
    def get_crrc2_c_delay(self) -> int: ...

    @abstractmethod
    def set_crrc2_c_delay(self, val: int) -> None: ...

    @abstractmethod
    def get_crrc2_f_delay(self) -> int: ...

    @abstractmethod
    def set_crrc2_f_delay(self, val: int) -> None: ...

    @abstractmethod
    def get_crrc2_pzc_coeff(self) -> int: ...

    @abstractmethod
    def set_crrc2_pzc_coeff(self, val: int) -> None: ...

    # ---- trapezoidal filter ----
    @abstractmethod
    def get_trapez_enable(self) -> bool: ...

    @abstractmethod
    def set_trapez_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_trapez_r(self) -> int: ...

    @abstractmethod
    def set_trapez_r(self, val: int) -> None: ...

    @abstractmethod
    def get_trapez_m(self) -> int: ...

    @abstractmethod
    def set_trapez_m(self, val: int) -> None: ...

    @abstractmethod
    def get_trapez_t(self) -> int: ...

    @abstractmethod
    def set_trapez_t(self, val: int) -> None: ...

    @abstractmethod
    def get_trapez_e(self) -> int: ...

    @abstractmethod
    def set_trapez_e(self, val: int) -> None: ...

    @abstractmethod
    def get_trapez_ft(self) -> int: ...

    @abstractmethod
    def set_trapez_ft(self, val: int) -> None: ...

    # ---- CFD ----
    @abstractmethod
    def get_cfd_enable(self) -> bool: ...

    @abstractmethod
    def set_cfd_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_cfd_factor(self) -> float: ...

    @abstractmethod
    def set_cfd_factor(self, val: float) -> None: ...

    @abstractmethod
    def get_cfd_delay(self) -> int: ...

    @abstractmethod
    def set_cfd_delay(self, val: int) -> None: ...

    @abstractmethod
    def get_cfd_time_window_low(self) -> int: ...

    @abstractmethod
    def set_cfd_time_window_low(self, val: int) -> None: ...

    @abstractmethod
    def get_cfd_time_window_high(self) -> int: ...

    @abstractmethod
    def set_cfd_time_window_high(self, val: int) -> None: ...

    # ---- Charge Comparison ----
    @abstractmethod
    def get_cc_enable(self) -> bool: ...

    @abstractmethod
    def set_cc_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_cc_time(self) -> int: ...

    @abstractmethod
    def set_cc_time(self, val: int) -> None: ...

    # ---- PSD Zero Crossing ----
    @abstractmethod
    def get_psd_zc_enable(self) -> bool: ...

    @abstractmethod
    def set_psd_zc_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_psd_zc_mode(self) -> int: ...

    @abstractmethod
    def set_psd_zc_mode(self, val: int) -> None: ...

    @abstractmethod
    def get_psd_zc_time_window_low(self) -> int: ...

    @abstractmethod
    def set_psd_zc_time_window_low(self, val: int) -> None: ...

    @abstractmethod
    def get_psd_zc_time_window_high(self) -> int: ...

    @abstractmethod
    def set_psd_zc_time_window_high(self, val: int) -> None: ...

    # ---- pulse memory ----
    @abstractmethod
    def get_mem1_sig_select(self) -> int: ...

    @abstractmethod
    def set_mem1_sig_select(self, val: int) -> None: ...

    @abstractmethod
    def get_mem2_sig_select(self) -> int: ...

    @abstractmethod
    def set_mem2_sig_select(self, val: int) -> None: ...

    @abstractmethod
    def get_mem_amount(self) -> int: ...

    @abstractmethod
    def get_mem_frame_sizes(self) -> np.ndarray:
        """Returns uint32 array of per-channel frame sizes."""
        ...

    @abstractmethod
    def read_waveform_banks(self) -> tuple[np.ndarray, np.ndarray]:
        """Returns (bank1, bank2) as int16 arrays."""
        ...

    # ---- histogram ----
    @abstractmethod
    def read_histogram(self) -> np.ndarray:
        """Returns uint32 array of shape (n_bins,)."""
        ...

    @abstractmethod
    def clear_histogram(self) -> None: ...

    @abstractmethod
    def get_histogram_size(self) -> int: ...

    # ---- sync trigger (channel-independent / global) ----
    @abstractmethod
    def get_sync_enable(self) -> bool: ...

    @abstractmethod
    def set_sync_enable(self, val: bool) -> None: ...

    @abstractmethod
    def get_sync_sw_trig(self) -> int: ...

    @abstractmethod
    def set_sync_sw_trig(self, val: int) -> None: ...

    @abstractmethod
    def get_sync_trig_src(self) -> int: ...

    @abstractmethod
    def set_sync_trig_src(self, val: int) -> None: ...

    @abstractmethod
    def get_sync_timestamp(self) -> int: ...


class DigitizerBackend(ScopeBackend, MCABackend, ABC):
    """Combined backend that satisfies both scope and MCA interfaces.

    All concrete backends (gRPC, IIO, …) should inherit from this class.
    """

    def close(self) -> None:
        """Release hardware resources. Safe to call multiple times. Override as needed."""
