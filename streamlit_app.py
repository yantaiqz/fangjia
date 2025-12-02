import streamlit as st
import pandas as pd
import math
import altair as alt
import io

# -----------------------------------------------------------------------------
# 1. 模拟数据生成 (为了演示两级联动结构)
# 如果您有真实的 CSV 文件，请确保文件包含 '城市' 和 '城区' 两列，并取消后续读取文件的注释
# -----------------------------------------------------------------------------
def get_dummy_csv_data():
    # 这里模拟了带有【城市】和【城区】两级结构的数据
    csv_content = """城市,城区,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025
北京,全城均价,38000,52000,62000,60000,58000,60000,65000,63000,61000,58000,56000
北京,朝阳区,42000,58000,68000,66000,65000,68000,72000,70000,68000,65000,63000
北京,海淀区,45000,62000,75000,73000,72000,78000,85000,82000,80000,76000,74000
北京,通州区,22000,35000,45000,42000,40000,41000,43000,40000,38000,35000,33000
上海,全城均价,35000,48000,55000,53000,54000,58000,68000,66000,64000,63000,61000
上海,浦东新区,38000,52000,60000,58000,59000,65000,75000,72000,70000,68000,66000
上海,黄浦区,65000,85000,95000,92000,95000,105000,120000,115000,110000,108000,105000
烟台,全城均价,6500,7200,8200,9500,10000,10500,10800,10000,9500,9200,8800
烟台,芝罘区,7000,7800,9000,10500,11000,11500,11800,11000,10500,10000,9600
烟台,莱山区,7500,8500,10000,11500,12500,13500,14000,13000,12500,12000,11500
烟台,开发区,6000,6800,8000,9200,9800,10200,10500,9800,9200,8800,8500"""
    return io.StringIO(csv_content)

# -----------------------------------------------------------------------------
# 页面配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='房价趋势透视',
    page_icon='📈',
)

# -----------------------------------------------------------------------------
# 数据加载函数 (修改版)
# -----------------------------------------------------------------------------

@st.cache_data
def get_gdp_data():
    """
    修改说明：
    1. 读取数据时，现在需要同时处理 '城市' 和 '城区'。
    2. 如果您使用本地文件，请将 io.StringIO 替换为您的文件路径。
    """
    
    # === 如果使用本地文件，请取消注释以下两行，并注释掉 dummy_csv_data ===
    # DATA_FILENAME = Path(__file__).parent/'data/fangchan_data.csv'
    # raw_df = pd.read_csv(DATA_FILENAME, delimiter=',') # 假设新CSV是用逗号分隔
    
    # === 使用演示数据 ===
    raw_df = pd.read_csv(get_dummy_csv_data(), delimiter=',')

    # 获取年份列（排除掉非年份的列）
    # 假设前两列是 '城市' 和 '城区'，剩下的都是年份
    id_vars = ['城市', '城区']
    year_columns = [col for col in raw_df.columns if col not in id_vars]

    # Melt 转换：保留 城市 和 城区 作为标识符
    df = raw_df.melt(
        id_vars=id_vars,
        value_vars=year_columns,
        var_name='时间',
        value_name='房价',
    )
    
    # 数据清洗
    df['时间'] = pd.to_numeric(df['时间'])
    
    return df

try:
    gdp_df = get_gdp_data()
