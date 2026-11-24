# Pose_Bridge TODO

## 待办
- [ ] Save Pose：GroupPro 分组角色（骨架不在视图层）的保存实测（需要一个分组场景；缩略图代码已走 `mounted`）
- [ ] Save Pose：缩略图失败时姿势仍保存的路径实测（代码有 try/except，未触发过）
- [ ] 为 `core/index_cache.py`、`core/mhx_rules.py` 补充 pytest
- [ ] 配置远程仓库并推送

## 已完成
- [x] 初始提交存档（f9e1619），104 项测试 + ruff 通过
- [x] Save Pose 在 Blender 5.2 用 MCP 实测（普通骨架）
  - 保存 .pbpose + 缩略图 .png，内容正确（骨骼变换 + 25 个 MHX 开关）
  - 子文件夹自动创建；重名自动加序号（test one → test one 2）；非法字符被清理（bad:/na*me? → bad na me）
  - 往返一致：改动 5 根骨骼后应用保存的文件，与原姿势逐骨一致
  - 偏好设置、骨架状态测后均已恢复
