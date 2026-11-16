# SUFD — first principles

> Status: founding draft, 2026-11-16. A direction, not a product. Everything here
> is either (a) built in `sufd/sufd/` and tested, or (b) marked **open**.

## 0. The claim

Modfus asked *where does the user's data live and who decides it moves?* SUFD asks a
different question: **what is the unit of an interface?**

Today the unit is the **app**: a human-authored screen for a *known* data source.
That model breaks the moment an unknown source appears (a new sensor, a new radio, a
new peripheral) — nobody has written its screen yet.

SUFD's unit is the **signal**. Anything that varies over time and can be sampled —
a heat sensor, the battery, a touch, a microphone, a log stream, *SUFD's own CPU
load* — is a signal. SUFD reads every signal in real time, **works out what the
signal is**, and **generates the way for a human to follow it**. No app has to exist.

> Two readers, one signal. SUFD and the human sit at adjacent angles to the same
> thing. SUFD reads it at machine speed; the human reads it at human speed; the
> interface is the transducer between the two.

## 1. The five nouns

| Noun | Meaning | Built in |
|---|---|---|
| **Signal** | A named source of `(t, value)` samples, with unknown semantics. | `signal.py` |
| **Envelope** | What SUFD has *learned* about a signal: kind, range, rate, noise, drift, period, surprise. The minimum description needed to *receive* it and *render* it. Online, always updating. | `envelope.py` |
| **Lens** | A visual encoding chosen *from the envelope* (not from the app): mark, scale, window, decimation. | `lens.py`, `render.py` |
| **Follow** | The shared attention between SUFD and the human on one signal: SUFD's "now" cursor, SUFD's notes (what it noticed and why), and the human's pointer. | `follow.py` |
| **Self** | SUFD's own signals (loop lag, CPU, signal count) fed through the *same* pipeline, plus the **sense ledger** of every sense it has met. | `selfmodel.py` |

The reflexive trick: SUFD does not need a separate "self-monitoring" subsystem.
Its own metrics are signals; the same envelope→lens pipeline reads them. A new
ESP32 sensor and SUFD's own CPU temperature go through identical code.

## 2. The loop

```
 source ──► Signal ──► Envelope ──► Lens ──► Surface ──► human
              ▲            │          ▲                    │
              │            ▼          │                    │ points / asks
              │        surprise ──► Follow ◄───────────────┘
              │            │
              └── Self ◄───┘   (SUFD reads itself with the same loop)
```

1. **Ingest.** Samples arrive in a ring buffer. Nothing is assumed about meaning.
2. **Learn the envelope.** Online statistics (Welford mean/var, robust range from
   quantiles, median Δt and jitter, lag-1 autocorrelation, noise from first
   differences, least-squares trend, autocorrelation period, EW surprise).
   Cost per sample is O(1); the heavier estimates run on a window at a slower cadence.
3. **Pick the lens from the envelope.** A *grammar* maps envelope → encoding (§4).
4. **Render at human bandwidth.** The signal may be 1 kHz; the human can follow
   ~10 updates/s over a 5–120 s horizon. Decimate by *min/max per pixel column* so a
   one-sample spike is never averaged away.
5. **Follow.** Wherever surprise concentrates, SUFD annotates *and says why*
   ("jumped 5.1× its usual step"). The human can point at any region; SUFD answers
   from the envelope.

## 3. Why the interface can be generated: an information argument

