#!/bin/bash
# 초기 게인 조합 일괄 자동튜닝 테스트 (출력 필터 없음)
# 사용: ./run_all_inits.sh  또는  ./run_all_inits.sh "10 0 0" "1000 1000 1000"
cd ~/hyun-project1 || exit 1
if [ $# -gt 0 ]; then
  SETS=("$@")
else
  SETS=(
    "0 0 0" "10 0 0" "100 0 0" "100 100 100" "1000 500 50" "1000 1000 1000"
    "1 0 0" "10000 0 0" "0 100 0" "0 0 100"
    "100 0 1000" "100 1000 0" "10 10 100"
    "100000 0 100000" "0 100000 100000"
  )
fi
STAMP=$(date +%m%d_%H%M)
LOG="autotune_all_${STAMP}.log"
SUM="autotune_all_${STAMP}_summary.txt"
START=$(date +%s)
echo "튜너 파일: $(md5sum AUTO_TUNE_PROJ.py)" | tee -a "$LOG"
echo "조합 ${#SETS[@]}개: ${SETS[*]}" | tee -a "$LOG"
printf "%-18s %-30s %-9s %-5s %-8s %s\n" "초기게인" "최종게인(P/I/D)" "최종A_k" "런수" "120런수" "튜닝기록" > "$SUM"
for g in "${SETS[@]}"; do
  echo "" | tee -a "$LOG"
  echo "===== 엔코더 점검 (1 rev, P50)  $(date +%T) =====" | tee -a "$LOG"
  out=$(sudo ./AUTO_CONTROL_PROJ 1 2 216 50 0 0 2>&1)
  echo "$out" | tee -a "$LOG"
  csv=$(echo "$out" | awk '{w=$NF} END{print w}')
  endpos=$(awk -F, 'NF>=2 && $1+0==$1 {p=$2} END{gsub(/ /,"",p); print p}' "$csv" 2>/dev/null)
  echo "점검 끝 위치: ${endpos:-읽기실패} rev" | tee -a "$LOG"
  if ! awk -v x="$endpos" 'BEGIN{exit !(x!="" && x>0.5 && x<1.5)}'; then
    echo "!!! 엔코더 이상 (끝 위치 ${endpos:-없음}). 배선 확인 후 남은 조합만 다시 실행. 중단." | tee -a "$LOG"
    printf "%-18s %s\n" "$g" "엔코더 점검 실패로 중단" >> "$SUM"
    break
  fi
  echo "===== 초기 게인 $g  $(date +%T) =====" | tee -a "$LOG"
  python3 -u AUTO_TUNE_PROJ.py $g 2>&1 | tee -a "$LOG" | tee /tmp/last_tune.txt
  final=$(grep "Best gains" /tmp/last_tune.txt | tail -1 | sed 's/.*: //')
  [ -z "$final" ] && final=$(grep "Final gains" /tmp/last_tune.txt | tail -1 | sed 's/.*: //')
  score=$(grep "Best score" /tmp/last_tune.txt | tail -1 | awk '{print $NF}')
  ak=$(awk -v s="$score" 'BEGIN{ if (s=="" || s=="inf") print "-"; else printf "%.3f", s*10 }')
  runs=$(grep -c "^Run:" /tmp/last_tune.txt)
  bad=$(grep -o "A_k = [0-9.]*" /tmp/last_tune.txt | awk '$3>=100' | wc -l)
  hist=$(grep "Tuning history" /tmp/last_tune.txt | awk '{print $NF}')
  fs=$(echo "$final" | python3 -c "import sys,ast; g=ast.literal_eval(sys.stdin.read().strip() or '[]'); print('/'.join(f'{x:.4g}' for x in g) if g else '-')" 2>/dev/null)
  printf "%-18s %-30s %-9s %-5s %-8s %s\n" "$g" "${fs:--}" "$ak" "$runs" "$bad" "$hist" >> "$SUM"
  sleep 3
done
echo "" | tee -a "$LOG"
echo "===== 요약 (총 $(( ($(date +%s) - START) / 60 ))분) =====" | tee -a "$LOG"
cat "$SUM" | tee -a "$LOG"
echo "120런수 = A_k 100 이상인 런 수 (0 0 0 첫 런 외에 있으면 엔코더 끊김 의심)" | tee -a "$LOG"
echo "전체 로그: $LOG   요약: $SUM"
