# Web Demo

隔离的浏览器入口，所有 Web 相关文件只放在 `web/` 下，不改动现有 `pipeline.py` 和 `util/` 的处理逻辑。

## 功能

- 左侧 6 个参数面板
- 两个上传按钮：图片 + Labelme JSON
- 右上角即时参数 demo：三角形、六边形、不规则多边形
- 右下角真实任务运行进度、日志和 overlay 输出
- 后端逐步调用现有 `pipeline.py` 的四个子命令，不改现有项目结构

## 启动

```bash
python3 web/server.py
```

默认地址：

```text
http://127.0.0.1:8000
```

## 说明

- 图片和 JSON 文件名主干必须一致
- JSON 需要是 Labelme 格式，并带 `imageWidth`、`imageHeight`、`shapes`
- 真实 pipeline 仍依赖原项目已有 Python 库，例如 `shapely`、`scipy`、`Pillow`、`matplotlib`
- 如果这些依赖未安装，Web 界面可以打开，但点击 `Run` 时后端会返回简短错误信息
