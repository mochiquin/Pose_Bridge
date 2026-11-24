# AGENTS.md — Pose_Bridge 开发契约

## 1. 架构红线
- `core/`（纯 Python）：库扫描、过滤、缓存、命名、叠加层规划。**严禁**导入 `bpy`、`mathutils`、`bmesh`、`executor/`。
- `executor/`、`properties.py`、`operators.py`、`ui_panel.py`、`preferences.py`、`__init__.py`（宿主层）：只读写 Blender 数据、调用 DAZ Importer 操作符，不堆业务判断。
- 路径一律使用 `pathlib.Path`，不使用 `os.path`。包内使用显式相对导入。

## 2. 领域红线
- **GroupPro 分组**：角色可能只由 `gp_*` 空物体以集合实例显示，骨架不在视图层里。任何需要骨架在视图层的操作，必须通过 `executor/group_mount.py` 临时挂载集合，并在 `try/finally` 中恢复原状，出错也必须恢复。
- 不删除、不重命名用户的集合、空物体和对象；不保存、不覆盖用户的 .blend 工程。
- 依赖 DAZ Importer（GPL）：只调用其操作符，不复制其代码。

## 3. 工作流
1. 先规划后动手：新需求先出修改计划，用户确认后再改代码。
2. 修改 `core/` 必须同步新增或更新 `tests/` 里的 pytest。
3. 每次修改 `.py` 后执行 `python -m pytest -v` 与 `ruff check .`，必须全部通过。
4. 宿主层改动在 Blender 5.2 中用 MCP 实测；不做 Octane 无头测试。
