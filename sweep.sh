#!/usr/bin/env bash

usage() {
    echo '사용법: ./sweep.sh [--target 목표 --time 시간] 1|2|3|3a|3b [게인...]' >&2
    exit 2
}

cd -- "$(dirname -- "$0")" || exit 1
target=10
duration=5
while [ "$#" -gt 0 ]; do
    case "$1" in
        --target) [ "$#" -ge 2 ] || usage; target=$2; shift 2 ;;
        --time) [ "$#" -ge 2 ] || usage; duration=$2; shift 2 ;;
        *) break ;;
    esac
done
[[ $target =~ ^-?([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || usage
[[ $duration =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || usage
python3 - "$target" "$duration" <<'PY' || exit 2
import math, sys
target, duration = map(float, sys.argv[1:])
if not math.isfinite(target) or target == 0 or not 5 <= duration <= 10:
    sys.exit('목표는 0이 아닌 유한한 값, 시간은 5~10초여야 합니다.')
PY
[ "$#" -ge 1 ] || usage
stage=$1
shift
case "$stage" in
    1) [ "$#" -eq 0 ] || usage ;;
    2) [ "$#" -eq 4 ] || usage ;;
    3|3a|3b) { [ "$#" -eq 6 ] || [ "$#" -eq 9 ]; } || usage ;;
    *) usage ;;
esac
for value in "$@"; do
    [[ $value =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || usage
done
mkdir -p runs || exit 1
manifest=runs/sweep_manifest_v2.tsv
if [ ! -e "$manifest" ]; then
    printf 'time\tstage\tp\ti\td\tstatus\tfile\ttarget\tduration\n' > "$manifest" || exit 1
fi
log=$(mktemp) || exit 1
trap 'rm -f -- "$log"' EXIT
interrupted=0
trap 'interrupted=1' INT

run_one() {
    local p=$1 i=$2 d=$3 status state line file found=0
    [ "$interrupted" -eq 0 ] || return 130
    : > "$log"
    ./run.sh "$target" "$duration" 216 "$p" "$i" "$d" | tee -i "$log"
    status=${PIPESTATUS[0]}
    state=ok
    if [ "$interrupted" -ne 0 ] || [ "$status" -eq 130 ]; then
        state=interrupted
        interrupted=1
    elif [ "$status" -ne 0 ]; then
        state=failed
    fi
    while IFS= read -r line; do
        case "$line" in
            '저장: runs/'*)
                file=${line#저장: }
                if [ "$state" = ok ] && ! python3 check_sweep.py "$file" "$target" "$duration" "$p" "$i" "$d"; then
                    state=abnormal
                    status=1
                fi
                printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -Iseconds)" "$stage" "$p" "$i" "$d" "$state" "$file" "$target" "$duration" >> "$manifest" || return 1
                found=1
                ;;
        esac
    done < "$log"
    if [ "$found" -eq 0 ]; then
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -Iseconds)" "$stage" "$p" "$i" "$d" "$state" '-' "$target" "$duration" >> "$manifest" || return 1
        echo 'CSV 기록 없음: 스윕 중단' >&2
        return 1
    fi
    [ "$interrupted" -eq 0 ] || return 130
    [ "$status" -eq 0 ] || return "$status"
    sleep 1
    [ "$interrupted" -eq 0 ] || return 130
}

case "$stage" in
    1)
        for p in 50 100 200; do
            for d in 0 1 2 4; do
                run_one "$p" 0 "$d" || exit "$?"
            done
        done
        ;;
    2)
        while [ "$#" -gt 0 ]; do
            p=$1 d=$2
            shift 2
            for i in 0 50 100 200; do
                run_one "$p" "$i" "$d" || exit "$?"
            done
        done
        ;;
    3|3a|3b)
        repeats=3
        [ "$stage" != 3b ] || repeats=2
        while [ "$#" -gt 0 ]; do
            p=$1 i=$2 d=$3
            shift 3
            for ((repeat=1; repeat<=repeats; repeat++)); do
                run_one "$p" "$i" "$d" || exit "$?"
            done
        done
        ;;
esac
