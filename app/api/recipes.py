from fastapi import APIRouter, Depends, Form, HTTPException,  File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from app.api.users import get_current_user
from app.models.models import RecipeDetails, RecipeReview, Notification
from bson import ObjectId
from app.db.connection import db
import shutil
import os
import uuid
from datetime import datetime
from typing import Optional
from pymongo.errors import OperationFailure
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pymongo import MongoClient
from typing import List


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

        user = db.users.find_one({"cust_id": recipe["userId"]})
        if user:
            recipe["username"] = user.get("cust_username")
        else:
            recipe["username"] = " "

        # Fetch total likes for each recipe
        likes_count = db.likes.count_documents(
            {"recipe_id": recipe["_id"], "status": 1})
        recipe["total_likes"] = likes_count

    print(recipes_list)

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
    for recipe in recipes:
        recipe["_id"] = str(recipe["_id"])

        user = db.users.find_one({"cust_id": recipe["userId"]})
        if user:
            recipe["username"] = user.get("cust_username")

        # Fetch total likes for each recipe
        likes_count = db.likes.count_documents(
            {"recipe_id": recipe["_id"], "status": 1})
        recipe["total_likes"] = likes_count

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
        for recipe in recipes:
            recipe["_id"] = str(recipe["_id"])

            user = db.users.find_one({"cust_id": recipe["userId"]})
            if user:
                recipe["username"] = user.get("cust_username")

        # Fetch total likes for each recipe
            likes_count = db.likes.count_documents(
                {"recipe_id": recipe["_id"], "status": 1})
            recipe["total_likes"] = likes_count

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
            print("yes")
            return {"status": "yes"}
        else:
            print("yes")
            return {"status": "no"}


@app.post("/postreview/")
async def post_review(review: RecipeReview):
    review_data = review.dict()
    review_data['timestamp'] = datetime.utcnow()
    # Convert string to ObjectId for MongoDB operation

    db.reviews.insert_one(review_data)

    # Fetch the recipe title and owner's ID
    recipe = db.recipes.find_one({"_id": review.recipe_id})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    owner_id = recipe['userId']  # This should be the recipe owner's ID
    title = recipe['title']
    id = recipe['_id']

    # Create the notification for the recipe owner
    notification_data = {
        "recipient_id": owner_id,
        "message": f"Your recipe '{id}' name '{title}' was reviewed by user {review.user_id}.",
        "recipe_id": review.recipe_id,
        "read": False,
        "timestamp": datetime.utcnow()
    }
    # Insert the notification into the database
    db.notifications.insert_one(notification_data)

    return {"message": "Review posted successfully", "review_id": str(review_data['recipe_id'])}


@app.get("/getreviews/{recipe_id}/")
async def get_reviews(recipe_id: str):
    reviews = list(db.reviews.find({"recipe_id": recipe_id}))

    for review in reviews:
        # Assuming 'timestamp' is a datetime object, format it to a date string.
        review['timestamp'] = review['timestamp'].strftime('%Y-%m-%d')
        review['_id'] = str(review['_id'])  # Convert ObjectId to str

        # Fetch user information using user_id from the 'users' collection
        user_id = review.get('user_id')
        print("hello?", user_id)
        user_info = db.users.find_one({"cust_id": user_id})
        if user_info:
            # Assuming the username is stored in the 'username' field
            print("name???", user_info['cust_username'])
            review['username'] = user_info.get('cust_username')

    reviews.reverse()
    return {"reviews": reviews}


# notification

@app.get("/notifications/{user_id}")
async def get_notifications(user_id: str):
    # Ensure that user_id is valid and retrieve notifications
    notifications = list(db.notifications.find({"recipient_id": user_id}))

    # Convert all ObjectIds to strings for JSON serialization
    for notification in notifications:
        notification['_id'] = str(notification['_id'])
        notification['timestamp'] = notification['timestamp'].isoformat()
        # Ensure all ObjectIds in 'recipe_id' are converted to strings if they are not already
        if isinstance(notification.get('recipe_id'), ObjectId):
            notification['recipe_id'] = str(notification['recipe_id'])

    return notifications


@app.patch("/notifications/{notification_id}/read")
async def mark_notification_as_read(notification_id: str):
    # Convert string to ObjectId for MongoDB operation
    result = db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read": True}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification marked as read"}


# Search

@app.on_event("startup")
async def startup_event():

    # Create text indexes, if they don't exist already
    try:
        db.recipes.create_index([
            ('title', 'text'),
            ('cuisine', 'text'),
            ('tags', 'text')
            # ('ingredients.name', 'text')
        ])
        print("Text indexes created.")
    except OperationFailure as e:
        print("An error occurred while creating indexes:", e)


@app.get("/search/")
def search(query: str,  user_data: dict = Depends(get_current_user)):
    if not query:
        return {"results": []}

    # Perform a text search on the 'recipes' collection using the provided 'query'
    recipes_cursor = db.recipes.find({"$text": {"$search": query}})

    # Convert the cursor to a list
    recipes_list = []
    for recipe in recipes_cursor:
        recipe_id = str(recipe['_id'])  # Convert ObjectId to string
        print(f"Recipe ID: {recipe_id}")  # Print the ID
        recipe['_id'] = recipe_id

        likes_count = db.likes.count_documents(
            {"recipe_id": recipe_id, "status": 1})
        recipe["total_likes"] = likes_count

        recipes_list.append(recipe)

    response = {"results": recipes_list}
    return response

    # Recommendation Trial Start


