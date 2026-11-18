# SUFD knowledge base

Status: M0, 2026-11-16. Built from 16 books on the user's disk, plus lawful online substitutes for a second reading
list. Every claim carries a provenance tag and a verification status. The base is meant to be *used*: each item
names the decision it drives and the package that implements it.

## 0. How to read this

**Provenance tags**

| Tag | Meaning |
|---|---|
| **[B]** | stated in a source that was read (book or lawful substitute), with title and page/section |
| **[D]** | derived by us from first principles |
| **[S]** | established by simulation; script in `bench/claims.py` or `bench/run.py`, **reproduced by us** unless noted |
| **[K]** | from memory, source not read — verify before relying |
| **[FP]** | our inference or design choice, not a finding |

**Verification status**
- **verified** — `bench/verify_citations.py` extracted the printed page ±1 from the PDF and found the key terms
  (see §11). This is a *keyword* check: it proves the topic is on that page, not that the exact equation is.
- **agent-read** — a research agent read it and reported the page; not re-verified by us.
- **web-read** — a web source read by an agent; URL given.
- **unverified** — [K]/[FP] items.

**Page numbers** are the book's printed pages unless marked "pdf". Offsets between printed and PDF pages: Antoniou
and Dorf PDF = printed + 26; Giron-Sierra ≈ +34; Living Computers + 15; ML-Industrial +15–18 (drifts); AI-Art −15
(Ch1–10).

## 1. Glossary — keyword packages (defined by the module they name)



| Package | Plain-English role | Holds |
|---|---|---|
| `eno/` | intake — signals arrive and are made trustworthy | signal, transport, decode, ingest, timing, history |
| `emem/` | baseline and noise — what calm looks like and why it wanders | noise typing, spectral, calibration checks |
| `idea/` | understanding — the learned model of one signal | envelope, model, identification, states |
| `akpaneka/` | judgement and action — when something deserves a human | detect, alarm, notes, act |
| `kufre/` | self — SUFD's knowledge of itself and of relations | mind/ledger, runtime, needs, relate, thermal, governor, sampling, persist |
| `edimek/` | surface — where the human and SUFD sit at adjacent angles | lens, render, follow, layout, view rules, explain |

## 2. The central idea: one currency

Every SUFD judgement is a statement about how well a signal is predicted, in bits.

| Judgement | Definition | Why |
|---|---|---|
| surprise | surprisal −log₂ p(yₜ │ past) of the one-step predictive distribution, on the quantisation-bin probability | K-gir-wold, K-dor-observer, K-ant-quant-q2/12 |
| understood | out-of-sample prequential code-length gain over naive, bits/sample; ≤ floor ⇒ `unmodelled` | K-liv-mdl |
| model choice | exponentially weighted prequential log-loss (a mixture, not a hard switch) | K-mli-FPE-BIC, K-fpp3-rolling |
| regime change | innovation CUSUM **plus** a frozen-baseline detector | K-cusum-raw-collapse, K-karaoglan-residual |
| alarm | alarm budget on surprisal × consequence; deadband, on/off delay | K-hse-rates, K-siemens-table2 |
| relationship | bits saved predicting B from A's past, net of MDL cost, on a temporal hold-out | K-gdb-holdout |
| attention | render rate ∝ excess-surprisal information rate × value, capped by human bandwidth | K-mit831-cycle |
| self-efficiency | bits gained per CPU-ms per model and sense | the user's ask |
| sensor identity | poles of the fitted model: τ = −T/ln a; ζ, ωₙ from AR(2) complex roots | K-ther-firstorder, K-dor-freq-ident |

## 3. Lawful-source ledger — what each requested book became

Rule: only author-hosted, open-access, government (NASA, NIST, HSE), open-textbook, vendor and course material.
Pirated copies were not used. "None found" means no lawful free copy was found, not that none exists.

| Requested | Lawful source used | Read? |
|---|---|---|
| Åström & Hägglund, *PID Controllers* | Åström *Control System Design* Ch.6 (Caltech course page); Åström & Murray *Feedback Systems* (CC BY-NC-SA); MIT OCW 16.30 lec21/23 | yes |
| Ogata, *Modern Control Engineering* | none found; AM08 / MIT 16.30 cover the same ground | no (substitute) |
| Khalil, *Nonlinear Systems* | none found; AM08 §9.5, MIT 16.30 lec21 | no (substitute) |
| Bendat & Piersol, *Random Data* | J.O. Smith, *Spectral Audio Signal Processing* (CCRMA) | no (substitute) |
| MacDonald, *Noise and Fluctuations* | Milotti, "1/f noise: a pedagogical review" (arXiv physics/0204033); NIST SP 1065 | no (substitute) |
| Mandelbrot, *Fractals and Scaling in Finance* | Zhang et al. (arXiv 2310.19051); Clauset–Shalizi–Newman (arXiv 0706.1062) | no (substitute) |
| Tanenbaum, *Computer Networks* | Peterson & Davie, *Systems Approach* (CC BY 4.0) | no (substitute) |
| Bertsekas & Gallager, *Data Networks* | author-free at MIT (contents verified); Ch.3 equations **not read** | partly |
| Jane Liu, *Real-Time Systems* | Linux deadline-scheduler docs; Giacomossi et al. (arXiv 2604.19275, CC BY 4.0) | no (substitute) |
| Gross–Shortle–Thompson | Adan & Resing, *Queueing Systems* (TU Eindhoven) | no (substitute) |
| Incropera & DeWitt | Lienhard, *A Heat Transfer Textbook* (free, personal use) — contents only; Wikipedia "Biot number" | no (substitute) |
| Ellison; Lasance | Nexperia AN11261; eepower Foster/Cauer article; Raspberry Pi docs | no (substitute) |
| Wickens; Card–Moran–Newell; Sheridan & Ferrell | MIT 6.831 lec04 (CC BY-NC-SA); NASA CR-542; Hess 1997 (NASA-hosted); Bachelder et al. 2018; Kosinski & Cummings | no (substitute) |
| Hollifield; ISA-18.2; EEMUA 191; NAMUR NA 102 | HSE CHIS6; Siemens ISA-18 white paper; ASM Consortium/Honeywell; IChemE guide; Naghoosi et al.; Adnan et al. | no (substitute) |
| Stanton, *Human Factors Methods* | none found | no |
| Wald, *Sequential Analysis* | Wikipedia SPRT | no (substitute, thin) |
| Chen & Gupta | Truong–Oudre–Vayatis (arXiv 1801.00718); Basseville–Nikiforov is author-free but 403 from this network | substitute |
| Hastie–Tibshirani–Friedman, *ESL* | author-free PDF but 403 from this network; Hyndman & Athanasopoulos FPP3 for validation | ESL **not read** |
| Montgomery, *Intro to SQC* | NIST/SEMATECH e-Handbook §6.3 | no (substitute) |

