import streamlit as st
import pandas as pd
import math
from pathlib import Path
import altair as alt

# -----------------------------------------------------------------------------
# 1. 页面配置 & 视觉优化
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='房产大数据看板',
    page_icon='🏠',
    layout="wide"
)

st.markdown("""
<style>
    /* === 1. 页面布局：两侧留白与居中 === */
    .block-container {
        max-width: 1200px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        margin: auto;
    }
    
    div[data-testid="column"] { gap: 1rem; }
    
    /* === 2. 隐藏 Streamlit 原生元素 === */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    
    /* === 3. 按钮样式 === */
    .neal-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-weight: 600;
        font-size: 14px;
        color: #1f2937;
        background: linear-gradient(to bottom, #ffffff, #f3f4f6);
        border: 1px solid #d1d5db;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        text-decoration: none !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
        white-space: nowrap;
    }
    
    .neal-btn:hover {
        background: #fff;
        border-color: #6366f1;
        color: #4f46e5;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transform: translateY(-1px);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
        font-family: 'Inter', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 数据加载
# -----------------------------------------------------------------------------
@st.cache_data
def get_gdp_data():
    DATA_FILENAME = Path(__file__).parent/'data/fangchan_full_data.csv'
    raw_df = pd.read_csv(DATA_FILENAME, delimiter=',')
    id_vars = ['城市', '城区', '类型']
    year_columns = [col for col in raw_df.columns if col not in id_vars]
    df = raw_df.melt(id_vars=id_vars, value_vars=year_columns, var_name='时间', value_name='价格')
    df['时间'] = pd.to_numeric(df['时间'])
    return df

try:
    gdp_df = get_gdp_data()
except Exception as e:
    st.error(f"数据错误: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 3. 顶部导航区
# -----------------------------------------------------------------------------
c_head_1, c_head_2 = st.columns([0.85, 0.15])
with c_head_1:
    st.subheader("🏠 房产大数据看板", divider="gray")
with c_head_2:
    st.markdown(
        '''
        <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%; padding-top: 5px;">
            <a href="https://haowan.streamlit.app/" target="_blank" class="neal-btn">
               ✨ 更多好玩应用
            </a>
        </div>
        ''', 
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 4. 筛选控制栏
# -----------------------------------------------------------------------------
with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 2.5, 1, 4])
    with c1:
        cities = gdp_df['城市'].unique()
        selected_city = st.selectbox('城市', cities, label_visibility="collapsed", index=0)
    with c2:
        metric_type = st.radio('类型', ["房价", "房租"], horizontal=True, label_visibility="collapsed")
    with c3:
        min_year = gdp_df['时间'].min()
        max_year = 2025
        from_year, to_year = st.slider('年份', min_year, max_year, [min_year, max_year], label_visibility="collapsed")
    
    districts_in_city = gdp_df[gdp_df['城市'] == selected_city]['城区'].unique()
    with c4:
        st.write("") 
        st.write("") 
        all_districts = st.checkbox("全选区域", value=True)
    with c5:
        if all_districts:
            selected_districts = st.multiselect('区域', districts_in_city, districts_in_city, label_visibility="collapsed")
        else:
            selected_districts = st.multiselect('区域', districts_in_city, label_visibility="collapsed", placeholder="选择区域...")

# -----------------------------------------------------------------------------
# 5. 主图表区域 (修复坐标轴显示)
# -----------------------------------------------------------------------------
unit = '元/㎡' if metric_type == '房价' else '元/㎡/月'

filtered_df = gdp_df[
    (gdp_df['城市'] == selected_city) &
    (gdp_df['城区'].isin(selected_districts)) &
    (gdp_df['类型'] == metric_type) & 
    (gdp_df['时间'] <= to_year) & 
    (from_year <= gdp_df['时间'])
]

if filtered_df.empty:
    st.info("👋 请调整上方筛选条件以查看数据。")
    st.stop()

# === 图表配置调整 ===
base = alt.Chart(filtered_df).encode(
    x=alt.X('时间', axis=alt.Axis(format='d', title=None, grid=False, domain=False, tickSize=0)),
    y=alt.Y(
        '价格', 
        scale=alt.Scale(zero=False), 
        axis=alt.Axis(
            title=unit, 
            gridColor='#f0f0f0', 
            labelLimit=0,      # 不截断文字
            titlePadding=20,   # 增加标题与数字的间距
            minExtent=60       # <--- 核心修复：强制给 Y 轴预留 60px 宽度，防止数字被切
        )
    ),
    color=alt.Color('城区', legend=alt.Legend(title=None, orient='top', columns=6, symbolLimit=0))
)

lines = base.mark_line(strokeWidth=3, opacity=0.8)
points = base.mark_circle(size=60).encode(
    tooltip=['城区', '时间', alt.Tooltip('价格', format=',')]
)

# 使用 configure_layout 增加左侧内边距，作为双重保险
chart = (lines + points).properties(height=400).interactive()
# chart = chart.configure_layout(padding={"left": 10}) # 备选方案，如果 minExtent 不够用可开启此行

st.altair_chart(chart, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. 数据概览
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(f"**📊 {from_year} vs {to_year} 涨跌一览**")

first_year_df = filtered_df[filtered_df['时间'] == from_year]
last_year_df = filtered_df[filtered_df['时间'] == to_year]

cols = st.columns(6)

for i, district in enumerate(selected_districts):
    col = cols[i % 6]
    with col:
        s_vals = first_year_df[first_year_df['城区'] == district]['价格'].values
        e_vals = last_year_df[last_year_df['城区'] == district]['价格'].values
        
        if len(s_vals) > 0 and len(e_vals) > 0:
            start, end = s_vals[0], e_vals[0]
            if start != 0 and not math.isnan(start):
                pct = (end - start) / start
                st.metric(
                    label=district,
                    value=f"{end:,.0f}",
                    delta=f"{pct:+.1%}"
                )
            else:
                st.metric(label=district, value="N/A")