except Exception as e:
    st.error(f"数据加载失败。请确保您的CSV文件包含 '城市' 和 '城区' 两列。错误信息: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 页面绘制
# -----------------------------------------------------------------------------

'''
# 📈 城区房价趋势透视
选择特定城市，深入分析该城市各板块/城区的价格演变
'''

# Add some spacing
st.write('')
st.write('')

# === 第一级选择：城市 (单选) ===
# 获取城市列表
cities = gdp_df['城市'].unique()
selected_city = st.selectbox('请选择城市', cities, index=0)

# === 第二级选择：城区 (多选) ===
# 根据第一级选择的城市，筛选出该城市下的所有城区
districts_in_city = gdp_df[gdp_df['城市'] == selected_city]['城区'].unique()

# 默认全选该城市的城区
container = st.container()
all = st.checkbox("全选城区", value=True)
if all:
    selected_districts = container.multiselect(
        f'选择 {selected_city} 的具体区域',
        districts_in_city,
        districts_in_city
    )
else:
    selected_districts = container.multiselect(
        f'选择 {selected_city} 的具体区域',
        districts_in_city
    )


# === 时间滑块 ===
min_value = gdp_df['时间'].min()
max_value = gdp_df['时间'].max()

from_year, to_year = st.slider(
    '时间区间',
    min_value=min_value,
    max_value=max_value,
    value=[min_value, max_value]
)

st.write('')
st.write('')

# -----------------------------------------------------------------------------
# 数据过滤逻辑
# -----------------------------------------------------------------------------
filtered_df = gdp_df[
    (gdp_df['城市'] == selected_city) &       # 过滤城市
    (gdp_df['城区'].isin(selected_districts)) & # 过滤城区
    (gdp_df['时间'] <= to_year) & 
    (from_year <= gdp_df['时间'])
]

if filtered_df.empty:
    st.warning("请至少选择一个城区以显示数据")
    st.stop()

st.header(f'{selected_city} 各区域房价走势', divider='gray')

# -----------------------------------------------------------------------------
# 图表绘制 (Altair)
# -----------------------------------------------------------------------------

# 1. 定义基础图表
base = alt.Chart(filtered_df).encode(
    x=alt.X('时间', axis=alt.Axis(format='d', title='年份')),
    y=alt.Y('房价', 
            scale=alt.Scale(zero=False), # 动态调整纵坐标起点
            axis=alt.Axis(title='平均房价 (元/㎡)')),
    color=alt.Color('城区', legend=alt.Legend(title="区域")) # 颜色现在映射到 '城区'
)

# 2. 折线图
lines = base.mark_line()

# 3. 数据点 + Tooltip
points = base.mark_circle(size=60).encode(
    opacity=alt.value(1),
    tooltip=[
        alt.Tooltip('城市', title='城市'),
        alt.Tooltip('城区', title='区域'),
        alt.Tooltip('时间', title='年份'),
        alt.Tooltip('房价', title='均价(元)', format=',')
    ]
)

chart = (lines + points).interactive()

st.altair_chart(chart, use_container_width=True)

# -----------------------------------------------------------------------------
# 增长率指标展示
# -----------------------------------------------------------------------------

st.header(f'{to_year}年 同比增长数据 ({selected_city})', divider='gray')

st.write('')

# 获取首尾年份数据用于计算
first_year_data = gdp_df[gdp_df['时间'] == from_year]
last_year_data = gdp_df[gdp_df['时间'] == to_year]

cols = st.columns(4)

# 遍历用户选择的【城区】进行展示
for i, district in enumerate(selected_districts):
    col = cols[i % 4] # 修改为 % 4 以适配定义的列数

    with col:
        # 尝试获取对应城区的数据
        try:
            start_price = first_year_data[
                (first_year_data['城市'] == selected_city) & 
                (first_year_data['城区'] == district)
            ]['房价'].values[0]
            
            end_price = last_year_data[
                (last_year_data['城市'] == selected_city) & 
                (last_year_data['城区'] == district)
            ]['房价'].values[0]

            if math.isnan(start_price) or start_price == 0:
                growth = 'n/a'
                delta_color = 'off'
            else:
                pct_change = (end_price - start_price) / start_price
                growth = f'{pct_change:+.2%}'
                
                if pct_change > 0:
                    delta_color = 'normal' # 绿色 (默认)
                else:
                    delta_color = 'inverse' # 红色 (在Streamlit标准主题中，inverse通常表示负面或相反颜色，或者直接使用 'normal' 配合负号)
                    # 注: Streamlit 的 metric 会自动根据正负号把 normal 渲染成红/绿，
                    # 但如果你想强制跌是红色，可以使用 'inverse' 试一下，或者保持 'normal' 让系统自动处理。
            
            st.metric(
                label=district, # 指标名称现在是城区名
                value=f'{end_price:,.0f}',
                delta=growth,
                delta_color='normal' 
            )
        except IndexError:
            st.warning(f"{district}: 数据缺失")