## 4. Per-book verdicts

| Book | Verdict | Used for |
|---|---|---|
| Antoniou, *DSP* | **Strong.** Derivation-first; sampling, windows, quantisation, group delay. No Welch/Kalman. | sampling, resolution, noise floor |
| Giron-Sierra, *DSP with MATLAB* | **Strong on theory** (Wold, Gaussian conditioning, Gabor); MATLAB cookbook otherwise. | prediction, resolution |
| Dorf & Bishop, *Modern Control Systems* | **Strong** on feedback, margins, observers. Almost nothing on hysteresis/windup. | loops, observers, identification |
| Theraja, *Electrical Technology*; Bird | **Mixed.** Clear on first-order response and tempco; thin on device physics. | identification, physics |
| Hayt; Sadiku; EEE313/319 slides; 316 pptx | **Mixed.** Useful physical facts; static-field chapters irrelevant. | transduction, Friis, tempco |
| Griffiths | **Skipped by the user's choice** (scan; Hayt/Sadiku cover the same physics). | — |
| AI in Forecasting (CRC 2024) | **Mixed.** Baselines and vocabulary are sound; its MASE is wrong (defined as "mean absolute square error ×100"), evaluation is in-sample. | baseline ladder |
| Graph Databases (CRC 2024) | **Mostly irrelevant** (social media). Property-graph model, temporal hold-out survive. | relations |
| React and React Native, 5th ed. | **Mixed.** Keys, batching, threading lessons; "minimal diff" is a heuristic. | protocol rules |
| Living Computers (Brazma) | **Popular science.** Only the Eigen error threshold is derived. Mutual-information framing and von Neumann separation are useful; much is analogy. | "understood", Sensefile |
| ML for Industrial Applications | **Weak.** Poor paraphrased survey; zero hits for predictive maintenance/ARIMA/z-score. Only FPE/BIC parsimony and the time-split rule survive. | parsimony, validation |
| AI for Art Creation | **Weak for us.** Music/aesthetics. Grounding stages, post-hoc LLM rationalisation, show-the-learned-representation survive. | notes, explanation |
| Numerical Methods deck | **Unread** (181 slide images). | — |

## 5. Principles by package

Columns: ID · principle · source · tag · status · decision it drives (and where). Implementing package in brackets.

### 5.1 `eno/` — intake, sampling, timing

| ID | Principle | Source | Tag | Status | Drives |
|---|---|---|---|---|---|
| K-ant-alias | A tone above fs/2 appears at a wrong frequency (at fs it appears as DC). Aliasing cannot be detected from one record; the only operational test is re-measuring at higher rates. | Antoniou pp229-230, 356 | B | verified | the rate is a hypothesis: probe or spectral-tail test ⇒ `alias_suspect` flag [emem/spectral] |
| K-ant-sampling-thm | Sampling theorem: X(jω)=0 for │ω│≥ωs/2. | Antoniou pp294-296 | B | verified | as above |
| K-gir-alias-dc | Sampling a 3 Hz sine at 4 Hz gives a triangle; fs=f gives a constant. | Giron-Sierra pp22-25 | B | agent-read | alias test scenario `alias_tone` |
| K-ant-decimator | A decimator is a low-pass at ωs/2M then downsampling. Min/max decimation is an envelope operator, not a sample stream. | Antoniou §18.1-18.3 p832 | B | agent-read | two paths: min/max for the eye; anti-aliased for analysis [edimek vs emem] |
| K-ant-groupdelay | Causal smoothing has group delay τg=−dφ/dω; zero-phase filtering is non-causal and impossible live. | Antoniou pp252, 587 | B | verified (p252) | declare view-lag; show raw next to smoothed [edimek] |
| K-rfc3550-jitter | Jitter J += (│D│−J)/16 on D=(Rj−Sj)−(Ri−Si); a constant clock offset cancels. | RFC 3550 §6.4.1, App. A.8 | B | web-read | fast/slow jitter pair; ratio step flags change [eno/timing] |
| K-moon-skew | Skew from the lower-envelope line through (arrival − node timestamp) vs time; line = clock, excess = queueing. | Moon-Skelly-Towsley UMass TR 98-43 §5.1 | B | web-read | skew estimator [eno/timing] |
| K-rfc5905-offset | θ=½[(T2−T1)+(T3−T4)], δ=(T4−T1)−(T3−T2); symmetric path assumed; 100 ppm over 64 s = −6.4 ms. | RFC 5905 §8, §10 | B | web-read | offset caveat [eno/timing] |
| K-adan-littles | Little's law L=λW holds for any stable system. | Adan & Resing §3.4 p26 | B | web-read | ingest-queue sanity check [kufre/runtime] |
| K-adan-mm1 | M/M/1: mean sojourn 1/(μ(1−ρ)); S exponential, P(S>t)=e^(−μ(1−ρ)t); p99 ≈ 4.6× mean. | Adan & Resing (4.9), (4.13) | B/D | web-read | delay-shape class: floor + exponential excess = stable queue; rising p99/median ⇒ ρ→1 [eno/timing] |
| K-adan-pk | M/G/1 mean wait = ρE(R)/(1−ρ), E(R)=½(c²+1)E(B). Service variability multiplies delay. | Adan & Resing (7.14)-(7.16) | B | web-read | as above |
| K-ti-ble | BLE data delivered only at connection events; interval 7.5 ms–4 s in 1.25 ms steps; slave latency 0–499. | TI SWRU271I | B | web-read | detect the modal spacing, don't call it jitter [eno/timing] |
| K-oasis-qos | MQTT 3.1.1 QoS 1 has no retransmission timer; redelivery on reconnect with DUP=1. | OASIS §4.3.2, §4.4 | B | web-read | duplicate/late ⇒ TCP/reconnect, not the sensor [eno/ingest] |
| K-esp-modem | Modem sleep wakes per DTIM/listen interval; longer interval = slower response. | Espressif ESP-IDF low-power Wi-Fi guide | B | web-read | delay floor follows DTIM [eno/timing] |
| K-giac-latency | Stock Linux worst-case latency >9 ms at 250 Hz on Pi 5; PREEMPT_RT <225 µs. | Giacomossi et al., arXiv 2604.19275 | B | web-read | host loop lag as a signal; budget by worst case [kufre/runtime] |
| K-liu-edf | EDF feasible iff U≤1 (deadline=period); RM sufficient U≤n(2^(1/n)−1)→ln 2. | UPenn slides | B | web-read | render-deadline budget |
| K-clip | A clipped sensor makes estimators run open loop and wind up; censor clipped samples. | AM08 §10.4; Åström Ch.6 | B/D | web-read | `censored` flag; freeze EW update at the rail [eno/ingest, idea] |

