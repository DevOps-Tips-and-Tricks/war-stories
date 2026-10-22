#!/usr/bin/env python3
"""
Apply the recording audio filter chain to an OBS audio input, over obs-websocket.

Setup once in OBS:
    Tools -> WebSocket Server Settings -> Enable WebSocket server -> Show Connect Info
    (default port 4455; copy the password)

    pip install obsws-python

Usage:
    # see which audio inputs exist
    ./obs-audio-chain.py --password SECRET --list

    # measure your room first (see --help), then apply
    ./obs-audio-chain.py --password SECRET --source "iPhone Mic" --noise-floor -54

    # audit what is currently set, as JSON you can commit
    ./obs-audio-chain.py --password SECRET --source "iPhone Mic" --dump > audio-chain.json

    # the source already has filters of its own: see them, then remove them
    ./obs-audio-chain.py --password SECRET --source "iPhone Mic" --noise-floor -54 --prune --dry-run
    ./obs-audio-chain.py --password SECRET --source "iPhone Mic" --noise-floor -54 --prune

The gate thresholds are derived from the noise floor you measured, because those are
the only two numbers in the chain that depend on your room rather than on your voice.
Everything else lives in CHAIN below — edit it there, commit it, and re-run.
"""

import argparse
import json
import sys

try:
    import obsws_python as obs
except ImportError:
    sys.exit("missing dependency:  pip install obsws-python")


# --- the chain, in processing order (top of the OBS filter list first) ----------
#
# Filter kinds are OBS's internal IDs. Settings keys are OBS's internal names,
# which do not always match the labels in the UI:
#   open_threshold / close_threshold  ->  "Open Threshold" / "Close Threshold"
#   attack_time / release_time        ->  "Attack" / "Release"
#   output_gain                       ->  "Output Gain"

CHAIN = [
    {
        "name": "1 Noise Suppression",
        "kind": "noise_suppress_filter_v2",
        "fallback_kind": "noise_suppress_filter",
        "settings": {
            "method": "rnnoise",      # "speex" is lighter on CPU but worse on speech
            "suppress_level": -30,    # only used when method is "speex"
        },
    },
    {
        "name": "2 Noise Gate",
        "kind": "noise_gate_filter",
        "optional": True,             # skipped with --no-gate
        "settings": {
            # close_threshold / open_threshold are filled in from --noise-floor
            "attack_time": 10,        # ms. lower than OBS's default 25 so word starts survive
            "hold_time": 250,         # ms. keeps the gate open between words
            "release_time": 150,      # ms
        },
    },
    {
        "name": "3 Equalizer",
        "kind": "basic_eq_filter",
        "settings": {
            "low": -4.0,              # dB, trims room rumble and desk thump
            "mid": 0.0,
            "high": 1.5,              # dB, a little presence
        },
    },
    {
        "name": "4 Compressor",
        "kind": "compressor_filter",
        "settings": {
            "ratio": 4.0,             # OBS defaults to 10, which flattens speech
            "threshold": -18.0,       # dB
            "attack_time": 6,         # ms
            "release_time": 60,       # ms
            "output_gain": 4.0,       # dB. raise until peaks sit around -9 .. -6
            "sidechain_source": "",   # none
        },
    },
    {
        "name": "5 Limiter",
        "kind": "limiter_filter",
        "settings": {
            "threshold": -3.0,        # dB. -3 not -1.5: this is a recording, leave headroom
            "release_time": 60,       # ms
        },
    },
]

GATE_MARGIN = 6      # dB above the measured noise floor for close threshold
GATE_HYSTERESIS = 8  # dB between close and open


def build_chain(noise_floor, use_gate, input_gain):
    chain = []

    if input_gain is not None:
        chain.append({
            "name": "0 Gain",
            "kind": "gain_filter",
            "settings": {"db": float(input_gain)},
        })

    for step in CHAIN:
        step = json.loads(json.dumps(step))  # deep copy, so --dump stays honest

        if step["kind"] == "noise_gate_filter":
            if not use_gate:
                continue
            close = noise_floor + GATE_MARGIN
            step["settings"]["close_threshold"] = float(close)
            step["settings"]["open_threshold"] = float(close + GATE_HYSTERESIS)

        chain.append(step)

    return chain


def existing_filters(client, source):
    try:
        return {f["filterName"]: f for f in client.get_source_filter_list(source).filters}
    except Exception as e:
        sys.exit(f"could not read the filters on {source!r} -- {e}\n"
                 "run --list to see the exact source names")


def find_extras(chain, present):
    """Filters on the source that are not part of the chain.

    Returns (duplicates, others). A duplicate has the same kind as a chain step, so
    the audio would go through that processing twice -- two compressors, two gates.
    """
    kinds = {}
    for step in chain:
        for kind in (step["kind"], step.get("fallback_kind")):
            if kind:
                kinds[kind] = step["name"]

    names = {step["name"] for step in chain}
    duplicates, others = [], []
    for name, f in present.items():
        if name in names:
            continue
        if f.get("filterKind") in kinds:
            duplicates.append((f, kinds[f["filterKind"]]))
        else:
            others.append(f)
    return duplicates, others


