#!/bin/bash

# ==============================================================
# 二进制内核代码复用机制 - 极严谨性能测试矩阵 (自适应提前终止版)
# ==============================================================

if [ "$EUID" -ne 0 ]; then
  echo "请使用 sudo 运行此脚本: sudo ./run_benchmarks.sh"
  exit 1
fi

# ================= 配置区 =================
TARGETS=(1 2 3)
STATES=("hot" "warm" "cold")
NUM_RUNS=100           # 单次执行内部的循环次数
THRESHOLD_PCT=90.0     # 有效数据的纯净度阈值 (IQR 保留率)
TARGET_SUCCESSES=5     # 【核心参数】期望收集的成功批次数量 (达到即提前停止)
MAX_ATTEMPTS=20        # 【核心参数】最长尝试次数 (未达标则拿现有成功数据兜底)

CSV_FILE="results_matrix_aggregated.csv"
# ==========================================

echo "Target,State,Valid_Batches,Grand_Median,Grand_Mean,Avg_StdDev,Avg_Minor_Flt,Avg_Major_Flt" > $CSV_FILE

echo "=========================================================="
echo " 启动 3x3 性能矩阵测试"
echo " 策略: 目标收集 $TARGET_SUCCESSES 个有效批次 (阈值 ${THRESHOLD_PCT}%)"
echo "       最多尝试 $MAX_ATTEMPTS 次，提前达标则自动跳出。"
echo "=========================================================="

for t in "${TARGETS[@]}"; do
    for s in "${STATES[@]}"; do
        
        target_name=""
        if [ "$t" -eq 1 ]; then target_name="Custom_SO"; fi
        if [ "$t" -eq 2 ]; then target_name="Native_SO"; fi
        if [ "$t" -eq 3 ]; then target_name="Static_Bin"; fi

        echo -e "\n---> 正在评估: [Target $t ($target_name)] | 状态: [$s]"
        
        valid_count=0
        sum_median=0
        sum_mean=0
        sum_stddev=0
        sum_minor=0
        sum_major=0

        for attempt in $(seq 1 $MAX_ATTEMPTS); do
            echo -n "  尝试 ($attempt/$MAX_ATTEMPTS) [已成功: $valid_count/$TARGET_SUCCESSES] ... "
            
            # 运行 C 测试程序
            OUTPUT=$(./benchmark_single -t $t -s $s -n $NUM_RUNS)
            
            # 提取 IQR 保留率
            RETAINED=$(echo "$OUTPUT" | grep -oP '(?<=\()[0-9.]+(?=% retained)')
            
            if [ -z "$RETAINED" ]; then
                echo -e "\e[31m执行或解析失败\e[0m"
                continue
            fi

            # 判断是否达到纯净度高标准
            IS_VALID=$(awk "BEGIN {print ($RETAINED >= $THRESHOLD_PCT) ? 1 : 0}")

            if [ "$IS_VALID" -eq 1 ]; then
                echo -e "\e[32m质量达标 (置信度: ${RETAINED}%)\e[0m"
                
                cur_median=$(echo "$OUTPUT" | grep "Median Cycles" | awk -F':' '{print $2}' | tr -d ' ')
                cur_mean=$(echo "$OUTPUT" | grep "Mean Cycles" | awk -F':' '{print $2}' | tr -d ' ')
                cur_stddev=$(echo "$OUTPUT" | grep "Std Deviation" | awk -F':' '{print $2}' | tr -d ' ')
                cur_minor=$(echo "$OUTPUT" | grep "Avg Minor Faults:" | awk -F':' '{print $2}' | awk '{print $1}')
                cur_major=$(echo "$OUTPUT" | grep "Avg Major Faults:" | awk -F':' '{print $2}' | awk '{print $1}')
                
                sum_median=$(awk "BEGIN {print $sum_median + $cur_median}")
                sum_mean=$(awk "BEGIN {print $sum_mean + $cur_mean}")
                sum_stddev=$(awk "BEGIN {print $sum_stddev + $cur_stddev}")
                sum_minor=$(awk "BEGIN {print $sum_minor + $cur_minor}")
                sum_major=$(awk "BEGIN {print $sum_major + $cur_major}")
                
                valid_count=$((valid_count + 1))
                
                # 随时更新一下最有代表性的干净 log
                cp ftrace_T${t}_${s^^}.log ftrace_T${t}_${s^^}_representative.log 2>/dev/null

                # 【自适应提前停止逻辑】
                if [ $valid_count -ge $TARGET_SUCCESSES ]; then
                    echo -e "  \e[35m[提前达成] 已集齐 $TARGET_SUCCESSES 个高质量批次，提前终止本项测试。\e[0m"
                    break
                fi
            else
                echo -e "\e[33m噪声过大被剔除 (置信度: ${RETAINED}%)\e[0m"
            fi
            
            sleep 0.5 # 短暂冷却，避免连续高频执行导致 CPU 睿频波动
        done

        # ================= 聚合统计逻辑 =================
        if [ $valid_count -gt 0 ]; then
            # 无论是因为满足 TARGET_SUCCESSES 提前跳出，还是跑满了 MAX_ATTEMPTS，只要有成功数据就求平均
            grand_median=$(awk "BEGIN {printf \"%.0f\", $sum_median / $valid_count}")
            grand_mean=$(awk "BEGIN {printf \"%.2f\", $sum_mean / $valid_count}")
            avg_stddev=$(awk "BEGIN {printf \"%.2f\", $sum_stddev / $valid_count}")
            avg_minor=$(awk "BEGIN {printf \"%.2f\", $sum_minor / $valid_count}")
            avg_major=$(awk "BEGIN {printf \"%.2f\", $sum_major / $valid_count}")
            
            echo -e "  \e[36m=> 聚合完成: 均值 $grand_mean Cycles (基于 $valid_count 个有效批次)\e[0m"
            
            echo "$target_name,$s,$valid_count,$grand_median,$grand_mean,$avg_stddev,$avg_minor,$avg_major" >> $CSV_FILE
        else
            # 20 次全部是脏数据（极罕见，说明系统被极其严重的底层 I/O 风暴锁死）
            echo -e "  \e[31m[警告] 历经 $MAX_ATTEMPTS 次尝试，均未达到 ${THRESHOLD_PCT}% 纯净度标准。\e[0m"
            echo "$target_name,$s,0,N/A,N/A,N/A,N/A,N/A" >> $CSV_FILE
        fi
        
    done
done

echo "=========================================================="
echo " 测试矩阵执行完毕！结果保存在: $CSV_FILE"
echo " 纯净度代表性微观轨迹已保存为: ftrace_*_representative.log"
echo "=========================================================="