### 5.2 `emem/` — noise and baseline

| ID | Principle | Source | Tag | Status | Drives |
|---|---|---|---|---|---|
| K-ant-quant-q2/12 | Quantisation noise is uniform on ±q/2, variance q²/12, white — while the signal is much larger than q. | Antoniou p638 | B | verified | floor σ at q/√12; surprisal on the quantisation-bin probability [idea/model] |
| K-ant-quant-breakdown | Below ~1 LSB the independence assumption fails (limit cycles, dead zones). | Antoniou pp651+ | B | agent-read | flat trace + 1-LSB blip must not read as a jump (scenario `quantised_blip`) |
| K-liv-shannon-hartley | Capacity ≈ ½log₂(1+S/N) bits per use; real bits per sample are set by the noise floor. | Living Computers pp181-183 | B | agent-read | report effective bits; don't store/display finer [emem/noise] |
| K-bird-loading | Meters and ADC inputs load the circuit; a high-impedance source biases readings and slows apparent τ. | Bird §10.11 pp118-119 | B | agent-read | note for thermistor/LDR nodes [calib] |
| K-sasp-welch | Periodogram is inconsistent (std≈mean at every bin); average frames: Ŝ=(1/K)ΣP_m, default M≈K≈√N, 50% Hann overlap. | J.O. Smith SASP | B | web-read | never threshold a single FFT [emem/noise] |
| K-welch-K8 | log-PSD std ≈ 4.34/√K dB; K≥8 gives ±1.5 dB. | derivation | D | unverified | K≥8 rule |
| K-sp1065-adev | Allan variance σ²(τ)=½⟨(ȳ_{k+1}−ȳ_k)²⟩; ADEV slope −½ white, 0 flicker, +½ random walk; the minimum is the optimal averaging time. | NIST SP 1065 §5.1 | B | web-read | **EW rate λ≈Δt/τ_min**; noise type from slope [emem/noise] |
| K-sp1065-lag1 | Lag-1 identification: fractionally integrated noise has ρ₁=δ/(1−δ), so δ=r₁/(1+r₁); stationary iff δ<½. | NIST SP 1065 §5.5 (OCR-garbled) | B/K | web-read | cheap online noise-type test, no FFT [emem/noise] |
| K-milotti-1f | Uniformly distributed relaxation rates give 1/f; power is equal per decade; no flattening over 6 decades observed. | Milotti §2-5 | B | web-read | wandering is normal; "stationary mean" is relative to the window |
| K-fgn-memory | Var(mean of n)=σ²n^(2H−2); as H→1 averaging barely helps. | Zhang et al.; derivation | K/D | web-read | note on estimator limits |
| K-hill | Power-law tail MLE α̂=1+n/Σln(x/x_min); σ is a stable scale only if α>3. | Clauset–Shalizi–Newman eq 3.1 | B | web-read | α̂<3 ⇒ MAD/quantile thresholds, clipped innovations [emem/noise] |
| K-flicker-claim | **A mean±3σ band calibrated on an initial window is exceeded 4.45% of the time on 1/f noise (seeds 0.21%–20.5%), 1.68% with a 10⁴ window; white control 0.29%.** | `bench/claims.py` | **S, reproduced** | verified by us | σ for flicker signals comes from ADEV at the alarm timescale or a detrended residual [akpaneka/detect] |
| K-coherence | Magnitude-squared coherence C=│Gxy│²/(GxxGyy); with K=1 frame C≡1; null threshold 1−0.05^{1/(K−1)}. | Wikipedia; Carter-Knapp-Nuttall | B/K | web-read | "shared content" only at K≥10 and above the null [emem/calib] |
| K-ant-resolution | DFT resolution Δω=ωs/N; rectangular main-lobe width 2π/τ (inversely ∝ window length), ripple −13.26 dB regardless of length. | Antoniou §7.8 pp337-356 | B | verified (+1 page) | period resolution ≈ P²/T; "cycles needed" follows from resolution and SNR, not a fixed 3 [emem/spectral] |
| K-gir-gabor-heisenberg | Gabor/Heisenberg: σt·σΩ≥½; Δf·Δt≥1 for cycle counting; the STFT window trades time against frequency resolution. | Giron-Sierra pp359-369 | B | verified | replaces the "≥3 cycles" rule; non-stationary signals need STFT [emem/spectral] |
| K-ant-psd-definition | PSD S(ω)=lim E│X_T₀│²/2T₀; area under S equals mean power r(0); WSS defined; white noise has flat S and r=Kδ. | Antoniou §13 pp604-605, 609 | B | verified | spectral definitions [emem/noise] |
| K-ant-wiener-khinchine | Wiener–Khinchine: S(ω)=F{r(τ)}. | Antoniou (13.16) p608 | B | verified | autocorrelation route to the spectrum [emem/spectral] |

### 5.3 `idea/` — prediction, surprise, identification

