# `system_design.json`

用于保存设计阶段产物，回答“系统具体怎么组织”。

```json
{
  "project_structure": {
    "directories": [],
    "modules": []
  },
  "contracts": [],
  "data_flow": [],
  "mvp_plan": {
    "in_scope": [],
    "out_of_scope": [],
    "milestones": [],
    "first_deliverable": ""
  }
}
```

关键字段：

* `project_structure.directories`：目录级组织方式
* `project_structure.modules`：模块级组织方式
* `contracts`：模块或角色之间的交接契约
* `data_flow`：关键流程的数据流转路径
* `mvp_plan.in_scope`：本轮明确纳入的范围
* `mvp_plan.out_of_scope`：明确排除的范围
* `mvp_plan.milestones`：关键里程碑
* `mvp_plan.first_deliverable`：当前第一交付目标
