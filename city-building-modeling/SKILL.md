---
name: city-building-modeling
description: 本项目现代城市建筑与工业设施（发电厂、水厂、变电站、医院、公安局、消防站、学校、商业办公楼等）的分件参数化高细节建模流程：A0功能与工艺审视→拆件6格多视图参考→基于building_kit_v01声明式构件库单件建模（含三级细节强制清单）→链接实例化总装与管线道路场地衔接→防穿插/防丢件自查闸门。用于新建或改进城市建筑资产，确保小模型也能按标准积木原语稳定产出同等质量建筑。
---

# 城市与工业建筑分件参数化建模流程（City & Industrial Building Modeling）

本 Skill 从燃气联合循环电厂（`power-plant-v01` a01–a09，15 个高细节部件 + 176×136 m 总装，697 对象）及医院、公安局、水厂的实战迭代中提炼而成。

> **核心目标**：让任何规模的模型（包括小模型）不需要手算复杂三维旋转矩阵或手写底层 `bmesh` 拓扑，而是通过调用本 Skill 包内置的 [`scripts/building_kit_v01.py`](scripts/building_kit_v01.py)、[`scripts/power_plant_kit_v01.py`](scripts/power_plant_kit_v01.py) 和 [`scripts/city_kit_common.py`](scripts/city_kit_common.py) 中的**声明式构件原语**，像填工程图纸一样稳定建出细节丰富、比例准确、无穿插错位的城市建筑群。

## 零、 Skill 独立包目录结构（自带全套脚本与范例，开箱即用）
- [`SKILL.md`](SKILL.md)：本流程规范、原语速查表、三级细节强制清单与十四项自查闸门。
- [`scripts/building_kit_v01.py`](scripts/building_kit_v01.py)：通用建筑、立面门窗、梯台走道、场地道路与审阅环境标准库（已内置 a09 防呆修复与无外部 FBX 时的程序化树木回退）。
- [`scripts/power_plant_kit_v01.py`](scripts/power_plant_kit_v01.py)：底层 `Geo` 按材质 `bmesh` 合并器、`WF` 立面二维坐标系、管道弯头/阀门、折返楼梯/护笼爬梯、百叶/压型板、绝缘子/悬链线、格构塔架库。
- [`scripts/city_kit_common.py`](scripts/city_kit_common.py)：Blender 5.x 场景初始化、三平面花岗岩/基础材质、摄影棚灯光与部件统计工具。
- [`scripts/finish_part_v01.py`](scripts/finish_part_v01.py)：交审闸门（检查 episode 事件、证据、inspection；可选重建数据集）。原件原样拷贝，md5 `21fe2e625d5be0b554a00e331df95570`。
- [`scripts/record_modeling_step.py`](scripts/record_modeling_step.py)：训练事件记录器（每事件一个 JSON + 证据哈希快照）。原件原样拷贝，md5 `f707ee535d94515942ee6135b68ae0c7`。
- [`scripts/MD5SUMS.txt`](scripts/MD5SUMS.txt)：包内全部脚本 md5，`cd scripts && md5sum -c MD5SUMS.txt` 复核。
- [`scripts/gen_reference.ps1`](scripts/gen_reference.ps1) / [`scripts/gen_edit.ps1`](scripts/gen_edit.ps1)：第 1、2 步出概念图与 6 格多视图。**只能在 Windows（PowerShell）上用**；密钥走用户本机 DPAPI 文件 + `tools/pipeline/image-provider.json`（`-Provider 02` 读 `image-provider-02.json`），**密钥没有入包**。原件只读拷自用户本机 `.agents/skills/reference-procedural-modeling/scripts/`。
- [`scripts/log_feedback.py`](scripts/log_feedback.py)：逐字记录用户反馈为 `user_feedback` 事件。**依赖 `record_modeling_step.py`**（同目录 import `append_event`），两者一起放在工程 `tools/pipeline/` 下。原件只读拷自 `tools/pipeline/`。
- [`references/building-generator-template.py`](references/building-generator-template.py)：小模型可直接复制填空的生成器脚手架模板。
- [`references/power-plant-a09-example.py`](references/power-plant-a09-example.py)：燃气电厂完整生产级范例（15 个高细节部件 + 176×136 m 总装，1032 行完整实现）。
- [`references/power-plant-lock-example.md`](references/power-plant-lock-example.md)：燃气电厂 `lock.md` 范例（A0 审视、结构读取、尺寸与总平面、材质真值表）。

