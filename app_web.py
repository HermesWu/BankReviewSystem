import streamlit as st
import sqlite3
import pandas as pd
import os

# 1. 页面全局配置
st.set_page_config(page_title="APP 评价协同处理中心", page_icon="🎯", layout="wide")

DB_PATH = "data/app_reviews.db"

# 2. 读取数据库数据的函数（加入缓存机制，让网页秒开）
@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    # 按时间倒序读取工作表
    df = pd.read_sql_query("SELECT * FROM reviews_todo ORDER BY full_time DESC", conn)
    conn.close()
    return df

st.title("🎯 APP 评价协同处理中心")

df = load_data()

if df.empty:
    st.warning("⚠️ 数据库中暂无数据，请先运行你的爬虫任务。")
else:
    # 3. 顶部实时数据看板
    st.markdown("### 📊 实时大盘")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总评论数", len(df))
    col2.metric("待处理 (人工作业)", len(df[df['status'] == '待处理']))
    col3.metric("已解决", len(df[df['status'] == '已解决']))
    col4.metric("🚨 差评数", len(df[df['sentiment'] == '负向']))

    st.markdown("---")
    st.markdown("### 📝 协作工作台 (可直接双击表格进行修改)")

    # 4. 状态筛选器
    status_filter = st.selectbox("状态快速筛选", ["全部", "待处理", "处理中", "已解决", "已忽略"])
    if status_filter != "全部":
        df_display = df[df['status'] == status_filter]
    else:
        df_display = df

    # 5. 🌟 核心魔法：生成可交互、可编辑的超级表格
    edited_df = st.data_editor(
        df_display,
        column_config={
            # 配置协作专属的三列为可编辑下拉框和文本框
            "status": st.column_config.SelectboxColumn(
                "处理状态",
                options=["待处理", "处理中", "已解决", "已忽略"],
                required=True,
            ),
            "assignee": st.column_config.TextColumn("跟进人 (例如: 张三)"),
            "remark": st.column_config.TextColumn("处理备注 (例如: 已提Bug单)"),
            
            # 其他原始数据列配置为只读，防止被同事不小心改掉
            "source": st.column_config.Column("来源", disabled=True),
            "full_time": st.column_config.Column("具体时间", disabled=True),
            "content": st.column_config.Column("评价内容", disabled=True, width="large"),
            "score": st.column_config.Column("评分", disabled=True),
            "sentiment": st.column_config.Column("情感", disabled=True),
            "category": st.column_config.Column("分类", disabled=True),
            "summary": st.column_config.Column("AI 总结", disabled=True),
            
            # 隐藏不需要在前台展示的字段
            "id": None, "date": None, "title": None, "created_at": None
        },
        disabled=["source", "full_time", "content", "score", "sentiment", "category", "summary"],
        hide_index=True,
        use_container_width=True,
        height=500
    )

    # 6. 保存机制
    if st.button("💾 保存所有修改至底层数据库", type="primary"):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 将网页上修改后的数据，精准更新到底层 SQLite 数据库中
        for index, row in edited_df.iterrows():
            cursor.execute('''
                UPDATE reviews_todo 
                SET status = ?, assignee = ?, remark = ?
                WHERE source = ? AND full_time = ? AND content = ?
            ''', (row['status'], row['assignee'], row['remark'], row['source'], row['full_time'], row['content']))
            
        conn.commit()
        conn.close()
        
        st.success("✅ 数据已成功同步至底层数据库！")
        st.cache_data.clear()  # 清除页面缓存，强制刷新最新数据