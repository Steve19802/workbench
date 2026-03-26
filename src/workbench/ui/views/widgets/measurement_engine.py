
# measurement_engine.py
from __future__ import annotations
import numpy as np
from ....contracts.enums import ScopeModes

# ------------------------------------------------------------
# Time helpers (original functions, slightly cleaned)
# ------------------------------------------------------------
def slice_by_cursors(x: np.ndarray, y: np.ndarray, x1: float | None, x2: float | None):
    """Slices (x, y) to the range [x1, x2] if both are defined and x2 != x1."""
    if x1 is None or x2 is None or x1 == x2:
        return x, y
    if x2 < x1:
        x1, x2 = x2, x1
    m = (x >= x1) & (x <= x2)
    if not np.any(m):
        return x, y
    return x[m], y[m]

def basic_stats(y: np.ndarray):
    """Compute basic statistics: Vpp, Vrms, Vavg, Vmin, Vmax."""
    if y.size == 0:
        return dict(vpp=None, vrms=None, vavg=None, vmin=None, vmax=None)
    vmin = float(np.min(y))
    vmax = float(np.max(y))
    vavg = float(np.mean(y))
    vrms = float(np.sqrt(np.mean(np.square(y))))
    return dict(vpp=vmax - vmin, vrms=vrms, vavg=vavg, vmin=vmin, vmax=vmax)

def frequency_zero_cross(x: np.ndarray, y: np.ndarray):
    """Estimate frequency by zero-crossings with linear interpolation."""
    if y.size < 2:
        return None
    yc = y - np.mean(y)
    s = np.signbit(yc)
    idx = np.where(s[:-1] != s[1:])[0]
    if idx.size < 2:
        return None
    tzc = []
    for i in idx:
        x1, x2 = x[i], x[i + 1]
        y1, y2 = yc[i], yc[i + 1]
        if y2 == y1:
            continue
        t0 = x1 - y1 * (x2 - x1) / (y2 - y1)  # linear crossing
        tzc.append(t0)
    if len(tzc) < 2:
        return None
    dt = np.diff(np.array(tzc))
    if dt.size == 0:
        return None
    # Period ≈ 2 * median(dt) (two crossings per cycle)
    T = 2.0 * float(np.median(dt))
    if T <= 0:
        return None
    return 1.0 / T

def duty_cycle(x: np.ndarray, y: np.ndarray, threshold: float | None = None):
    """Compute duty cycle by simple binarization against a threshold."""
    if y.size == 0:
        return None
    thr = float(np.mean(y)) if threshold is None else float(threshold)
    high = y > thr
    return 100.0 * (np.count_nonzero(high) / y.size)

# ------------------------------------------------------------
# Frequency helpers
# ------------------------------------------------------------
def spectrum_to_power(y, spectrum_format: str = "abs", db_floor: float = -300.0):
    """
    Convert spectrum to linear power per bin.
    spectrum_format:
    - 'db'  : y is in dB (dBV, dBFS, dBu or power dB) -> P = 10^(dB/10)
    - 'abs' : y is in linear magnitude (e.g., Vrms/bin) -> P = y^2
    db_floor: floor to avoid underflow when converting dB to linear.
    """
    y = np.asarray(y)
    fmt = (spectrum_format or "abs").lower()
    if fmt == "db":
        return np.power(10.0, y / 10.0)
    # default: abs (magnitude)
    return np.square(np.abs(y))

def _find_fundamental(f: np.ndarray, P: np.ndarray) -> tuple[float, int, float]:
    """
    Return (freq0, idx0, value_0) of the largest peak ≠ DC.
    f: Hz, P: relative power per bin.
    """
    if f.size == 0 or P.size == 0 or f.size != P.size:
        return np.nan, -1, np.nan
    mask = f > 0
    if not np.any(mask):
        return np.nan, -1, np.nan
    idx_rel = np.argmax(P[mask])
    idx_abs_candidates = np.flatnonzero(mask)
    idx0 = int(idx_abs_candidates[idx_rel])
    freq0 = float(f[idx0])
    value_0 = float(P[idx0])
    return freq0, idx0, value_0

def _sum_power_around(f: np.ndarray, P: np.ndarray, f_target: float, half_width_bins: int = 1) -> tuple[float, int]:
    """
    Sum power within ±half_width_bins around the bin closest to f_target.
    Returns (power_sum, idx_center).
    """
    if f.size == 0:
        return 0.0, -1
    idx = int(np.argmin(np.abs(f - f_target)))
    lo = max(idx - half_width_bins, 0)
    hi = min(idx + half_width_bins, len(f) - 1)
    return float(np.sum(P[lo:hi + 1])), idx

def _notch_mask(n: int, centers: list[int], half_width_bins: int, exclude_dc: bool = False) -> np.ndarray:
    """
    True = keep, False = notch (remove) around each center ± half_width_bins.
    - Validates out-of-range indices or -1.
    - Deduplicates centers.
    - Optionally exclude DC (index 0) from keep.
    """
    if n <= 0:
        return np.zeros(0, dtype=bool)
    keep = np.ones(n, dtype=bool)
    hw = max(int(half_width_bins), 0)
    valid_centers = []
    for c in centers or []:
        if c is None:
            continue
        c = int(c)
        if c < 0 or c >= n:
            continue
        valid_centers.append(c)
    if not valid_centers and not exclude_dc:
        return keep
    valid_centers = np.unique(valid_centers)
    for c in valid_centers:
        lo = max(c - hw, 0)
        hi = min(c + hw, n - 1)
        keep[lo:hi + 1] = False
    if exclude_dc and n > 0:
        keep[0] = False
    return keep

