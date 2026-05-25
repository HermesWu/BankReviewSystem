# database.py
import sqlite3
import os

# 🌟 修改点 1：将数据库路径指向 data 文件夹
DB_DIR = "data"
DB_NAME = os.path.join(DB_DIR, "app_reviews.db")

def init_db():
    """初始化数据库，确保文件夹存在并创建表结构"""
    # 🌟 修改点 2：自动创建 data 文件夹
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        print(f"📁 已创建数据文件夹: {DB_DIR}")

    conn = sqlite3.connect(DB_NAME)
    # ... 后面建表的代码保持不变 ...
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, date TEXT, full_time TEXT, title TEXT, content TEXT, 
            score INTEGER, sentiment TEXT, category TEXT, summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, full_time, content) 
        )
    ''')
    conn.commit()
    conn.close()
    print(f"🏠 数据库已就绪: {DB_NAME}")

# 🌟 修改点 3：确保 save_to_db 使用正确的 DB_NAME
def save_to_db(new_data):
    if not new_data: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    insert_sql = '''
        INSERT OR IGNORE INTO reviews 
        (source, date, full_time, title, content, score, sentiment, category, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    data_tuples = [
        (
            item.get('来源'), item.get('日期'), item.get('具体时间'),
            item.get('标题'), item.get('内容'), item.get('评分'),
            item.get('情感倾向'), item.get('问题分类'), item.get('一句话总结')
        ) for item in new_data
    ]
    
    try:
        cursor.executemany(insert_sql, data_tuples)
        conn.commit()
        print(f"💾 成功同步 {len(new_data)} 条数据至数据库（自动跳过重复记录）。")
    except Exception as e:
        print(f"❌ 数据库写入失败: {e}")
    finally:
        conn.close()

# 👇 直接在文件最底部加上这两行
print("正在加载数据库模块...")
init_db()