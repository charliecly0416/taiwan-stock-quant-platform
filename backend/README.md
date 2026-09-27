# 清洁版只读 API

后端只负责把 `clean_product` 的统一流程暴露为只读 HTTP API。它不连接数据库、券商、订单系统或登录系统。

```bash
pip install -r requirements.txt
python run.py
```

接口：

- `GET /api/health`：进程存活检查
- `GET /api/ready`：只读产品就绪检查
- `GET /api/tw-stock/config`：模型、策略和数据配置
- `GET /api/tw-stock/data/<name>`：查询已治理数据
- `POST /api/tw-stock/daily`：只读日更 dry-run
- `GET /api/tw-stock/replay?model=...&start=...&end=...`：动态历史回放

实时采集由 `FINMIND_TOKEN` 控制；没有本地数据文件时，回放可以使用仓库内 fixture 做演示，数据查询接口不会把 fixture 当作已采集数据。