---

## 一、 为什么小模型必须按本流程建模（四条铁律）

1. **禁止直接堆大白盒，必须分件 + 三级细节**：
   - 每个单体建筑、附属机房、设备、大门岗亭、可动门扇都作为独立部件（`PP01`、`PP02`…）在自身局部坐标系原点建模、单独渲染特写、单独存盘 `parts/<id>_<name>.blend`，最后在总装里用 `B.instance()` 实例化摆放。
2. **禁止在墙面上手动算 3D 世界坐标排门窗**：
   - 凡是在建筑立面上布置带形窗、分格窗、卷帘门、人行门、百叶窗、壁柱、腰线、压型钢板竖肋、落水管，**一律先建立墙面局部坐标系 `F = B.WF(origin, rz, normal_sign)`**，在 `(u 沿墙宽, v 高度, w 向外凸出)` 二维坐标下调用原语。
3. **禁止为每根栏杆/竖肋单独建 Blender Object**：
   - 每个部件使用一个 `g = B.Geo(K, pid)` 收集器。所有盒子、梁、圆柱、回转体、管道、百叶全部写入内存 `bmesh`，部件结束时调一次 `g.flush()`，自动按材质合并网格并按 `38°` 阈值切硬边/平滑面。
4. **禁止跳过 A0 工艺/流线审视照抄 AI 概念图的错位布局**：
   - AI 概念图常有流线错误（如大门设在两个岗亭外、烟囱位置前后颠倒、电线横跨整个厂区、厂房前散落无功能碎盒子）。动工前必须在 `lock.md` 写明 **A0 采用/修改/否决表**。

---

## 二、 完整 6 步工作流

### 第 1 步：概念参考与 A0 工程逻辑锁定（`lock.md`）
1. **生成整体概念图**：用接口 `02`（`scripts/gen_reference.ps1 -Provider 02 -Size 1536x1024`）生成俯视 3/4 角写实建筑群概念图，提示词须写明“游戏内写实截图、物理材质、真实工程尺度、清晰展示主建筑/附属设施/围墙大门/院内环路”。
2. **编写 `art/references/city/<asset-v01>/lock.md`**，必须包含以下 6 个章节：
   - **A0 参考审视表**：逐项列出概念图中的元素 → `采用 / 修改 / 否决` + 工程与功能理由（例如：工艺流程方向是否连贯？消防环路是否闭合？大门与岗亭是否在围墙线上？绿化是否克制？）。
   - **场地坐标系与模数假设**：统一以米为单位，**原点 `(0,0,0)` 固定在临街面（南边界 `Y=0`）中点**，`X` 向右（沿街），`Y` 向院内，`Z` 向上；临街公共道路在 `Y<0`（不进资产包）。建筑尺寸优先对齐 `4 m / 8 m` 结构模数。
   - **部件拆解清单（`ID + 英文名 + 尺寸假设 + 枢轴约定`）**：
     - 静态建筑/设备：枢轴在底面中心 `(0,0,0)` 或前脸轴线起点。
     - **可动门扇（必拆独立部件）**：电动推拉门扇（`slide_axis='-X'`，含行程 `travel`）、平开门扇（枢轴在门轴铰链边 `x=0`）。
   - **总平面坐标表**：写出院内主干道/环路矩形 `(x0,y0,x1,y1)`、每个部件在总装里的 `(X, Y, Yaw)`。
   - **三级细节强制清单**（见第三节）。
   - **材质真值表**：调用 `B.standard_palette(C, prefix)` 并列出主色调。

### 第 1.5 步：lock 数字自洽规则（锁定前必过）
1. **加和必须闭合**：凡写成"A + B + C = 总高/总长"的数字，锁定前逐条复算；分项与总数矛盾时，以有设计依据的那个为准改另一个，并在变更记录写明。
2. **lock 与生成器必须一致**：生成器里的尺寸常量（洞口、层高、标高、间距）逐项和 lock 对照；不一致时由 lock 拥有者决定，改 lock 或改生成器，二者不能各说各的。
3. **实例（cn-primary-school-v01）**：
   - 出屋面楼梯间：lock 原文"到 22.9（屋面 18.45 +3.0 机房 +0.45 压顶）"，18.45+3.0+0.45=**21.9 ≠ 22.9**；生成器用 `PH=ROOFZ+4.0`。r2 改为 **+4.0**，22.9 不变。
   - 教室窗宽：lock 写 **3.2×2.2**，生成器为 **3.0×2.2**（`±1.5`）。r2 lock 改为 3.0（窗地比约 0.18，仍 ≥1/6）。
