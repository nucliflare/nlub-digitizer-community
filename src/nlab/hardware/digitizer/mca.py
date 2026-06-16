from __future__ import annotations

from enum import IntEnum
from typing import TypedDict, Union

import numpy as np

from .backends.base import MCABackend
from .scope import ListSpec, ParameterSpec, RangeSpec

# ---------------------------------------------------------------------------
# MCA parameter enum — values equal the corresponding vdpp_config.json widget id
# ---------------------------------------------------------------------------


class MCAParam(IntEnum):
    # --- JSON widget ids (value == id in vdpp_config.json "mca" section) ---
    PULSE_POLARITY = 6
    TRIGGER_LEVEL = 7
    PRETRIGGER_SAMPLES = 8
    FRAME_SAMPLES = 9
    ENERGY_BIN = 10
    TRG_SOURCE = 13
    BASELINE_WINDOW = 14
    CFD_FACTOR = 15
    CFD_DELAY = 16
    CRRC2_CDELAY = 17
    CRRC2_FDELAY = 18
    CC_ENABLE = 19
    CC_TIME = 20
    TRAPEZ_ENABLE = 21
    TRAPEZ_R = 22
    TRAPEZ_M = 23
    TRAPEZ_T = 24
    TRAPEZ_E = 25
    TRAPEZ_FT = 26
    TIME_LIMIT = 28
    CRRC2_PZC = 46
    LP_COEFFS = 51  # coefficients array returned at id 51
    CFD_ENABLE = 52
    CFD_TW_LOW = 53
    CFD_TW_HIGH = 54
    MEM1_SIG_SELECT = 57
    MEM2_SIG_SELECT = 58
    EXT_TRIG_ENABLE = 61
    PILEUP_WINDOW = 62
    EDGE_DET_COEFF = 68
    TEMP_COEFF = 69  # vdpp_config.json "hw" section
    TEMP_OFFSET = 70  # vdpp_config.json "hw" section
    PSD_ZC_ENABLE = 71
    PSD_ZC_MODE = 72
    PSD_ZC_LOW = 73
    PSD_ZC_HIGH = 74
    # --- internal — no JSON widget id ---
    GLOBAL_ENABLE = 200
    DMA_ENABLED = 201
    LP_PRESET = 202  # write-only preset loader (0=200 MHz, 1=700 MHz, 2=average)