| ID | Principle | Source | Tag | Status | Drives |
|---|---|---|---|---|---|
| K-gir-wold | Wold: a covariance-stationary process = deterministic part + MA(∞) of white innovations. The innovation is the only defensible "surprise". | Giron-Sierra pp158-159 | B | verified | surprise = standardised innovation [idea/model] |
| K-gir-gauss-conditioning | Gaussian conditioning: mean=μ₁+Σ₁₂Σ₂₂⁻¹(x₂−μ₂), cov=Σ₁₁−Σ₁₂Σ₂₂⁻¹Σ₂₁ — this is the Kalman update. | Giron-Sierra p155 | B | agent-read | Kalman core [idea/model] |
| K-dor-observer | Observer x̂′=Ax̂+Bu+L(y−Cx̂); error dynamics e′=(A−LC)e; L places poles iff observable. | Dorf pp847-850 | B | verified | innovation = y−Cx̂ [idea/model] |
| K-dor-observability | Observability rank test rank[C;CA;…;CAⁿ⁻¹]=n. | Dorf p839 | B | verified | "can this sense inform that quantity at all?" [kufre/relate] |
| K-fc-baselines | Baseline ladder: naive, SMA, SES (F=F+α(D−F)), Holt, Holt-Winters, ARIMA. Seasonal naive added from standard practice. | AI-Forecasting Ch1 p4, Ch5, Ch13 | B | agent-read | predictor ladder; every rung must beat naive [idea/model] |
| K-fc-mase | The book's MASE definition is wrong; correct MASE = MAE / in-sample naive MAE. MAPE explodes near 0. | AI-Forecasting Ch5 §5; standard | B(error)/D | agent-read | online skill ratio = EW│e_model│/EW│e_naive│ |
| K-mli-FPE-BIC | Parsimony: AIC=−2L+2d, BIC=−2L+d ln N, FPE=(1/N)Σe²·(1+d/N)/(1−d/N). | ML-Industrial pp136-137 | B | verified | penalise rungs; with N≈100 and AR order p the factor matters [idea/model] |
| K-mli-timesplit | Never split time series randomly; rolling window, training earlier than test. | ML-Industrial p131 | B | verified | prequential evaluation [idea/model] |
| K-fpp3-rolling | Rolling forecasting origin; hold out ~20%. | FPP3 §5.10, §5.8 | B | web-read | evaluation protocol |
| K-fpp3-ljungbox | Ljung-Box Q*=T(T+2)Σr_k²/(T−k), ℓ=10 or T/5; dof = ℓ − fitted params. | FPP3 §5.4 | B | web-read | innovation whiteness check before charting [akpaneka/detect] |
| K-dor-freq-ident | A −20 dB/decade slope with −45° at the corner identifies a first-order system and its time constant. | Dorf §8.3 p577 | B | agent-read | identification by probing (later) |
| K-ther-firstorder | First-order step: v=V(1−e^(−t/τ)), τ=RC (Ch5) or L/R (Ch22); 63.2% at τ; initial slope V/τ. | Theraja Ch5 pp239-242, Ch22 pp818-820; Bird Ch17 pp259-263 | B | agent-read; Bird verified | τ=−T/ln a from the fitted pole [idea/ident] |
| K-ther-nolag | "No transients in pure resistive circuits": only stored energy makes a lag. A lag-free step ⇒ resistive/photonic transducer. | Theraja Ch22 §22.1 p816 | B | agent-read | `lag_class` instant vs first-order [idea/ident] |
| K-bird-transient | RC/RL transients: reaches 63.2% in τ and ≈99.3% in 5τ; 0.918 of final value at 2.5τ. | Bird Ch17 pp259-263 | B | verified | τ from step events; settling time 5τ [idea/ident] |
| K-ther-damping | Overshoot/ringing ⇒ second order; monotone approach ⇒ first order. | Theraja §10.6, §22.3 | B | agent-read | ζ from AR(2) roots |
| K-ident-excitation | Identification needs excitation; without a step/change the result is "unexcited", never a guess. | Ljung (persistent excitation) | K | unverified | report "unexcited" [idea/ident] |

### 5.4 `akpaneka/` — detection, alarms, action

| ID | Principle | Source | Tag | Status | Drives |
|---|---|---|---|---|---|
| K-nist-cusum | CUSUM S⁺=max(0,S⁺+x−μ₀−k), signal when >h; k=δσ/2; h≈4–5σ. | NIST e-Handbook 6.3.2.3 | B | web-read | detector [akpaneka/detect] |
| K-siegmund | One-sided ARL₀ ≈ [e^{−2Δb}−1+2Δb]/(2Δ²), b=h+1.166. **Reproduced: h=4→338, h=5→938 vs NIST 336/930.** NIST's table text misdescribes its own columns. | `bench/claims.py`; NIST pmc3231 | **S, reproduced** | verified by us | h from a target ARL₀ [akpaneka/detect] |
| K-cusum-raw-collapse | **Raw-data CUSUM collapses on autocorrelated data: in-control ARL 477 (φ=0) → 50 (φ=0.5) → 32 (φ=0.9); on standardised innovations 477/477/473.** | `bench/claims.py` | **S, reproduced** | verified by us | always chart innovations [akpaneka/detect] |
| K-karaoglan-residual | Residual charts detect mean shifts poorly on positively autocorrelated data: a step shows as only δ(1−φ) because the predictor absorbs it. | Karaoğlan 2010 (citing Harris-Ross, Wardell et al.) | B/D | web-read | **plus a frozen-baseline detector** (recent mean+spectrum vs stored baseline) [akpaneka/detect] |
| K-nist-ewma | EWMA z=λx+(1−λ)z; limits ±L·s·√(λ/(2−λ)), L=3, λ 0.2–0.3; assumes independent normal data. | NIST 6.3.2.4 | B | web-read | alternative detector |
| K-truong-pelt | Offline: PELT exact for a linear penalty, O(T) with random regime lengths; BIC penalty; models assume independent noise. | Truong et al. §5.1.2 | B | web-read | localise the change after an alarm, on innovations [akpaneka/detect] |
| K-hse-rates | Long-term alarm rate ≤1 per 10 min; ≤10 in the first 10 min after an upset. | HSE CHIS6 p1 (citing EEMUA 191) | B | web-read | S3 budget [akpaneka/alarm] |
| K-siemens-table5 | Acceptable 1–2 per 10 min per position; ≤10 in any 10 min; <1% of 10-min periods may exceed 10; chattering and fleeting alarms target 0; stale <5/day; priorities ~5/15/80%. | Siemens ISA-18 WP Table 5 | B | web-read | S3 gate [akpaneka/alarm] |
| K-siemens-table2 | Starting deadband (% of range) and on/off delay: flow 5%/15 s, level 5%/60 s, pressure 2%/15 s, temperature 1%/60 s. Process-plant values. | Siemens Table 2; Naghoosi Table 1 | B | web-read | **defaults to calibrate, not constants** [akpaneka/alarm] |
| K-naghoosi-roc | Optimal threshold/deadband is the ROC point closest to the origin **assuming equal costs**. | Naghoosi et al. ACC 2011 | B | web-read | use consequence-weighted costs where known |
| K-adnan-delay | Expected detection delay E(DD)=q₁/q₂ samples (i.i.d.); delay timers trade FAR/MAR for delay. | Adnan et al. ACC 2011 §III-V | B | web-read | on/off-delay design [akpaneka/alarm] |
| K-siemens-rationalise | Each alarm must justify itself: consequence and time-to-respond set priority. | Siemens §4.2 p6 | B | web-read | **a watch exists only if a declared use follows it** [akpaneka/alarm] |
| K-dor-S+C | Loop gain L=GcG gives sensitivity S=1/(1+L) and complementary sensitivity C=L/(1+L), S+C=1: disturbance rejection and noise attenuation cannot both be had at one frequency. | Dorf §4.5-4.8 pp237-238 | B | verified | every adaptive gain (EW rate, auto-range speed, watch threshold) is chosen with this trade-off [idea, akpaneka, edimek] |
| K-dor-gain-phase-margin | Gain margin 1/│L(jω)│ at φ=−180°; a pure delay adds phase −ωT and no magnitude change. | Dorf §9.4 pp655, 668 | B | verified | loop delay (sampling + filter + render) must leave phase margin [edimek/view_rules] |
| K-ast-windup | When the actuator/sensor saturates the loop runs open; integral winds up. Back-calculation: I += k_i·h·e + (h/T_t)(sat(v)−v), T_d<T_t<T_i, T_t=√(T_i·T_d). | AM08 §10.4 Eq 10.16; Åström Ch.6 pp226-231 | B | web-read | anti-windup in EW estimators; conditional integration at a rail [idea] |
| K-am08-relay | Relay with hysteresis c: silent for amplitude ≤c; phase lag arcsin(c/a); limit cycles persist, only amplitude/frequency change. Describing function is approximate. | AM08 §9.5 Ex.9.11; MIT 16.30 lec21 | B | web-read | hysteresis ≥ noise peak, with a stated delay [edimek axis loop, akpaneka/alarm] |