4. 每次 lock 修订写入文末"变更记录"（日期、版本、决定人、旧值→新值、理由）。

### 第 2 步：从主概念图抽 6 格部件多视图（`parts/sheet-*.png`）
- 不要凭一张远景图猜部件背面和局部构造。用 `scripts/gen_edit.ps1 -Image concept.png -Provider 02 -Size 1536x1024` 抽出核心部件的 6 格多视图（正视、侧视、背视、俯视、2 张近景构造特写），存放在 `art/references/city/<asset-v01>/parts/sheet-*.png`。

### 第 3 步：用 `building_kit_v01.py` 声明式编写各部件函数
在 `tools/pipeline/build_city_<name>_v01.py` 中，直接复用 `.agents/skills/city-building-modeling/references/building-generator-template.py` 模板。

#### 常用声明式原语速查表（`import building_kit_v01 as B`）
| 类别 | 函数调用 | 作用与防呆特性 |
|---|---|---|
| **网格收集器** | `g = B.Geo(K, pid)` ... `g.flush()` | 按材质自动合并 `bmesh`，自动计算法线与 `38°` 硬边 |
| **基础体素** | `g.box(m, center, dim, rz, rx, ry)` / `g.boxa(m, pMin, pMax)` | 任意旋转长方体 / 对角点轴对齐长方体 |
| **型钢与梁柱** | `g.beam(m, p0, p1, w, h)` / `g.hbeam(m, p0, p1, b, h)` / `g.angle(m, p0, p1, a, t)` | 任意两点间的矩形梁、真实翼缘腹板 H 型钢、角钢 |
| **回转与曲面** | `g.cyl(m, p0, p1, r)` / `g.lathe(m, [(r,z),...], c, seg, axis)` / `g.loft(m, loopA, loopB)` | 圆柱/圆台、带封头罐体/烟囱/风筒回转体、变截面烟道/坡道放样 |
| **格构塔架** | `B.lattice_column(g, m, base, H, w0, w1)` / `B.lattice_beam(g, m, p0, p1, d)` | 变截面四角钢格构柱、空间桁架横梁（构架、铁塔、管桥支架） |
| **立面画布** | `F = B.WF(origin, rz, ns)` → `F.box(g, m, u, v, w, du, dv, dw)` | 将三维立面转为 `(u沿墙, v向上, w向外)` 二维局部坐标系 |
| **压型钢板墙** | `B.ribbed(g, m, F, u0, u1, v0, v1, pitch=.30, vtop=fn, skip=holes)` | 自动生成底板+梯形竖肋，支持山墙斜顶 `vtop(u)`，自动跳过 `skip=[(ua,ub,va,vb)]` 门窗洞口 |
| **门窗与百叶** | `B.ribbon_window` / `B.punched_window` / `B.person_door` / `B.roller_door` / `B.louvre_bank` | 自带窗套、挑出窗台、深色内衬、竖梃横档、雨棚拉杆、壁灯、卷帘罩、斜百叶叶片 |
| **工业梯台** | `B.zigzag_stair` / `B.flight` / `B.ladder` / `B.grating` / `B.railing` / `B.ring_platform` | 双跑折返楼梯塔、直跑钢梯、带护笼爬梯、包边格栅、带踢脚板栏杆、带梯口内返栏杆的环形平台 |
| **防穿插走道** | `B.split_walkway(g, GRATE, STRUCT, STEEL, x, spans_y, z, w, risers)` | 遇竖向立管自动分段断开格栅、加端梁并套穿层套管，严禁管道刺穿踏板 |
| **工艺管线** | `B.tube(g, m, pts, r, bend=.6)` / `B.flange` / `B.valve` | 折线点列自动生成圆弧弯头管道、法兰盘、带手轮球阀/闸阀 |
| **电力悬链线** | `B.insulator` / `B.string` / `B.catenary(g, m, a, b, sag)` | 复合支柱绝缘子（大小交替伞裙）、悬垂串、抛物线软导线 |
| **安全立体字** | `B.mesh_text(K, C, name, '建筑名称', loc, size, m, rot, extrude)` | 生成中文立体字并**立即转为 `MESH`**，确保 `B.instance()` 总装不丢字 |
| **总装场地** | `B.precast_wall` / `B.road_dashes` / `B.crosswalk` / `B.curbed_lawn` / `B.parking_row` / `B.yard_light` / `B.fire_hydrant` | 预制板围墙、道路虚线、斑马线、带路缘石草坪、带轮挡停车位（自动导出 JSON）、路灯、消火栓 |

