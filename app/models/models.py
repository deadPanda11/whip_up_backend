from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class UserIn(BaseModel):
    username: str
    email: str
    password: str
    verified: int = 0
    imageUrl: str = ""
    bio: str = ""


class VerificationToken(BaseModel):
    user_id: str
    token: str


class Email(BaseModel):
    email: str


class resetToken(BaseModel):
    email: str
    token: str


class UserLogin(BaseModel):
    email: str
    password: str


class resetPass(BaseModel):
    email: str
    newPassword: str
    otp: str


class UserUpdate(BaseModel):
    username: Optional[str]
    imageUrl: str
    bio: Optional[str]


class RecipeIngredient(BaseModel):
    name: str
    quantity: str


class RecipeStep(BaseModel):
    description: str


class RecipeDetails(BaseModel):
    userId: str
    title: str
    servings: int
    difficulty: str
    cookTime: str
    cuisine: str
    tags: List[str]
    ingredients: List[RecipeIngredient]
    steps: List[RecipeStep]
    imageUrl: str
   


class Bookmarks(BaseModel):
    cust_id: str
    recipe_id: str
    status: int


class Likes(BaseModel):
    cust_id: str
    recipe_id: str
    status: int


class Notification(BaseModel):
    
    recipient_id: str
    message: str
    recipe_id: str
    read: bool = False
    timestamp: datetime = datetime.utcnow()


# # REVIEWS
    
class RecipeReview(BaseModel):
    recipe_id: str
    user_id: str
    username: str = ''
    comment: str
    rating: float 
    