### 5.5 `kufre/` — self, relations, thermal, efficiency

| ID | Principle | Source | Tag | Status | Drives |
|---|---|---|---|---|---|
| K-liv-mdl | Information is relative to an interpreter; Kolmogorov complexity is uncomputable, so estimate by compression; "understood" = code-length gain conditional on what is already known. MDL framing is ours. | Living Computers pp33-34, 175-179 | B / MDL=FP | agent-read | `unmodelled` / `described` [kufre/mind] |
| K-liv-mutual-info | Kolmogorov's remedy for "information of x about y" is mutual information; random strings have maximal Shannon information and no value. | Living Computers pp175-177 | B | verified (+1 page) | edge strength = MI, not correlation; surprise × value [kufre/relate] |
| K-liv-vonneumann | Machine = constructor U + copier R + controller C + code; the description is interpreted *and* blindly copied; replicators need a host interpreter. | Living Computers pp7-13 | B | agent-read | Sensefile = description; pull = hash-checked blind copy; declare the interpreter version [later] |
| K-liv-error-threshold | Q=(1−u)^L must exceed 1/f ⇒ u≲1/L; per-bit error <1/n to carry n bits. Single-peak landscape, fixed length. | Living Computers pp128-132 | B | verified (+1 page) | lossy re-propagated state needs anchoring to a signed master [kufre/persist] |
| K-liv-gold | Gold's theorem: no algorithm learns every language from finite examples; the class must be restricted a priori. | Living Computers pp213-215 | B | verified (+1 page) | declare the hypothesis class; if nothing fits, `unmodelled` [idea] |
| K-gdb-lpg | Labeled property graph: nodes and edges carry properties; a many-to-many join becomes an edge with properties. | Graph-DB Ch2 §2.2, Ch8 §8.3 | B | agent-read | typed graph; lag/strength/n on the edge [kufre/relate] |
| K-gdb-holdout | Evaluate inferred edges by a temporal hold-out: fit at t₁, judge on t₂. | Graph-DB Ch2 §2.3.1 | B | agent-read | edge promotion [kufre/relate] |
| K-granger | Granger causality = predictive improvement; equals transfer entropy for Gaussian signals. "predicts", never "causes". | Barnett-Barrett-Seth 2009 | K | unverified | edge naming and test (`common_cause`) |
| K-thermal-lumped | C dT/dt = P−(T−Tₐ)/R_th, τ=R_th·C_th; valid for Bi<0.1 (<3% error). | Wikipedia "Biot number" | B (secondary) | web-read | host thermal model [kufre/thermal] |
| K-nexperia-foster | Foster models are curve fits (R,C have no location); Cauer models have physical nodes; fits can split a term into near-equal τ. | Nexperia AN11261 §5; eepower | B | web-read | 2-term Foster, τ's ≥5× apart, reject near-equal [kufre/thermal] |
| K-rpi-throttle | Pi: throttling progressive 80–85 °C, hard limit 85 °C; **Pi 4 has no soft limit** (60 °C is Pi 3B+); Pi 5 fan 50/60/67.5/75 °C. | Raspberry Pi documentation | B | web-read | exclude throttled samples from RC fit |
| K-rpi-getthrottled | `vcgencmd get_throttled`: 0x1 undervoltage, 0x2 freq capped, 0x4 throttled, 0x8 soft limit; 16–19 = has occurred. | Raspberry Pi OS docs | B | web-read | censoring flags [kufre/thermal] |
| K-rpi-tau | Pi 5 unfanned throttles at ≈200 s ⇒ τ≈100 s (rough). A Pi 4 value needs the user's own log. | RPi Pi 5 article; derivation | D | web-read | expectation only |
| K-governor-bandit | Without exploration a dropped model can never prove it became useful after a regime change. | design | FP | unverified | governor re-trials after every regime change [kufre/governor] |