MCA_PARAMETER_SPECS: dict[MCAParam, ParameterSpec] = {
    # int16_t on wire (input.txt: VDPP_dpp_set_trigger_level)
    MCAParam.TRIGGER_LEVEL: RangeSpec(min_val=-32768, max_val=32767, step=1, default=-512),
    MCAParam.PULSE_POLARITY: ListSpec(items=(0, 1), default=0),
    # VDPP_BSLN_WIND enum; 0-6 map to 8/16/32/64/128/256/512 ns (input.txt: VDPP_dpp_set_bsln_window)
    MCAParam.BASELINE_WINDOW: ListSpec(items=(0, 1, 2, 3, 4, 5, 6), default=3),
    # uint16_t; config widget limits 8-8184 step 8
    MCAParam.PRETRIGGER_SAMPLES: RangeSpec(min_val=8, max_val=8184, step=8, default=24),
    MCAParam.FRAME_SAMPLES: RangeSpec(min_val=128, max_val=16376, step=8, default=256),
    # VDPP_HIST_BIN enum; items are actual bin-divisor values (input.txt: VDPP_dpp_set_energy_bin)
    MCAParam.ENERGY_BIN: ListSpec(items=(1, 2, 4, 8, 16, 32, 64, 128, 256, 512), default=1),
    # uint8_t; config widget limits 0-99
    MCAParam.PILEUP_WINDOW: RangeSpec(min_val=0, max_val=99, step=1, default=0),
    # uint32_t; config widget limits 0-999999
    MCAParam.TIME_LIMIT: RangeSpec(min_val=0, max_val=999999, step=1, default=0),
    MCAParam.GLOBAL_ENABLE: ListSpec(items=(False, True), default=False),
    # float on wire (input.txt: VDPP_dpp_set_temp_coeff)
    MCAParam.TEMP_COEFF: RangeSpec(min_val=-1.0, max_val=1.0, step=1e-9, default=-0.00026735),
    # int16_t on wire (input.txt: VDPP_dpp_set_temp_offset); config hw section bounds
    MCAParam.TEMP_OFFSET: RangeSpec(min_val=-1024, max_val=1024, step=1, default=7),
    MCAParam.TRAPEZ_ENABLE: ListSpec(items=(False, True), default=False),
    # uint16_t; config widget step 8
    MCAParam.TRAPEZ_R: RangeSpec(min_val=0, max_val=4088, step=8, default=64),
    MCAParam.TRAPEZ_M: RangeSpec(min_val=0, max_val=4088, step=8, default=64),
    # uint32_t; config widget limits 0-16777216 (input.txt: VDPP_dpp_set_trapez_T)
    MCAParam.TRAPEZ_T: RangeSpec(min_val=0, max_val=16777216, step=8, default=96),
    # uint16_t; config widget limits 0-16376 step 8
    MCAParam.TRAPEZ_E: RangeSpec(min_val=0, max_val=16376, step=8, default=256),
    # VDPP_TRAPEZ_WINDOW enum; 0-6 (input.txt: VDPP_dpp_set_trapez_FT)
    MCAParam.TRAPEZ_FT: ListSpec(items=(0, 1, 2, 3, 4, 5, 6), default=0),
    MCAParam.CFD_ENABLE: ListSpec(items=(False, True), default=False),
    # double on wire; config widget limits 0.2-1.0 step 0.1
    MCAParam.CFD_FACTOR: RangeSpec(min_val=0.2, max_val=1.0, step=0.1, default=0.4),
    # uint16_t; config widget limits 2-255
    MCAParam.CFD_DELAY: RangeSpec(min_val=2, max_val=255, step=1, default=2),
    MCAParam.CC_ENABLE: ListSpec(items=(False, True), default=False),
    # uint16_t; config widget limits 8-16376 step 8
    MCAParam.CC_TIME: RangeSpec(min_val=8, max_val=16376, step=8, default=8),
    # VDPP_TRG_SRC enum; 0=threshold, 1=CFD, 2=CR-RC2 (input.txt: VDPP_dpp_set_trg_source)
    MCAParam.TRG_SOURCE: ListSpec(items=(0, 1, 2), default=0),
    # uint16_t; CRRC2 coarse delay uses same 0-6 index as VDPP_BSLN_WIND
    MCAParam.CRRC2_CDELAY: ListSpec(items=(0, 1, 2, 3, 4, 5, 6), default=0),
    # uint16_t; config widget 8-1016 step 8 (input.txt: VDPP_dpp_set_crrc2_Fdelay)
    MCAParam.CRRC2_FDELAY: RangeSpec(min_val=8, max_val=1016, step=8, default=8),
    # int16_t; config widget -32768-32761 step 1 (input.txt: VDPP_dpp_set_crrc2_pzc_coeff)
    MCAParam.CRRC2_PZC: RangeSpec(min_val=-32768, max_val=32761, step=1, default=32761),
    # uint16_t; config widget 0-16376 step 8
    MCAParam.CFD_TW_LOW: RangeSpec(min_val=0, max_val=16376, step=8, default=8),
    # uint16_t; config widget 8-16376 step 8
    MCAParam.CFD_TW_HIGH: RangeSpec(min_val=8, max_val=16376, step=8, default=64),
    # VDPP_DBG_SIGNAL enum; 8 options (0-7)
    MCAParam.MEM1_SIG_SELECT: ListSpec(items=(0, 1, 2, 3, 4, 5, 6, 7), default=0),
    MCAParam.MEM2_SIG_SELECT: ListSpec(items=(0, 1, 2, 3, 4, 5, 6, 7), default=1),
    MCAParam.EXT_TRIG_ENABLE: ListSpec(items=(False, True), default=False),
    # uint32_t (input.txt: VDPP_dpp_set_edge_det_coeff); no config widget bounds
    # > ⚠️ UNVERIFIED: upper bound not specified in vdpp_config.json
    MCAParam.EDGE_DET_COEFF: RangeSpec(min_val=0, max_val=65535, step=1, default=0),
    MCAParam.PSD_ZC_ENABLE: ListSpec(items=(False, True), default=False),
    # uint8_t; 0=CR-RC2 filter, 1=Triangular filter
    MCAParam.PSD_ZC_MODE: ListSpec(items=(0, 1), default=0),
    # uint16_t; config widget 8-2048 step 8
    MCAParam.PSD_ZC_LOW: RangeSpec(min_val=8, max_val=2048, step=8, default=8),
    MCAParam.PSD_ZC_HIGH: RangeSpec(min_val=8, max_val=2048, step=8, default=16),
    # uint8_t preset index; 0=200 MHz, 1=700 MHz, 2=average
    MCAParam.LP_PRESET: RangeSpec(min_val=0, max_val=2, step=1, default=0),
}


