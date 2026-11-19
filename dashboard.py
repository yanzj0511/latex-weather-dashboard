import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import altair as alt
import datetime

# 1. 页面设置与美化
st.set_page_config(page_title="全球乳胶产区天气监控", layout="wide", page_icon="🌍")
st.title("🌍 全球乳胶产区天气监控大屏")
st.caption(f"📅 数据更新时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 2. 产区坐标配置
plantations = [
    {"city": "宋卡府 (Songkhla)", "lat": 7.20, "lon": 100.60},
    {"city": "素叻他尼 (Surat Thani)", "lat": 9.14, "lon": 99.33},
    {"city": "洛坤 (Nakhon Si)", "lat": 8.43, "lon": 99.96},
    {"city": "巨港 (Palembang)", "lat": -2.99, "lon": 104.76},
    {"city": "棉兰 (Medan)", "lat": 3.59, "lon": 98.67},
    {"city": "吉隆坡 (Kuala Lumpur)", "lat": 3.14, "lon": 101.69},
    {"city": "怡保 (Ipoh)", "lat": 4.60, "lon": 101.08},
    {"city": "胡志明市 (Ho Chi Minh)", "lat": 10.82, "lon": 106.63},
    {"city": "平阳省 (Binh Duong)", "lat": 11.17, "lon": 106.67},
    {"city": "海南儋州", "lat": 19.52, "lon": 109.58},
    {"city": "云南西双版纳", "lat": 22.01, "lon": 100.80},
    {"city": "阿比让 (Abidjan)", "lat": 5.36, "lon": -4.01}
]


# 3. 抓取数据（实时 + 去年历史 + 当日最低温）
@st.cache_data(ttl=3600)
def fetch_weather_data():
    results = []
    now = datetime.datetime.now()
    last_year = now.replace(year=now.year - 1)
    current_hour = now.hour
    today_str = now.strftime('%Y-%m-%d')

    for p in plantations:
        # API 1: 实时天气 + 今天全天预报（用于提取今日最低温）
        url_now = f"https://api.open-meteo.com/v1/forecast?latitude={p['lat']}&longitude={p['lon']}&current=temperature_2m,precipitation,weather_code&daily=temperature_2m_min&timezone=auto"
        res_now = requests.get(url_now)

        # API 2: 去年同一天历史数据
        start_date = last_year.strftime('%Y-%m-%d')
        url_hist = f"https://archive-api.open-meteo.com/v1/archive?latitude={p['lat']}&longitude={p['lon']}&start_date={start_date}&end_date={start_date}&hourly=temperature_2m&timezone=auto"
        res_hist = requests.get(url_hist)

        if res_now.status_code == 200:
            data_now = res_now.json()
            current = data_now['current']

            temp_now = round(current['temperature_2m'], 1)
            precip = round(current['precipitation'], 1)

            # 提取今日最低温（注意 daily 返回的是数组，取第0个）
            today_min = round(data_now['daily']['temperature_2m_min'][0], 1)

            # 天气代码转文字
            weather_codes = {0: "晴", 1: "多云", 2: "阴", 3: "阴", 45: "雾", 51: "小雨", 61: "雨", 80: "阵雨",
                             95: "雷雨"}
            weather_text = weather_codes.get(current['weather_code'], "未知")

            # 解析历史温度
            temp_past = None
            if res_hist.status_code == 200:
                data_hist = res_hist.json()
                if 'hourly' in data_hist and 'time' in data_hist['hourly']:
                    times = data_hist['hourly']['time']
                    temps = data_hist['hourly']['temperature_2m']
                    target_time_str = f"{start_date}T{current_hour:02d}:00"
                    try:
                        idx = times.index(target_time_str)
                        if temps[idx] is not None:
                            temp_past = round(temps[idx], 1)
                    except ValueError:
                        pass

            results.append({
                "城市": p['city'],
                "温度(℃)": temp_now,
                "当日最低温(℃)": today_min,  # 新增列
                "去年同时间(℃)": temp_past,
                "天气": weather_text,
                "降水量(mm)": precip,
                "经度": p['lon'],
                "纬度": p['lat']
            })
    return pd.DataFrame(results)


try:
    df = fetch_weather_data()
except Exception as e:
    st.error(f"数据抓取失败。错误信息：{e}")
    st.stop()

# 4. 顶部核心指标卡片
col1, col2, col3, col4 = st.columns(4)
col1.metric("监控产区总数", f"{len(df)} 个")
col2.metric("当前最低温", f"{df['温度(℃)'].min():.1f} ℃")
col3.metric("当前最高温", f"{df['温度(℃)'].max():.1f} ℃")
col4.metric("今日全产区极端最低", f"{df['当日最低温(℃)'].min():.1f} ℃")  # 新增指标


# 5. 绘制美化版地图（根据当日最低温预警）
def get_color(temp):
    # 割胶预警逻辑：低于20度红色，20-24度橙色，大于24度绿色
    if temp < 20:
        return [255, 75, 75, 200]
    elif temp < 24:
        return [255, 165, 0, 200]
    else:
        return [40, 167, 69, 200]


# 这里改为根据“当日最低温”来变色，比单纯看实时温度更有业务指导意义
df['color'] = df['当日最低温(℃)'].apply(get_color)

view_state = pdk.ViewState(latitude=5.0, longitude=105.0, zoom=1.5, pitch=0)
layer = pdk.Layer(
    "ScatterplotLayer", data=df, get_position=["经度", "纬度"],
    get_color="color", get_radius=80000, pickable=True,
)

st.subheader("🗺️ 产区温度预警分布 (基于当日最低温)")
st.pydeck_chart(pdk.Deck(
    map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    layers=[layer], initial_view_state=view_state,
    tooltip={"text": "{城市}\n当前: {温度(℃)}℃\n今日最低: {当日最低温(℃)}℃\n天气: {天气}\n降水: {降水量(mm)}mm"},
))

# 6. 对比柱状图
st.subheader("📊 今年与去年同期温度对比")
chart_df = df.melt(id_vars=['城市'], value_vars=['温度(℃)', '去年同时间(℃)'], var_name='数据源', value_name='温度')
chart_df = chart_df.dropna(subset=['温度'])

bars = alt.Chart(chart_df).mark_bar().encode(
    x=alt.X('城市:N', sort=alt.EncodingSortField(field='温度', order='descending'), axis=alt.Axis(labelAngle=-45)),
    y=alt.Y('温度:Q', scale=alt.Scale(domain=[0, 40]), title='温度 (℃)'),
    color=alt.Color('数据源:N', scale=alt.Scale(domain=['温度(℃)', '去年同时间(℃)'], range=['#4c78a8', '#f58518']),
                    title='图例'),
    xOffset='数据源:N',
    tooltip=['城市', '数据源', alt.Tooltip('温度:Q', format='.1f')]
)

text = bars.mark_text(align='center', baseline='bottom', dx=0, dy=-5, color='black', fontSize=11).encode(
    text=alt.Text('温度:Q', format='.1f')
)

chart = (bars + text).properties(height=400).interactive()
st.altair_chart(chart, use_container_width=True)

# 7. 美化版数据表格（包含当日最低温）
st.subheader("📋 各产区实时数据明细")

# 整理要显示的列，把当日最低温加进去
display_cols = ['城市', '温度(℃)', '当日最低温(℃)', '天气', '降水量(mm)']
display_df = df[display_cols].copy()

# 格式化数字
for col in ['温度(℃)', '当日最低温(℃)', '降水量(mm)']:
    display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "-")


# 样式函数（让当日最低温低于20度时变红）
def highlight_temp(val):
    try:
        temp = float(val)
        if temp < 20:
            return 'color: #ff4b4b; font-weight: bold; text-align: center;'
        elif temp < 24:
            return 'color: #ffa500; font-weight: bold; text-align: center;'
        else:
            return 'color: #28a745; text-align: center;'
    except:
        return 'text-align: center;'


styles = [
    {'selector': 'thead th',
     'props': [('background-color', '#f0f2f6'), ('color', '#31333F'), ('font-weight', 'bold'), ('text-align', 'center'),
               ('padding', '10px')]},
    {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px'), ('border-bottom', '1px solid #e0e0e0')]},
    {'selector': 'tbody tr:hover', 'props': [('background-color', '#f9f9f9')]}
]

# 渲染表格，高亮“当日最低温”
styled_df = display_df.style \
    .map(highlight_temp, subset=['当日最低温(℃)']) \
    .set_table_styles(styles) \
    .hide(axis='index')

st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)