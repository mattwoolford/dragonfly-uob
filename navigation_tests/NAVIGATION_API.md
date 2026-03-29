# NavigationInterface API Reference

> `navigation_test2.py` — Dragonfly UoB 导航模块接口文档
> `navigation_test2.py` — Navigation module interface reference for Dragonfly UoB

---

## 目录 / Contents

1. [快速接入 / Quick Start](#1-快速接入--quick-start)
2. [状态机 / State Machine](#2-状态机--state-machine)
3. [构造函数 / Constructor](#3-构造函数--constructor)
4. [公开接口 / Public API](#4-公开接口--public-api)
   - [connect()](#41-connect)
   - [get_status()](#42-get_status)
   - [goto()](#43-goto)
   - [hold()](#44-hold)
   - [cancel()](#45-cancel)
   - [rth()](#46-rth)
   - [check_safety()](#47-check_safety)
   - [get_distance_to_target()](#48-get_distance_to_target)
   - [start_refresh() / stop_refresh()](#49-start_refresh--stop_refresh)
5. [地理围栏规则 / Geofence Rules](#5-地理围栏规则--geofence-rules)
6. [错误码 / Error Codes](#6-错误码--error-codes)
7. [典型调用流程 / Typical Call Flow](#7-典型调用流程--typical-call-flow)

---

## 1. 快速接入 / Quick Start

```python
import asyncio
from navigation_test2 import NavigationInterface

async def main():
    nav = NavigationInterface(refresh_interval=5.0)

    # 1. 连接飞控 / Connect to flight controller
    await nav.connect()                        # 默认 udp://:14540

    # 2. 发送目标点（非阻塞）/ Send target (non-blocking)
    await nav.goto(lat=51.4224, lon=-2.6670, alt=20.0)

    # 3. 地面站轮询状态 / Ground station polls status
    while True:
        status = nav.get_status()
        print(status)
        if status["state"] in ("ARRIVED", "ERROR"):
            break
        await asyncio.sleep(5)

    # 4. 关闭刷新任务 / Stop background refresh
    nav.stop_refresh()

asyncio.run(main())
```
---

## 2. 状态机 / State Machine

### 状态定义 / State Definitions

| 状态值 / Value | 含义（中）| Meaning (EN) |
|---|---|---|
| `IDLE` | 未连接 | Not connected |
| `CONNECTING` | 正在建立连接 | Establishing connection |
| `CONNECTED` | 已连接，待命 | Connected, standby |
| `FLYING` | 正在飞往目标 | Flying to target |
| `HOVERING` | 悬停中 | Hovering in place |
| `ARRIVED` | 已到达目标（距目标 < 2 m）| Arrived at target (dist < 2 m) |
| `RTH` | 正在返航 | Returning to launch |
| `ERROR` | 发生错误 | Error occurred |

### 状态转移图 / State Transition Diagram

```
IDLE
 └─ connect() ──────────────► CONNECTING
                                  │
                         成功/OK  │  失败/FAIL
                                  ▼
                              CONNECTED ◄──────────────────┐
                                  │                        │
                  goto(合法点)    │   goto(非法点)         │
                                  ▼       ▼                │
                              FLYING   ERROR               │
                                  │                        │
              到达(<2m)/ARRIVED   │   hold()/cancel()      │
                                  ▼       ▼                │
                              ARRIVED  HOVERING            │
                                  │                        │
                              rth()                        │
                                  ▼                        │
                               RTH ──────────────────────►─┘
```

> **注意 / Note**：`hold()` 与 `cancel()` 可在 `FLYING` 状态下随时调用，都会切换到 `HOVERING`。
> `hold()` and `cancel()` can be called at any time during `FLYING` and both transition to `HOVERING`.

---

## 3. 构造函数 / Constructor

```python
NavigationInterface(drone_instance=None, refresh_interval=5.0)
```

| 参数 / Parameter | 类型 / Type | 默认值 / Default | 说明 / Description |
|---|---|---|---|
| `drone_instance` | `mavsdk.System` \| `None` | `None` | 传入已有 System 实例复用；为 None 时内部自动创建 / Pass an existing System to reuse; creates one internally if None |
| `refresh_interval` | `float` | `5.0` | 后台状态刷新间隔（秒）/ Background status refresh interval (seconds) |

---

## 4. 公开接口 / Public API

---

### 4.1 `connect()`

```python
async def connect(address: str | None = None) -> bool
```

**功能 / Description**
智能连接飞控，连接成功后自动启动后台状态刷新协程。
Smart connection to the flight controller; automatically starts the background refresh loop on success.

**参数 / Parameters**

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `address` | `str \| None` | `None` | 连接地址。为 None 时先检测已有连接，无则使用 `udp://:14540` / Connection address. If None, checks for an existing connection first, then falls back to `udp://:14540` |

**推荐地址 / Recommended addresses**

| 场景 / Scenario | 地址 / Address |
|---|---|
| 仿真 SITL / Simulation | `udpin://0.0.0.0:14540` |
| 实机 RPi 5 / Real drone RPi 5 | `serial:///dev/ttyAMA0:57600` |

**返回值 / Returns**
`True` — 连接成功 / Connected
`False` — 连接失败 / Failed

**状态变化 / State transition**
`IDLE → CONNECTING → CONNECTED`（成功）
`IDLE → CONNECTING → ERROR`（失败）

**示例 / Example**
```python
ok = await nav.connect("udpin://0.0.0.0:14540")
if not ok:
    print(nav.get_status()["error"])
```

---

### 4.2 `get_status()`

```python
def get_status() -> dict
```

**功能 / Description**
返回当前无人机完整状态快照，是地面站的**主要轮询入口**。所有字段均可直接序列化为 JSON。
Returns the current UAV status snapshot — the **primary polling entry point** for the ground station. All fields are directly JSON-serialisable.

**返回字段 / Return fields**

| 字段 / Field | 类型 / Type | 说明 / Description |
|---|---|---|
| `state` | `str` | 当前状态机值，见 [状态定义](#状态定义--state-definitions) / Current state machine value |
| `lat` | `float \| None` | 当前纬度（WGS-84）/ Current latitude (WGS-84) |
| `lon` | `float \| None` | 当前经度 / Current longitude |
| `alt` | `float \| None` | 当前绝对高度（AMSL，米）/ Current absolute altitude (AMSL, m) |
| `target_lat` | `float \| None` | 目标纬度；无任务时为 `None` / Target latitude; `None` when no mission |
| `target_lon` | `float \| None` | 目标经度 / Target longitude |
| `target_alt` | `float \| None` | 目标高度 / Target altitude |
| `progress_pct` | `float` | 任务完成百分比 `0.0–100.0` / Mission completion percentage |
| `remaining_m` | `float \| None` | 剩余距离（米）；无任务时为 `None` / Remaining distance (m); `None` when no mission |
| `error` | `str` | 错误原因码；无错误时为 `""` / Error reason code; `""` when no error |
| `timestamp` | `float` | 快照 Unix 时间戳（秒，3位小数）/ Snapshot Unix timestamp (s, 3 decimal places) |

**示例输出 / Example output**
```json
{
  "state": "FLYING",
  "lat": 51.422180,
  "lon": -2.668500,
  "alt": 89.3,
  "target_lat": 51.4224,
  "target_lon": -2.6670,
  "target_alt": 20.0,
  "progress_pct": 63.5,
  "remaining_m": 48.2,
  "error": "",
  "timestamp": 1741420800.123
}
```

> **建议轮询间隔 / Recommended poll interval**：与 `refresh_interval` 保持一致（默认 5 s）。

---

### 4.3 `goto()`

```python
async def goto(lat: float, lon: float, alt: float) -> bool
```

**功能 / Description**
核心导航指令。执行地理围栏安全检查后向飞控发送目标位置，**立即返回（非阻塞）**，进度由后台刷新协程自动维护，地面站通过 `get_status()` 轮询即可。
Core navigation command. Performs geofence safety checks, sends the target position to the FC, and **returns immediately (non-blocking)**. Progress is maintained by the background refresh loop; poll via `get_status()`.

**参数 / Parameters**

| 参数 | 类型 | 说明 |
|---|---|---|
| `lat` | `float` | 目标纬度（WGS-84）/ Target latitude (WGS-84) |
| `lon` | `float` | 目标经度 / Target longitude |
| `alt` | `float` | 目标高度（**相对高度，米**，上限 50 m）/ Target altitude (**relative, metres**, max 50 m) |

**返回值 / Returns**
`True` — 指令已发送，状态切换为 `FLYING`
`False` — 安全检查未通过，状态切换为 `ERROR`，原因见 `get_status()["error"]`

**到达判定 / Arrival detection**
后台协程检测到距目标 **< 2 m** 时自动切换至 `ARRIVED`，`progress_pct` 置为 `100.0`。
The background coroutine automatically switches to `ARRIVED` and sets `progress_pct` to `100.0` when within **2 m** of the target.

**示例 / Example**
```python
ok = await nav.goto(51.4224, -2.6670, 20.0)
if not ok:
    print("拦截原因:", nav.get_status()["error"])
```

---

### 4.4 `hold()`

```python
async def hold() -> None
```

**功能 / Description**
R09：立即暂停当前任务，无人机原地悬停。任务目标与进度数据**保留**，可通过再次调用 `goto()` 恢复飞行。
R09: Immediately pause the current mission; the drone hovers in place. Mission target and progress data are **preserved**; call `goto()` again to resume.

**状态变化 / State transition**
`FLYING → HOVERING`（任意状态均可调用）

**示例 / Example**
```python
await nav.hold()
# get_status()["state"] == "HOVERING"
```

---

### 4.5 `cancel()`

```python
async def cancel() -> None
```

**功能 / Description**
取消当前飞行任务：发送悬停指令，**同时清空目标点和进度数据**。之后需重新调用 `goto()` 才能继续飞行。
Cancel the current flight mission: sends a hold command and **clears target and progress data**. A new `goto()` call is required to resume flight.

**与 `hold()` 的区别 / Difference from `hold()`**

| | `hold()` | `cancel()` |
|---|---|---|
| 飞控指令 / FC command | `action.hold()` | `action.hold()` |
| 目标点保留 / Target preserved | ✅ | ❌ 清空 / Cleared |
| 进度保留 / Progress preserved | ✅ | ❌ 重置为 0 / Reset to 0 |
| 状态 / State | `HOVERING` | `HOVERING` |
| 恢复方式 / Resume | 重新 `goto()` | 重新 `goto()` |

**状态变化 / State transition**
`FLYING → HOVERING`，`target_*` 全部置 `None`，`progress_pct = 0.0`

**示例 / Example**
```python
await nav.cancel()
status = nav.get_status()
# status["state"]       == "HOVERING"
# status["target_lat"]  == None
# status["progress_pct"] == 0.0
```

---

### 4.6 `rth()`

```python
async def rth() -> None
```

**功能 / Description**
R09：触发自动返航（Return to Launch）。飞控将自动飞回起飞点并降落。
R09: Trigger automatic Return to Launch (RTL). The FC will fly back to the launch point and land.

**状态变化 / State transition**
`任意 → RTH`

**示例 / Example**
```python
await nav.rth()
# get_status()["state"] == "RTH"
```

---

### 4.7 `check_safety()`

```python
def check_safety(lat: float, lon: float, alt: float) -> tuple[bool, str]
```

**功能 / Description**
R30 地理围栏预检查（纯逻辑，无网络调用）。`goto()` 内部自动调用，也可单独使用。
R30 geofence pre-check (pure logic, no network calls). Called internally by `goto()`; can also be used standalone.

**返回值 / Returns**

| 情况 / Case | 返回 / Return |
|---|---|
| 安全 / Safe | `(True, "SAFE")` |
| 目标在飞行区域外 / Outside flight area | `(False, "OUTSIDE_FLIGHT_AREA")` |
| 目标在 SSSI 禁飞区内 / Inside SSSI NFZ | `(False, "INSIDE_SSSI_NFZ")` |
| 高度超限 / Altitude too high | `(False, "ALTITUDE_TOO_HIGH")` |

**示例 / Example**
```python
ok, reason = nav.check_safety(51.4224, -2.6670, 20.0)
# ok=True, reason="SAFE"

ok, reason = nav.check_safety(51.4224, -2.6670, 99.0)
# ok=False, reason="ALTITUDE_TOO_HIGH"
```

---

### 4.8 `get_distance_to_target()`

```python
async def get_distance_to_target(target_lat: float, target_lon: float) -> float
```

**功能 / Description**
从遥测流读取当前位置，用 Haversine 公式计算与目标点的水平距离（米）。
Reads the current position from the telemetry stream and computes horizontal distance to the target in metres using the Haversine formula.

**返回值 / Returns**
`float` — 水平距离（米）/ Horizontal distance (metres)

**示例 / Example**
```python
dist = await nav.get_distance_to_target(51.4224, -2.6670)
print(f"距目标 {dist:.1f} m / Distance to target: {dist:.1f} m")
```

---

### 4.9 `start_refresh()` / `stop_refresh()`

```python
def start_refresh() -> None
def stop_refresh() -> None
```

**功能 / Description**
手动控制后台状态刷新协程的启停。`connect()` 成功后会**自动调用** `start_refresh()`，通常无需手动启动。
Manually start or stop the background status refresh coroutine. `connect()` **automatically calls** `start_refresh()` on success; manual invocation is rarely needed.

**使用场景 / When to use**

| 操作 / Action | 说明 / Note |
|---|---|
| `start_refresh()` | 在未使用 `connect()` 而直接传入已连接 System 时手动启动 / Start manually when bypassing `connect()` with a pre-connected System |
| `stop_refresh()` | 程序退出前调用，清理异步任务 / Call before program exit to clean up the async task |

**示例 / Example**
```python
nav.start_refresh()   # 手动启动 / Manual start
# ...
nav.stop_refresh()    # 退出前清理 / Clean up before exit
```

---

## 5. 地理围栏规则 / Geofence Rules

| 规则 / Rule | 参数 / Parameter | 值 / Value |
|---|---|---|
| R01 | 飞行区域 / Flight area | 4 顶点多边形（WGS-84）/ 4-vertex polygon (WGS-84) |
| R02 | SSSI 禁飞区 / NFZ | 7 顶点多边形 / 7-vertex polygon |
| R04 | 最大高度 / Max altitude | `50.0 m`（相对高度 / relative）|
| R30 | 预检查触发 / Pre-check trigger | 每次 `goto()` 调用前强制执行 / Enforced before every `goto()` |

> **坐标格式注意 / Coordinate format note**：接口统一使用 **(纬度, 经度)** 顺序传参；Shapely 内部存储为 (经度, 纬度)，模块已自动处理转换，调用方无需关心。
> The API consistently uses **(latitude, longitude)** parameter order. Shapely stores coordinates as (longitude, latitude) internally; the module handles the conversion automatically.

---

## 6. 错误码 / Error Codes

| 错误码 / Code | 触发场景 / Trigger |
|---|---|
| `OUTSIDE_FLIGHT_AREA` | 目标点在合法飞行区域外 / Target outside the permitted flight area |
| `INSIDE_SSSI_NFZ` | 目标点在 SSSI 禁飞区内 / Target inside the SSSI no-fly zone |
| `ALTITUDE_TOO_HIGH` | 目标高度超过 50 m / Target altitude exceeds 50 m |
| `CONNECTION_FAIL: <msg>` | 连接飞控失败 / Failed to connect to FC |
| `TELEMETRY_FAIL: <msg>` | 遥测数据读取失败 / Telemetry read failure |
| `PROGRESS_FAIL: <msg>` | 进度更新失败 / Progress update failure |

错误码可通过 `get_status()["error"]` 读取。
Error codes are available via `get_status()["error"]`.

---

## 7. 典型调用流程 / Typical Call Flow

### 场景 A：标准任务执行 / Standard mission execution

```
connect()
    └─► get_status() → state="CONNECTED"

goto(lat, lon, alt)
    └─► 安全检查通过 → state="FLYING"
    └─► [后台每5s刷新] get_status() → progress_pct 递增
    └─► 到达 → state="ARRIVED", progress_pct=100.0
```

### 场景 B：飞行中取消 / Cancel mid-flight

```
goto(lat, lon, alt)         → state="FLYING"
    ↓ (用户取消/User cancels)
cancel()                    → state="HOVERING", target=None, progress=0%
    ↓ (重新规划/Re-plan)
goto(new_lat, new_lon, alt) → state="FLYING"
```

### 场景 C：安全拦截 / Safety interception

```
goto(0.0, 0.0, 10.0)
    └─► 安全检查失败 → state="ERROR", error="OUTSIDE_FLIGHT_AREA"
    └─► get_status()["error"] == "OUTSIDE_FLIGHT_AREA"
```

### 场景 D：紧急返航 / Emergency RTL

```
# 任意状态下 / From any state:
rth()  →  state="RTH"
```

---

*文档版本 / Doc version: 2026-03-08 | 对应模块 / Module: `navigation_test2.py`*