---

---

## 三、 建筑与工业设施“三级细节”强制清单（缺一不可）

小模型在写每个部件前，必须核对该部件是否集齐以下三级细节：

1. **办公/公共建筑类（如办公楼、集控楼、门诊楼、公安局主楼）**：
   - **一级（体量）**：主楼层数与层高（通常 `3.6–4.2 m`）、入口裙房或雨棚体量、屋顶楼梯间/电梯机房凸出体量。
   - **二级（立面）**：底部深色勒脚（`0.4–0.8 m`）、开间壁柱（转角加宽）、每层水平腰线、带石材窗套与挑出窗台的分格窗（`B.punched_window`）、主入口双柱挑出雨棚 + 玻璃幕墙门 + 台阶 + 无障碍坡道与不锈钢扶手。
   - **三级（近景）**：女儿墙金属压顶、屋顶防水卷材层、屋顶外机百叶与冷凝风扇、屋顶女儿墙内侧一圈镀锌避雷带（`B.tube`）、雨棚正面立体字（`B.mesh_text`）、后勤门与壁灯。

2. **工业厂房/机房类（如主厂房、过滤室、水泵房、车间、车库）**：
   - **一级（体量）**：大跨度主体、双坡或平顶屋面、屋脊通风器、山墙跨度比例。
   - **二级（立面）**：混凝土勒脚、压型钢板竖肋墙面（`B.ribbed`）、标志性水平色带（山墙处沿屋面坡度斜升 `B.wall_poly`）、上下双层带形采光窗（`B.ribbon_window`）、山墙大型卷帘设备门（`B.roller_door`）+ 旁侧带雨棚人行门（`B.person_door`）。
   - **三级（近景）**：屋面直立锁边肋条、挑檐天沟、四角转角包边条、带管卡的落水管（`B.downpipe`，只在转角或合理柱距设，不要密排成壁柱）、屋脊通风器百叶、外墙检修壁灯、电缆桥架或风道接口。

3. **露天空冷/锅炉/化工/变电设备类（如余热锅炉、冷却塔、主变、开关站、调压站）**：
   - **一级（体量）**：主箱体/塔体/罐群、外露 H 型钢框架（`g.hbeam`）与柱脚混凝土基础墩、柱间 X 形抗风支撑。
   - **二级（通道与管路）**：之字形钢梯塔（`B.zigzag_stair`）或带护笼爬梯（`B.ladder`）、多层格栅走道（`B.grating`）与安全黄/工业蓝栏杆（`B.railing`）、进出主管路（`B.tube`）。
   - **三级（近景）**：箱体竖向加劲肋与水平刚性梁、人孔门、法兰盘（`B.flange`）与手轮阀门（`B.valve`）、穿层套管（`B.split_walkway`）、压力表/控制箱、铭牌与安全警示牌（`B.mesh_text`）、顶部障碍灯与避雷针。

4. **大门/围墙/总装场地类（`PP13` + `SITE`）**：
   - **一级（布局）**：主入口直通前环路、环路围绕主建筑闭合、设备区与办公区动静分区。
   - **二级（门卫与道路）**：带帽门垛、电动推拉门扇（含地轨与开门退让行程、电机箱、导向轮柱）、人行小门、位于围墙线上的门卫室（三面带形窗、宽白檐口、朝院内开门）、车行道虚线、停止线、过街斑马线、带轮挡停车位。
   - **三级（管廊与环境）**：跨路架空管桥（循环水管、燃气管、母线桥，净空 `≥ 5.0 m`）、门卫室内办公桌与显示器、室外空调外机、监控立杆、竖排厂名牌、场区路灯、室外消火栓、克制的沿街行道树与办公区草坪灌木。