### 5.6 `edimek/` — surface, human, explanation

| ID | Principle | Source | Tag | Status | Drives |
|---|---|---|---|---|---|
| K-kosinski-rt | Simple visual RT ≈190 ms (sound 160, touch 155); choice RT ∝ log N (Hick); recognition ~+40 ms/item. | Kosinski & Cummings App. C | B | web-read | event latency budget |
| K-mit831-cycle | Perceptual cycle Tp≈100 ms (50–200); closed-loop Tp+Tc+Tm≈240 ms; events <Tp apart fuse. | MIT 6.831 lec04 | B | web-read | S2 budget; updates >~10 Hz add nothing to a human follower [FP] |
| K-hess-crossover | Human as controller: Y_pY_c≈ω_c e^{−τ_e s}/s near crossover; τ_e≥0.2 s; ω_c≈1.7–2 rad/s. | Hess 1997; NASA CR-542 | B | web-read | live-follow content limit ≈0.15–0.3 Hz |
| K-bachelder-pulsive | Operators act as pulsive controllers with a threshold and a consistent delay. | Bachelder et al. 2018 | B | web-read | display deadband/delay should mirror the human's |
| K-three-rules | **The ≈0.2–0.3 Hz limit governs following the live value, not reading history.** Three separate rules: (1) history/pattern — min/max to pixel columns, window from period and resolution; (2) live-follow — readout/pointer track content only up to the human band, faster shows as level/band; (3) animation — scroll at display refresh, information coalesced ≤10 Hz. | v4 correction | FP | unverified | `edimek/view_rules` |
| K-art-grounding | Explanations should state that something happened, what kind, and why. | AI-Art Ch1 pp7-9 | B | verified | every note has kind + stat [akpaneka/notes] |
| K-art-posthoc-LLM | An LLM asked "why" gives a rationalisation, not an account of the model's workings. | AI-Art Ch1 p9 | B | verified | LLM only verbalises computed statistics; never sees raw data [edimek/explain] |
| K-art-envelope-layer | Show the learned representation, with brightness for data support; show uncertainty. | AI-Art Ch1 pp12-14, 20 | B | agent-read | learned-normal band, opacity by support [edimek/render] |
| K-art-distribution | Report a distribution, not one score; skewed data: median and tail flags. | AI-Art Ch13 pp321, 327-329 | B | agent-read | median/MAD/tail flag in the envelope |
| K-react-keys | React's diff assumes (1) different element types ⇒ rebuild; (2) keys identify stable children. Stable slot id = key. | React Ch1-2, Ch20; React docs | B/K | agent-read | slot id = key; lens change = re-mount [edimek] |
| K-react-batching | Several state updates in one tick coalesce into one render; transitions mark low-priority updates. | React Ch10 | B | agent-read | coalesce per slot ≤10-15 Hz keeping latest |
| K-rn-threads | Keep per-sample work off the input thread; pass values not trees. | React Native Ch16, Ch26 | B | agent-read | numeric values for hot slots; canvas for traces |

### 5.7 Physics of signals (feeds `idea/` identification and `kufre/needs`)

| ID | Principle | Source | Tag | Status |
|---|---|---|---|---|
| K-ther-tempco | R_t=R₀(1+α₀t); copper α₀=0.00427/°C; carbon/semiconductors/insulators negative α. | Theraja §1.10-1.11 pp11-12 | B | agent-read |
| K-hayt-sigma-temp | Silicon σ rises ×10 from 300→330 K; metals do the opposite. | Hayt §5.6 p137 | B | agent-read |
| K-bird-battery | V=E−Ir; r=(E−V)/I; effective capacity falls with discharge current. | Bird §4.6, §4.9 pp34, 39 | B | agent-read |
| K-ther-diode | I=I₀(e^{V/ηV_T}−1); I₀ doubles per 10 °C; forward-voltage tempco ≈ −2 mV/°C. | Theraja Ch52; tempco is ours | B / FP | agent-read |
| K-hayt-faraday | emf=−dΦ/dt: induction sensors respond to a derivative and are zero-mean AC. | Hayt §10.1 p323 | B | agent-read |
| K-sad-friis | Friis: P_r=G_t G_r(λ/4πr)²P_t, far field r>2d²/λ; 6 dB per doubling; λ=12.5 cm at 2.4 GHz. | Sadiku §13.8 pp622-623 | B | agent-read |
| K-ther-crest | RMS, form factor 1.11 and crest factor √2 for a sine; harmonic symmetry separates waveform shapes. | Theraja §11.13-11.19 | B | agent-read |
| K-ther-runaway | Thermal runaway is positive feedback: heat→leakage→current→heat. | Bird §12.9 p158 | B | agent-read |
| K-noise-johnson | Johnson v²=4kTRΔf; shot i²=2qIΔf; flicker 1/f. | standard; Sadiku gives k | K | unverified |

### 5.8 Lessons measured while building the M1 skeleton

