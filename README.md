# Pose Bridge

Blender 5.2 插件：在 3D 视图侧边栏里浏览 DAZ 姿势 / 动画库，一键套用到 MHX 骨架上；也可以把当前姿势保存成自己的姿势库。

> 版本 0.1.0 · 分类：Animation · 位置：`View3D > Sidebar > Pose Bridge`

## 功能

- **缩略图库浏览**：扫描一个或多个文件夹（递归），按文件夹层级导航，支持分页、按名称/文件夹搜索、按姿势/动画过滤。大型库带缓存，不用每次重新扫描。
- **一键套用**：选中缩略图后套用到目标骨架，支持撤销 / 重做（按角色记录，包括手动调整的关节）。
- **T-pose**：把目标骨架恢复到默认姿势，MHX 开关复位并移除动作。默认勾选 **T-Pose in FK**：复位后四肢保持 FK、手指控制关闭，所有关节（如 `forearm.fk.L`）都能直接摆；取消勾选则保持 MHX 默认（IK 开），此时 FK 骨骼不会带动角色。
- **调整层（Adjust Layer）**：保留已套用的动画不动，在上面新增一层，之后 K 的关键帧以偏移量的形式存进新层，原动画不会被修改。
- **保存姿势**：把当前姿势存成 `.pbpose` 文件（可附带缩略图），自动出现在库里，往返应用结果一致。重名不覆盖，会自动加序号。
- **GroupPro 兼容**：角色只由 `gp_*` 空物体以集合实例显示、骨架不在视图层时也能正常工作，临时挂载的集合在操作结束后一定会恢复。
- **MHX 手指控制**：套用 DAZ 姿势时自动关闭对应侧的手指控制开关，保证手指姿势可见。

## 依赖

- Blender 5.2
- [DAZ Importer](https://bitbucket.org/Diffeomorphic/import_daz)：套用 DAZ 的 `.duf` 姿势 / 动画时需要。插件只调用它的操作符，不包含它的代码。套用 Pose Bridge 自己的 `.pbpose` 文件不需要它。

## 安装

1. 把本仓库放进 Blender 的插件目录，文件夹名保持 `Pose_Bridge`：

   ```text
   %APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\Pose_Bridge
   ```

2. 在 Blender 的 `Edit > Preferences > Add-ons` 里启用 **Pose Bridge**。
3. 在插件偏好设置里点 **Add Folder** 添加库文件夹，或点 **From DAZ Importer** 自动添加 DAZ 的 `Poses` / `Animations` 目录。
4. 回到 3D 视图侧边栏的 **Pose Bridge** 标签，选择目标骨架，点 **Scan**。

之后每次启用插件或打开 .blend 文件，库会自动从缓存恢复（没有缓存时自动扫描一次），不需要再点 Scan。库文件夹里新增或删除了文件时，点 **Rescan** 重新扫描。

启用插件和添加文件夹后，请用正常方式退出 Blender，偏好设置才会被保存。

## 使用

1. 选择 **Target Rig**（目标骨架），点 **Scan** 读取库（**Rescan** 强制重新扫描）。
2. 点文件夹进入，点缩略图下方的名字选中姿势 / 动画，点 **Apply** 套用。
3. 不满意可以 **Undo** / **Redo**；想回到默认姿势点 **T-pose**。
4. 套用动画后想微调：点 **Add Adjust Layer**，摆骨骼并按 `I` 打关键帧；不要了点 **Discard**。
5. 保存当前姿势：点 **Save Pose...**，填名称和可选的子文件夹（如 `Maria/Sitting`），确认。

### 保存位置

默认保存到：

```text
%APPDATA%\Blender Foundation\Blender\5.2\config\Pose Bridge Poses
```

可以在插件偏好设置的 **Saved Poses Folder** 里改。这个文件夹第一次保存时才会创建，之后自动算作库的根目录。

## 开发

项目分两层：

- `core/`：纯 Python（库扫描、过滤、缓存、命名、叠加层规划），不导入 `bpy`，可以直接用 pytest 测试。
- `executor/`、`operators.py`、`ui_panel.py`、`properties.py`、`preferences.py`：宿主层，只读写 Blender 数据和调用 DAZ Importer 的操作符。

```bash
pip install pytest ruff
python -m pytest -v
ruff check .
```

开发约定见 [AGENTS.md](AGENTS.md)。

## 许可证

[MIT](LICENSE) © 2026 mochiquin

本插件依赖的 DAZ Importer 使用 GPL，插件只通过其操作符调用，不包含它的代码。
