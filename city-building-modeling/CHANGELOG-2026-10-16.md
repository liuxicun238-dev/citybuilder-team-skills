# CHANGELOG 2026-10-16 — city-building-modeling v2

来源：cn-primary-school-v01 a01/a01r2 实战（SKILL_V2_DIFF.md、A09_STYLE_NOTES.md、KIT_NOTES.md、QC_a01.md、lock.md 变更记录）。kit 原件和生成器都没有修改。

## 新增文件
- `scripts/finish_part_v01.py`：从 city-school-kit-v01/tools/pipeline 原样拷贝，md5 `21fe2e625d5be0b554a00e331df95570`
- `scripts/record_modeling_step.py`：原样拷贝，md5 `f707ee535d94515942ee6135b68ae0c7`
- `scripts/MD5SUMS.txt`：包内 5 个脚本的 md5（另外 3 个与 ORIGINAL_MD5.txt 一致）
- `CHANGELOG-2026-10-16.md`（本文件）

## SKILL.md 修改
1. §零 目录结构：列出两个新脚本及 md5，以及 MD5SUMS.txt
2. 新增 §二「第 1.5 步：lock 数字自洽规则」：加和要闭合；lock 和生成器要一致。附两个实例：梯间 +3.0→+4.0（原来 18.45+3.0+0.45=21.9，和写明的 22.9 对不上）；窗宽 3.2（lock）对 3.0（生成器），改为 3.0
3. §三 新增「远/中/近三级细节密度」：按 A09_STYLE_NOTES 写入数值（壁柱 0.45/转角 0.70、腰线 0.28×0.10、勒脚 0.6/+0.08、女儿墙 0.9×0.24 + 压顶 0.06/0.42、窗套 0.15/0.12、窗台 0.12×0.26/+0.40、横档 0.72h、落水管加雨水斗 + 鹅颈 + 每 3 m 管卡、窗后 DARK 室内体量、雨棚 WHITE 吊顶 + 滴水线、壁灯、空调机位、避雷带 +0.09、出挑 0.06–0.26）。原来按建筑类型分的四类清单保留
4. §四 防坑检查表从 8 条扩到 14 条（每条写明现象/原因/修复）：窗套顶角黑块（项目侧窗包装函数）、山墙重叠导致的转角黑点（从 T 到 D−T）、mesh_text 开放边（封口/挤出）、kit 材质偏暗（项目侧覆盖，不改 kit）、单件特写 HDRI 楼群（干净天空）、wall_poly 至少 3 点
5. §五 新增第 4 项 Linux 运行与依赖：MODELING_DATASET_ROOT、modeling_training_config.json、缺少的 build_vlm_dataset_v02.py / build_code_dataset_v01.py（BUILD FAILED，可用 --no-build）、脚本要放在 tools/pipeline/ 下、Linux 命令行、CJK 字体

## 未改
- 原有 Windows PowerShell 命令保留；kit 三个脚本、references/、agents/ 未动

## 试跑结果（cn-primary-school-v01 a01r3，2026-10-16 约 10:13 UTC+8）
按 §五.4 执行：把包内 `scripts/finish_part_v01.py`、`scripts/record_modeling_step.py` 拷入工程 `tools/pipeline/`（代码不改；md5 拷贝后仍为 21fe2e62…/f707ee53…，与 MD5SUMS.txt 一致），然后运行：
```bash
cp /workspace/city-building-modeling-v2/city-building-modeling/scripts/{finish_part_v01,record_modeling_step}.py tools/pipeline/
export MODELING_DATASET_ROOT=/workspace/city-school-kit-v01/dataset
BLD_VERSION=a01 BLD_ASSEMBLY=1 BLD_LOD=0 /workspace/tools/blender-5.2.2-linux-x64/blender -b -P tools/pipeline/build_city_cn_primary_school_v01.py
BLD_VERSION=a01 BLD_ASSEMBLY=1 BLD_LOD=1 /workspace/tools/blender-5.2.2-linux-x64/blender -b -P tools/pipeline/build_city_cn_primary_school_v01.py
python3 tools/pipeline/record_modeling_step.py --episode cn-primary-school-v01 --event-file /tmp/inspection_a01r3.json   # rc=0
python3 tools/pipeline/finish_part_v01.py --episode cn-primary-school-v01 --no-build                                 # rc=0
```
结果：PASS ×11（脚本、blend、渲染图 ×26、参考图 ×3、lock 快照、kit 快照 ×4、无盘符路径、thumbnail_check 3/3、issues、next_change）；**WARN ×1**（parent `cn-primary-school-v01-smoke` 没有 inspection，属历史遗留）；FAIL 0。RESULT：PASS with warnings。

