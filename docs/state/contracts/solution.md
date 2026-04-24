# `solution.json`

用于保存方案阶段产物，回答“整体准备怎么做”。

```json
{
  "selected_stack": {
    "frontend": "",
    "backend": "",
    "database": "",
    "agent_framework": "",
    "deployment": ""
  },
  "module_mapping": [],
  "risks": [],
  "alternatives": []
}
```

字段说明：

* `selected_stack`：当前选定的技术栈
* `module_mapping`：方案层的模块划分与职责映射
* `module_mapping[].module`：模块名称
* `module_mapping[].responsibilities`：该模块承担的职责列表
* `module_mapping[].covers_requirements`：该模块直接承接的需求或能力点
* `module_mapping[].depends_on`：该模块依赖的其他模块
* `module_mapping[].tech_note`：可选的模块级技术说明
* `risks`：当前方案的主要风险点
* `alternatives`：被考虑过的备选方案

约束：

* `module_mapping` 只描述方案层模块，不写文件名、类名、接口参数等设计细节
* 当还没有任何有效模块方案时，`module_mapping` 应为空数组，而不是放空壳对象
* `depends_on` 只写内部模块依赖，不写第三方库依赖
* 如果某项内容已经细到 API、目录、数据结构，应下沉到 `system_design.json`
