#!/usr/bin/env bash

if [ "$#" -ne 6 ]; then
    echo "사용법: $0 <목표> <시간> 216 <P> <I> <D>" >&2
    exit 2
fi

cd -- "$(dirname -- "$0")" || exit 1
mkdir -p runs || exit 1
log=$(mktemp) || exit 1
trap 'rm -f -- "$log"' EXIT
interrupted=0
trap 'interrupted=1' INT

# 중단되어 파일명을 받지 못했을 때 새로 생긴 CSV만 찾는다.
declare -A existing
for file in ./*.csv; do
    [ -e "$file" ] || continue
    existing["$file"]=1
done

move_csv() {
    local file=$1 dest="runs/${1#./}" n=1
    while [ -e "$dest" ] || [ -L "$dest" ]; do
        dest="runs/${file#./}"
        dest="${dest%.csv}.$n.csv"
        ((n++))
    done
    mv -n -- "$file" "$dest" || return 1
    if [ -e "$file" ]; then
        echo "이동 실패: $file" >&2
        return 1
    fi
    echo "저장: $dest"
}

sudo ./AUTO_CONTROL_PROJ "$@" | tee -i "$log"
status=${PIPESTATUS[0]}
last_line=$(tail -n 1 -- "$log")
case "$last_line" in
    'CSV file created: '*)
        csv=${last_line#CSV file created: }
        case "$csv" in
            */*|'') echo "잘못된 CSV 이름: $csv" >&2; status=1 ;;
            *)
                if [ -f "$csv" ]; then
                    python3 PROJECT_SCORE.py "$csv" || status=1
                    move_csv "./$csv" || status=1
                else
                    echo "CSV를 찾을 수 없습니다: $csv" >&2
                    status=1
                fi
                ;;
        esac
        ;;
    *)
        if [ "$interrupted" -eq 1 ]; then
            for file in ./*.csv; do
                [ -f "$file" ] || continue
                [ "${existing[$file]+yes}" ] && continue
                move_csv "$file" || status=1
            done
        else
            echo "출력 마지막 줄에서 CSV 이름을 찾지 못했습니다." >&2
            [ "$status" -ne 0 ] || status=1
        fi
        ;;
esac
if [ "$interrupted" -ne 0 ]; then
    trap - INT
    kill -s INT "$$"
    exit 130
fi
exit "$status"
