---
name: auto-document-update
enabled: true
event: stop
pattern: .*
action: warn
---

📝 **对话结束提醒**

在结束之前，请考虑运行文档更新脚本：

```bash
python src/update_docs.py
```

这个脚本会：
1. 自动总结本次对话内容
2. 更新 @需求文档-new.md
3. 更新 @CLAUDE.md
4. 更新 @findings.md
5. 更新 @progress.md
6. 更新 @task_plan.md

---

*如果你已经手动更新了文档，可以忽略此提醒。*
