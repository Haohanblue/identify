from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
import smtplib
from email.mime.text import MIMEText
import hashlib
import pandas as pd
import os
# 初始化数据库
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 定义用户模型
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    unique_link = Column(String, unique=True, index=True)
    identify = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)

# 创建表
Base.metadata.create_all(bind=engine)

# FastAPI应用
app = FastAPI()

class UserCreate(BaseModel):
    name: str
    phone: str
    email: str
    identify: bool = False
    email_sent: bool = False

class EmailSendRequest(BaseModel):
    user_ids: list[int]

@app.post("/users/")
def create_user(user: UserCreate):
    db = SessionLocal()
    unique_link = str(uuid.uuid4())

    db_user = User(
        name=user.name,
        phone=user.phone,
        email=user.email,
        unique_link=unique_link,
        identify=user.identify,
        email_sent=user.email_sent
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()
    return {"id": db_user.id, "unique_link": db_user.unique_link}

@app.post("/send-emails/")
def send_emails(email_request: EmailSendRequest):
    db = SessionLocal()
    users = db.query(User).filter(User.id.in_(email_request.user_ids)).all()
    
    if not users:
        db.close()
        raise HTTPException(status_code=404, detail="Users not found")

    smtp_server = "smtp.qq.com"
    smtp_port = 465
    smtp_user = "haohanblue@foxmail.com"
    smtp_password = "ojcxbljvpbxehijh"
    server_ip = "http://localhost:8001/confirm/"
    print(users)
    for user in users:
        print(user)
        message = f"你好，{user.name}！请点击以下链接确认你的面试邀请！{server_ip}{user.unique_link}"
        msg = MIMEText(message)
        msg['Subject'] = f'{user.name} 面试邀请确认'
        msg['From'] = smtp_user
        msg['To'] = user.email
        try:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            server.login(smtp_user, smtp_password)
            print(f"登录成功!")
            server.sendmail(smtp_user, user.email, msg.as_string())
            print(f"邮件发送成功!")
            user.email_sent = True
            db.commit()
        except Exception as e:
            db.close()
            raise HTTPException(status_code=500, detail=f"邮件发送失败: {e}")

    db.close()
    return {"detail": "邮件发送成功"}
@app.post("/import-users/")
def import_users(file_path: str):
    db = SessionLocal()
    full_path = os.path.join(os.getcwd(), file_path)
    try:
        # 读取Excel文件
        df = pd.read_excel(full_path,engine='openpyxl')
        print(df)
        # 遍历每一行并调用create_user
        for _, row in df.iterrows():
            user = UserCreate(
                name=str(row['姓名']),
                phone=str(row['手机']),
                email=str(row['邮箱']),
                identify=False,
                email_sent=False

            )
            create_user(user)  # 直接调用 create_user 函数

    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=f"导入用户失败: {e}")

    db.close()
    return {"detail": "用户导入成功"}

@app.get("/confirm/{unique_link}")
def confirm_user(unique_link: str):
    db = SessionLocal()
    user = db.query(User).filter(User.unique_link == unique_link).first()
    
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="用户未找到")

    user.identify = True
    db.commit()
    db.close()
    return {"detail": "用户确认成功"}

@app.get("/users/all")
#查询所有用户的信息
def read_users():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
