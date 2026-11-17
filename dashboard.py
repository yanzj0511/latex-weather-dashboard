import streamlit as st
import pandas as pd
import pydeck as pdk

# 1. 设置网页配置和标题
st.set_page_config(page_title="全球乳胶产区天气监控", layout="wide")
st.title("🌍 全球乳胶产区天气监控大屏")

try:
    # 读取 Excel 数据
    df = pd.read_excel("latest_weather.xlsx")


    # --- 核心：配置地图打点颜色逻辑 ---
    # 定义一个函数：如果温度低于20度，返回红色；低于24度，返回黄色；否则绿色
    def get_color(temp):
        if temp < 20:
            return [255, 75, 75, 200]  # 红色 (RGBA)
        elif temp < 24:
            return [255, 165, 0, 200]  # 黄色
        else:
            return [40, 167, 69, 200]  # 绿色


    # 把颜色应用到数据框里
    df['color'] = df['当前温度(℃)'].apply(get_color)

    # --- 顶部指标卡片 ---
    col1, col2, col3 = st.columns(3)
    col1.metric("监控产区总数", f"{len(df)} 个")
    col2.metric("当前全球最低温", f"{df['当前温度(℃)'].min()} ℃")
    col3.metric("当前全球最高温", f"{df['当前温度(℃)'].max()} ℃")

    # --- 画全球地图 ---
    st.subheader("🗺️ 产区温度分布图")

    # 定义地图视角（这里是粗略定位到东南亚和全球）
    view_state = pdk.ViewState(
        latitude=5.0,
        longitude=105.0,
        zoom=1.5,
        pitch=0,
    )

    # 创建打点图层
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["经度", "纬度"],  # 对应 Excel 里的经度和纬度列
        get_color="color",  # 使用上面计算出的颜色
        get_radius=100000,  # 点的半径大小（根据地图缩放级别调整）
        pickable=True,  # 允许鼠标悬停
    )

    # 渲染地图
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{城市}\n温度: {当前温度(℃)}℃"},  # 鼠标悬停提示
        )
    )

    # --- 底部表格 ---
    st.subheader("📋 各产区实时温度明细")


    # 用颜色标记表格
    def color_temp(val):
        color = '#ff4b4b' if val < 20 else '#ffa500' if val < 24 else '#28a745'
        return f'color: {color}; font-weight: bold;'


    # 隐藏颜色列表和经纬度列，让表格更干净
    display_df = df.drop(columns=['color', '纬度', '经度'])
    st.dataframe(display_df.style.map(color_temp, subset=['当前温度(℃)']), use_container_width=True)

except FileNotFoundError:
    st.error("未找到数据文件，请先运行 fetch_weather.py 抓取数据！")