# Scripts

这里放从仓库根目录运行的任务入口。脚本负责组装参数、调用 `code/a_drying/` 中的代码并写出结果，不应重复实现模型核心逻辑。

建议入口：

```text
prepare_data.py
solve_problem1.py
solve_problem2.py
solve_problem3.py
solve_problem4.py
export_results.py
make_figures.py
```
