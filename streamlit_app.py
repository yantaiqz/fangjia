import streamlit as st
import pandas as pd
import math
from pathlib import Path
import altair as alt
import io

import json
import datetime
import os

import time 


# -------------------------- 右上角功能区 --------------------------

st.markdown("""
<style>

    /* 隐藏右上角的 Streamlit 主菜单（包含部署、源码、设置等） */
    #MainMenu {visibility: hidden;}
    /* 隐藏页脚（包含 "Made with Streamlit" 文字） */
    footer {visibility: hidden;}
    /* 隐藏顶部的 header（包含部署按钮） */
    header[data-testid="stHeader"] {display: none;}
    
    /* 2. HTML 链接按钮 (Get New Apps) */
    .neal-btn {
        font-family: 'Inter', sans-serif;
        background: #fff;
        border: 1px solid #e5e7eb;
        color: #111;
        font-weight: 600;
        font-size: 14px;
        padding: 8px 16px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
        text-decoration: none !important;
        width: 100%;
        height: 38px; /* 强制与 st.button 高度对齐 */
    }
    .neal-btn:hover {
        background: #f9fafb;
        border-color: #111;
        transform: translateY(-1px);
    }
    .neal-btn-link { text-decoration: none; width: 100%; display: block; }
</style>
""", unsafe_allow_html=True)


# 创建右上角布局（占满整行，右侧显示按钮/链接）
col_empty, col_more = st.columns([0.8, 0.2])

with col_more:
    # 修复：改用 HTML 链接按钮（替代 webbrowser 方式，兼容 Streamlit 云环境）
    st.markdown(
        f"""
        <a href="https://haowan.streamlit.app/" target="_blank" class="neal-btn-link">
            <button class="neal-btn">✨ 更多好玩应用</button>
        </a>
        """, 
        unsafe_allow_html=True
    )



# --- 权限配置 ---
FREE_PERIOD_SECONDS = 60      # 免费试用期 60 秒
ACCESS_DURATION_HOURS = 24    # 密码解锁后的访问时长 24 小时
UNLOCK_CODE = "vip24"        # 预设的解锁密码
# --- 配置结束 ---

# -------------------------------------------------------------
# --- 1. 初始化会话状态 ---
# -------------------------------------------------------------

# 'start_time': 首次访问时间，用于计算免费试用期
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()
    # 'access_status': 'free' (免费期), 'locked' (需解锁), 'unlocked' (已解锁)
    st.session_state.access_status = 'free'
    st.session_state.unlock_time = None # 记录密码解锁的时间点

# -------------------------------------------------------------
# --- 2. 检查访问状态和时间逻辑 ---
# -------------------------------------------------------------

current_time = datetime.datetime.now()
access_granted = False # 默认无权限

# 检查当前状态并更新
if st.session_state.access_status == 'free':
    time_elapsed = (current_time - st.session_state.start_time).total_seconds()
    
    if time_elapsed < FREE_PERIOD_SECONDS:
        # 仍在免费期内
        access_granted = True
        time_left = FREE_PERIOD_SECONDS - time_elapsed
        st.info(f"⏳ **免费试用中... 剩余 {time_left:.1f} 秒。**")
    else:
        # 免费期结束，进入锁定状态
        st.session_state.access_status = 'locked'
        st.session_state.start_time = None # 清除免费期计时
        st.rerun() # 强制刷新以立即显示锁定界面
        