# ------------------------------------------------------------
# Main API
# ------------------------------------------------------------
def compute_metric(
    metric_name: str,
    x: np.ndarray,
    y: np.ndarray,
    *,
    x1=None,
    x2=None,
    duty_threshold=None,
    domain: ScopeModes | None = ScopeModes.TIME,
    spectrum_format: str = "abs",
    max_harmonics: int = 10,
    harmonic_bin_halfwidth: int = 3,
):
    """
    Compute time and frequency metrics.

    Parameters
    ----------
    metric_name : {"Vpp","Vrms","Vavg","Vmin","Vmax","Frequency","Duty","THD","THD+N","SINAD"}
    x :
        - domain=ScopeModes.TIME: time [s]
        - domain=ScopeModes.SPECTRUM: frequency [Hz]
    y :
        - domain=ScopeModes.TIME: time-domain signal [V]
        - domain=ScopeModes.SPECTRUM: spectral magnitude Y (linear)
    x1, x2 : cursor limits (s or Hz, depending on domain)
    duty_threshold : threshold for Duty (%)
    domain : ScopeModes
    max_harmonics : maximum harmonics (k >= 2) to consider
    harmonic_bin_halfwidth : half-width (in bins) to sum around each tone
    
    Returns
    -------
    float or None
    """
    if x is None or y is None:
        return None
    x = np.asarray(x)
    y = np.asarray(y)
    if x.size != y.size:
        n = min(x.size, y.size)
        x, y = x[:n], y[:n]
    name = (metric_name or "").strip()
    xs, ys = slice_by_cursors(x, y, x1, x2)

    # -------------------- Time-domain metrics --------------------
    if name in ("Vpp", "Vrms", "Vavg", "Vmin", "Vmax", "Duty") or (name == "Frequency" and domain == ScopeModes.TIME):
        if ys.size == 0:
            return None
        if name == "Vpp":
            stats = basic_stats(ys); return stats["vpp"]
        if name == "Vrms":
            stats = basic_stats(ys); return stats["vrms"]
        if name == "Vavg":
            stats = basic_stats(ys); return stats["vavg"]
        if name == "Vmin":
            stats = basic_stats(ys); return stats["vmin"]
        if name == "Vmax":
            stats = basic_stats(ys); return stats["vmax"]
        if name == "Duty":
            return duty_cycle(xs, ys, threshold=duty_threshold)
        if name == "Frequency":
            fzc = frequency_zero_cross(xs, ys)
            return float(fzc) if (fzc is not None and np.isfinite(fzc)) else None

    # -------------------- Frequency-domain metrics --------------------
    if name in ("Fund. Freq.", "Fund. Val.", "THD", "THD+N", "SINAD"):
        if domain != ScopeModes.SPECTRUM:
            return None
        if xs.size == 0 or ys.size == 0:
            return None
        f = xs
        pwr_y = spectrum_to_power(ys, spectrum_format=spectrum_format)
        freq0, idx0, pwr0 = _find_fundamental(f, ys)
        if not np.isfinite(freq0) or idx0 < 0 or not np.isfinite(pwr0):
            return None
        if name == "Fund. Freq.":
            return float(freq0)
        if name == "Fund. Val.":
            return float(ys[idx0])

        harmonics_power = 0.0
        harmonic_indices = [idx0]
        f_max = float(f[-1])
        for k in range(2, int(max_harmonics) + 1):
            fk = k * freq0
            if fk > f_max:
                break
            p_k, idx_k = _sum_power_around(f, pwr_y, fk, half_width_bins=harmonic_bin_halfwidth)
            harmonics_power += p_k
            if idx_k >= 0:
                harmonic_indices.append(idx_k)

        p0_sum, _ = _sum_power_around(f, pwr_y, freq0, half_width_bins=harmonic_bin_halfwidth)
        fundamental_power = max(p0_sum, 0.0)
        thd_power = max(harmonics_power, 0.0)

        keep = _notch_mask(len(f), harmonic_indices, half_width_bins=harmonic_bin_halfwidth)
        keep = keep & (f > 0)
        noise_power = float(np.sum(pwr_y[keep]))
        noise_power = max(noise_power, 0.0)

        if name == "THD":
            if fundamental_power <= 0.0:
                return None
            thd = np.sqrt(thd_power) / np.sqrt(fundamental_power)
            return float(100.0 * thd)  # %

        if name == "THD+N":
            if fundamental_power <= 0.0:
                return None
            thdn = np.sqrt(thd_power + noise_power) / np.sqrt(fundamental_power)
            return float(100.0 * thdn)  # %

        if name == "SINAD":
            denom = thd_power + noise_power
            if denom <= 0.0 or not np.isfinite(denom):
                return None
            sinad = 10.0 * np.log10(fundamental_power / denom)
            return float(sinad)  # dB

    return None