### 远/中/近三级细节密度（按 a09 PP12 / PP01 量化，教学/办公楼套用）
**远景（体量与轮廓，aerial / q 视角可读）**
- 开间壁柱 0.45 宽 × 0.16 出挑，**转角加宽到 0.70**（教学楼 0.7–0.8）；层高 3.6–4.2；柱距 3.6 / 4 m 模数。
- 女儿墙 0.9 高 × 0.24 厚 + 铝压顶 0.06 厚、宽 0.42（两侧挑出）。
- 勒脚 0.6 高（范围 0.4–0.8）、四周外扩 0.08。
- 出屋面楼梯间/机房（带门 + 侧百叶 + 压顶）、屋顶冷凝机组。
**中景（立面层次，front / back / gable 视角）**
- 每层腰线 0.28 高 × 0.10 出挑；檐口线脚。
- 窗（每樘约 11 个盒子）：窗套两侧 0.15 宽 × 0.12 出挑、窗楣 0.15、挑出窗台 0.12 高 × 0.26 出挑、比洞口宽 0.40；横档在 0.72h，竖梃 1–2 根只在横档以下；DARK 内衬 + 玻璃退进 0.03。
- **窗后 DARK 室内体量**（教室/内廊进深体量，不只是贴片），防止透过大窗看穿空腔。
- **落水管 + 雨水斗 + 管卡**：只在转角 + 合理柱距（后墙中间 1 根），鹅颈弯（檐口→墙面→地面→出水口外撇），**每 3 m 一个管卡**；离墙 0.30，在腰线/檐口之外。
- 空调机位（百叶外罩 `louvre_bank`）；带形窗竖梃每 1.5 m，洞高 >1.2 加横档。
- 入口雨棚（PP12：7.4×3.6、厚 0.42）+ 2 根 r=0.14 圆柱 + 3 级台阶到 0.6 平台 + 7.2 m 坡道双侧栏杆 h0.9。
**近景（close / entry / roof 视角）**
- **雨棚底面 WHITE 吊顶 + 前缘滴水线**，筒灯装在吊顶下。
- **壁灯**：后勤门/疏散门门顶、门厅侧墙（灯座 + 灯罩）。
- **女儿墙压顶**（铝 0.06）、屋面卷材 0.12 + 分格、避雷带 r=0.012 标高 = 女儿墙顶 + 0.09、每 3 m 支撑卡。
- 玻璃门：4 根竖框 + 中横框 2.45 + 顶框 + 两根拉手；人行门雨罩 + 两根斜拉杆。
- 瓷砖分缝、立体字（`mesh_text`）。
**总体规则**：每个可见立面元素都有"洞口 → 套 → 台"三层；所有出挑在 0.06–0.26 m，不出现 0 厚度贴片；重复构件（竖肋、管卡、百叶）用固定间距循环，不手摆。

---

## 四、 发电站 a01–a09 血泪防坑检查表（交审前必查）

小模型每跑完一版渲染，必须对照以下 14 条硬性检查项逐图自查：

1. **【防爆白】墙面与场地反照率检查**：
   - 浅灰墙板 RGB 不得高于 `(0.55, 0.57, 0.59)`，场地硬质铺装 `PAVE` RGB 控制在 `(0.28, 0.28, 0.30)`。直接使用 `B.standard_palette()`，严禁使用 `(0.85, 0.85, 0.85)` 以上的纯白墙面或地面。
2. **【防穿帮】远景裁剪与 HDRI 背景检查**：
   - 总装渲染必须调 `B.setup_site_review_context()`，相机 `clip_end=6000`，铺设 `±4000 m` 审阅草地并用 `LightPath -> Is Camera Ray` 将背景天空替换为干净蓝灰天空，严禁露出 HDRI 贴图里的模糊高楼或地面黄十字。
3. **【防截断】高耸部件（烟囱/铁塔）全身框入检查**：
   - 高度 `>30 m` 的部件（如 56 m 烟囱、36 m 铁塔），`q` 视角相机距离 `D` 必须 `≥ 2.0 × H`（或焦距 `35–38 mm`），检查渲染图顶部避雷针和底部基础墩必须完整在画面内，不得切顶或切脚。