class MCASettingEntry(TypedDict):
    id: int
    value: int | float | str | bool | list[int]


# ---------------------------------------------------------------------------
# Filter sub-objects
# ---------------------------------------------------------------------------


class Trapezoid:
    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_enable(self) -> bool:
        return self._b.get_trapez_enable()

    def set_enable(self, val: bool) -> None:
        self._b.set_trapez_enable(val)

    def get_r(self) -> int:
        return self._b.get_trapez_r()

    def set_r(self, val: int) -> None:
        self._b.set_trapez_r(val)

    def get_m(self) -> int:
        return self._b.get_trapez_m()

    def set_m(self, val: int) -> None:
        self._b.set_trapez_m(val)

    def get_t(self) -> int:
        return self._b.get_trapez_t()

    def set_t(self, val: int) -> None:
        self._b.set_trapez_t(val)

    def get_e(self) -> int:
        return self._b.get_trapez_e()

    def set_e(self, val: int) -> None:
        self._b.set_trapez_e(val)

    def get_ft(self) -> int:
        return self._b.get_trapez_ft()

    def set_ft(self, val: int) -> None:
        self._b.set_trapez_ft(val)


class CFD:
    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_enable(self) -> bool:
        return self._b.get_cfd_enable()

    def set_enable(self, val: bool) -> None:
        self._b.set_cfd_enable(val)

    def get_factor(self) -> float:
        return self._b.get_cfd_factor()

    def set_factor(self, val: float) -> None:
        self._b.set_cfd_factor(val)

    def get_delay(self) -> int:
        return self._b.get_cfd_delay()

    def set_delay(self, val: int) -> None:
        self._b.set_cfd_delay(val)

    def get_time_window_low(self) -> int:
        return self._b.get_cfd_time_window_low()

    def set_time_window_low(self, val: int) -> None:
        self._b.set_cfd_time_window_low(val)

    def get_time_window_high(self) -> int:
        return self._b.get_cfd_time_window_high()

    def set_time_window_high(self, val: int) -> None:
        self._b.set_cfd_time_window_high(val)


class CRRC2:
    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_c_delay(self) -> int:
        return self._b.get_crrc2_c_delay()

    def set_c_delay(self, val: int) -> None:
        self._b.set_crrc2_c_delay(val)

    def get_f_delay(self) -> int:
        return self._b.get_crrc2_f_delay()

    def set_f_delay(self, val: int) -> None:
        self._b.set_crrc2_f_delay(val)

    def get_pzc_coeff(self) -> int:
        return self._b.get_crrc2_pzc_coeff()

    def set_pzc_coeff(self, val: int) -> None:
        self._b.set_crrc2_pzc_coeff(val)


class ChargeComparison:
    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_enable(self) -> bool:
        return self._b.get_cc_enable()

    def set_enable(self, val: bool) -> None:
        self._b.set_cc_enable(val)

    def get_time(self) -> int:
        return self._b.get_cc_time()

    def set_time(self, val: int) -> None:
        self._b.set_cc_time(val)


class PSDZeroCrossing:
    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_enable(self) -> bool:
        return self._b.get_psd_zc_enable()

    def set_enable(self, val: bool) -> None:
        self._b.set_psd_zc_enable(val)

    def get_mode(self) -> int:
        return self._b.get_psd_zc_mode()

    def set_mode(self, val: int) -> None:
        self._b.set_psd_zc_mode(val)

    def get_time_window_low(self) -> int:
        return self._b.get_psd_zc_time_window_low()

    def set_time_window_low(self, val: int) -> None:
        self._b.set_psd_zc_time_window_low(val)

    def get_time_window_high(self) -> int:
        return self._b.get_psd_zc_time_window_high()

    def set_time_window_high(self, val: int) -> None:
        self._b.set_psd_zc_time_window_high(val)


