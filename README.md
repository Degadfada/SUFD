# SUFD

**The unit of an interface is the signal, not the app.**

SUFD reads any signal in real time, works out what it is, and generates the visual a human can follow it with. SUFD follows the same signal beside them, at machine speed, while the human follows at human speed. The interface is the transducer between the two.

Plug in a sensor nobody has written a screen for. SUFD notices it, describes its behaviour, asks what it is once, puts it to use, and shows you what it sees, with the reason for every note.

```
 source ──► Signal ──► Envelope ──► Lens ──► Surface ──► human
              ▲            │          ▲                    │
              │            ▼          │                    │ points / asks
              │        surprise ──► Follow ◄───────────────┘
              │            │
              └── Self ◄───┘      SUFD reads itself with the same loop
```

> **Status: slice 1, a direction and not a product.** The pipeline works end to end on simulated and recorded signals. Live streaming, real hardware and the language layer are not built. The scoreboard below reports where the current build still fails.

## Try it

Zero dependencies: stdlib only, Python ≥ 3.9.

```bash
python demo.py            # first contact with a simulated, unlabeled ESP32 heat sensor → out/demo.html
python -m pytest -q       # 77 tests
python bench/run.py       # score the build against the numeric gates → bench/scoreboard.md

python -m sufd serve --sim                  # the daemon + phone surface on http://127.0.0.1:8810 (prints the URL)
python -m sufd serve --host 0.0.0.0         # reachable from your phone on the LAN (prints a URL with a pairing token)
python bench/skeleton_soak.py --minutes 30  # separate client process, measured sensor→pixel latency, memory, errors
```

The phone page streams the phone's own senses (link round-trip time always; motion, battery and network where the
browser exposes them, which on plain `http://` LAN pages often means only the link signal) and shows SUFD's panels.
Tap a chart to point at a moment; SUFD answers from the envelope.

Open `out/demo.html`. At t=60 s an unlabeled ESP32 channel joins. By t≈92 s SUFD has described it. At t=100 s the human confirms "temperature sensor". At t=200 s a heater turns on and SUFD flags it before anyone asks. The page shows each moment, SUFD's narration, the human pointing at an event, SUFD's own vitals rendered by the same pipeline, and where the human's attention budget goes.

## The five nouns

| Noun | What it is | Code |
|---|---|---|
| **Signal** | A named source of `(t, value)` samples with unknown meaning | [eno/signal.py](sufd/eno/signal.py) |
| **Envelope** | What SUFD has *learned*: kind, range, rate, noise, drift, period, surprise. It is online, inspectable and always updating | [idea/envelope.py](sufd/idea/envelope.py) |
| **Lens** | A visual encoding chosen *from the envelope*: mark, scale, window, decimation | [edimek/lens.py](sufd/edimek/lens.py), [edimek/render.py](sufd/edimek/render.py) |
| **Follow** | Shared attention: SUFD's "now", its notes with reasons, and the human's pointer | [akpaneka/notes.py](sufd/akpaneka/notes.py), [edimek/follow.py](sufd/edimek/follow.py) |
| **Self** | SUFD's own metrics fed through the same pipeline, plus the ledger of every sense it has met | [kufre/mind.py](sufd/kufre/mind.py) |

SUFD has no separate self-monitoring subsystem. Its CPU load and a new ESP32 heat sensor go through identical code.

## Design commitments

- **The real-time path is not an LLM.** Ingest, envelope, surprise, lens choice and rendering are deterministic statistics and DSP, O(1) per sample. A local model (Ollama) is reserved for naming and explaining. It runs asynchronously and reads the envelope, never the stream.
- **Spend pixels where the signal is surprising.** Decimation keeps the min and max per pixel column, so a one-sample spike is never averaged away. The test for any lens is whether the human would still understand the story with the on-model samples removed.
- **Never an unexplained alarm.** Every note carries its reason: "jumped 5.1× its usual step".
- **Understanding is inspectable.** A sense is envelope + label + uses, held in a ledger. It is deliberately not a hidden embedding.
- **Unconfirmed labels never trigger actions.** SUFD says "so far", and drift re-opens the question.

