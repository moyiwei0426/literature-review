# CLI USAGE

## 当前可用命令

### 1. 查看状态
```bash
python3 scripts/cli.py show-status
```

### 2. 跑检索
```bash
python3 scripts/cli.py run-retrieval --query "large language model literature review automation" --max-results 6
```

### 3. 跑去重
```bash
python3 scripts/cli.py run-dedup --input data/generated/candidates/<file>.json
```

### 4. 跑 parsing demo
```bash
python3 scripts/cli.py run-parsing-demo \
  --paper-id demo-paper \
  --pdf-url https://arxiv.org/pdf/2411.18583v1 \
  --title "Demo Paper"
```

### 5. 跑 extraction demo
```bash
python3 scripts/cli.py run-extraction-demo --input data/generated/chunks/<paper_id>.json --paper-id <paper_id>
```

### 6. 跑 analysis demo
```bash
python3 scripts/cli.py run-analysis-demo --input data/generated/profiles/<paper_id>.json
```

### 7. 跑 gap demo
```bash
python3 scripts/cli.py run-gap-demo \
  --coverage data/generated/analysis_cli/coverage.json \
  --matrix data/generated/analysis_cli/matrix.json \
  --contradiction data/generated/analysis_cli/contradiction.json
```

### 8. 跑 writing demo
```bash
python3 scripts/cli.py run-writing-demo \
  --gaps data/generated/gap_cli/verified_gaps.json \
  --matrix data/generated/analysis_cli/matrix.json \
  --title "Demo Review"
```

## 当前说明
- Retrieval / Dedup / Parsing / Extraction / Analysis / Gap / Writing 都已有最小 CLI 入口
- `run-gap-demo` 当前要求 matrix 为 JSON 文件
- `run-analysis-demo` 现会导出 `coverage.json`、`matrix.json`、`matrix.csv`、`matrix.md`、`contradiction.json`
- 写作阶段当前仍使用 LaTeX compile stub
