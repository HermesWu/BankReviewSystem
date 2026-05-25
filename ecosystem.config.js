module.exports = {
  apps : [
    {
      name: "app_api",
      script: "/root/AppAgent/venv/bin/python",
      cwd: "/root/AppAgent/BankReviewSystem",
      args: "-m uvicorn api:app --host 0.0.0.0 --port 8000",
      autorestart: true,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        "PYTHONUNBUFFERED": "1"
      }
    },
    {
      name: "app_web",
      // ✨ 核心优化点：强制用 python 解释器启动
      script: "/root/AppAgent/venv/bin/python",
      cwd: "/root/AppAgent/BankReviewSystem",
      // ✨ 核心优化点：改用 python -m streamlit 方式运行，永不报错
      args: "-m streamlit run app_web.py",
      autorestart: true,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss"
    }
  ]
};
