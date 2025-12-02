import streamlit as st
import pandas as pd
import math
from pathlib import Path
import altair as alt

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='房价趋势透视',
    page_icon='📈', # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data
def get_gdp_data():
    """Grab GDP data from a CSV file.

    This uses caching to avoid having to read the file every time. If we were
    reading from an HTTP endpoint instead of a file, it's a good idea to set
    a maximum age to the cache with the TTL argument: @st.cache_data(ttl='1d')
    """

    # Instead of a CSV on disk, you could read from an HTTP endpoint here too.
    DATA_FILENAME = Path(__file__).parent/'data/fangchan_data.csv'
    raw_gdp_df = pd.read_csv(DATA_FILENAME, delimiter=';')

    MIN_YEAR = 1998
    MAX_YEAR = 2025

    # The data above has columns like:
    # - Country Name
    # - Country Code
    # - [Stuff I don't care about]
    # - GDP for 1960
    # - GDP for 1961
    # - GDP for 1962
    # - ...
    # - GDP for 2022
    #
    # ...but I want this instead:
    # - Country Name
    # - Country Code
    # - Year
    # - GDP
    #
    # So let's pivot all those year-columns into two: Year and GDP


    gdp_df = raw_gdp_df.melt(
        ['Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        '时间',
        '房价',
    )
    
    # Convert years from string to integers
    gdp_df['时间'] = pd.to_numeric(gdp_df['时间'])
    gdp_df = gdp_df.rename(columns={'Country Code': '城市'})
    return gdp_df

gdp_df = get_gdp_data()

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# 📈 房价趋势透视
过去30年核心城市房产价格趋势数据分析
'''

# Add some spacing
''
''

min_value = gdp_df['时间'].min()
max_value = gdp_df['时间'].max()

from_year, to_year = st.slider(
    '时间区间',
    min_value=min_value,
    max_value=max_value,
    value=[2005, max_value])

countries = gdp_df['城市'].unique()

if not len(countries):
    st.warning("Select at least one country")

selected_countries = st.multiselect(
    '城市',
    countries,
    ['北京', '上海', '深圳', '杭州', '成都', '烟台'])

''
''
''

# Filter the data
filtered_gdp_df = gdp_df[
    (gdp_df['城市'].isin(selected_countries))
    & (gdp_df['时间'] <= to_year)
    & (from_year <= gdp_df['时间'])
]

st.header('房价走势', divider='gray')

# 1. 定义基础图表 (Base Chart)
# 这里只定义 X, Y 和 颜色，不定义具体的形状
base = alt.Chart(filtered_gdp_df).encode(
    x=alt.X('时间', axis=alt.Axis(format='d', title='年份')), # format='d' 去掉年份中的逗号
    y=alt.Y('房价', 
            scale=alt.Scale(zero=False), # zero=False 确保纵坐标不强制从0开始，自动适配数据范围
            axis=alt.Axis(title='平均房价 (元/㎡)')),
    color='城市'
)

# 2. 创建折线层 (Line Layer)
lines = base.mark_line()

# 3. 创建圆点层 (Points Layer) - 关键步骤
# 这一层负责在每个数据点画一个圆，并绑定 tooltip 鼠标悬停事件
points = base.mark_circle(size=60).encode(
    opacity=alt.value(1),  # 设置点的透明度，1为完全不透明
    tooltip=[
        alt.Tooltip('城市', title='城市'),
        alt.Tooltip('时间', title='年份'),
        alt.Tooltip('房价', title='均价(元)', format=',') # format=',' 添加千位分隔符
    ]
)

# 4. 组合并渲染 (Combine and Render)
# 将折线和圆点叠加 (lines + points)
chart = (lines + points).interactive() 

st.altair_chart(chart, use_container_width=True)

first_year = gdp_df[gdp_df['时间'] == from_year]
last_year = gdp_df[gdp_df['时间'] == to_year]

st.header(f'{to_year}年房价同比增长', divider='gray')

''

cols = st.columns(4)

for i, country in enumerate(selected_countries):
    col = cols[i % len(cols)]

    with col:
        first_gdp = first_year[first_year['城市'] == country]['房价'].iat[0] 
        last_gdp = last_year[last_year['城市'] == country]['房价'].iat[0] 

        if math.isnan(first_gdp):
            growth = 'n/a'
            delta_color = 'off'
        else:
            # growth = f'{last_gdp / first_gdp:,.2f}x'
            # delta_color = 'normal'

            pct_change = (last_gdp - first_gdp) / first_gdp
            growth = f'{pct_change:+.2%}'
            delta_color = 'normal'
            
        st.metric(
            label=f'{country}',
            value=f'{last_gdp:,.0f}',
            delta=growth,
            delta_color=delta_color
        )