class LPFilter:
    """FIR input low-pass filter."""

    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_size(self) -> int:
        return self._b.get_lp_coeffs_size()

    def get_coeffs(self) -> np.ndarray:
        return self._b.get_lp_coeffs()

    def set_coeffs(self, val: list[int]) -> None:
        self._b.set_lp_coeffs(val)

    def set_preset(self, preset_index: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.LP_PRESET].validate(preset_index, "lp_preset")
        self._b.set_lp_coeffs_preset(preset_index)

    def get_iir_average(self) -> int:
        """IIR LP input filter average (read-only hardware register)."""
        return self._b.get_iir_lp_average()


class MCAFilters:
    """Groups all DSP filter settings under named sub-objects."""

    def __init__(self, backend: MCABackend) -> None:
        self.trapezoid = Trapezoid(backend)
        self.cfd = CFD(backend)
        self.crrc2 = CRRC2(backend)
        self.charge_comparison = ChargeComparison(backend)
        self.psd_zc = PSDZeroCrossing(backend)
        self.lp = LPFilter(backend)


# ---------------------------------------------------------------------------
# Read-only statistics view
# ---------------------------------------------------------------------------


class MCAStatistics:
    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_count_rate(self) -> int:
        return self._b.get_count_rate()

    def get_pulse_deadtime(self) -> int:
        return self._b.get_pulse_deadtime()

    def get_events_lost(self) -> int:
        return self._b.get_events_lost()

    def get_elapsed_time(self) -> int:
        # > ⚠️ UNVERIFIED: units — nlab_mca.py divides by 10 in get_enable_time()
        return self._b.get_elapsed_time()

    def get_pulse_overrange(self) -> int:
        return self._b.get_pulse_overrange_counter()

    def get_pulse_pileup(self) -> int:
        return self._b.get_pulse_pileup_counter()

    def get_energy_overrange(self) -> int:
        return self._b.get_energy_overrange_counter()

    def get_energy_estimation_error(self) -> int:
        return self._b.get_energy_estimation_error()

    def get_throughput_error(self) -> int:
        return self._b.get_throughput_error_counter()


# ---------------------------------------------------------------------------
# Sync trigger view (channel-independent)
# ---------------------------------------------------------------------------


class SyncTrigger:
    def __init__(self, backend: MCABackend) -> None:
        self._b = backend

    def get_enable(self) -> bool:
        return self._b.get_sync_enable()

    def set_enable(self, val: bool) -> None:
        self._b.set_sync_enable(val)

    def get_sw_trig(self) -> int:
        return self._b.get_sync_sw_trig()

    def set_sw_trig(self, val: int) -> None:
        self._b.set_sync_sw_trig(val)

    def get_trig_src(self) -> int:
        return self._b.get_sync_trig_src()

    def set_trig_src(self, val: int) -> None:
        self._b.set_sync_trig_src(val)

    def get_timestamp(self) -> int:
        # > ⚠️ UNVERIFIED: units — nlab_mca.py divides by 1e9 in get_timestamp()
        return self._b.get_sync_timestamp()

    def fire(self) -> None:
        """Send a software trigger pulse."""
        self._b.set_sync_sw_trig(1)


# ---------------------------------------------------------------------------
# MultiChannelAnalyzer
# ---------------------------------------------------------------------------