试跑发现文档需要更正或补充：
1. §五.4 命令里的 `--event-file` 没有说明 JSON 格式。实际至少要有 `kind`（如 `"inspection"`）和 `action_id`（= 生成器写入的 `<episode>-<BLD_VERSION>`）。inspection 还要有 `thumbnail_check`（3 项 `{feature,present}`）、`issues[]`、`next_change`，否则 finish_part 报 FAIL。建议附一个最小示例
2. parent 链按「同一脚本的上一个 action_finished」推算。同一个 `BLD_VERSION` 反复重跑（a01→a01r2→a01r3）时，链条不会按修订号分开。建议文档写明每次修订用新的 `BLD_VERSION`（如 a01r3），或把修订说明写进 inspection
3. 调试时用临时 `BLD_VERSION` 跑单件，也会往正式 episode 写 action 记录。建议调试时把 `MODELING_DATASET_ROOT` 指到临时目录
4. §五.3 仍是 Windows 的 `D:\python\python.exe`，建议在旁边加一句「Linux 见 §五.4」
5. Linux 上应默认加 `--no-build`，§五.4 已经写了，与实测一致，不用改

## 第二轮修改（2026-10-16 10:13 UTC+8 之后，skill 管理员意见 + 试跑结果）
1. 「第 1.5 步：lock 数字自洽规则」从 §三 前面移到第 1 步之后、第 2 步之前，内容没改
2. §零 的「八项自查闸门」改为「十四项自查闸门」，与 §四 的 14 条对应
3. 在 /workspace 下搜索 `gen_reference.ps1`、`gen_edit.ps1`、`log_feedback.py`，一个都没找到，没有加入包。§零 新增一条「包内缺失的外部脚本」，说明它们缺失、需要向 skill 管理员索取
4. §五.4 新增退出码说明：finish_part 失败时 exit 1，接 `| tail` 会把返回码吞掉，要先 `set -o pipefail`，附示例
5. （试跑 1）§五.4 补充 `--event-file` 的 JSON 最少字段（kind、action_id；inspection 还要 thumbnail_check×3、issues[]、next_change），附最小示例
6. （试跑 2）§五.4 写明每次修订要用新的 BLD_VERSION（a01→a01r2→a01r3），否则 parent 链分不开
7. （试跑 3）§五.4 写明调试时把 MODELING_DATASET_ROOT 指到临时目录（`mktemp -d`），避免写进正式 episode
8. （试跑 4）§五.3 的 Windows 命令后注明「Linux 见 §五.4」
- 试跑第 5 条（Linux 默认加 --no-build）文档已经写了，不用改。按类型分的旧细节清单保持原样

## 第三轮修改（2026-10-16 12:30 UTC+8 之后，cn-primary-school a01r4 / a02r3 返工经验）
1. §四 新增第 15 项「【防细节不够】」：现象、原因、修复。
2. §四 新增第 16 项闸门「小件必须有真实原型和安装逻辑」：三个问题（是什么 / 怎么固定 / 连到哪里），答不上来就删除或重做，审计结果写进 QC 文件；用户 user-1214 圈出的 6 处问题作为反例（门墩壁灯灰盒、人行门上方悬空板、栏杆圆片、门卫室碎百叶、玻璃门细杆把手 + 玻璃上的方块、斜插短管）。
3. §四 新增「四.1 细节补充清单」：先做参考板再建模；比例对照规范；近景细节分层清单；预算再分配手段（降字形分辨率、暗盒改面片、截面挤出合并、自动删隐藏面、圆柱 8 段）；绘制三角数与唯一网格/实例三角数分开记录；铺装缝用贴图 + 法线贴图。
4. §零 中的「十四项自查闸门」改为「十六项」。
- 只改了 /workspace 下的这份 skill 副本，G: 上的原件没有动。
