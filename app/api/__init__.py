# Import the different routers from their respective modules
# from .authentication import router as auth_router
from .email import app as email_router
from .recipes import app as recipes_router
from .users import app as users_router

# Optionally, you can import and organize other components like models or utilities
# from .models import Model1, Model2
# from .utils import some_function

# Optionally, you can create an alias for your routers to have cleaner imports in other parts of the code
# For example:
# auth_router = authentication.router

# You can also expose the routers under a specific namespace if needed
# For example:
# app.include_router(auth_router, prefix="/auth")

# List of routers to be included in the main FastAPI app
__all__ = ["email_router", "recipes_router", "users_router"]
