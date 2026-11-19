#!/usr/bin/env bash

cd -- "$(dirname -- "$0")" || exit 1
mkdir -p runs || exit 1

move_results() {
    local file dest n failed=0
    for file in ./*.csv ./*.html; do
        [ -f "$file" ] || continue
        dest="runs/${file#./}"
        n=1
        while [ -e "$dest" ] || [ -L "$dest" ]; do
            dest="runs/${file#./}"
            dest="${dest%.*}.$n.${file##*.}"
            ((n++))
        done
        if mv -n -- "$file" "$dest" && [ ! -e "$file" ]; then
            echo "저장: $dest"
        else
            echo "이동 실패: $file" >&2
            failed=1
        fi
    done
    return "$failed"
}

interrupted=0
pid=
interrupt() {
    interrupted=1
    if [ -n "$pid" ]; then
        sudo kill -s INT -- "-$pid" 2>/dev/null || :
    fi
}
trap interrupt INT

# 별도 세션의 sudo도 암호를 묻지 않도록 먼저 인증한다.
if sudo -v && [ "$interrupted" -eq 0 ]; then
    # 터미널 세션은 유지하면서 튜너에 별도 프로세스 그룹을 부여한다.
    set -m
    # 백그라운드 작업이 상속하는 SIGINT 무시 상태를 복원한다.
    python3 -c 'import os, signal; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execvp("python3", ["python3", "AUTO_TUNE_PROJ.py"])' &
    pid=$!
    if [ "$interrupted" -eq 1 ]; then
        sudo kill -s INT -- "-$pid" 2>/dev/null || :
    fi
    wait "$pid"
    status=$?
    if [ "$interrupted" -eq 1 ]; then
        # wait가 신호로 일찍 깨어나도 자식과 sudo의 종료를 기다린다.
        wait "$pid" 2>/dev/null || :
        while sudo kill -0 -- "-$pid" 2>/dev/null; do
            sleep 0.1
        done
    fi
else
    status=1
fi

move_results || status=1
[ "$interrupted" -eq 0 ] || exit 130
exit "$status"