elif st.session_state.access_status == 'unlocked':
    unlock_expiry = st.session_state.unlock_time + datetime.timedelta(hours=ACCESS_DURATION_HOURS)
    
    if current_time < unlock_expiry:
        # 在 24 小时有效期内
        access_granted = True
        time_left_delta = unlock_expiry - current_time
        hours = int(time_left_delta.total_seconds() // 3600)
        minutes = int((time_left_delta.total_seconds() % 3600) // 60)
        
        st.info(f"🔓 **付费权限剩余:** {hours} 小时 {minutes} 分钟")
    else:
        # 24 小时已过期，进入锁定状态
        st.session_state.access_status = 'locked'
        st.session_state.unlock_time = None
        st.rerun() # 强制刷新

# -------------------------------------------------------------
# --- 3. 锁定界面及密码输入 ---
# -------------------------------------------------------------

if not access_granted:
    st.error("🔒 **访问受限。免费试用期已结束！**")
    st.markdown(f"""
    <div style="background-color: #fff; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 15px;">
        <p style="font-weight: 600; color: #1f2937; margin-bottom: 5px;">🔑 10元解锁无限制访问权限，获取代码链接 (请在微信中打开)</p>
        <p style="font-size: 0.9em; background-color: #eef2ff; padding: 8px; border-radius: 4px; overflow-wrap: break-word;">
            <code>#小程序://闲鱼/i4ahD0rqwGB5lba</code>
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("access_lock_form"):
        password_input = st.text_input("解锁代码:", type="password", key="password_input_key")
        submit_button = st.form_submit_button("验证并解锁")
        
        if submit_button:
            if password_input == UNLOCK_CODE:
                st.session_state.access_status = 'unlocked'
                st.session_state.unlock_time = datetime.datetime.now()
                st.success("🎉 解锁成功！您已获得 1 天访问权限。页面即将刷新...")
                st.rerun()
            else:
                st.error("❌ 代码错误，请重试。")
                
    # 强制停止脚本，隐藏所有受保护的内容
    st.stop()
    
# -------------------------- 2. 安全的计数器逻辑 --------------------------
COUNTER_FILE = "visit_stats.json"

def update_daily_visits():
    """安全更新访问量，如果出错则返回 0，绝不让程序崩溃"""
    try:
        today_str = datetime.date.today().isoformat()
        
        # 1. 检查 Session，防止刷新页面重复计数
        if "has_counted" in st.session_state:
            if os.path.exists(COUNTER_FILE):
                try:
                    with open(COUNTER_FILE, "r") as f:
                        return json.load(f).get("count", 0)
                except:
                    return 0
            return 0

        # 2. 读取或初始化数据
        data = {"date": today_str, "count": 0}
        
        if os.path.exists(COUNTER_FILE):
            try:
                with open(COUNTER_FILE, "r") as f:
                    file_data = json.load(f)
                    if file_data.get("date") == today_str:
                        data = file_data
            except:
                pass # 文件损坏则从0开始
        
        # 3. 计数 +1
        data["count"] += 1
        
        # 4. 写入文件 (最容易报错的地方，加了try保护)
        with open(COUNTER_FILE, "w") as f:
            json.dump(data, f)
        
        st.session_state["has_counted"] = True
        return data["count"]
        
    except Exception as e:
        # 如果发生任何错误（如权限不足），静默失败，不影响页面显示
        return 0


# -------- 每日访问统计 (即使报错也不崩溃) --------
daily_visits = update_daily_visits()
# visit_text = f"Daily Visits: {daily_visits}" if selected_lang == "English" else f"今日访问: {daily_visits}"
visit_text = f"今日访问: {daily_visits}"

st.markdown(f"""
<div style="text-align: center; color: #64748b; font-size: 0.7rem; margin-top: 10px; padding-bottom: 20px;">
    {visit_text}
</div>
""", unsafe_allow_html=True)



# -----------------------------------------------------------------------------
# 页面配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='房产大数据看板',
    page_icon='🏠',
    layout="wide" # 使用宽屏模式以容纳更多信息
)

# -----------------------------------------------------------------------------
# 数据加载函数
# -----------------------------------------------------------------------------
@st.cache_data
def get_gdp_data():
    # 读取模拟数据
    # raw_df = pd.read_csv(get_dummy_csv_data(), delimiter=',')    
    # raw_df = pd.read_csv('fangchan_full_data.csv')

    DATA_FILENAME = Path(__file__).parent/'data/fangchan_full_data.csv'
    raw_df = pd.read_csv(DATA_FILENAME, delimiter=',')

    # 现在的标识符包含：城市、城区、类型
    id_vars = ['城市', '城区', '类型']
    year_columns = [col for col in raw_df.columns if col not in id_vars]

    # Melt 转换
    df = raw_df.melt(
        id_vars=id_vars,
        value_vars=year_columns,
        var_name='时间',
        value_name='价格',
    )
    
    df['时间'] = pd.to_numeric(df['时间'])
    return df

try:
    gdp_df = get_gdp_data()
except Exception as e:
    st.error(f"数据加载失败。请确保CSV包含【城市, 城区, 类型】三列。错误: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 侧边栏 (Sidebar) - 用于控制全局筛选
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title('⚙️ 筛选面板')
    
    # 1. 城市选择
    cities = gdp_df['城市'].unique()
    selected_city = st.selectbox('📍 选择城市', cities, index=0)

    # 2. 城区选择
    districts_in_city = gdp_df[gdp_df['城市'] == selected_city]['城区'].unique()
    all_districts = st.checkbox("全选城区", value=True)
    
    if all_districts:
        selected_districts = st.multiselect(f'选择 {selected_city} 的区域', districts_in_city, districts_in_city)
    else:
        selected_districts = st.multiselect(f'选择 {selected_city} 的区域', districts_in_city)

    st.divider()

    # 3. 时间滑块
    min_year = gdp_df['时间'].min()
    # max_year = gdp_df['时间'].max()
    max_year = 2025
    from_year, to_year = st.slider('📅 时间区间', min_year, max_year, [min_year, max_year])

# -----------------------------------------------------------------------------
# 主页面内容
# -----------------------------------------------------------------------------

st.title(f'🏠 {selected_city} 房产价格趋势透视')
st.caption("数据来源：模拟演示数据 | 包含二手房挂牌均价与租金均价")

# === 核心交互：切换房价/房租 ===
# 使用 segmented control (如果 Streamlit 版本较新) 或 radio
metric_type = st.radio(
    "📊 请选择数据视角：",
    ["房价", "房租"],
    horizontal=True,
    help="切换查看买卖价格或租赁价格趋势"
)

# 动态设置单位
if metric_type == '房价':
    unit = '元/㎡'
    y_axis_title = '平均单价 (元/㎡)'
else:
    unit = '元/㎡/月'
    y_axis_title = '平均租金 (元/㎡/月)'

# -----------------------------------------------------------------------------
# 数据过滤
# -----------------------------------------------------------------------------
filtered_df = gdp_df[
    (gdp_df['城市'] == selected_city) &
    (gdp_df['城区'].isin(selected_districts)) &
    (gdp_df['类型'] == metric_type) &  # 增加类型过滤
    (gdp_df['时间'] <= to_year) & 
    (from_year <= gdp_df['时间'])
]

if filtered_df.empty:
    st.info("⚠️ 当前筛选条件下暂无数据，请调整侧边栏选项。")
    st.stop()

# -----------------------------------------------------------------------------
# 图表绘制
# -----------------------------------------------------------------------------
st.subheader(f'{metric_type}走势图', divider='gray')

base = alt.Chart(filtered_df).encode(
    x=alt.X('时间', axis=alt.Axis(format='d', title='年份')),
    y=alt.Y('价格', 
            scale=alt.Scale(zero=False), 
            axis=alt.Axis(title=y_axis_title)),
    color=alt.Color('城区', legend=alt.Legend(title="区域"))
)

lines = base.mark_line(strokeWidth=3)
points = base.mark_circle(size=60).encode(
    opacity=alt.value(1),
    tooltip=[
        alt.Tooltip('城区', title='区域'),
        alt.Tooltip('时间', title='年份'),
        alt.Tooltip('价格', title=f'{metric_type}', format=','),
        alt.Tooltip('类型', title='数据类型')
    ]
)

chart = (lines + points).interactive()
st.altair_chart(chart, use_container_width=True)

# -----------------------------------------------------------------------------
# 增长率指标展示
# -----------------------------------------------------------------------------
st.subheader(f'📈 {from_year}-{to_year}年 {metric_type}涨幅榜', divider='gray')

# 获取首尾年份数据用于计算
# 注意：这里需要重新从 filtered_df 取，因为它已经包含了类型过滤
first_year_df = filtered_df[filtered_df['时间'] == from_year]
last_year_df = filtered_df[filtered_df['时间'] == to_year]

cols = st.columns(4)

for i, district in enumerate(selected_districts):
    col = cols[i % 4]
    
    with col:
        # 获取起点和终点价格
        start_vals = first_year_df[first_year_df['城区'] == district]['价格'].values
        end_vals = last_year_df[last_year_df['城区'] == district]['价格'].values
        
        if len(start_vals) > 0 and len(end_vals) > 0:
            start_price = start_vals[0]
            end_price = end_vals[0]
            
            if start_price == 0 or math.isnan(start_price):
                growth_str = "N/A"
                delta_color = "off"
            else:
                pct = (end_price - start_price) / start_price
                growth_str = f"{pct:+.2%}"
                delta_color = "normal"
            
            st.metric(
                label=f"{district}",
                value=f"{end_price:,.0f} {unit.replace('元/', '')}", # 简化单位显示
                delta=growth_str,
                delta_color=delta_color
            )
        else:
            # 如果某一年缺失数据
            st.metric(label=district, value="暂无数据", delta=None)
