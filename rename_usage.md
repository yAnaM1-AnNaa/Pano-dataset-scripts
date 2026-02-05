# 批量文件重命名工具使用指南

## 功能概览
这个脚本提供多种文件重命名功能，支持关键词替换、添加前后缀、去除数字、正则表达式替换等。

## 基本语法
```bash
python batch_rename.py [选项] [重命名模式]
```

## 使用示例

### 1. 替换关键词
```bash
# 将文件名中的 "lamp" 替换为 "light"
python batch_rename.py -d ./data/source --replace-keyword lamp light --dry-run

# 实际执行（去掉 --dry-run）
python batch_rename.py -d ./data/source --replace-keyword lamp light
```

### 2. 添加前缀
```bash
# 为所有JSON文件添加前缀 "processed_"
python batch_rename.py -d ./data --add-prefix processed_ -p "*.json"
```

### 3. 添加后缀
```bash
# 为所有图片文件添加后缀 "_backup"（在扩展名前）
python batch_rename.py -d ./images --add-suffix _backup -p "*.jpg"
```

### 4. 去除数字
```bash
# 去除所有文件名中的数字
python batch_rename.py -d ./data --remove-digits --dry-run
```

### 5. 正则表达式替换
```bash
# 将连续的数字替换为单个下划线
python batch_rename.py -d ./data --regex "\d+" "_"

# 将空格替换为下划线
python batch_rename.py -d ./data --regex " " "_"
```

### 6. 标准化文件名
```bash
# 标准化：转小写、空格变下划线、去除特殊字符
python batch_rename.py -d ./data --standardize
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `-d, --directory` | 目标目录 | `-d ./data/source` |
| `--dry-run` | 预览模式，不实际执行 | `--dry-run` |
| `-r, --recursive` | 递归处理子目录 | `-r` |
| `-p, --pattern` | 文件匹配模式 | `-p "*.json"` |

## 安全建议
1. **总是先使用 `--dry-run`** 预览重命名结果
2. **备份重要文件** 在批量重命名前
3. **小范围测试** 先在小目录测试，再应用到大目录

## 实际应用场景

### 场景1：清理数据集文件名
```bash
# 1. 预览去除数字后的效果
python batch_rename.py -d ./data/source --remove-digits --dry-run

# 2. 实际执行
python batch_rename.py -d ./data/source --remove-digits
```

### 场景2：统一文件命名格式
```bash
# 标准化所有JSON文件名
python batch_rename.py -d ./annotations --standardize -p "*.json"
```

### 场景3：批量添加版本号
```bash
# 为所有模型文件添加版本后缀
python batch_rename.py -d ./models --add-suffix _v2 -p "*.pth"
```

## 注意事项
- 重命名是不可逆操作，请谨慎使用
- 如果目标文件名已存在，重命名会失败
- 建议在版本控制环境下使用，便于回滚