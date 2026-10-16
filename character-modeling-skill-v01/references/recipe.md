# 独立运行与资源

## 依赖

普通Python 3.11及以上，numpy/scipy/scikit-image/Pillow（见requirements.txt）；Blender需其内置Python的bpy、bmesh、numpy、mathutils。已用Blender 5.2.2 LTS测试。较旧版本可能需要适配OBJ导入、CDT或动作API；不要默默安装/更换用户软件。Windows已实测；Linux/macOS入口使用平台无关路径，但尚未实机验证。

在用户允许的位置准备Python环境，按需执行：

```text
python -m pip install -r requirements.txt
```

安装依赖可能联网；建模过程自身不调用图像API、不下载模型。模型构造无需GPU，Cycles可用CPU。高模约126万三角面，运行时和空间用量取决于机器；保留多阶段网格与溯源会占较多空间，事先检查可用空间。

## 完整性检查

解压后可先执行`python -B scripts/verify_package.py`，检查文件是否缺失或被修改。MANIFEST.json记录包内文件哈希；ZIP旁另有整体SHA256。若你有意修改配方，保留修改记录，哈希不匹配不等于造型错误。

## 运行

解压后在包目录运行；路径含空格时加引号：

```text
python -X utf8 -B scripts/run_recipe.py --out "绝对路径/新的输出目录" --blender "Blender可执行文件绝对路径"
```

Windows示例：使用你机器上实际存在的python.exe和blender.exe，不照抄作者机器路径。Linux/macOS也可把PATH内的`blender`传给--blender。

`--prepare-only`仅检查依赖并把配方准备到workspace，不建模；之后用同一参数加`--resume`执行。非空输出默认拒绝，确认是本任务目录后才用--resume；完成阶段必须通过哈希检查。修改配方后建议新输出目录，不把旧done标记当新版本验证。

输出目录必须在包目录之外。入口将TEMP/TMP/TMPDIR、Blender用户配置/脚本/数据、缓存和建模记录指向输出目录；不会移动原有用户配置。普通Python依赖在调用入口前安装。

## 包内结构

- `payload/tools/pipeline/`：原创头/鼻/唇/身体/四肢及绑定案例代码。
- `payload/.agents/skills/game-character-modeling/scripts/`：绕序修正、结构检查、四视图渲染。
- `payload/.agents/skills/game-ear-modeling/scripts/`：从零耳体与局部修形范例。
- `payload/art/references/citizens-clay-male-v01/`：头正/斜/侧候选图。
- 同级`citizen-ear-clay-v01`、`citizen-nose-clay-v01`、`citizen-mouth-clay-v01`：局部白模参考。

payload里的`__CHAR_PROJECT__`、`__CHAR_A18__`、`__CHAR_BLENDER__`是移植占位符，不要直接执行这些模板。入口复制代码到输出workspace后，将占位符替换为本次实际路径再执行。没有指向原项目的绝对路径，也不需要原项目资产。

## 配方范围与依赖顺序

基础头剖面/约束三角化→头部绕序与比例调整→颌颈→耳体/局部修形/双耳装配→鼻体/连接环/局部平顺→嘴唇面与接触轮廓→下巴→肩胸→手臂→手掌手指→腹腰背→骨盆双腿分趾足→腰足连接平顺→结构与四视图→22骨行走→全帧/局部检查及打包。

头部约24cm、全身约178cm均为配方设计尺寸。实际OBJ厘米/Y上/−Z前；绑定blend米制/Z上/+Y前。render/inspection.blend是归一化检查场景，不是引擎单位文件。使用deliverable中的rest/walk场景保留米制。

## 交付位置

- `deliverable/citizen-rest.blend`：全身白模+骨架，REST姿势。
- `deliverable/citizen-walk.blend`：32帧/24fps原地循环，第33帧闭合关键帧。
- `deliverable/citizen-original-cm.obj`：源码重新生成网格，无UV。
- `deliverable/walk-preview.gif`、rest/head/hand/foot/side PNG：实际模型渲染。
- `inspection.json`、`boundary-classification.json`、`deliverable/additional-audit.json`及workspace动作检查：结构和动画数值。
- 每步log/done、recipe-manifest.json、environment.json及records：过程证据。

运行器验证子进程退出及预期产物，但不会自动判外观通过。失败查看对应log，不要反复覆盖输入、忽略异常或拿旧文件冒充新结果。

本包封装后实际运行记录见[portable-test.json](portable-test.json)。验证的是包内代码可执行与产物齐全，不是造型通过。
