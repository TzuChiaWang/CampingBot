from werkzeug.security import generate_password_hash
from models import User

def create_user():
    print("=== 創建新用戶 ===")
    username = input("請輸入用戶名: ")
    password = input("請輸入密碼: ")
    
    # 生成密碼雜湊
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
    # 創建用戶
    if User.create(username, hashed_password):
        print(f"\n用戶 '{username}' 創建成功！")
        print(f"用戶名: {username}")
        print(f"密碼雜湊: {hashed_password}")
    else:
        print(f"\n錯誤：用戶 '{username}' 已存在。")

if __name__ == "__main__":
    create_user()