| ID | Finding | Evidence | Tag | Status | Drives |
|---|---|---|---|---|---|
| K-burst-resample | **Bursty arrivals can freeze the daemon.** A WebSocket batch lands within ~1 ms, so the median sample interval is microscopic; `_resample` then built a grid of hundreds of thousands of points and the autocorrelation search is O(n²). A flood test hung for >40 s. | `tests/test_hardening.py`; stack dump in `_refresh → _period_once` | S | verified by us | cap the resample grid at 2×WINDOW (no-op for regular data); time-sliced drain; quarantine signals whose ingest is slow [idea/envelope, kufre/runtime] |
| K-arrival-time | Arrival time is a poor timestamp for batched sources: samples in one packet share a timestamp. | same hang; K-rfc3550-jitter | S/D | verified by us | node timestamps + skew correction in M2 [eno/timing] |
| K-cascade-clocks | **Two cascaded 10 Hz clocks (render, then per-surface patch timer) gave sensor→pixel p50 134 ms / p95 209 ms — S2 failed.** One patch clock (render dirty focus panels at the tick, then wake all surfaces) gave **p50 66 / p95 102 / p99 112 ms** on loopback. | `bench/skeleton_soak.py` | S | verified by us | exactly one coalescing stage between sample and pixel [kufre/runtime, eno/transport] |
| K-soak-memory | **Memory.** 30-min soak with default 4096-sample rings: +6.2% after a 5-min warm-up (fails the 5% bar), 28.8 → 34.0 MB. 20-min leak test with 128-sample rings (every buffer full within ~2 min), growth measured after 8 min: **0.0%** (plateau 32.6–33.6 MB). The plateau is close to the default-ring figure, so part of the first +6.2% is probably allocator/cache warm-up, not only buffer fill. Definitive default-ring check: the 24 h Pi soak (M7). | `bench/soak_m1_default_ring.json`, `bench/soak_m1.json` | S | verified by us (PC, loopback, simulated phone) | no leak once buffers are full; ring size is configurable (`--ring`); an unbounded-names path (new-signal cap 256) and the narration list were also bounded [kufre/runtime, kufre/mind] |
| K-ws-interleave | RFC 6455 §5.4: control frames (ping) may arrive between the fragments of a message; the partial message must survive the interruption. A first implementation lost it. | `tests/test_wsproto.py` | K | verified by us (test) | fragment state kept on the reader [eno/wsproto] |
| K-ingest-cost | The "O(1) per sample" claim is false for slice 1: `_refresh` costs O(n²/3) every 16 samples. Measured 74 µs (simple scalar) to ~350 µs (mixed demo load) per sample on this PC; a Pi 4 is plausibly 5–10× slower (projection, **[FP]**), i.e. a few hundred samples/s in total. | `bench/run.py` perf; flood drain timing | S (PC) / FP (Pi) | verified by us (PC) | M3: incremental estimators (recursive, not windowed re-computation); compute governor [idea, kufre/governor] |
| K-ws-security | A browser can be driven by a hostile page to open a WebSocket to localhost or the LAN (cross-site hijacking); defences: pairing token (constant-time compare), Origin must equal Host, localhost bind by default, caps on frame/batch/name/rate/connections. | `tests/test_runtime.py` | K | verified by us (test) | transport posture [eno/transport] |
| K-svg-in-img | An SVG shown through `<img>` cannot run script, so a hostile string inside a note can never execute; sensor-supplied names go to the DOM via `textContent` only. | `edimek/web/phone.html` | K | unverified | surface safety |

## 6. Physical-signatures table (the basis of the S1 evaluation set)

Each row is a class in the frozen 180-case set (`bench/scenarios.py: signature()`: 12 classes × 5 seeds × 3 noise
levels). Cells marked [B] have a source above; the rest are [FP]/[K] and are treated as priors to calibrate.

| Class | Rate / range | τ and shape | Noise | Source mix |
|---|---|---|---|---|
| temperature (NTC/RTD) | ≤1 Hz; −40…125 °C | τ≈1–60 s in air; exponential, no overshoot | white + quantisation | exponential [B]; magnitudes [FP] |
| light (LDR) | ≤10 Hz; MΩ dark to 1–100 kΩ lit, log in lux | slow, asymmetric | thermal + 1/f | range [B]; speed [FP] |
| light (photodiode) | up to MHz; linear | ns step; instant | shot | [B] Theraja Ch53 |
| battery | ≤0.1 Hz; Li-ion ≈3.0–4.2 V | plateau then knee; instant sag ΔV=I·r | low | V=E−Ir [B]; Li-ion range [FP] |
| switch / door | event-driven; two levels | edges with ms bounce; long dwell | none between edges | [B] no-transient; bounce [FP] |
| accelerometer | 50 Hz–kHz; ±2–16 g | rest │a│≈1 g; ringing if underdamped | white | damping [B]; gravity [FP] |
| microphone (level feature) | 20 Hz features; ≥0 | bursty | thermal | [FP]; raw audio is class P3 |
| RSSI | 1–10 Hz; −100…−30 dBm | slow roll-off + fading dips | log-normal-ish | Friis [B]; indoor exponent [FP] |
| current / power | DC or 50 Hz | steps; inrush decays τ=L/R | mains pickup | RMS/crest, L/R [B] |
| humidity | ≤0.1 Hz; 0–100 % | τ 5–60 s; saturates | low | [FP] |
| distance (ToF) | 10–50 Hz; cm–m | piecewise smooth, jumps, dropouts | timer quantisation | r=ct/2 [B] |
| host CPU temperature | slow; 30–85 °C | first-order lag to load; throttle clamp | low | Joule [B]; τ [FP] |

## 7. Threat model, privacy and trust

**Assets:** the human's attention; the integrity of labels and actions; privacy of people near sensors; SUFD's host.
**Adversaries:** a rogue or spoofed node; a compromised Wi-Fi/MQTT segment; sensor-supplied strings (injection into
UI or an LLM); a curious second surface; accidental bystander capture.

**Trust states per node:** `untrusted` → `paired` → `attested` (Ed25519 device keys, nonce-bound — reuse EGIS ADR-008).
- Untrusted senses may be *displayed* but never raise high-priority alarms and never drive actions.
- Sensor-supplied names/strings are data: escaped in HTML, never concatenated into an LLM prompt.

**Privacy classes** (a new unlabelled sense defaults to P2):

| Class | Examples | Raw ring | Compressed tier | Summaries | Surface / LLM |
|---|---|---|---|---|---|
| P0 device health | CPU, loop lag, battery, RSSI of SUFD's own links | minutes | days | forever | any granted surface; LLM may read the envelope |
| P1 environment | temperature, humidity, light, pressure | minutes | days | forever | any granted surface; LLM may read the envelope |
| P2 presence/behaviour | door, motion, worn/carried IMU, RSSI of other people's devices | ≤60 s | hours, reduced resolution | forever, aggregated | explicit grant per surface; LLM only with a grant |
| P3 content | microphone audio, camera, text, keystrokes | **never** (features at source: level only) | features only | features only | never leaves the device; LLM never |

**Bystander rule:** when a P2 or P3 sense is active the surface shows a visible sensing indicator; each sense has a
one-tap kill switch; nothing from them persists beyond the raw ring unless the owner confirms the sense and class.

**Actions** are gated by eight interlocks (trust, confirmed, fresh-and-modelled, uncensored, observable effect,
reversible and rate-limited, veto window, flood guard) and a global kill switch. See plan §6 M4.

## 8. Corrections to earlier statements (changelog)