4. **【防穿模】立管与走道/楼梯碰撞检查**：
   - 凡有竖向管道经过水平格栅平台，必须用 `B.split_walkway()` 分段避让并加套管，且穿层高度处跳过管卡；楼梯塔外移到钢柱外侧，严禁斜梯或泵组撞柱子。
5. **【防悬空/缺口】平台梯口栏杆闭合检查**：
   - 烟囱环形平台、冷却塔顶平台、滤室平台在爬梯/钢梯出口处必须留出通道缺口 `gap`，且两侧必须有内返栏杆（`B.ring_platform` 已内置）。
6. **【防丢字】3D 文字转网格检查**：
   - 所有标牌文字必须使用 `B.mesh_text()`（内部自动 `convert(target='MESH')`），严禁留 `FONT` 曲线物体导致总装 `B.instance()` 丢失文字。
7. **【防陡梯】钢梯倾角检查**：
   - 室外钢梯每跑水平长度 `run` 与爬升高度 `rise` 之比须使倾角在 `35°–42°` 之间，严禁做出 `>48°` 的陡梯。
8. **【防断路】人行步道与斑马线连通检查**：
   - 办公楼与草坪之间留出 `2.5–3.0 m` 铺装步道，穿过车行干道处必须画斑马线（`B.crosswalk`）连通到主厂房或对侧地坪，不能让草坪路缘石把人行路线封死。

9. **【防窗角黑块】`punched_window` 窗套顶角**：
   - 现象：窗套两上角各一个小黑方块。原因：kit 窗套竖条一直到顶，和窗楣共面重叠。修复：项目侧写窗包装函数（如 `school_window()`），竖条只到窗楣下沿，左边框移回洞口内；**不改 kit**。
10. **【防转角黑点】山墙与侧墙重叠**：
   - 现象：楼梯间转角出现黑点（SC02 在 19.3 / 23.1 m）。原因：山墙和南、北墙在转角重叠一段体积，同材质合并后共面。修复：山墙从 `u=T` 起、到 `D−T` 止（T=墙厚）。
11. **【防开放边】`mesh_text` 字形**：
   - 现象：QC 报开放边（字体轮廓自交，焊接后仍在）。原因：字形只有正面或轮廓自交。修复：给文字加 extrude 厚度并封口（cap），或把文字贴在实体底板上遮住背面；焊接距离放到 1e-3。
12. **【防偏暗】kit 材质渲染太黑（如栏杆立柱）**：
   - 现象：栏杆/扶手立柱渲染接近纯黑。原因：kit 原语的材质分配偏暗。修复：项目侧材质覆盖（生成器里替换该材质或在 palette 扩展里覆盖颜色）；**严禁修改 kit 原件**。
13. **【防背景穿帮】单件特写的 HDRI 楼群**：
   - 现象：部件特写背景里有模糊楼群。原因：`C.studio()` 用 city.exr HDRI，`setup_site_review_context` 只管总装。修复：单件特写也用干净天空（`Is Camera Ray` 混入蓝灰 (0.58,0.66,0.75)，如生成器里的 `clean_sky()`）。
14. **【防崩溃】`B.wall_poly` 点数**：
   - 现象：Blender 5.2 下 `faces.new` 抛 TypeError，脚本中断。原因：传入 2 点多边形，而 `Geo.mesh` 只 catch ValueError。修复：`wall_poly` 一律传 **≥3 点**。

---

## 五、 快速启动命令与训练数据记录

1. **复制模板新建生成器**：
   - 参照 [`.agents/skills/city-building-modeling/references/building-generator-template.py`](references/building-generator-template.py) 创建 `tools/pipeline/build_city_<building>_v01.py`。
2. **后台运行与指定部件快速迭代**：
   - 调试单个部件（只跑 `PP04` 的 `q` 视角，跳过总装）：
     ```powershell
     $env:BLD_VERSION='a01'; $env:BLD_PARTS='PP04'; $env:BLD_VIEWS='q'; $env:BLD_ASSEMBLY='0'
     & 'E:\Steam\steamapps\common\Blender\blender.exe' -b -P tools\pipeline\build_city_<building>_v01.py
     ```
   - 全量出图与总装：
     ```powershell
     $env:BLD_VERSION='a01'; $env:BLD_PARTS='all'; $env:BLD_VIEWS='all'; $env:BLD_ASSEMBLY='1'
     & 'E:\Steam\steamapps\common\Blender\blender.exe' -b -P tools\pipeline\build_city_<building>_v01.py
     ```
