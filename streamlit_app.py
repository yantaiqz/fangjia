import streamlit as st
import pandas as pd
import math
from pathlib import Path
import altair as alt

# -----------------------------------------------------------------------------
# 1. 页面配置 & CSS 极致压缩
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='房产大数据看板',
    page_icon='🏠',
    layout="wide"
)

st.markdown("""
<style>
    /* === 核心布局压缩 === */
    /* 减少顶部空白 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    
    /* 减少组件间的垂直间距 */
    div[data-testid="column"] {
        gap: 0.5rem;
    }
    div.stButton > button {
        height: auto;
        padding-top: 0.3rem;
        padding-bottom: 0.3rem;
    }
    
    /* === 隐藏无关元素 === */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    
    /* === 右上角按钮样式 === */
    .neal-btn {
        background-color: #f0f2f6;
        color: #31333F;
        border: 1px solid #dce0e6;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        text-decoration: none;
        transition: all 0.2s;
        display: inline-block;
    }
    .neal-btn:hover {
        background-color: #e6e9ef;
        border-color: #c0c7d0;
    }
    
    /* === 调整指标卡片样式 === */
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem !important; /* 缩小数字字体 */
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 数据加载 (保持不变)
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
# 3. 顶部导航栏 (标题 + 外部链接)
# -----------------------------------------------------------------------------
col_title, col_link = st.columns([0.85, 0.15])

with col_title:
    st.subheader("🏠 房产大数据看板", divider="grey") # 使用 Subheader+Divider 替代 Title，更省空间

with col_link:
    st.markdown(
        '<div style="text-align: right; padding-top: 5px;">'
        '<a href="https://haowan.streamlit.app/" target="_blank" class="neal-btn">✨ 更多应用</a>'
        '</div>', 
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 4. 紧凑筛选区 (一行搞定核心筛选)
# -----------------------------------------------------------------------------
# 布局策略：城市(1.5) | 类型(1.5) | 时间(3) | 区域全选开关(1.5) | 区域多选(4.5)
c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 2.5, 1, 4])

with c1:
    cities = gdp_df['城市'].unique()
    selected_city = st.selectbox('城市', cities, label_visibility="collapsed", index=0)

with c2:
    # 使用 Radio 但看起来像 Tabs
    metric_type = st.radio('类型', ["房价", "房租"], horizontal=True, label_visibility="collapsed")

with c3:
    min_year = gdp_df['时间'].min()
    max_year = 2025
    # label_visibility="collapsed" 隐藏标题以节省空间
    from_year, to_year = st.slider('年份', min_year, max_year, [min_year, max_year], label_visibility="collapsed")

# 区域筛选逻辑
districts_in_city = gdp_df[gdp_df['城市'] == selected_city]['城区'].unique()

with c4:
    st.write("") # 稍微对其
    st.write("") 
    all_districts = st.checkbox("全选区域", value=True)

with c5:
    if all_districts:
        selected_districts = st.multiselect('区域', districts_in_city, districts_in_city, label_visibility="collapsed")
    else:
        selected_districts = st.multiselect('区域', districts_in_city, label_visibility="collapsed", placeholder="请选择区域...")

# -----------------------------------------------------------------------------
# 5. 数据处理与图表 (主视觉区)
# -----------------------------------------------------------------------------

# 单位定义
unit = '元/㎡' if metric_type == '房价' else '元/㎡/月'

# 数据过滤
filtered_df = gdp_df[
    (gdp_df['城市'] == selected_city) &
    (gdp_df['城区'].isin(selected_districts)) &
    (gdp_df['类型'] == metric_type) & 
    (gdp_df['时间'] <= to_year) & 
    (from_year <= gdp_df['时间'])
]

if filtered_df.empty:
    st.warning("⚠️ 暂无数据，请调整筛选。")
    st.stop()

# 图表绘制
base = alt.Chart(filtered_df).encode(
    x=alt.X('时间', axis=alt.Axis(format='d', title=None, grid=False)), # 移除X轴标题，简洁
    y=alt.Y('价格', scale=alt.Scale(zero=False), axis=alt.Axis(title=unit)),
    color=alt.Color('城区', legend=alt.Legend(title=None, orient='top', columns=6, symbolLimit=0)) # 图例放顶部，更紧凑
)

lines = base.mark_line(strokeWidth=2.5)
points = base.mark_circle(size=50).encode(
    tooltip=['城区', '时间', alt.Tooltip('价格', format=',')]
)

chart = (lines + points).properties(height=380).interactive() # 固定高度

st.altair_chart(chart, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. 涨幅榜 (紧凑网格布局)
# -----------------------------------------------------------------------------
# 标题与指标区更近
st.markdown(f"**📈 {from_year}-{to_year}年 涨跌幅概览**")

first_year_df = filtered_df[filtered_df['时间'] == from_year]
last_year_df = filtered_df[filtered_df['时间'] == to_year]

# 改为 6 列，显得更精致
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
                # 仅显示数字和简单的涨跌百分比
                st.metric(
                    label=district,
                    value=f"{end:,.0f}",
                    delta=f"{pct:+.1%}"
                )
            else:
                st.metric(label=district, value="N/A", delta=None)
