#!/usr/bin/env bash
# Record the README demo GIF: the scorer, the replay eval, a gate receipt.
#
#   brew install asciinema agg   (once)
#   ./scripts/make_demo.sh       (from the repo root)
#
# Output: docs/demo.gif. Keep it 15-25s, under ~2 MB.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v asciinema >/dev/null || { echo "need asciinema: brew install asciinema"; exit 1; }
command -v agg >/dev/null || { echo "need agg (asciinema GIF player): brew install agg"; exit 1; }

# Example state in a temp dir, so the demo never touches live skillopt/ data.
demo="$(mktemp -d)"
trap 'rm -rf "$demo"' EXIT
cp examples/best_skill.starter.md "$demo/best_skill.md"
cp skillopt/held_out.example.json "$demo/held_out.json"
cp examples/trajectories.example.jsonl "$demo/trajectories.jsonl"

cat > "$demo/demo.sh" <<EOS
export SKILLOPT_DIR="$demo"
run() { printf '\$ %s\n' "\$*"; "\$@"; }
run python3 skillopt/sleep_cycle.py status
sleep 5; clear
run python3 skillopt/sleep_cycle.py replay --skill-a "$demo/best_skill.md" --skill-b examples/best_skill.starter.md
sleep 4; clear
echo '# gate receipt example'
echo '{"accepted": true, "val_mean_before": 1.83, "val_mean_after": 2.04, "delta_mean": 0.21, "ci_level": 0.95, "ci_low": 0.06, "ci_high": 0.41}'
sleep 5
EOS
asciinema rec --overwrite --command "bash --norc --noprofile $demo/demo.sh" "$demo/demo.cast"
agg --theme monokai --cols 100 --rows 22 --speed 1 "$demo/demo.cast" docs/demo.gif
echo "wrote docs/demo.gif - put it right under the README badges"
