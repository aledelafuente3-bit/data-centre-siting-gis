#!/usr/bin/env python3
"""
step20_critic_montecarlo.py
----------------------------
Run with:  ./gis_venv/bin/python3 step20_critic_montecarlo.py

SECTION A — CRITIC (Diakoulaki et al. 1995)
  C_j = σ_j × Σ_{i≠j}(1 − |r_{ij}|)
  w_j = C_j / Σ C_j
  Run independently for each pillar. Compare to baseline weights.

SECTION B — Monte Carlo Dirichlet (1,000 draws × 5 sensitivities)
  MC-A  ESI criterion weights     (OFI, SII at baseline)
  MC-B  OFI criterion weights     (ESI, SII at baseline)
  MC-C  SII criterion weights     (ESI, OFI at baseline)
  MC-D  Pillar weights            (criterion weights at baseline)
  MC-E  All criterion weights simultaneously

Speed strategy: pre-extract all criterion + baseline pillar values as 1D arrays
at 50,000 randomly sampled viable cells. Each draw = weighted sum on 50,000
floats → Spearman ρ.  Total runtime < 60 s.

Outputs:  00_ADMIN/critic_montecarlo_results.json
"""

import os, json, subprocess, time
import numpy as np

PROJ_ENV = {
    **os.environ,
    "PROJ_LIB":  "/Applications/QGIS-LTR.app/Contents/MacOS/share/proj",
    "GDAL_DATA": "/Applications/QGIS-LTR.app/Contents/MacOS/share/gdal",
}
GDAL_BIN = "/Applications/QGIS-LTR.app/Contents/MacOS/bin"

NROWS, NCOLS = 2597, 4086
BASE = "/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS"
RDIR = f"{BASE}/11_processed_layers/rasters"
ADM  = f"{BASE}/00_ADMIN"

N_DRAWS  = 1_000
N_SAMPLE = 50_000
RNG      = np.random.default_rng(seed=42)

# ── I/O ──────────────────────────────────────────────────────────────────────
def run(cmd):
    r = subprocess.run(cmd, env=PROJ_ENV, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-400:])


def read_raster(tif):
    tmp = tif + ".tmp20.raw"
    run([f"{GDAL_BIN}/gdal_translate", "-of", "ENVI", "-ot", "Float32",
         "-co", "INTERLEAVE=BSQ", tif, tmp])
    arr = np.fromfile(tmp, dtype=np.float32).reshape(NROWS, NCOLS).astype(np.float64)
    for f in [tmp, tmp + ".hdr"]:
        try: os.remove(f)
        except: pass
    arr[(arr == -9999.0) | (arr == 255.0)] = np.nan
    return arr


# ── Load all layers ───────────────────────────────────────────────────────────
print("Loading layers …", flush=True)
mask_raw = read_raster(f"{RDIR}/mask_7states_1km_EPSG5070.tif")
mask_bin = (mask_raw == 1)

CRITERION_FILES = {
    "water_current": "water_stress_baseline_bws_suitability.tif",
    "nri_eal":       "nri_eal_buildings_suitability_1km.tif",
    "cmip6_heat":    "cmip6_heat_suitability_1km.tif",
    "tx_230kV":      "tx_230kV_suitability_1km.tif",
    "ixp":           "ixp_proximity_suitability_1km.tif",
    "roads":         "roads_suitability_1km.tif",
    "carbon_co2e":   "carbon_current_co2e_suitability.tif",
    "eji":           "eji_suitability_1km.tif",
    "water_future":  "water_stress_future2050bau_ws_suitability.tif",
}

L = {k: read_raster(f"{RDIR}/{f}") for k, f in CRITERION_FILES.items()}

gric_arr  = read_raster(f"{RDIR}/gric_s1_threepillar_1km.tif")
esi_arr   = read_raster(f"{RDIR}/esi_composite_1km.tif")
ofi_arr   = read_raster(f"{RDIR}/ofi_composite_1km.tif")
sii_arr   = read_raster(f"{RDIR}/sii_composite_1km.tif")

# Viable = mask cell with valid GRIC (after M0 exclusions)
viable     = mask_bin & ~np.isnan(gric_arr)
viable_idx = np.where(viable.ravel())[0]          # indices into flat array
n_viable   = len(viable_idx)
print(f"  Viable cells: {n_viable:,}")

# Fixed random sample of viable cells (same cells for every draw)
sample_pos   = RNG.choice(n_viable, size=min(N_SAMPLE, n_viable), replace=False)
sample_idx   = viable_idx[sample_pos]             # global flat indices