def apply_step(client, source, step, present, dry_run):
    name, settings = step["name"], step["settings"]

    if name in present:
        action = "update"
        if not dry_run:
            client.set_source_filter_settings(source, name, settings, overlay=True)
    else:
        action = "create"
        if not dry_run:
            try:
                client.create_source_filter(source, name, step["kind"], settings)
            except Exception:
                fallback = step.get("fallback_kind")
                if not fallback:
                    raise
                # older OBS: the v2 noise suppression filter does not exist
                client.create_source_filter(source, name, fallback, settings)

    return action


def main():
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
How to measure --noise-floor:
  1. Open OBS, sit where you record, stay silent for ten seconds.
  2. Read the lowest steady value on the mixer meter for that input. That is the
     noise floor. Pass it as a negative number, e.g. --noise-floor -54
  3. Then say a normal paragraph and watch the peaks. If the gap between the noise
     floor and your speech peaks is under 25 dB, no gate setting will sound good --
     fix the room and the mic distance first.
""",
    )
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=4455)
    p.add_argument("--password", required=True, help="from Tools -> WebSocket Server Settings")
    p.add_argument("--source", help="exact name of the audio input in the OBS mixer")
    p.add_argument("--noise-floor", type=float,
                   help="measured room noise floor in dB, e.g. -54 (required unless --no-gate)")
    p.add_argument("--input-gain", type=float,
                   help="add a Gain filter first, in dB. only if raw peaks are below -25")
    p.add_argument("--no-gate", action="store_true",
                   help="skip the noise gate. a badly tuned gate is worse than room noise")
    p.add_argument("--list", action="store_true", help="list audio inputs and exit")
    p.add_argument("--dump", action="store_true", help="print the source's current filters as JSON")
    p.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    p.add_argument("--prune", action="store_true",
                   help="remove every filter on the source that is not part of the chain. "
                        "their settings are printed as JSON first, so they can be recreated")
    args = p.parse_args()

    try:
        client = obs.ReqClient(host=args.host, port=args.port, password=args.password, timeout=5)
    except Exception as e:
        sys.exit(f"could not reach OBS at {args.host}:{args.port} -- {e}\n"
                 "is the WebSocket server enabled in Tools -> WebSocket Server Settings?")

    if args.list:
        print("audio inputs:")
        for i in client.get_input_list().inputs:
            kind = i.get("inputKind", "")
            if "audio" in kind or "capture" in kind or "wasapi" in kind or "coreaudio" in kind:
                print(f"  {i['inputName']}   [{kind}]")
        return

    if not args.source:
        sys.exit("--source is required (run --list to see the names)")

    if args.dump:
        print(json.dumps(client.get_source_filter_list(args.source).filters, indent=2))
        return

    if not args.no_gate and args.noise_floor is None:
        sys.exit("--noise-floor is required unless you pass --no-gate (see --help)")

    chain = build_chain(args.noise_floor, not args.no_gate, args.input_gain)
    present = existing_filters(client, args.source)
    duplicates, others = find_extras(chain, present)

    if duplicates or others:
        print(f"warning: {args.source!r} already has filters that are not part of the chain:")
        for f, step_name in duplicates:
            print(f"  {f['filterName']}   [{f['filterKind']}]  same kind as {step_name!r}"
                  " -- would process the audio twice")
        for f in others:
            print(f"  {f['filterName']}   [{f['filterKind']}]")
        print()

    if duplicates and not args.prune:
        sys.exit("nothing changed. either re-run with --prune to remove the filters above,\n"
                 "or delete them in OBS (right-click the source -> Filters).\n"
                 f"save their settings first if you tuned them:  --source {args.source!r} --dump")

    if args.prune:
        for f in [f for f, _ in duplicates] + others:
            # one line of JSON per filter: enough to recreate it by hand if it was a mistake
            print("removed " if not args.dry_run else "would remove ", end="")
            print(json.dumps({k: f.get(k) for k in ("filterName", "filterKind", "filterSettings")}))
            if not args.dry_run:
                client.remove_source_filter(args.source, f["filterName"])
        if duplicates or others:
            print()

    for step in chain:
        action = apply_step(client, args.source, step, present, args.dry_run)
        print(f"{action:>6}  {step['name']}")

    # order matters: filters process top to bottom, so pin the indices
    if not args.dry_run:
        for index, step in enumerate(chain):
            client.set_source_filter_index(args.source, step["name"], index)

    print()
    if args.dry_run:
        print("dry run -- nothing was changed")
    else:
        print("applied. final order:")
        for f in client.get_source_filter_list(args.source).filters:
            state = "" if f.get("filterEnabled", True) else "  (disabled)"
            print(f"  {f['filterIndex']}  {f['filterName']}{state}")
        print("\nStill manual in OBS (no websocket API for these):")
        print("  - Advanced Audio Properties -> Downmix to Mono, for the mic channel")
        print("  - Settings -> Audio -> Sample Rate: 48 kHz")
        print("  - Settings -> Output -> Recording -> Format: Hybrid MP4")


if __name__ == "__main__":
    main()
