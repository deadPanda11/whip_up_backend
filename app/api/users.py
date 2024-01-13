from fastapi import APIRouter, Form, HTTPException, status, Depends, Cookie, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from connection import db  # Assuming your connection is set up in connection.py
from app.models.models import UserIn, UserUpdate, VerificationToken, resetPass, Email, UserLogin
from passlib.context import CryptContext
from bson import ObjectId
import random
import string
from app.api.email import send_email
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import shutil
import os
import uuid

# Set up password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = APIRouter()
security = HTTPBearer()

uploads_folder = "uploads"
profile_pictures_folder = os.path.join(uploads_folder, "profile_pictures")

# Create the folders if they don't exist
os.makedirs(profile_pictures_folder, exist_ok=True)


@app.post("/signup/")
async def addUser(user: UserIn):
    user = user.dict()  # Convert Pydantic model to dictionary

    # Hash the password
    hashed_password = pwd_context.hash(user["password"])

    # Check if an email exists from the collection of users
    existing_user = db.users.find_one({
        "cust_email": user["email"],
        "verified": 1
    })

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Customer Exists")

    # Create user data
    data = {
        "cust_id": str(ObjectId()),
        "cust_username": user["username"],
        "cust_email": user["email"],
        "cust_pass": hashed_password,
        "verified": 0,
        "imageUrl": "",
        "bio": "I love cooking!",
    }

    otp = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Save the token
    token_data = {
        "user_id": data["cust_id"],
        "token": otp
    }
    db.verificationtokens.insert_one(token_data)

    # If the email doesn't exist, create the user
    db.users.insert_one(data)
    await send_email(to_email=user["email"], subject="Welcome to WhipUp",
                     message=f"Hello! Welcome to WhipUp. Your OTP is: {otp}")

    return {"message": "User Created", "userId": data['cust_id']}


@app.post("/verify-otp/")
async def verifyOtp(verification_data: VerificationToken):

    verification_token = db.verificationtokens.find_one({
        "user_id": verification_data.user_id,
        "token": verification_data.token
    })

    if verification_token is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid OTP"})

    result = db.users.update_one(
        {"cust_id": verification_data.user_id},
        {"$set": {"verified": 1}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=500, detail="Failed to update user verification status")

    return {"message": "OTP verified successfully"}


@app.post("/send-otp/")
async def sendOtp(email: Email):
    try:
        emaill = email.email

        existing_user = db.users.find_one({'cust_email': emaill})

        if not existing_user:
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": "Customer Does Not Exist"})

        print("Here")
        otp = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=6))

        subject = "Your OTP for password reset"
        message = f"Your OTP is: {otp}"

        await send_email(emaill, subject, message)

        token_data = {
            "email": emaill,
            "token": otp
        }
        db.resetTokens.insert_one(token_data)

        return {"message": "OTP sent successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


SECRET_KEY = "1946a8e113ddc02ada2a8414bd138012ff3b2c3d0fe9614d9821bb2f28661dd7"
ALGORITHM = "HS256"


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    try:
        print("in decode")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload['cust_email'])
        return payload['cust_email']
    except JWTError:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    print(token)
    print("in get user")
    # Assuming you have a decode_token function
    cust_email = decode_token(token)
    print(cust_email)

    user_data = db.users.find_one({"cust_email": cust_email, "verified": 1})

    if user_data:
        return user_data

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@app.post("/login/")
async def login(user: UserLogin):
    user_data = db.users.find_one({
        'cust_email': user.email,
        'verified': 1
    })
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No verified account with this email.")
    if not pwd_context.verify(user.password, user_data["cust_pass"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")

    access_token = create_access_token({"cust_email": user_data["cust_email"]})
    return {"access_token": access_token, "token_type": "bearer", "message": "Login Successful", "email": user.email, "user_id": user_data["cust_id"], "username": user_data["cust_username"], "imageUrl": user_data["imageUrl"]}


uploads_folder = "uploads"

@app.post("/upload-image/")
async def upload_user_image(
    user_email: str = Form(...),
    image: UploadFile = File(...),
):
    try:
        print("Received User Email:", user_email)
        print("Received Image File:", image.filename)

        # Ensure the uploads folder exists
        if not os.path.exists(uploads_folder):
            os.makedirs(uploads_folder)

        # Ensure the profile_pictures folder exists within uploads
        profile_pictures_folder = os.path.join(uploads_folder, "profile_pictures")
        if not os.path.exists(profile_pictures_folder):
            os.makedirs(profile_pictures_folder)

        # Generate a unique filename for the uploaded image
        file_path = os.path.join(profile_pictures_folder, f"user_image_{str(uuid.uuid4())}.jpg")

        # Save the uploaded file
        with open(file_path, "wb") as image_file:
            shutil.copyfileobj(image.file, image_file)

        file_path = file_path.replace("\\", "/")

        # Update the user's image URL in the database
        # Replace this with your actual MongoDB update logic
        db.users.update_one(
            {"cust_email": user_email},
            {"$set": {"imageUrl": file_path}},
        )

        return JSONResponse(
            content={"message": "Image uploaded successfully", "imageUrl": file_path}
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Internal Server Error: {str(e)}"}, status_code=500
        )


profile_pictures_folder = 'uploads/profile_pictures'

@app.get("/profile-picture/{file_path:path}")
async def get_profile_picture(file_path: str):
    file_name = os.path.basename(file_path)
    full_path = os.path.join(profile_pictures_folder, file_name)
    
    if os.path.isfile(full_path):
        return FileResponse(full_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")
    

@app.post("/reset-password/")
async def reset_password(user: resetPass):
    try:
        email = user.email
        hashed_password = pwd_context.hash(user.newPassword)
        entered_otp = user.otp

        # Retrieve the stored OTP for the user's email
        stored_token = db.resetTokens.find_one({
            "email": email,
            "token": entered_otp
        })
        if not stored_token:
            raise HTTPException(status_code=401, detail="Invalid OTP")

        # Find the user by email and update the password
        result = db.users.update_one(
            {"cust_email": email},
            {"$set": {"cust_pass": hashed_password}}
        )

        if result.modified_count > 0:
            return {"message": "Password reset successful"}

        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/profile/{user_email}/")
async def get_user_profile(user_email: str):
    user_data = db.users.find_one({'cust_email': user_email})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return {"email": user_data["cust_email"], "username": user_data["cust_username"], "imageUrl": user_data["imageUrl"], "bio": user_data["bio"]}


@app.put("/profile/{user_email}/")
async def update_user_profile(user_email: str, user_update: UserUpdate):

    print(user_email)
    print(user_update.username)
    print(user_update.imageUrl)
    print(user_update.bio)
    # Parsing the new data from request body
    new_username = user_update.username
    new_imageUrl = user_update.imageUrl
    new_bio = user_update.bio

    # Check if the user exists in the database
    user_data = db.users.find_one({'cust_email': user_email})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Preparing the update data
    update_data = {}
    if new_username:
        update_data['cust_username'] = new_username
    if new_imageUrl:
        update_data['imageUrl'] = new_imageUrl
    if new_bio:
        update_data['bio'] = new_bio

    # Update the user data
    db.users.update_one({'cust_email': user_email}, {'$set': update_data})

    return {"message": "Profile updated successfully", "updated_data": update_data}