# ── Pre-extract 1D arrays at sample cells ─────────────────────────────────────
# Shape: (N_SAMPLE,)  — NaN where that criterion has no data at this cell
Ls = {k: arr.ravel()[sample_idx] for k, arr in L.items()}
gric_s = gric_arr.ravel()[sample_idx]
esi_s  = esi_arr.ravel()[sample_idx]
ofi_s  = ofi_arr.ravel()[sample_idx]
sii_s  = sii_arr.ravel()[sample_idx]

# Also pre-extract at ALL viable cells for CRITIC correlations
Lv = {k: arr.ravel()[viable_idx] for k, arr in L.items()}

print(f"  Sample cells extracted: {len(sample_idx):,}")

PILLAR_KEYS = {
    "ESI": ["water_current", "nri_eal",  "cmip6_heat"],
    "OFI": ["tx_230kV",      "ixp",      "roads"],
    "SII": ["carbon_co2e",   "eji",      "water_future"],
}

BASELINE_W = {
    "ESI": np.array([1/3,   1/3,   1/3]),
    "OFI": np.array([0.611, 0.278, 0.111]),
    "SII": np.array([1/3,   1/3,   1/3]),
}

LABELS = {
    "water_current": "Water stress (current)",
    "nri_eal":       "NRI EAL 18-hazard",
    "cmip6_heat":    "CMIP6 heat 2041–60",
    "tx_230kV":      "230kV TX proximity",
    "ixp":           "IXP proximity",
    "roads":         "Roads proximity",
    "carbon_co2e":   "Carbon CO2e",
    "eji":           "EJI burden (inv.)",
    "water_future":  "Water stress (2050 BAU)",
}


# ── Weighted 1D pillar from pre-extracted sample vectors ─────────────────────
def pillar_1d(keys, weights, vectors):
    """NaN-safe weighted mean. vectors: dict of 1D arrays."""
    acc = np.zeros(len(next(iter(vectors.values()))))
    tw  = np.zeros_like(acc)
    for k, w in zip(keys, weights):
        v = vectors[k]
        ok = ~np.isnan(v)
        acc[ok] += w * v[ok]
        tw[ok]  += w
    return np.where(tw > 0, acc / tw, np.nan)


def gric_1d(esi, ofi, sii, pw=None):
    if pw is None:
        pw = np.array([1/3, 1/3, 1/3])
    acc = np.zeros(len(esi))
    tw  = np.zeros_like(acc)
    for p, w in zip([esi, ofi, sii], pw):
        ok = ~np.isnan(p)
        acc[ok] += w * p[ok]
        tw[ok]  += w
    return np.where(tw > 0, acc / tw, np.nan)


def spearman_1d(a, b):
    """Spearman ρ ignoring NaN pairs."""
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 50:
        return np.nan
    ra = a[ok].argsort().argsort().astype(np.float64)
    rb = b[ok].argsort().argsort().astype(np.float64)
    n  = ra.size
    d2 = ((ra - rb) ** 2).sum()
    return float(1.0 - 6.0 * d2 / (n * (n * n - 1)))


# ═══════════════════════════════════════════════════════════════════════════
# SECTION A — CRITIC
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "="*62)
print("SECTION A: CRITIC weight derivation")
print("="*62)

critic_out = {}

