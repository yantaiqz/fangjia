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
