from fastapi import APIRouter, Depends, Form, HTTPException,  File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from app.api.users import get_current_user
from app.models.models import RecipeDetails
from bson import ObjectId
from app.db.connection import db
import shutil
import os
import uuid


app = APIRouter()


@app.post("/addrecipe/")
async def add_recipe(recipe: RecipeDetails):
    recipe_data = {
        "userId": recipe.userId,
        "title": recipe.title,
        "servings": recipe.servings,
        "difficulty": recipe.difficulty,
        "cookTime": recipe.cookTime,
        "cuisine": recipe.cuisine,
        "tags": recipe.tags,
        "ingredients": [ingredient.dict() for ingredient in recipe.ingredients],
        "steps": [step.dict() for step in recipe.steps],
        "imageUrl": recipe.imageUrl
    }

    # Convert ObjectIds to str for JSON serialization
    recipe_data["_id"] = str(ObjectId())

    db.recipes.insert_one(recipe_data)
    return {"message": "Recipe added successfully", "recipe": recipe_data}


uploads_folder = "uploads"


@app.post("/upload-recipe-image/")
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
        recipes_folder = os.path.join(uploads_folder, "recipes")
        if not os.path.exists(recipes_folder):
            os.makedirs(recipes_folder)

        # Generate a unique filename for the uploaded image
        file_path = os.path.join(
            recipes_folder, f"recipe_image_{str(uuid.uuid4())}.jpg")

        # Save the uploaded file
        with open(file_path, "wb") as image_file:
            shutil.copyfileobj(image.file, image_file)

        file_path = file_path.replace("\\", "/")

        return JSONResponse(
            content={"message": "Image uploaded successfully",
                     "imageUrl": file_path}
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Internal Server Error: {str(e)}"}, status_code=500
        )


recipes_folder = 'uploads/recipes'

# Fetching Recipes


@app.get("/getrecipes/")
async def get_all_recipes(user_data: dict = Depends(get_current_user)):
    recipes = db.recipes.find()

    # Convert the recipes from Cursor type to a list of dictionaries
    recipes_list = [recipe for recipe in recipes]

    # Convert ObjectIds to string since they're not JSON serializable
    for recipe in recipes_list:
        recipe["_id"] = str(recipe["_id"])

    return {"recipes": recipes_list}


@app.get("/recipe-image/{file_path:path}")
async def recipe_image(file_path: str):
    file_name = os.path.basename(file_path)
    full_path = os.path.join(recipes_folder, file_name)

    if os.path.isfile(full_path):
        return FileResponse(full_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")

# Get Each Recipe


@app.get("/getrecipe/{recipe_id}")
async def get_recipe_by_id(recipe_id: str, user_data: dict = Depends(get_current_user)):
    # Fetch the recipe with the given ID
    recipe = db.recipes.find_one({"_id": recipe_id})

    # If recipe not found, raise an HTTP exception with a 404 status code
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return {"recipe": recipe}


@app.get("/getmyrecipes/")
async def get_my_recipes(user_data: dict = Depends(get_current_user)):

    userId = user_data.get("cust_id")

    recipes = list(db.recipes.find({"userId": userId}))
    print(recipes)

    return {"recipes": recipes}


@app.post("/bookmark/{user_id}/{recipe_id}/")
async def change_bookmarks(user_id: str, recipe_id: str):
    bookmark = db.bookmarks.find_one(
        {'cust_id': user_id, 'recipe_id': recipe_id})
    if not bookmark:
        bookmark_data = {
            "cust_id": user_id,
            "recipe_id": recipe_id,
            "status": 1
        }
        db.bookmarks.insert_one(bookmark_data)
        return {"status": "bookmarked"}

    else:
        if (bookmark["status"] == 1):
            db.bookmarks.update_one(
                {"cust_id": user_id, "recipe_id": recipe_id},
                {"$set": {"status": 0}}
            )
            return {"status": "unbookmarked"}
        else:
            db.bookmarks.update_one(
                {"cust_id": user_id, "recipe_id": recipe_id},
                {"$set": {"status": 1}}
            )
            return {"status": "bookmarked"}


@app.get("/getbookmark/{user_id}/{recipe_id}/")
async def get_bookmarks(user_id: str, recipe_id: str):
    bookmark = db.bookmarks.find_one(
        {'cust_id': user_id, 'recipe_id': recipe_id})
    if not bookmark:
        print("no")
        return {"status": "no"}
    else:
        if (bookmark["status"] == 1):
            return {"status": "yes"}
        else:
            return {"status": "no"}


@app.get("/getbookmarkedrecipes/")
async def get_bookmarked_recipes(user_data: dict = Depends(get_current_user)):
    bookmarks = db.bookmarks.find(
        {'cust_id': user_data.get("cust_id"), 'status': 1})
    if not bookmarks:
        return {"status": "no bookmarks"}

    else:
        recipe_ids = [bookmark["recipe_id"] for bookmark in bookmarks]
        # Assuming you're using MongoDB
        recipes = list(db.recipes.find({"_id": {"$in": recipe_ids}}))
        return {"recipes": recipes}


@app.post("/like/{user_id}/{recipe_id}/")
async def change_likes(user_id: str, recipe_id: str):
    like = db.likes.find_one(
        {'cust_id': user_id, 'recipe_id': recipe_id})
    if not like:
        like_data = {
            "cust_id": user_id,
            "recipe_id": recipe_id,
            "status": 1
        }
        db.likes.insert_one(like_data)
        return {"status": "liked"}

    else:
        if (like["status"] == 1):
            db.likes.update_one(
                {"cust_id": user_id, "recipe_id": recipe_id},
                {"$set": {"status": 0}}
            )
            return {"status": "unliked"}
        else:
            db.likes.update_one(
                {"cust_id": user_id, "recipe_id": recipe_id},
                {"$set": {"status": 1}}
            )
            return {"status": "unliked"}


@app.get("/getlike/{user_id}/{recipe_id}/")
async def get_likes(user_id: str, recipe_id: str):
    like = db.likes.find_one(
        {'cust_id': user_id, 'recipe_id': recipe_id})
    if not like:
        print("no")
        return {"status": "no"}
    else:
        if (like["status"] == 1):
            return {"status": "yes"}
        else:
            return {"status": "no"}