for pillar, keys in PILLAR_KEYS.items():
    # Build matrix using ALL viable cells where EVERY criterion is non-NaN
    cols = np.column_stack([Lv[k] for k in keys])
    ok   = np.all(~np.isnan(cols), axis=1)
    mat  = cols[ok]
    n    = mat.shape[0]

    sigma    = mat.std(axis=0)
    corr     = np.corrcoef(mat.T)
    # conflict for criterion j = sum over i≠j of (1 − |r_{ij}|)
    conflict = np.array([
        (1.0 - np.abs(corr[j])).sum() - (1.0 - abs(corr[j, j]))
        for j in range(len(keys))
    ])
    C        = sigma * conflict
    w_critic = C / C.sum()
    w_base   = BASELINE_W[pillar]

    critic_out[pillar] = {
        "n_cells": int(n),
        "criteria": {
            k: {
                "sigma":      round(float(sigma[i]), 5),
                "conflict":   round(float(conflict[i]), 5),
                "C_j":        round(float(C[i]), 5),
                "w_critic":   round(float(w_critic[i]), 4),
                "w_baseline": round(float(w_base[i]), 4),
                "delta":      round(float(w_critic[i] - w_base[i]), 4),
            }
            for i, k in enumerate(keys)
        },
        "corr_matrix": {
            keys[i]: {keys[j]: round(float(corr[i,j]),4) for j in range(len(keys))}
            for i in range(len(keys))
        }
    }

    # Print
    print(f"\n  {pillar}  (n = {n:,} complete cells)")
    print(f"  {'Criterion':<26}  {'σ':>6}  {'Conflict':>8}  "
          f"{'w_CRITIC':>9}  {'w_base':>8}  {'Δ':>7}")
    print("  " + "-"*72)
    for i, k in enumerate(keys):
        d = critic_out[pillar]["criteria"][k]
        arrow = "↑" if d["delta"] > 0.02 else ("↓" if d["delta"] < -0.02 else "≈")
        print(f"  {LABELS[k]:<26}  {d['sigma']:>6.4f}  {d['conflict']:>8.4f}  "
              f"{d['w_critic']:>9.4f}  {d['w_baseline']:>8.4f}  {d['delta']:>+7.4f} {arrow}")

    print(f"\n  Pearson r matrix:")
    hdr = "  " + " "*28 + "".join(f"{k[:8]:>10}" for k in keys)
    print(hdr)
    for i, ki in enumerate(keys):
        row = f"  {LABELS[ki][:26]:<26}  " + "".join(
            f"{corr[i,j]:>10.4f}" for j in range(len(keys)))
        print(row)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION B — Monte Carlo Dirichlet
# ═══════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*62)
print("SECTION B: Monte Carlo Dirichlet  (n=1,000 draws each)")
print("="*62)

alpha3 = np.ones(3)
alpha9 = np.ones(9)

mc_out = {}

def run_mc(label, description, draw_fn, score_fn):
    print(f"\n  [{label}] {description} … ", end="", flush=True)
    t0   = time.time()
    rhos = []
    for _ in range(N_DRAWS):
        w   = draw_fn()
        new = score_fn(w)
        rho = spearman_1d(gric_s, new)
        if not np.isnan(rho):
            rhos.append(rho)
    rhos = np.array(rhos)
    elapsed = time.time() - t0
    r = {
        "n_valid":        len(rhos),
        "median_rho":     round(float(np.median(rhos)),   4),
        "p5_rho":         round(float(np.percentile(rhos,  5)), 4),
        "p95_rho":        round(float(np.percentile(rhos, 95)), 4),
        "min_rho":        round(float(rhos.min()), 4),
        "pct_above_0.95": round(float((rhos >= 0.95).mean() * 100), 1),
        "pct_above_0.90": round(float((rhos >= 0.90).mean() * 100), 1),
    }
    mc_out[label] = r
    verdict = "ROBUST" if r["median_rho"] >= 0.95 else \
              ("MODERATE" if r["median_rho"] >= 0.85 else "SENSITIVE")
    print(f"median ρ={r['median_rho']:.4f}  "
          f"CI=[{r['p5_rho']:.4f}–{r['p95_rho']:.4f}]  "
          f"ρ≥0.95:{r['pct_above_0.95']}%  "
          f"{verdict}  ({elapsed:.0f}s)")


# Pre-compute CRITIC-weighted 1D pillar vectors (for comparison)
esi_critic_s = pillar_1d(PILLAR_KEYS["ESI"],
                          [critic_out["ESI"]["criteria"][k]["w_critic"]
                           for k in PILLAR_KEYS["ESI"]], Ls)
ofi_critic_s = pillar_1d(PILLAR_KEYS["OFI"],
                          [critic_out["OFI"]["criteria"][k]["w_critic"]
                           for k in PILLAR_KEYS["OFI"]], Ls)
sii_critic_s = pillar_1d(PILLAR_KEYS["SII"],
                          [critic_out["SII"]["criteria"][k]["w_critic"]
                           for k in PILLAR_KEYS["SII"]], Ls)

# MC-A: ESI criterion weights (OFI, SII at baseline)
run_mc("MC-A", "ESI criterion weights  (OFI, SII baseline)",
       draw_fn=lambda: RNG.dirichlet(alpha3),
       score_fn=lambda w: gric_1d(pillar_1d(PILLAR_KEYS["ESI"], w, Ls), ofi_s, sii_s))

# MC-B: OFI criterion weights (ESI, SII at baseline)
run_mc("MC-B", "OFI criterion weights  (ESI, SII baseline)",
       draw_fn=lambda: RNG.dirichlet(alpha3),
       score_fn=lambda w: gric_1d(esi_s, pillar_1d(PILLAR_KEYS["OFI"], w, Ls), sii_s))

