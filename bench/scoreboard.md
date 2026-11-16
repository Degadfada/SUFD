# SUFD scoreboard

Build: slice-1 baseline · generated 2026-11-16 05:02

| Gate | Result |
|---|---|
| S1 top-1 ≥ 0.80 (fixed 180-case set) | FAIL |
| S1 top-3 ≥ 0.95 | FAIL |
| S1 described within 64 samples (median) | PASS |
| M3 ramp false jumps = 0 | PASS |
| M3 sine false jumps = 0 | PASS |
| M3 1-LSB blip: stays scalar, no event | FAIL |
| M3 period error bar present | — (not implemented) |
| M3 white noise ⇒ unmodelled | FAIL |
| M3 flicker exceedance ≤ 2× nominal (0.54%) | FAIL |
| M3 white exceedance within 0.5–2× nominal | FAIL |
| S3 exactly one episode per true crossing | PASS |
| S4 1σ shift detected ≤ 10 samples | FAIL |
| S4 correlated shift detected | FAIL |
| S3 chatter events = 0 | PASS |
| S3 fleeting alarms = 0 | PASS |
| M2 hostile input: 0 exceptions | FAIL |
| M2 fuzz (2000 random inputs): 0 exceptions | FAIL |
| M3 alias flag | — (not implemented) |
| M3 τ/ζ identification | — (not implemented) |
| S5 PIT calibration | — (not implemented) |
| M2 jitter/skew attribution | — (not implemented) |
| S6 CPU ≤ 5% of one core (PC, demo load) | PASS |

**7 / 22 gates pass.**

## Raw metrics

```json
{
 "false_jumps_per_1000": {
  "ramp": 0.0,
  "sine": 0.0,
  "white": 0.0,
  "flicker": 0.0,
  "heavy_tail": 3.8
 },
 "quantised_blip_flagged": {
  "kind": "binary",
  "notes_at_blip": [
   "changed to 21.51 after 285 s",
   "changed to 21.5 after 1 s"
  ]
 },
 "period": {
  "sine_rel_err": 0.0,
  "sine_err_bar": null,
  "sine_jitter_rel_err": 0.0,
  "sine_jitter_err_bar": null
 },
 "band_exceedance": {
  "nominal": 0.0027,
  "seeds": 20,
  "white": 0.0,
  "white_worst": 0.0,
  "heavy_tail": 0.00144,
  "heavy_tail_worst": 0.0024,
  "flicker": 0.02387,
  "flicker_worst": 0.08996,
  "flicker_10k": 0.01528,
  "flicker_10k_worst": 0.07104
 },
 "detection": {
  "mean_shift_delay": null,
  "mean_shift_false_before": 0,
  "ar1_mean_shift_delay": null,
  "ar1_mean_shift_false_before": 0
 },
 "chatter": {
  "activations": 1,
  "chatter_events": 0,
  "fleeting": 0
 },
 "hostile": {
  "exceptions": 6,
  "first": [
   "ingest(9.0,None): TypeError",
   "ingest(13.0,2.0): ValueError",
   "ingest(29.0,0.0): ValueError"
  ]
 },
 "white_is_unmodelled": false,
 "fuzz": {
  "exceptions": 1278,
  "by_type": {
   "TypeError": 213,
   "ValueError": 1065
  }
 },
 "S1_signature": {
  "cases": 180,
  "top1": 0.333,
  "top3": 0.417,
  "described_median_samples": 32.0
 },
 "perf": {
  "samples": 6520,
  "us_per_sample": 349.9,
  "cpu_share_realtime": 0.0076
 },
 "capabilities": {
  "alias_flag": null,
  "tau_zeta": null,
  "pit_calibration": null,
  "timing_jitter_skew": null,
  "stuck_clip_gap_flags": null,
  "relations": null,
  "thermal": null,
  "privacy_class": null,
  "trust": null
 }
}
```