The envelope is a *model of the signal's typical behaviour*. Surprise
(`|Δ| / typical |Δ|`) is the part the model could not predict — the only part
carrying information. A good lens spends pixels (and the human's attention) where
surprise is, and almost none where the signal is on-model. This is the same idea as
the Modfus hub's "stream only the entropy": the hub streams only the slots that
changed; SUFD *shows* only the parts that mattered.

So the design test for any lens is: **if you removed the on-model samples, would the
human still understand the story?** If yes, the lens is honest.

## 4. The lens grammar (first cut)

| Envelope says | Mark | Why |
|---|---|---|
| numeric, smooth, continuous | `strip` — line over a scrolling window, auto-ranged | position on a common scale is the most accurate human channel |
| two values only | `steps` — step line / timeline lane | state, not magnitude; dwell time is the story |
| few distinct strings/ints | `lanes` — one lane per category | membership + sequence |
| fixed-length numeric vector | `trajectory` — path in the plane of the two leading components, fading tail | shows motion, not 3 separate numbers |
| periodic (autocorr peak ≥ 0.5) | window := ~3 periods, mark period on axis | lets the eye lock to the cycle |
| positive and spans ≥ 3 decades | log scale | otherwise the low end is flat |

Auto-range uses **hysteresis**: the y-axis only widens immediately but only
narrows after sustained evidence, otherwise the axis "breathes" and the human loses
the signal.

**Open:** a learned lens (model proposes encodings, humans correct) — only after the
hand-written grammar has produced a corpus of (envelope, lens, correction) triples.

## 5. First contact: how SUFD grows a new sense

The user's example: an ESP32 with a wireless heat sensor joins.

1. **Notice.** A new source id appears (mDNS/BLE/MQTT/serial → `Signal`). The ledger
   records `first_seen` and state `new`. Nothing is shown as authoritative yet.
2. **Observe.** For a warm-up of N samples SUFD only reads. State `observing`.
3. **Describe.** SUFD states *behaviour*, not a guess dressed as fact:
   "slow, smooth, drifting up 0.4 per min, 18.2–24.9, 1 sample/s".
4. **Hypothesise.** It offers ranked candidates *with reasons*
   ("temperature-like: bounded 15–45, slow, smooth") and **asks the human once**.
   An announced hint from the device (`unit="C"`) skips the question.
5. **Use.** A confirmed sense becomes a *watch*: bounds learned from its own
   envelope (mean ± kσ, max plausible slope), and a link from the sense to the
   *needs* it can inform (thermal safety of the host, comfort, fire).
   The watch raises notes through **Follow**, so the human sees what SUFD sees.
6. **Remember.** The ledger keeps envelope, label, uses and when it was last
   trusted — SUFD can answer "what can you sense?" from its own state.

> "Understand the sense" = **envelope + label + uses**, all inspectable. It is
> deliberately not a hidden embedding: the human must be able to follow *how* SUFD
> understands.

## 6. What is and isn't an LLM

Real-time signal reading must be **deterministic statistics/DSP**, not a language
model. An LLM on a Raspberry Pi answers in seconds; a 50 Hz signal won't wait.

| Job | Engine |
|---|---|
| ingest, envelope, surprise, lens choice, decimation, render | classical code, always on, O(1)/sample |
| naming a new sense, explaining a note in prose, answering "why?", proposing a new lens | a **local LLM via Ollama**, asynchronous, only when asked or on first contact |

The LLM is the *translator between the envelope and human language*; it is never in
the sample path, and it reads the envelope (a few hundred bytes), never the raw
stream. That is also what makes it feasible on a Pi.

## 7. Distribution — "the Ollama model"

Ollama's shape: a small local daemon, one CLI, a registry of pulled artifacts, a
text file (`Modelfile`) describing how to assemble one. SUFD adopts the *shape*:

```
sufd serve                 # daemon on the Pi: ingest, envelopes, lenses, ledger
sufd pair                  # show a code; the phone scans it → paired body
sufd senses                # the sense ledger (what SUFD can currently perceive)
sufd pull lens/thermal     # pull a lens or a sense-driver package
sufd show esp32.heat       # envelope + lens + notes for one signal
```

- **Raspberry Pi = the mind** (daemon, ledger, optional Ollama for language).
- **Phone = the surface/body** (screen, touch, its own sensors as signals; thin
  renderer). Same inversion the Modfus hub already made for weak hardware.
- **Sensor nodes (ESP32) = sense organs**: sample, sign, announce, never render.
- A **`Sensefile`** (like a Modelfile) declares a sense: transport, announced hints,
  default needs it can inform. Optional — SUFD must cope with no file at all, which
  is the first-contact path above.

Reuse from the Modfus hub, not rewrite: slot-diff streaming (`fus.py`) carries
lens patches to the phone; the grant filter (`grant.py`) decides *which signals each
surface may see*; the swarm (`swarm.py`) is how a second Pi joins the mind.

## 8. Honest limits

- Envelope-based kind inference will be wrong sometimes (a binary sensor that has
  only been `0` so far looks constant). SUFD must say *"so far"* and re-open the
  question when the envelope changes (**drift detection** re-triggers `describe`).
- "Candidates" for what a signal *is* are heuristics until a human confirms. The
  system never acts on an unconfirmed label beyond showing it.
- Following means the human is *never* handed an unexplained alarm: every note
  carries its reason from the envelope.
- The Pi can run only small local models; first-contact naming may take seconds.
  The *view* never waits for it.

## 9. Open questions

1. **Time base.** Signals from different devices have different clocks. First cut:
   SUFD stamps arrival time; later, per-device offset estimation.
2. **Multi-signal relations.** Correlation / lead-lag between signals ("heat leads
   fan current by 4 s") is the natural second-order envelope. Not built.
3. **Trust.** A rogue node can poison envelopes. Reuse EGIS device keys
   (Ed25519, nonce-bound) from `hub`/EGIS firmware before any real radio is trusted.
4. **Does SUFD replace `.fus` apps, or generate them?** Leaning: a lens *is* a tiny
   `.fus` view; apps become hand-authored lenses over several signals.
5. **Recovery & vault.** Inherit the Modfus recovery decisions (see `modfus/spec`) unchanged: one sealed vault,
   many carriers.

## 10. Build order

| # | Slice | Proves |
|---|---|---|
| **1 (built)** | signal → envelope → lens → SVG, self-signals, sense ledger, first-contact demo with a simulated ESP32 heat sensor | the generated-interface claim, without any app written for the sensor |
| 2 | live server: WebSocket stream of lens patches to a phone browser, human pointer returns to SUFD | the "adjacent seats" loop in real time |
| 3 | real ESP32 (MQTT or serial) on the Pi; announcement + signing | first contact on real hardware |
| 4 | Ollama on the Pi for naming/explaining | the language layer, off the sample path |
| 5 | `sufd` CLI + `Sensefile` + `pull` | the Ollama-shaped distribution |
| 6 | cross-signal relations, drift detection | second-order understanding |
