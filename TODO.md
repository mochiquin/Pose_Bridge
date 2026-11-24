# Pose_Bridge TODO

## 待办

- [ ] 配置远程仓库并推送
- [ ] 首次保存前，保存目录不存在所以不在库根目录里（保存一次后正常）：是否需要在 UI 里提示

## 已完成

- [x] core 补测试：新增 `tests/test_index_cache_edges.py`（24 项，`index_cache` 边界 + `natural_key`）；`mhx_rules` 原有测试已完整；修复 `load_cache` 遇到非 UTF-8 缓存文件会崩溃的 bug（现共 128 项通过）

- [x] 初始提交存档（f9e1619），104 项测试 + ruff 通过
- [x] Save Pose 在 Blender 5.2 用 MCP 实测
  - 保存 .pbpose + 缩略图 .png，内容正确（骨骼变换 + 25 个 MHX 开关）
  - 子文件夹自动创建；重名自动加序号；非法字符被清理
  - 往返一致：改动 5 根骨骼后应用保存的文件，与原姿势逐骨一致
  - 保存后新姿势出现在库中并被选中，强制重扫后仍在
  - GroupPro 分组状态（骨架不在视图层）保存成功，缩略图正常，场景状态完全恢复
  - 缩略图失败时姿势仍保存，状态栏提示 "no preview"
