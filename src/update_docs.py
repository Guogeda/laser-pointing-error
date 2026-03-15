#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档自动更新脚本
在多轮对话后，自动总结并更新项目文档
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class DocumentUpdater:
    def __init__(self):
        self.project_root = project_root
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 文档路径
        self.doc_paths = {
            'requirements': os.path.join(self.project_root, '需求文档-new.md'),
            'claude': os.path.join(self.project_root, 'CLAUDE.md'),
            'findings': os.path.join(self.project_root, 'findings.md'),
            'progress': os.path.join(self.project_root, 'progress.md'),
            'task_plan': os.path.join(self.project_root, 'task_plan.md'),
        }

    def read_file(self, filepath):
        """读取文件内容"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def write_file(self, filepath, content):
        """写入文件内容"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ 已更新: {os.path.basename(filepath)}")

    def update_findings(self, new_findings=None):
        """更新 findings.md"""
        content = self.read_file(self.doc_paths['findings'])

        if new_findings:
            # 在 Research Findings 部分添加新发现
            research_section = "## Research Findings\n"
            if research_section in content:
                insert_pos = content.find(research_section) + len(research_section)
                new_content = content[:insert_pos] + f"\n- **{self.timestamp}**: {new_findings}\n" + content[insert_pos:]
                self.write_file(self.doc_paths['findings'], new_content)
            else:
                print("⚠ 未找到 Research Findings 部分")

    def update_progress(self, phase_actions=None, files_modified=None):
        """更新 progress.md"""
        content = self.read_file(self.doc_paths['progress'])

        if phase_actions or files_modified:
            # 在当前 Phase 的 Actions taken 部分添加
            current_phase_marker = "### Phase 3: Implementation\n"
            if current_phase_marker in content:
                phase_start = content.find(current_phase_marker)
                actions_marker = "- Actions taken:\n"
                if actions_marker in content[phase_start:]:
                    actions_pos = content.find(actions_marker, phase_start) + len(actions_marker)

                    # 构建要插入的内容
                    insert_content = ""
                    if phase_actions:
                        for action in phase_actions:
                            insert_content += f"  - {action}\n"

                    if files_modified:
                        insert_content += "- Files created/modified:\n"
                        for f in files_modified:
                            insert_content += f"  - {f}\n"

                    new_content = content[:actions_pos] + insert_content + content[actions_pos:]
                    self.write_file(self.doc_paths['progress'], new_content)
                else:
                    print("⚠ 未找到 Actions taken 部分")
            else:
                print("⚠ 未找到当前 Phase 部分")

    def update_task_plan(self, completed_tasks=None):
        """更新 task_plan.md"""
        content = self.read_file(self.doc_paths['task_plan'])

        if completed_tasks:
            # 标记任务为完成
            for task in completed_tasks:
                old_task = f"- [ ] {task}"
                new_task = f"- [x] {task}"
                if old_task in content:
                    content = content.replace(old_task, new_task)

            self.write_file(self.doc_paths['task_plan'], content)

    def update_claude_md(self, new_notes=None):
        """更新 CLAUDE.md"""
        content = self.read_file(self.doc_paths['claude'])

        if new_notes:
            # 在 CLAUDE.md 的 Notes 部分或末尾添加
            notes_section = "## 注意事项\n"
            if notes_section in content:
                insert_pos = content.find(notes_section) + len(notes_section)
                new_content = content[:insert_pos] + f"\n### {self.timestamp}\n- {new_notes}\n" + content[insert_pos:]
                self.write_file(self.doc_paths['claude'], new_content)
            else:
                # 添加到文件末尾
                new_content = content + f"\n\n### 更新记录 ({self.timestamp})\n- {new_notes}\n"
                self.write_file(self.doc_paths['claude'], new_content)

    def update_requirements(self, new_requirements=None):
        """更新 需求文档-new.md"""
        content = self.read_file(self.doc_paths['requirements'])

        if new_requirements:
            # 在版本历史部分添加
            version_section = "## 版本历史\n"
            if version_section in content:
                insert_pos = content.find(version_section) + len(version_section)
                new_version = f"- v{datetime.now().strftime('%Y.%m.%d')} ({self.timestamp}) - {new_requirements}\n"
                new_content = content[:insert_pos] + new_version + content[insert_pos:]
                self.write_file(self.doc_paths['requirements'], new_content)
            else:
                print("⚠ 未找到版本历史部分")

    def interactive_update(self):
        """交互式更新文档"""
        import sys
        # 设置控制台编码为 UTF-8
        if sys.platform == 'win32':
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

        print("=" * 60)
        print("文档自动更新工具")
        print("=" * 60)
        print(f"\n当前时间: {self.timestamp}")
        print("\n请提供本次对话的总结信息（留空则跳过该部分）：\n")

        # 收集用户输入
        findings = input("🔍 新发现 (Research Findings): ").strip()
        actions = input("📋 完成的动作 (Actions, 多个用分号分隔): ").strip()
        files = input("📁 修改的文件 (Files, 多个用分号分隔): ").strip()
        tasks = input("✅ 完成的任务 (Tasks, 多个用分号分隔): ").strip()
        claude_notes = input("📌 CLAUDE.md 备注: ").strip()
        req_update = input("📋 需求文档更新: ").strip()

        # 处理输入
        action_list = [a.strip() for a in actions.split(';')] if actions else None
        file_list = [f.strip() for f in files.split(';')] if files else None
        task_list = [t.strip() for t in tasks.split(';')] if tasks else None

        # 执行更新
        print("\n" + "=" * 60)
        print("开始更新文档...")
        print("=" * 60)

        if findings:
            self.update_findings(findings)

        if action_list or file_list:
            self.update_progress(action_list, file_list)

        if task_list:
            self.update_task_plan(task_list)

        if claude_notes:
            self.update_claude_md(claude_notes)

        if req_update:
            self.update_requirements(req_update)

        print("\n✅ 文档更新完成！")

def main():
    updater = DocumentUpdater()

    if len(sys.argv) > 1:
        # 命令行模式
        print("命令行模式暂未实现，请使用交互式模式。")
        updater.interactive_update()
    else:
        # 交互式模式
        updater.interactive_update()

if __name__ == '__main__':
    main()
