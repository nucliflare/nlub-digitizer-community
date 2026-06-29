"""Save and load device settings as human-readable YAML.

Variable names correspond to MCAParam/ScopeParam/HVParam enum names (lowercase),
grouped by subsystem for readability.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from nlab.hardware.digitizer.hv import HVSupply
from nlab.hardware.digitizer.mca import MultiChannelAnalyzer
from nlab.hardware.digitizer.scope import Scope

log = logging.getLogger(__name__)


def save_settings(
    scope: Scope,
    mca: MultiChannelAnalyzer,
    hv: HVSupply | None,
    path: Path,
) -> None:
    """Read all parameters from hardware and write to YAML."""
    settings: dict = {
        "scope": {
            "trigger_level": scope.get_trigger_level(),
            "pretrigger_samples": scope.get_pretrigger_samples(),
            "frame_samples": scope.get_frame_samples(),
            "edge_mode": scope.get_trigger_mode().value,
            "dac_value": scope.get_dac_value(),
            "dma_enabled": scope.get_dma_enable(),
        },
        "mca": {
            "signal": {
                "pulse_polarity": mca.get_pulse_polarity(),
                "trigger_level": mca.get_trigger_level(),
                "baseline_window": mca.get_baseline_window(),
                "pretrigger_samples": mca.get_pretrigger_samples(),
                "frame_samples": mca.get_frame_samples(),
                "trg_source": mca.get_trg_source(),
                "ext_trig_enable": mca.get_ext_trig_enable(),
                "edge_det_coeff": mca.get_edge_det_coeff(),
            },
            "acquisition": {
                "energy_bin": mca.get_energy_bin(),
                "pileup_window": mca.get_pileup_window(),
                "time_limit": mca.get_time_limit(),
                "dma_enabled": mca.get_dma_enable(),
            },
            "debug": {
                "mem1_sig_select": mca.get_mem1_sig_select(),
                "mem2_sig_select": mca.get_mem2_sig_select(),
            },
            "crrc2": {
                "cdelay": mca.filters.crrc2.get_Cdelay(),
                "fdelay": mca.filters.crrc2.get_Fdelay(),
                "pzc": mca.filters.crrc2.get_pzc_coeff(),
            },
            "cfd": {
                "enable": mca.filters.cfd.get_enable(),
                "factor": mca.filters.cfd.get_factor(),
                "delay": mca.filters.cfd.get_delay(),
                "tw_low": mca.filters.cfd.get_time_window_low(),
                "tw_high": mca.filters.cfd.get_time_window_high(),
            },
            "trapezoid": {
                "enable": mca.filters.trapezoid.get_enable(),
                "r": mca.filters.trapezoid.get_R(),
                "m": mca.filters.trapezoid.get_M(),
                "t": mca.filters.trapezoid.get_T(),
                "e": mca.filters.trapezoid.get_E(),
                "ft": mca.filters.trapezoid.get_FT(),
            },
            "charge_comparison": {
                "enable": mca.filters.charge_comparison.get_enable(),
                "time": mca.filters.charge_comparison.get_time(),
            },
            "psd_zc": {
                "enable": mca.filters.psd_zc.get_enable(),
                "mode": mca.filters.psd_zc.get_mode(),
                "low": mca.filters.psd_zc.get_time_window_low(),
                "high": mca.filters.psd_zc.get_time_window_high(),
            },
            "temperature": {
                "coeff": mca.get_temp_coeff(),
                "offset": mca.get_temp_offset(),
            },
        },
    }

    if hv is not None:
        psu: dict = {
            "hv_voltage": hv.get_hv_adc_voltage(),
            "hv_compens_ct": hv.get_hv_compens_output(),
            "hv_compens_mode": 0,
            "temp_digital_enable": 0,
        }
        try:
            psu["hv_compens_mode"] = hv._b.get_hv_compens_output()
        except Exception:
            pass
        if hv.sipm_available():
            psu["sipm_voltage"] = hv.get_sipm_adc_voltage()
            psu["sipm_compens_ct"] = hv.get_sipm_compens_output()
        settings["psu"] = psu

    with open(path, "w") as f:
        yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
    log.info("Settings saved to %s", path)


def load_settings(
    scope: Scope,
    mca: MultiChannelAnalyzer,
    hv: HVSupply | None,
    path: Path,
) -> None:
    """Read YAML and apply all parameters to hardware."""
    with open(path) as f:
        settings = yaml.safe_load(f)

    if "scope" in settings:
        s = settings["scope"]
        if "trigger_level" in s:
            scope.set_trigger_level(int(s["trigger_level"]))
        if "pretrigger_samples" in s:
            scope.set_pretrigger_samples(int(s["pretrigger_samples"]))
        if "frame_samples" in s:
            scope.set_frame_samples(int(s["frame_samples"]))
        if "edge_mode" in s:
            from nlab.hardware.digitizer.scope import TriggerMode
            scope.set_trigger_mode(TriggerMode(int(s["edge_mode"])))
        if "dac_value" in s:
            scope.set_dac_value(int(s["dac_value"]))
        if "dma_enabled" in s:
            scope.set_dma_enable(bool(s["dma_enabled"]))

    if "mca" in settings:
        m = settings["mca"]

        sig = m.get("signal", {})
        if "pulse_polarity" in sig:
            mca.set_pulse_polarity(int(sig["pulse_polarity"]))
        if "trigger_level" in sig:
            mca.set_trigger_level(int(sig["trigger_level"]))
        if "baseline_window" in sig:
            mca.set_baseline_window(int(sig["baseline_window"]))
        if "pretrigger_samples" in sig:
            mca.set_pretrigger_samples(int(sig["pretrigger_samples"]))
        if "frame_samples" in sig:
            mca.set_frame_samples(int(sig["frame_samples"]))
        if "trg_source" in sig:
            mca.set_trg_source(int(sig["trg_source"]))
        if "ext_trig_enable" in sig:
            mca.set_ext_trig_enable(bool(sig["ext_trig_enable"]))
        if "edge_det_coeff" in sig:
            mca.set_edge_det_coeff(int(sig["edge_det_coeff"]))

        acq = m.get("acquisition", {})
        if "energy_bin" in acq:
            mca.set_energy_bin(int(acq["energy_bin"]))
        if "pileup_window" in acq:
            mca.set_pileup_window(int(acq["pileup_window"]))
        if "time_limit" in acq:
            mca.set_time_limit(int(acq["time_limit"]))
        if "dma_enabled" in acq:
            mca.set_dma_enable(bool(acq["dma_enabled"]))

        dbg = m.get("debug", {})
        if "mem1_sig_select" in dbg:
            mca.set_mem1_sig_select(int(dbg["mem1_sig_select"]))
        if "mem2_sig_select" in dbg:
            mca.set_mem2_sig_select(int(dbg["mem2_sig_select"]))

        crrc2 = m.get("crrc2", {})
        if "cdelay" in crrc2:
            mca.filters.crrc2.set_Cdelay(int(crrc2["cdelay"]))
        if "fdelay" in crrc2:
            mca.filters.crrc2.set_Fdelay(int(crrc2["fdelay"]))
        if "pzc" in crrc2:
            mca.filters.crrc2.set_pzc_coeff(int(crrc2["pzc"]))

        cfd = m.get("cfd", {})
        if "enable" in cfd:
            mca.filters.cfd.set_enable(bool(cfd["enable"]))
        if "factor" in cfd:
            mca.filters.cfd.set_factor(float(cfd["factor"]))
        if "delay" in cfd:
            mca.filters.cfd.set_delay(int(cfd["delay"]))
        if "tw_low" in cfd:
            mca.filters.cfd.set_time_window_low(int(cfd["tw_low"]))
        if "tw_high" in cfd:
            mca.filters.cfd.set_time_window_high(int(cfd["tw_high"]))

        trap = m.get("trapezoid", {})
        if "enable" in trap:
            mca.filters.trapezoid.set_enable(bool(trap["enable"]))
        if "r" in trap:
            mca.filters.trapezoid.set_R(int(trap["r"]))
        if "m" in trap:
            mca.filters.trapezoid.set_M(int(trap["m"]))
        if "t" in trap:
            mca.filters.trapezoid.set_T(int(trap["t"]))
        if "e" in trap:
            mca.filters.trapezoid.set_E(int(trap["e"]))
        if "ft" in trap:
            mca.filters.trapezoid.set_FT(int(trap["ft"]))

        cc = m.get("charge_comparison", {})
        if "enable" in cc:
            mca.filters.charge_comparison.set_enable(bool(cc["enable"]))
        if "time" in cc:
            mca.filters.charge_comparison.set_time(int(cc["time"]))

        psd = m.get("psd_zc", {})
        if "enable" in psd:
            mca.filters.psd_zc.set_enable(bool(psd["enable"]))
        if "mode" in psd:
            mca.filters.psd_zc.set_mode(int(psd["mode"]))
        if "low" in psd:
            mca.filters.psd_zc.set_time_window_low(int(psd["low"]))
        if "high" in psd:
            mca.filters.psd_zc.set_time_window_high(int(psd["high"]))

        temp = m.get("temperature", {})
        if "coeff" in temp:
            mca.set_temp_coeff(float(temp["coeff"]))
        if "offset" in temp:
            mca.set_temp_offset(int(temp["offset"]))

    if "psu" in settings and hv is not None:
        p = settings["psu"]
        if "hv_voltage" in p:
            hv.set_hv_voltage(float(p["hv_voltage"]))
        if "hv_compens_ct" in p:
            hv.set_hv_compens_ct(float(p["hv_compens_ct"]))
        if "hv_compens_tref" in p:
            hv.set_hv_compens_tref(float(p["hv_compens_tref"]))
        if "hv_compens_mode" in p:
            hv.set_hv_compens_mode(int(p["hv_compens_mode"]))
        if "temp_digital_enable" in p:
            hv.set_temp_digital_enable(int(p["temp_digital_enable"]))
        if hv.sipm_available():
            if "sipm_voltage" in p:
                hv.set_sipm_voltage(float(p["sipm_voltage"]))
            if "sipm_compens_ct" in p:
                hv.set_sipm_compens_ct(float(p["sipm_compens_ct"]))
            if "sipm_compens_tref" in p:
                hv.set_sipm_compens_tref(float(p["sipm_compens_tref"]))
            if "sipm_compens_mode" in p:
                hv.set_sipm_compens_mode(int(p["sipm_compens_mode"]))

    log.info("Settings loaded from %s", path)