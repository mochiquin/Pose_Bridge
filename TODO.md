# Pose_Bridge TODO

## 待办

- [ ] 库里没有动画：Genesis 8 Female 的 `Animations` 文件夹没加入库根目录（偏好里点 From DAZ Importer 可加）

## 已完成

- [x] 启用插件 / 打开文件后库自动恢复：`operators.ensure_library`（有缓存读缓存，没缓存自动扫描，无库文件夹则什么都不做）；Blender 内实测通过（有缓存 0.04s 恢复 8093 条；删缓存后自动扫描并重建缓存）。库文件夹的文件变化仍需手动 Rescan（未做自动发现）

- [x] T-pose 后 FK 骨骼（如 `forearm.fk.L`、手部、手指）动不了：原因是 T-pose 把 MHX 开关复位为 IK 开 + 手指控制开。新增 "T-Pose in FK" 选项（默认开）：复位后四肢 FK、手指控制关；`core/mhx_rules.fk_switch_values` + 4 项 pytest（共 132 项），Blender 内实测通过。MHX 自带的肘部限制（Z 轴锁、X -20°~135°、Y ±90°）不属于 bug，Limits 关掉即可解除

- [x] 核心操作在 Blender 5.2 用 MCP 实测（DAZ 姿势套用、撤销/重做、T-pose、DAZ 动画套用、调整层添加/丢弃）全部正常，测后场景已还原
  - T-pose 会把 MHX 开关复位为默认：IK 全部 =1、手指控制 =开
  - DAZ Importer 套用姿势会把 IK 强制切到 FK（IK=0）；先手动把 IK 打开再套用，结果和 FK 起点完全一致（骨骼位置差 0）

- [x] 配置远程仓库并推送（https://github.com/mochiquin/Pose_Bridge ，main 分支）；新增 README、LICENSE（MIT）、完善 `.gitignore`，作者改为 mochiquin

- [x] 保存目录不存在的 UI 提示：空库时面板也显示 Save Pose 并提示保存位置；保存对话框显示目标目录；无库文件夹时 Scan 报错提示可先保存姿势（Blender 内实测通过）

- [x] core 补测试：新增 `tests/test_index_cache_edges.py`（24 项，`index_cache` 边界 + `natural_key`）；`mhx_rules` 原有测试已完整；修复 `load_cache` 遇到非 UTF-8 缓存文件会崩溃的 bug（现共 128 项通过）

- [x] 初始提交存档（f9e1619），104 项测试 + ruff 通过
- [x] Save Pose 在 Blender 5.2 用 MCP 实测
  - 保存 .pbpose + 缩略图 .png，内容正确（骨骼变换 + 25 个 MHX 开关）
  - 子文件夹自动创建；重名自动加序号；非法字符被清理
  - 往返一致：改动 5 根骨骼后应用保存的文件，与原姿势逐骨一致
  - 保存后新姿势出现在库中并被选中，强制重扫后仍在
  - GroupPro 分组状态（骨架不在视图层）保存成功，缩略图正常，场景状态完全恢复
  - 缩略图失败时姿势仍保存，状态栏提示 "no preview"