3. **训练记录与闸门**：
   - 脚本开头自动记 `action_started`，结尾记 `action_finished`。
   - 每次看图自查后写 `inspection`（含 `thumbnail_check` 最显眼 3 特征核对），交用户审阅前跑 `D:\python\python.exe tools/pipeline/finish_part_v01.py --episode <episode_id>`（Windows；**Linux 见 §五.4**）。

4. **Linux 运行与依赖（`finish_part_v01.py` / `record_modeling_step.py`）**：
   - 两个脚本按 `PROJECT = 脚本位置 parents[2]` 推算工程根，需放在工程的 `tools/pipeline/` 下运行（从包内 `scripts/` 拷过去，不要改代码）。
   - **`MODELING_DATASET_ROOT`**：数据集根目录。两个脚本都优先读它。`finish_part` 不设时回退到 Windows 默认路径（Linux 上不可用），所以 Linux 上必须设。
   - **`tools/pipeline/modeling_training_config.json`**：`record_modeling_step` 在没有 `MODELING_DATASET_ROOT` 时读其中的 `dataset_root`，例如 `{"dataset_root": "/workspace/<project>/dataset"}`。
   - **缺失的数据集重建脚本**：`finish_part` 会调用 `build_vlm_dataset_v02.py` 和 `build_code_dataset_v01.py`，原件包里**没有**这两个脚本，BUILD 两行显示 FAILED；不影响门禁判断，可加 `--no-build` 跳过。
   - 命令：
     ```bash
     export MODELING_DATASET_ROOT=/workspace/<project>/dataset
     BLD_VERSION=a01 BLD_PARTS=PP04 BLD_VIEWS=q BLD_ASSEMBLY=0 \
       /workspace/tools/blender-5.2.2-linux-x64/blender -b -P tools/pipeline/build_city_<building>_v01.py
     python3 tools/pipeline/record_modeling_step.py --episode <episode_id> --event-file inspection.json
     python3 tools/pipeline/finish_part_v01.py --episode <episode_id> --no-build
     ```
   - 中文字体在 Linux 上调用 `mesh_text` 时显式传 `font=`（如 `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc`），Noto CJK 实际字高约 size×0.43。
   - **`--event-file` JSON 最少字段**：`kind`（如 `"inspection"`）和 `action_id`（= 生成器写入的 `<episode>-<BLD_VERSION>`）。inspection 还要有 `thumbnail_check`（3 项 `{feature, present}`）、`issues[]`、`next_change`，缺任何一项 finish_part 都报 FAIL。最小示例：
     ```json
     {"kind": "inspection", "action_id": "cn-primary-school-v01-a01r3",
      "thumbnail_check": [{"feature": "立体校名", "present": true},
                          {"feature": "入口雨棚", "present": true},
                          {"feature": "出屋面梯间", "present": true}],
      "issues": ["坡道扶手立柱偏黑"], "next_change": "项目侧覆盖栏杆材质"}
     ```
   - **每次修订用新的 `BLD_VERSION`**（a01 → a01r2 → a01r3）：parent 链按“同一脚本的上一个 action_finished”推算，同一个版本号反复重跑，修订之间的链条分不开。实在不能换版本号，就把修订说明写进 inspection。
   - **调试时用临时数据集根**：用临时 `BLD_VERSION` 跑单件也会往正式 episode 写 action 记录。调试时设 `MODELING_DATASET_ROOT=$(mktemp -d)`，交审的正式运行再指回正式目录。
   - **退出码**：finish_part 有 FAIL 时以 **exit 1** 退出。把输出接到 `| tail` 时管道的返回码是 tail 的，失败会被吞掉，所以先 `set -o pipefail`：
     ```bash
     set -o pipefail
     python3 tools/pipeline/finish_part_v01.py --episode <episode_id> --no-build | tail -n 40 || echo "FINISH_PART FAILED"
     ```