class MultiChannelAnalyzer:
    """High-level MCA / DPP interface."""

    specs: dict[MCAParam, ParameterSpec] = MCA_PARAMETER_SPECS

    def __init__(self, backend: MCABackend) -> None:
        self._b = backend
        self.filters = MCAFilters(backend)
        self.statistics = MCAStatistics(backend)
        self.sync = SyncTrigger(backend)

    # ---- device info ----

    def get_hw_version(self) -> int:
        return self._b.get_hw_version()

    def get_sw_version(self) -> int:
        return self._b.get_sw_version()

    def get_id_number(self) -> int:
        return self._b.get_id_number()

    # ---- signal parameters ----

    def get_trigger_level(self) -> int:
        return self._b.get_dpp_trigger_level()

    def set_trigger_level(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.TRIGGER_LEVEL].validate(val, "trigger_level")
        self._b.set_dpp_trigger_level(val)

    def get_pulse_polarity(self) -> int:
        return self._b.get_pulse_polarity()

    def set_pulse_polarity(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.PULSE_POLARITY].validate(val, "pulse_polarity")
        self._b.set_pulse_polarity(val)

    def get_baseline_window(self) -> int:
        return self._b.get_bsln_window()

    def set_baseline_window(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.BASELINE_WINDOW].validate(val, "baseline_window")
        self._b.set_bsln_window(val)

    def get_pretrigger_samples(self) -> int:
        return self._b.get_dpp_pretrigger_samples()

    def set_pretrigger_samples(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.PRETRIGGER_SAMPLES].validate(val, "pretrigger_samples")
        self._b.set_dpp_pretrigger_samples(val)

    def get_frame_samples(self) -> int:
        return self._b.get_dpp_frame_samples()

    def set_frame_samples(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.FRAME_SAMPLES].validate(val, "frame_samples")
        self._b.set_dpp_frame_samples(val)

    def get_trg_source(self) -> int:
        return self._b.get_trg_source()

    def set_trg_source(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.TRG_SOURCE].validate(val, "trg_source")
        self._b.set_trg_source(val)

    # ---- acquisition control ----

    def get_global_enable(self) -> bool:
        return self._b.get_global_enable()

    def set_global_enable(self, val: bool) -> None:
        self._b.set_global_enable(val)

    def get_dma_enable(self) -> bool:
        return self._b.get_dpp_dma_enable()

    def set_dma_enable(self, val: bool) -> None:
        self._b.set_dpp_dma_enable(val)

    def get_time_limit(self) -> int:
        return self._b.get_time_limit()

    def set_time_limit(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.TIME_LIMIT].validate(val, "time_limit")
        self._b.set_time_limit(val)

    def get_ext_trig_enable(self) -> bool:
        return self._b.get_ext_trig_enable()

    def set_ext_trig_enable(self, val: bool) -> None:
        self._b.set_ext_trig_enable(val)

    def get_energy_bin(self) -> int:
        return self._b.get_energy_bin()

    def set_energy_bin(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.ENERGY_BIN].validate(val, "energy_bin")
        self._b.set_energy_bin(val)

    def get_pileup_window(self) -> int:
        return self._b.get_pileup_window()

    def set_pileup_window(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.PILEUP_WINDOW].validate(val, "pileup_window")
        self._b.set_pileup_window(val)

    def get_measurement_in_progress(self) -> bool:
        return self._b.get_measurement_in_progress()

    # ---- temperature compensation ----

    def get_temp_coeff(self) -> float:
        return self._b.get_temp_coeff()

    def set_temp_coeff(self, val: float) -> None:
        self._b.set_temp_coeff(val)

    def get_temp_offset(self) -> int:
        return self._b.get_temp_offset()

    def set_temp_offset(self, val: int) -> None:
        self._b.set_temp_offset(val)

    # ---- edge detector coefficient ----

    def get_edge_det_coeff(self) -> int:
        return self._b.get_edge_det_coeff()

    def set_edge_det_coeff(self, val: int) -> None:
        self._b.set_edge_det_coeff(val)

    # ---- pulse memory signal routing ----

    def get_mem1_sig_select(self) -> int:
        return self._b.get_mem1_sig_select()

    def set_mem1_sig_select(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.MEM1_SIG_SELECT].validate(val, "mem1_sig_select")
        self._b.set_mem1_sig_select(val)

    def get_mem2_sig_select(self) -> int:
        return self._b.get_mem2_sig_select()

    def set_mem2_sig_select(self, val: int) -> None:
        MCA_PARAMETER_SPECS[MCAParam.MEM2_SIG_SELECT].validate(val, "mem2_sig_select")
        self._b.set_mem2_sig_select(val)

    def get_mem_amount(self) -> int:
        return self._b.get_mem_amount()

    def get_mem_frame_sizes(self) -> np.ndarray:
        return self._b.get_mem_frame_sizes()

    # ---- start / stop ----

    def start(self) -> None:
        self._b.set_global_enable(True)

    def stop(self) -> None:
        self._b.set_global_enable(False)

    # ---- data acquisition ----

    def acquire_spectrum(self) -> np.ndarray:
        """Read the accumulated histogram. Returns uint32 array of shape (n_bins,)."""
        return self._b.read_histogram()

    def clear_spectrum(self) -> None:
        self._b.clear_histogram()

    def get_histogram_size(self) -> int:
        return self._b.get_histogram_size()

    def acquire_waveforms(self) -> tuple[np.ndarray, np.ndarray]:
        """Read pulse memory banks. Returns (bank1, bank2) as int16 arrays."""
        return self._b.read_waveform_banks()

    # ---- diagnostics ----

    def print_status(self) -> None:
        """Print current MCA/DPP configuration to stdout."""
        f = self.filters
        print("── MCA / DPP ───────────────────────────────────")
        print(f"  hw_version        : {self.get_hw_version()}")
        print(f"  sw_version        : {self.get_sw_version()}")
        print(f"  id_number         : {self.get_id_number()}")
        print("  Signal:")
        print(f"    trigger_level   : {self.get_trigger_level()}")
        print(f"    pulse_polarity  : {self.get_pulse_polarity()}")
        print(f"    baseline_window : {self.get_baseline_window()}")
        print(f"    pretrigger      : {self.get_pretrigger_samples()} samples")
        print(f"    frame_samples   : {self.get_frame_samples()} samples")
        print(f"    trg_source      : {self.get_trg_source()}")
        print(f"    energy_bin      : {self.get_energy_bin()}")
        print(f"    pileup_window   : {self.get_pileup_window()}")
        print(f"    ext_trig_enable : {self.get_ext_trig_enable()}")
        print("  Acquisition:")
        print(f"    global_enable   : {self.get_global_enable()}")
        print(f"    dma_enable      : {self.get_dma_enable()}")
        print(f"    time_limit      : {self.get_time_limit()}")
        print(f"    in_progress     : {self.get_measurement_in_progress()}")
        print(f"    histogram_size  : {self.get_histogram_size()}")
        print("  Temperature:")
        print(f"    temp_coeff      : {self.get_temp_coeff():.8f}")
        print(f"    temp_offset     : {self.get_temp_offset()}")
        print("  Pulse memory:")
        print(f"    mem_amount      : {self.get_mem_amount()}")
        print(f"    mem1_sig_select : {self.get_mem1_sig_select()}")
        print(f"    mem2_sig_select : {self.get_mem2_sig_select()}")
        print(f"    edge_det_coeff  : {self.get_edge_det_coeff()}")
        print("  Filters:")
        print(f"    LP iir_average  : {f.lp.get_iir_average()}  coeffs_size={f.lp.get_size()}")
        print(
            f"    Trapezoid  en={f.trapezoid.get_enable()}  R={f.trapezoid.get_r()}  M={f.trapezoid.get_m()}  "
            f"T={f.trapezoid.get_t()}  E={f.trapezoid.get_e()}  FT={f.trapezoid.get_ft()}"
        )
        print(f"    CRRC2      Cd={f.crrc2.get_c_delay()}  Fd={f.crrc2.get_f_delay()}  PZC={f.crrc2.get_pzc_coeff()}")
        print(
            f"    CFD        en={f.cfd.get_enable()}  factor={f.cfd.get_factor():.2f}  delay={f.cfd.get_delay()}  "
            f"tw_lo={f.cfd.get_time_window_low()}  tw_hi={f.cfd.get_time_window_high()}"
        )
        print(f"    CC         en={f.charge_comparison.get_enable()}  time={f.charge_comparison.get_time()}")
        print(
            f"    PSD_ZC     en={f.psd_zc.get_enable()}  mode={f.psd_zc.get_mode()}  lo={f.psd_zc.get_time_window_low()}  hi={f.psd_zc.get_time_window_high()}"
        )
        print("  Sync trigger:")
        print(f"    enable          : {self.sync.get_enable()}")
        print(f"    trig_src        : {self.sync.get_trig_src()}")
        print(f"    timestamp       : {self.sync.get_timestamp()}")

    # ---- GUI helpers ----

    def get_settings(self) -> list[MCASettingEntry]:
        """Return current hardware state as a flat list for GUI consumption.

        IDs match vdpp_config.json mca/hw section widget ids.
        LP coefficients (LP_COEFFS) are returned as list[int] via .tolist().
        """
        return [
            MCASettingEntry(id=int(MCAParam.PULSE_POLARITY), value=self.get_pulse_polarity()),
            MCASettingEntry(id=int(MCAParam.TRIGGER_LEVEL), value=self.get_trigger_level()),
            MCASettingEntry(id=int(MCAParam.PRETRIGGER_SAMPLES), value=self.get_pretrigger_samples()),
            MCASettingEntry(id=int(MCAParam.FRAME_SAMPLES), value=self.get_frame_samples()),
            MCASettingEntry(id=int(MCAParam.ENERGY_BIN), value=self.get_energy_bin()),
            MCASettingEntry(id=int(MCAParam.TRG_SOURCE), value=self.get_trg_source()),
            MCASettingEntry(id=int(MCAParam.BASELINE_WINDOW), value=self.get_baseline_window()),
            MCASettingEntry(id=int(MCAParam.CFD_FACTOR), value=self.filters.cfd.get_factor()),
            MCASettingEntry(id=int(MCAParam.CFD_DELAY), value=self.filters.cfd.get_delay()),
            MCASettingEntry(id=int(MCAParam.CRRC2_CDELAY), value=self.filters.crrc2.get_c_delay()),
            MCASettingEntry(id=int(MCAParam.CRRC2_FDELAY), value=self.filters.crrc2.get_f_delay()),
            MCASettingEntry(id=int(MCAParam.CC_ENABLE), value=self.filters.charge_comparison.get_enable()),
            MCASettingEntry(id=int(MCAParam.CC_TIME), value=self.filters.charge_comparison.get_time()),
            MCASettingEntry(id=int(MCAParam.TRAPEZ_ENABLE), value=self.filters.trapezoid.get_enable()),
            MCASettingEntry(id=int(MCAParam.TRAPEZ_R), value=self.filters.trapezoid.get_r()),
            MCASettingEntry(id=int(MCAParam.TRAPEZ_M), value=self.filters.trapezoid.get_m()),
            MCASettingEntry(id=int(MCAParam.TRAPEZ_T), value=self.filters.trapezoid.get_t()),
            MCASettingEntry(id=int(MCAParam.TRAPEZ_E), value=self.filters.trapezoid.get_e()),
            MCASettingEntry(id=int(MCAParam.TRAPEZ_FT), value=self.filters.trapezoid.get_ft()),
            MCASettingEntry(id=int(MCAParam.TIME_LIMIT), value=self.get_time_limit()),
            MCASettingEntry(id=int(MCAParam.CRRC2_PZC), value=self.filters.crrc2.get_pzc_coeff()),
            MCASettingEntry(id=int(MCAParam.LP_COEFFS), value=self.filters.lp.get_coeffs().tolist()),
            MCASettingEntry(id=int(MCAParam.CFD_ENABLE), value=self.filters.cfd.get_enable()),
            MCASettingEntry(id=int(MCAParam.CFD_TW_LOW), value=self.filters.cfd.get_time_window_low()),
            MCASettingEntry(id=int(MCAParam.CFD_TW_HIGH), value=self.filters.cfd.get_time_window_high()),
            MCASettingEntry(id=int(MCAParam.MEM1_SIG_SELECT), value=self.get_mem1_sig_select()),
            MCASettingEntry(id=int(MCAParam.MEM2_SIG_SELECT), value=self.get_mem2_sig_select()),
            MCASettingEntry(id=int(MCAParam.EXT_TRIG_ENABLE), value=self.get_ext_trig_enable()),
            MCASettingEntry(id=int(MCAParam.PILEUP_WINDOW), value=self.get_pileup_window()),
            MCASettingEntry(id=int(MCAParam.EDGE_DET_COEFF), value=self.get_edge_det_coeff()),
            MCASettingEntry(id=int(MCAParam.TEMP_COEFF), value=self.get_temp_coeff()),
            MCASettingEntry(id=int(MCAParam.TEMP_OFFSET), value=self.get_temp_offset()),
            MCASettingEntry(id=int(MCAParam.PSD_ZC_ENABLE), value=self.filters.psd_zc.get_enable()),
            MCASettingEntry(id=int(MCAParam.PSD_ZC_MODE), value=self.filters.psd_zc.get_mode()),
            MCASettingEntry(id=int(MCAParam.PSD_ZC_LOW), value=self.filters.psd_zc.get_time_window_low()),
            MCASettingEntry(id=int(MCAParam.PSD_ZC_HIGH), value=self.filters.psd_zc.get_time_window_high()),
        ]
