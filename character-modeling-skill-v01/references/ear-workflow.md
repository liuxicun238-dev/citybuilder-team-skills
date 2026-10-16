# 从零耳体与装配

参考见payload/art/references/citizen-ear-clay-v01/reference.png。先读外轮廓、耳轮、对耳轮及分叉、耳轮脚、耳甲腔、耳屏、对耳屏、耳垂关系。单图看不到的背侧属于假设，本例耳高6.5cm是设计尺寸。

build-ear-example.py把参考二维曲线映射到局部厘米坐标，用主体隐式体积、脊线和凹腔构造耳体。脊线末端减高度和截面融入主体，避免细管堆薄片；耳甲腔真正凹下，耳屏有遮挡关系。轻滤波后marching cubes生成连续面；只剔除确认的小游离点，大组件分离需诊断。

refine-ear-example.py对耳屏局部平顺。装配代码assemble_head_ear_preview_v02.py按本头尺度/角度镜像安装，检查镜像后的绕序与正侧背大小。独立耳朵好看不等于头上合适；当前耳根是交叠试装，尚未焊接。

两脚本在payload/.agents/skills/game-ear-modeling/scripts/，由入口准备路径并运行。内部数值来自当前单图，不是所有人耳的通用尺寸。新人物先调整参考曲线、局部尺度和耳位，再实际看独立耳与整头。