@app.get("/recommendations/")
async def get_top_liked_recipes(
    user_data: dict = Depends(get_current_user)
):
    # Get user's liked and bookmarked recipe ids
    user_id = user_data["cust_id"]
    liked_recipe_ids = get_user_liked_recipe_ids(user_id)
    bookmarked_recipe_ids = get_user_bookmarked_recipe_ids(user_id)

    # Find the 3 most common recipe ids from likes and bookmarks
    common_recipe_ids = find_most_common_recipe_ids(
        liked_recipe_ids, bookmarked_recipe_ids)
    print("Common Recipe Ids: ", common_recipe_ids)

    # Get cuisine and difficulty for these recipe ids
    cuisines, difficulties = get_cuisine_and_difficulty(common_recipe_ids)
    print("Cuisines: ", cuisines)
    print("Difficulties: ", difficulties)

    # Filter recipes based on matching cuisine or difficulty
    filtered_recipes = filter_recipes_by_cuisine_or_difficulty(
        cuisines, difficulties)
    print("\nFiltered Recipes:")
    for recipe in filtered_recipes:
        print(recipe.get("title", "No Title"))

    # Count total likes for filtered recipes
    recipes_with_likes = count_total_likes(filtered_recipes)
    print("\nRecipes With Likes:")
    for recipe in recipes_with_likes:
        print(recipe.get("title", "No Title"))

    # Sort recipes by total likes and get the top 5
    top_liked_recipes = get_top_5_recipes(recipes_with_likes)
    print("\nTop 5:")
    for recipe in top_liked_recipes:
        print(recipe.get("title", "No Title"))

    # Fetch additional details for the top-liked recipes
    detailed_top_liked_recipes = fetch_detailed_recipes_info(top_liked_recipes)
    print("\nDetails:")
    for recipe in detailed_top_liked_recipes:
        print(recipe.get("title", "No Title"))

    for recipe in detailed_top_liked_recipes:
        recipe["_id"] = str(recipe["_id"])

        # Fetch total likes for each recipe
        likes_count = db.likes.count_documents(
            {"recipe_id": recipe["_id"], "status": 1})
        recipe["total_likes"] = likes_count

    print("\nMore Details:")
    for recipe in detailed_top_liked_recipes:
        print(recipe.get("title", "No Title"))
        user = db.users.find_one({"cust_id": recipe["userId"]})
        if user:
            recipe["username"] = user.get("cust_username")
        else:
            recipe["username"] = " "
    return {"recipes": detailed_top_liked_recipes}


def fetch_detailed_recipes_info(recipes: List[dict]):
    detailed_recipes = []
    for recipe in recipes:
        recipe_id = recipe["_id"]
        detailed_recipe = db.recipes.find_one({"_id": recipe_id})

        if detailed_recipe:
            detailed_recipe["_id"] = str(detailed_recipe["_id"])
            likes_count = db.likes.count_documents(
                {"_id": recipe_id, "status": 1})
            detailed_recipe["total_likes"] = likes_count

            detailed_recipes.append(detailed_recipe)

    return detailed_recipes


def get_user_liked_recipe_ids(user_id: str):
    likes_cursor = db.likes.find({"cust_id": user_id, "status": 1})
    return [like["recipe_id"] for like in likes_cursor]


def get_user_bookmarked_recipe_ids(user_id: str):
    bookmarks_cursor = db.bookmarks.find({"cust_id": user_id, "status": 1})
    return [bookmark["recipe_id"] for bookmark in bookmarks_cursor]


def find_most_common_recipe_ids(liked_recipe_ids: List[str], bookmarked_recipe_ids: List[str]):
    all_recipe_ids = liked_recipe_ids + bookmarked_recipe_ids
    return sorted(set(all_recipe_ids), key=lambda x: all_recipe_ids.count(x), reverse=True)[:3]


def get_cuisine_and_difficulty(recipe_ids: List[str]):
    cuisines = []
    difficulties = []
    for recipe_id in recipe_ids:
        recipe = db.recipes.find_one({"_id": recipe_id})
        if recipe:
            cuisines.append(recipe["cuisine"])
            difficulties.append(recipe["difficulty"])
    return cuisines, difficulties


def filter_recipes_by_cuisine_or_difficulty(cuisines: List[str], difficulties: List[str]):
    filtered_recipes = []
    added_recipe_ids = set()

    for cuisine in cuisines:
        recipes = db.recipes.find({"cuisine": cuisine})
        for recipe in recipes:
            if recipe["_id"] not in added_recipe_ids:
                recipe["_id"] = str(recipe["_id"])
                filtered_recipes.append(recipe)
                added_recipe_ids.add(recipe["_id"])

    for difficulty in difficulties:
        recipes = db.recipes.find({"difficulty": difficulty})
        for recipe in recipes:
            if recipe["_id"] not in added_recipe_ids:
                recipe["_id"] = str(recipe["_id"])
                filtered_recipes.append(recipe)
                added_recipe_ids.add(recipe["_id"])

    return filtered_recipes


def count_total_likes(recipes: List[dict]):
    recipes_with_likes = []
    for recipe in recipes:
        likes_count = db.likes.count_documents(
            {"recipe_id": recipe["_id"], "status": 1})
        recipe["total_likes"] = likes_count
        recipes_with_likes.append(recipe)
    return recipes_with_likes


def get_top_5_recipes(recipes_with_likes: List[dict]):
    return sorted(recipes_with_likes, key=lambda x: x["total_likes"], reverse=True)[:5]

    # Recommendation Trial End
