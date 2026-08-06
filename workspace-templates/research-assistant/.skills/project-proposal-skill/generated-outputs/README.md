# Generated Outputs

本目录只保留固定边界样例和本地调试产物。

- 版本库只跟踪 `sample-*.json` 和本 README，用于验收、guard 和导出测试。
- 普通试跑请优先写到 `/tmp` 或显式临时目录，不要把 `generated-outputs/` 当作长期工作区。
- `*.md`、`req-*.json`、`test-*.json`、`_test_*.json` 等都是本地 render 产物，默认被 `.gitignore` 忽略，不应提交。
