import sqlite3
import os

# 数据库存储路径
DB_DIR = "data"
DB_NAME = os.path.join(DB_DIR, "app_reviews.db")

def init_db():
    """初始化数据库，创建【不可变归档表】与【可修改工作表】"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ==========================================
    # 🛡️ 1. 创建防篡改归档表 (reviews_archive)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, date TEXT, full_time TEXT, title TEXT, content TEXT, 
            score INTEGER, sentiment TEXT, category TEXT, summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, full_time, content) 
        )
    ''')
    
    # 给归档表上两把物理锁
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS prevent_update_archive
        BEFORE UPDATE ON reviews_archive
        BEGIN
            SELECT RAISE(ABORT, '⛔ 底层安全拦截：归档表 (reviews_archive) 绝对禁止修改！');
        END;
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS prevent_delete_archive
        BEFORE DELETE ON reviews_archive
        BEGIN
            SELECT RAISE(ABORT, '⛔ 底层安全拦截：归档表 (reviews_archive) 绝对禁止删除！');
        END;
    ''')

    # ==========================================
    # 📝 2. 创建可操作工作表 (reviews_todo)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews_todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, date TEXT, full_time TEXT, title TEXT, content TEXT, 
            score INTEGER, sentiment TEXT, category TEXT, summary TEXT,
            
            -- 🌟 这里是工作表专属的“办公字段”
            status TEXT DEFAULT '待处理',      -- 处理状态
            assignee TEXT DEFAULT '未分配',   -- 负责人
            remark TEXT,                      -- 人工备注
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, full_time, content) 
        )
    ''')

    conn.commit()
    conn.close()
    print(f"🏠 数据库已就绪，已挂载【安全归档表】与【协同工作表】: {DB_NAME}")

def save_to_db(new_data):
    """将数据同时双写入两张表"""
    if not new_data:
        return
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 给两张表准备插入SQL (工作表省略状态、备注等字段，让其走默认值)
    insert_sql_archive = '''
        INSERT OR IGNORE INTO reviews_archive 
        (source, date, full_time, title, content, score, sentiment, category, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    insert_sql_todo = '''
        INSERT OR IGNORE INTO reviews_todo 
        (source, date, full_time, title, content, score, sentiment, category, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    # 组装数据元组
    data_tuples = [
        (
            item.get('来源'), item.get('日期'), item.get('具体时间'),
            item.get('标题'), item.get('内容'), item.get('评分'),
            item.get('情感倾向'), item.get('问题分类'), item.get('一句话总结')
        ) for item in new_data
    ]
    
    try:
        # 🌟 核心：双写模式！一份锁进保险箱，一份发到办公桌
        cursor.executemany(insert_sql_archive, data_tuples)
        cursor.executemany(insert_sql_todo, data_tuples)
        conn.commit()
        print(f"💾 成功双写同步 {len(new_data)} 条数据至【归档表】与【工作表】。")
    except Exception as e:
        print(f"❌ 数据库双写失败: {e}")
    finally:
        conn.close()

# 自动初始化触发点
print("正在加载数据库模块...")
init_db()