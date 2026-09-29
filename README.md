# 共炉保温编排台

本地单页应用：为 2～3 种需要在同一台炉子里分别完成连续保温的材料，
编排一条满足全部约束的**最短炉温设定曲线**；长度相同取温度序列
**字典序最小**的方案。

- 后端：Python + FastAPI（求解核心见 `app/solver.py`，纯标准库 BFS）
- 前端：原生 HTML / CSS / JavaScript（`static/`，无任何前端构建与框架）

## 一条命令启动

需要 Docker（含 Compose 插件）。

```bash
docker compose up --build -d
```

启动后浏览器访问：

- 页面：<http://localhost:8000/>
- 健康检查：<http://localhost:8000/healthz>
- 接口文档（FastAPI 自带）：<http://localhost:8000/docs>

停止：

```bash
docker compose down
```

端口在 `docker-compose.yml` 的 `ports` 中修改（宿主端口在冒号左侧）。

### 不用 Docker（可选）

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 业务规则

### 材料（2～3 种）

- 保温下限 / 上限：40～180°C 的整十数，下限不高于上限；
- 连续保温时长：5、10 或 15 分钟（对应 1、2、3 个连续档位）；
- 耐受上限：不低于保温上限、至多 200°C 的整十数。

### 炉温曲线

- 炉温初态 20°C；
- 每档持续 5 分钟，设定温度为 20～200°C 的整十数；
- 首档与初态温差、相邻档温差均不超过 20°C；
- 末档必须回到 20°C；
- 所有档位温度都不得超过**任何**材料的耐受上限；
- 只有连续达到所需时长（5 分钟一档）的档位全部落在该材料的保温区间
  `[下限, 上限]` 内，该材料才算达标；
- 不同材料可以共用同一档位；材料一旦达标，后续档位对它不再有要求。

### 目标

- 总档数 ≤ 20 的前提下，求档数最少的完整曲线；
- 最短解有多条时，取温度序列字典序最小（例如先升 40°C 排在先升 60°C
  之前）；
- 有解：展示曲线图、各材料**首次达标**的连续档位区间、逐档明细表，
  以及被多种材料共用的档位；
- 无解：页面给出明确的中文原因，**不展示任何部分方案**；
- 修改任意输入后，旧结果立即清除。

## 求解算法

在档位最多 20、温度只有 19 个整十值的规模下，直接做广度优先搜索：

- 状态 = `(当前温度, 各材料连续保温进度)`；进度为“当前已连续处于其区间
  内的档数”，达标后记为完成态；
- 从初态 `(20, 全 0)` 出发，按温度**升序**扩展下一档（温差 ≤ 20、
  不超过耐受上限）。BFS 保证档数最少，同层按温度升序入队保证温度序列
  字典序最小；
- 目标状态：当前温度回到 20°C 且所有材料均已完成；
- 扩展深度超过 20 即停止；搜不到目标即为无解。
- 另含一个保守的无解预检（如保温下限高于所有耐受上限的最小值），
  用于给出更具体的原因；预检通过不代表必然有解，最终以 BFS 为准。

## API

`POST /api/schedule`

```json
{
  "materials": [
    {"name": "材料A", "holdLow": 60, "holdHigh": 100, "duration": 10, "tolerance": 150},
    {"name": "材料B", "holdLow": 80, "holdHigh": 120, "duration": 5,  "tolerance": 160}
  ]
}
```

成功（HTTP 200）：

```json
{
  "solvable": true,
  "temperatures": [40, 60, 80, 80, 100, 80, 60, 40, 20],
  "stepCount": 9,
  "totalMinutes": 45,
  "toleranceCap": 150,
  "steps": [
    {"index": 1, "temperature": 40, "minutes": 5, "deltaFromPrev": 20,
     "inWindow": [], "shared": false}
  ],
  "windows": [
    {"material": "材料A", "startStep": 3, "endStep": 4,
     "steps": [3, 4], "temperatures": [80, 80], "minutes": 10}
  ],
  "sharedSteps": [3, 4],
  "materials": [ ... ]
}
```

无解（HTTP 200，便于页面区分“无解”与“参数错误”）：

```json
{"solvable": false, "reason": "在 20 档以内找不到满足全部约束并回到 20°C 的完整曲线。"}
```

参数非法时返回 HTTP 422，`detail` 为中文错误说明。

## 目录结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI 路由与参数校验
│   └── solver.py      # 规则常量、校验与 BFS 求解
├── static/
│   ├── index.html     # 页面
│   ├── styles.css     # 样式
│   └── app.js         # 表单、请求、结果与 SVG 曲线渲染
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```
