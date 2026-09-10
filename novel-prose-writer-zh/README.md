# novel-prose-writer-zh

独立中文小说正文生成 Skill。

## 它只干一件事

你随便给一句小说相关输入，它直接写正文。

不需要 Main，不需要 Writer Runtime，不需要 Human Writing L2，不需要项目目录，也不需要结构化表格。

## 可以这样用

```text
用 novel-prose-writer-zh 写：
一个修仙杂役半夜回来，发现同屋师兄的床铺空着，桌上还留着半碗没吃完的面。写 800 字左右。
```

```text
用 novel-prose-writer-zh 继续下面正文，直接往下写 1000 字：
<贴正文>
```

```text
用 novel-prose-writer-zh 把下面这段重写得像正常中文网文，不增加剧情：
<贴正文>
```

```text
用 novel-prose-writer-zh 写一章。
人物：……
这一章发生：……
结尾停在：……
```

甚至可以只说：

```text
用 novel-prose-writer-zh 随便写一段都市异能小说给我看，1000 字。
```

它会自己判断是 SCENE / CHAPTER / CONTINUE / REWRITE / FREEWRITE。

## 默认行为

- 只输出小说正文；
- 自然现代中文白话；
- 题材不自动古风化；
- 人物思考不写成方案分析报告；
- 不把大纲 bullet 一项一段机械翻译；
- 不为了“像人”故意加错字和废话；
- 不默认全文 humanize；
- 不依赖任何外部工作流。

## 可选参考文风

如果你贴一段你喜欢的真人正文并说“参考这种写法”，Skill 会读取 `references/VOICE_GUIDE.md`。

它只学习句子运动、叙事距离、对白衔接、心理停点和普通度，不复制原句、专名、桥段或独特比喻。

## 文件

```text
novel-prose-writer-zh/
├── SKILL.md
├── README.md
└── references/
    ├── INPUT_ADAPTER.md
    ├── WRITE_CORE.md
    ├── VOICE_GUIDE.md
    └── LOCAL_REPAIR.md
```

## 状态

```yaml
standalone: true
external_runtime_required: false
main_workflow_required: false
human_writing_l2_required: false
project_files_required: false
output_default: novel_prose_only
```