Full argument: [spec/first-principles.md](spec/first-principles.md).

## Layout

```
sufd/        the package, in six keyword packages (glossary.py; spec/knowledge-base.md §1):
               eno intake · emem baseline and noise · idea understanding
               akpaneka judgement and action · kufre self · edimek surface
               (old slice-1 import paths remain as compatibility shims until the end of M4)
spec/        first-principles.md (the design) · knowledge-base.md (sourced claims)
bench/       scenario corpus, numeric gates, scoreboard, citation + claim checks, host recorder
tests/       unit and traceability tests
demo.py      the first-contact story → out/demo.html
```

## Scoreboard

The gates are numeric and set in advance. A capability that doesn't exist scores "not implemented", which counts as a fail, never a silent pass. Slice 1 is the baseline:

**7 of 22 gates pass** ([bench/scoreboard.md](bench/scoreboard.md)).

| Passing | Failing |
|---|---|
| Described within 64 samples (median 32) | Kind-inference accuracy: top-1 0.33 against a 0.80 gate |
| No false jumps on ramps or sines | Shift detection within 10 samples |
| One episode per true threshold crossing, no chatter | Noise calibration: 1/f flicker breaks the ±3σ band |
| CPU 0.76% of real time, against a 5% budget | Hostile and fuzzed input: 1,278 exceptions in 2,000 cases |

Capabilities not yet built include alias flagging, τ/ζ identification, calibration (PIT) and timing-skew attribution. Failures are the work list. The sourced claims behind these gates, with provenance tags and a verification status for each, are in [spec/knowledge-base.md](spec/knowledge-base.md). Run `python bench/claims.py` to reproduce the simulation claims independently of SUFD's own code.

## Where it's going

SUFD takes the shape of Ollama for distribution. The mind is a small daemon with a CLI, the surface is a thin client, and sensors are pulled in with a text file.

```
sufd serve                 # daemon on the Pi: ingest, envelopes, lenses, ledger
sufd pair                  # show a code; the phone scans it
sufd senses                # what SUFD can currently perceive
sufd show esp32.heat       # envelope + lens + notes for one signal
sufd pull lens/thermal     # pull a lens or sense-driver package
```

| Role | Device |
|---|---|
| **Mind** | Raspberry Pi: daemon, ledger, optional Ollama |
| **Surface** | Phone: screen, touch, its own sensors as signals |
| **Sense organs** | ESP32 nodes: sample, sign, announce, never render |

| # | Slice | Proves | |
|---|---|---|---|
| 1 | signal → envelope → lens → SVG, self-signals, ledger | a generated interface with no app written for the sensor | **built** |
| 2 | live WebSocket lens patches to a phone browser; human pointer returns | the shared-attention loop in real time | next |
| 3 | real ESP32 (MQTT or serial) with signed announcements | first contact on real hardware | |
| 4 | Ollama on the Pi for naming and explaining | the language layer, off the sample path | |
| 5 | `sufd` CLI, `Sensefile`, `pull` | the Ollama-shaped distribution | |
| 6 | cross-signal relations, drift detection | second-order understanding | |

SUFD sits beside **Modfus** and reuses its hub: slot-diff streaming carries lens patches to the phone, and the grant filter decides which surfaces may see which signals.

## Honest limits

- Kind inference from an envelope is sometimes wrong. A binary sensor that has only read `0` so far looks constant.
- Candidate labels are heuristics until a human confirms them.
- A small model on a Pi may take seconds to name a sense. The view never waits for it.
- A rogue node could poison envelopes. No real radio is trusted until device keys and signing are in (slice 3).
- Estimators learned the hard way that real data is hostile. A rounding sawtooth looks like a period, jittered sampling breaks autocorrelation, and trend is meaningless on a cyclic signal. The scoreboard exists to keep these honest.