1. Pi 4 has **no** soft limit; 60 °C is Pi 3B+ only. (Earlier text implied 60/80 for Pi 4.)
2. Lumped-capacitance validity is Bi<0.1 for **<3%** error (earlier: 5%).
3. **CUSUM on innovations alone is not enough** — a mean shift appears as δ(1−φ) because the predictor absorbs it.
   Add a frozen-baseline detector (K-karaoglan-residual).
4. NIST's CUSUM ARL table text misdescribes its own columns; the Siegmund formula is correct and reproduced.
5. Slice-1 doc claimed a "1-LSB blip reads as a 99× jump". **Actually slice 1 misclassifies a flat quantised sensor
   with one blip as binary** and reports "changed to 21.51". (Found by `bench/run.py`; the first metric hid it.)
6. The human-bandwidth limit (≈0.2–0.3 Hz) applies to following a live value, **not** to reading a chart of history
   (K-three-rules).
7. Process-plant alarm numbers are defaults to calibrate, not constants (K-siemens-table2).
8. "ROC point nearest the origin" assumes equal miss and false-alarm costs (K-naghoosi-roc).

9. **First measured S2 failed** (p95 209 ms against 150 ms) because of two cascaded 10 Hz clocks; fixed to p95 102 ms (K-cascade-clocks).
10. **A burst of samples could hang the daemon** through unbounded resampling (K-burst-resample); the slice-1 estimator's
    "O(1) per sample" claim was wrong (K-ingest-cost).

## 9. Reproduced claims (`python bench/claims.py`)

| Claim | Agent's number | Our reproduction |
|---|---|---|
| mean±3σ on 1/f, 1000-sample calibration | 6.2% (0.9–17%) | **4.45%** (0.21–20.5%) |
| same, 10⁴-sample calibration | 1.8% (0.4–6.4%) | **1.68%** (0.0–8.7%) |
| white-noise control | 0.27% | **0.29%** |
| CUSUM k=0.5,h=5, raw AR(1) φ=0.5 / 0.9 | 56 / 29 | **50 / 32** (innovations 477 / 473) |
| Siegmund ARL₀ h=4 / h=5 | 336 / 930 (NIST) | **338 / 938** |

The 1/f figures depend on the generator and swing 0–20% across seeds; the qualitative result (far above nominal,
not fixed by learning longer) is robust.

## 10. Slice-1 baseline (the measured starting point)

From `bench/run.py --baseline`: **7 of 22 gates pass** on the 20+ scenarios and the 180-case set.

| Finding | Number |
|---|---|
| S1 signature top-1 / top-3 (fixed 180-case set) | **0.333 / 0.417** (gate: 0.80 / 0.95) |
| 1/f exceedance of a requested "3σ" watch band (20 seeds) | **2.39%** mean, 9.0% worst (nominal 0.27%) |
| white-noise exceedance of the same band | **0.0%** — the band is ±8.8σ because the spread is floored at 3×noise: too wide, real shifts are missed |
| 1σ mean shift detected | **never** (the watch is not a change detector) |
| correlated (φ=0.9) mean shift detected | **never** |
| flat quantised sensor + 1-LSB blip | classified **binary**; reports "changed to …" |
| white noise reported `unmodelled` | **no** (state does not exist) |
| random-input fuzz (2000 inputs) | **1278 unhandled exceptions** (64%) |
| hostile fixture | 6 exceptions |
| CPU on this PC under the demo load | 0.78% of one core (passes) |
| period, ramp/sine false jumps, chatter | pass |
| error bars, τ/ζ, alias flag, PIT, jitter/skew | **not implemented** |

## 11. Citation verification log

`bench/verify_citations.py` extracts the printed page ±1 and checks key terms (not equations). To re-run it, set
`SUFD_LECTURE_NOTES` and `SUFD_DOWNLOADS` to the folders that hold your copies of the PDFs (they are copyrighted and
not in this repository); it refuses to overwrite the recorded log from a partial run.
**21 of 21 [B] items that drive a design decision verified** — 17 on the cited page, 4 one page off (K-ant-resolution,
and Living Computers K-liv-mutual-info, K-liv-error-threshold, K-liv-gold, whose offset is +16 not +15). Details and
the machine-readable log: `bench/citations_log.json`. `tests/test_traceability.py` enforces that every logged
citation has a row here, every row marked "verified" has a log entry, IDs are unique, and every row carries a tag.

A first run flagged Antoniou's Wiener–Khinchine page as not found; the check had been too strict (it needed the PSD
definition and the theorem on the same pages). The theorem is on p608 and the PSD definition on p605; both verified.

Items **not** verified by us (agent-read or web-read) are marked as such in the tables; treat them as reliable
pointers, not quotations.

## 12. Unread and open

**Unread** (no lawful free copy or unreadable here — the user may supply local copies): Ogata, Khalil,
Åström & Hägglund (the book), Sheridan & Ferrell, Wickens, Card–Moran–Newell, Stanton, Hollifield, ISA-18.2 /
EEMUA 191 / NAMUR NA 102 (paid), Bendat & Piersol, MacDonald, Mandelbrot, Wald, Chen & Gupta, Montgomery,
Tanenbaum, Liu, Gross, Incropera, Ellison, Lasance, Welch 1967, Bertsekas Ch.3 equations; Basseville–Nikiforov and
ESL (author-free but 403 from this network); Griffiths, EEE319 carrier-transport, Numerical Methods deck (images).

**Open gaps** (no source found): fully verified 802.11 delay-tail exponent and retry limits; Bluetooth Core timing;
a fitted τ for a real Pi 4 (needs a 1 Hz log under a load step — `bench/record.py` runs on the Pi); smooth-pursuit
and display-update limits for humans (the 10 Hz and 0.15–0.3 Hz figures are [FP]); dead-zone describing-function
closed forms; alarm-threshold quantile theory for non-Gaussian autocorrelated data (the per-sample n-sample on-delay
estimate is our derivation); ESP32/ESP32-C3 on-chip temperature sensor behaviour [K — verify in Espressif docs at M2].

**Reading list to close the gaps lawfully:** Hyndman & Athanasopoulos *FPP3* (free); Basseville & Nikiforov
(author-free, IRISA); Cleveland *Elements of Graphing Data*; Endsley (situation awareness); ISA-18.2/EEMUA 191;
Ljung *System Identification*.