# MC-C: SII criterion weights (ESI, OFI at baseline)
run_mc("MC-C", "SII criterion weights  (ESI, OFI baseline)",
       draw_fn=lambda: RNG.dirichlet(alpha3),
       score_fn=lambda w: gric_1d(esi_s, ofi_s, pillar_1d(PILLAR_KEYS["SII"], w, Ls)))

# MC-D: Pillar weights (criterion weights at baseline)
run_mc("MC-D", "Pillar weights         (criterion weights baseline)",
       draw_fn=lambda: RNG.dirichlet(alpha3),
       score_fn=lambda pw: gric_1d(esi_s, ofi_s, sii_s, pw=pw))

# MC-E: All 9 criterion weights simultaneously, equal pillar weight
def all_crit_gric(w9):
    w_esi = w9[0:3] / w9[0:3].sum()
    w_ofi = w9[3:6] / w9[3:6].sum()
    w_sii = w9[6:9] / w9[6:9].sum()
    return gric_1d(pillar_1d(PILLAR_KEYS["ESI"], w_esi, Ls),
                   pillar_1d(PILLAR_KEYS["OFI"], w_ofi, Ls),
                   pillar_1d(PILLAR_KEYS["SII"], w_sii, Ls))

run_mc("MC-E", "All 9 criterion weights (pillar weights equal)",
       draw_fn=lambda: RNG.dirichlet(alpha9),
       score_fn=all_crit_gric)

# MC-F: CRITIC weights vs baseline Spearman check
print(f"\n  [CRITIC-check] Spearman ρ between CRITIC-weighted and baseline GRIC …", end="", flush=True)
gric_critic_s = gric_1d(esi_critic_s, ofi_critic_s, sii_critic_s)
rho_critic = spearman_1d(gric_s, gric_critic_s)
print(f" ρ = {rho_critic:.4f}")
mc_out["CRITIC_vs_baseline_rho"] = round(rho_critic, 4)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*62)
print("SUMMARY")
print("="*62)

print("\n  CRITIC weights vs baseline:\n")
for pillar in ["ESI", "OFI", "SII"]:
    print(f"  {pillar}")
    for k, d in critic_out[pillar]["criteria"].items():
        arrow = "↑" if d["delta"] > 0.02 else ("↓" if d["delta"] < -0.02 else "≈")
        print(f"    {LABELS[k]:<28}  baseline={d['w_baseline']:.3f}  "
              f"CRITIC={d['w_critic']:.3f}  {arrow}")

print(f"\n  Monte Carlo robustness (n={N_DRAWS} draws, {N_SAMPLE:,}-cell sample):\n")
print(f"  {'Run':<6}  {'Median ρ':>9}  {'5th–95th':>18}  "
      f"{'ρ≥0.95':>7}  {'ρ≥0.90':>7}  Verdict")
print("  " + "-"*68)
verdicts = {"MC-A": "ESI weights", "MC-B": "OFI weights",
            "MC-C": "SII weights", "MC-D": "Pillar weights",
            "MC-E": "All crit. weights"}
for label in ["MC-A","MC-B","MC-C","MC-D","MC-E"]:
    r = mc_out[label]
    v = "ROBUST"   if r["median_rho"] >= 0.95 else \
        "MODERATE" if r["median_rho"] >= 0.85 else "SENSITIVE"
    print(f"  {label:<6}  {r['median_rho']:>9.4f}  "
          f"[{r['p5_rho']:.4f}–{r['p95_rho']:.4f}]  "
          f"{r['pct_above_0.95']:>6.1f}%  {r['pct_above_0.90']:>6.1f}%  "
          f"{v}  ({verdicts[label]})")

print(f"\n  CRITIC vs baseline GRIC:  ρ = {mc_out['CRITIC_vs_baseline_rho']:.4f}")


# ── Save JSON ─────────────────────────────────────────────────────────────────
output = {
    "methodology": {
        "CRITIC": "Diakoulaki et al. (1995) — C_j = sigma_j x sum(1 - |r_ij|); "
                  "absolute correlations; viable cells with all pillar criteria non-NaN",
        "MonteCarlo": (f"Dirichlet(alpha=1) uniform simplex; {N_DRAWS} draws per sensitivity; "
                       f"Spearman rho on {N_SAMPLE}-cell random sample of viable cells; "
                       "seed=42 for reproducibility"),
    },
    "critic":       critic_out,
    "monte_carlo":  mc_out,
}
out_path = f"{ADM}/critic_montecarlo_results.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Results → {out_path}")
print("\nDONE — step20 complete")
